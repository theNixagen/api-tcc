from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.core.config import REPORT_TIMEZONE
from app.schemas.evento import (
    AcessoDiarioParResponse,
    EventoLike,
    VeiculoAcessosDiariosResponse,
    VeiculoEventosResponse,
)


def proximo_tipo_evento(ultimo_tipo_evento: str | None) -> str:
    return "saida" if ultimo_tipo_evento == "entrada" else "entrada"


def agrupar_eventos_por_veiculo(
    eventos: list[EventoLike],
) -> list[VeiculoEventosResponse]:
    veiculos: dict[str, VeiculoEventosResponse] = {}

    for evento in eventos:
        veiculo = veiculos.setdefault(
            evento.placa, {"placa": evento.placa, "eventos": []}
        )
        veiculo["eventos"].append(
            {
                "id": evento.id,
                "tipo_evento": evento.tipo_evento,
                "data_hora": evento.data_hora,
            }
        )

    return list(veiculos.values())


def registrar_evento(db: Session, placa: str, capturado_em: datetime | None = None) -> Evento:
    capturado_em = capturado_em or datetime.now(timezone.utc)
    ultimo_tipo_evento = db.scalars(
        select(Evento.tipo_evento)
        .where(Evento.placa == placa, Evento.data_hora <= capturado_em)
        .order_by(Evento.data_hora.desc(), Evento.id.desc())
        .limit(1)
    ).first()

    evento = Evento(placa=placa, tipo_evento=proximo_tipo_evento(ultimo_tipo_evento), data_hora=capturado_em)
    db.add(evento)
    db.flush()

    return evento


def listar_eventos_agrupados(db: Session, placa=None, inicio=None, fim=None, limit=100, offset=0):
    filtros = filtros_eventos(placa, inicio, fim)
    eventos = list(
        db.scalars(
            select(Evento).where(*filtros).order_by(Evento.data_hora.desc(), Evento.id.desc()).limit(limit).offset(offset)
        ).all()
    )
    return {
        "veiculos": agrupar_eventos_por_veiculo(sorted(eventos, key=lambda item: (item.placa, item.data_hora, item.id))),
        "total": db.scalar(select(func.count(Evento.id)).where(*filtros)), "limit": limit, "offset": offset,
    }


def exigir_fuso(valor):
    if valor is not None and (valor.tzinfo is None or valor.utcoffset() is None):
        raise HTTPException(422, "Datas devem incluir fuso horario")
    return valor.astimezone(timezone.utc) if valor is not None else None


def filtros_eventos(placa, inicio, fim):
    filtros = []
    if placa:
        filtros.append(Evento.placa == placa.upper())
    if inicio:
        filtros.append(Evento.data_hora >= exigir_fuso(inicio))
    if fim:
        filtros.append(Evento.data_hora <= exigir_fuso(fim))
    if inicio and fim and inicio > fim:
        raise HTTPException(422, "Periodo inicial maior que final")
    return filtros


def listar_acessos(db: Session, placa=None, entrada_inicio=None, entrada_fim=None, saida_inicio=None, saida_fim=None, limit=50, offset=0):
    janela = {"partition_by": Evento.placa, "order_by": (Evento.data_hora, Evento.id)}
    sequencia = select(
        Evento.id, Evento.placa, Evento.tipo_evento, Evento.data_hora.label("entrada"),
        func.lead(Evento.tipo_evento).over(**janela).label("proximo_tipo"),
        func.lead(Evento.data_hora).over(**janela).label("proxima_data"),
    )
    if placa:
        sequencia = sequencia.where(Evento.placa == placa.upper())
    sequencia = sequencia.subquery()
    pares = select(
        sequencia.c.id, sequencia.c.placa, sequencia.c.entrada.label("data_hora_entrada"),
        case((sequencia.c.proximo_tipo == "saida", sequencia.c.proxima_data)).label("data_hora_saida"),
    ).where(sequencia.c.tipo_evento == "entrada").subquery()
    filtros = []
    for campo, inicio, fim in [
        (pares.c.data_hora_entrada, entrada_inicio, entrada_fim),
        (pares.c.data_hora_saida, saida_inicio, saida_fim),
    ]:
        if inicio:
            filtros.append(campo >= exigir_fuso(inicio))
        if fim:
            filtros.append(campo <= exigir_fuso(fim))
        if inicio and fim and inicio > fim:
            raise HTTPException(422, "Periodo inicial maior que final")
    total = db.scalar(select(func.count()).select_from(pares).where(*filtros))
    itens = db.execute(select(pares).where(*filtros)
        .order_by(pares.c.data_hora_entrada.desc(), pares.c.id.desc()).limit(limit).offset(offset)).mappings().all()
    return {"itens": [dict(item) for item in itens], "total": total, "limit": limit, "offset": offset}


def gerar_acessos_diarios(
    eventos: list[EventoLike], data_relatorio: date
) -> list[VeiculoAcessosDiariosResponse]:
    veiculos: dict[str, VeiculoAcessosDiariosResponse] = {}
    abertos_por_placa: dict[str, AcessoDiarioParResponse] = {}

    for evento in eventos:
        if (
            evento.tipo_evento == "entrada"
            and evento.data_hora.date() == data_relatorio
        ):
            acesso: AcessoDiarioParResponse = {
                "data_hora_entrada": evento.data_hora,
                "data_hora_saida": None,
            }
            veiculo = veiculos.setdefault(
                evento.placa, {"placa": evento.placa, "acessos": []}
            )
            veiculo["acessos"].append(acesso)
            abertos_por_placa[evento.placa] = acesso
        elif evento.tipo_evento == "saida":
            acesso_aberto = abertos_por_placa.pop(evento.placa, None)
            if (
                acesso_aberto is not None
                and evento.data_hora > acesso_aberto["data_hora_entrada"]
            ):
                acesso_aberto["data_hora_saida"] = evento.data_hora

    return list(veiculos.values())


def relatorio_acessos_diarios(
    db: Session, data_relatorio: date, placa: str | None = None, limit=100, offset=0
):
    inicio = datetime.combine(data_relatorio, time.min, tzinfo=REPORT_TIMEZONE)
    fim = datetime.combine(data_relatorio + timedelta(days=1), time.min, tzinfo=REPORT_TIMEZONE) - timedelta(microseconds=1)
    acessos = listar_acessos(db, placa, inicio, fim, limit=limit, offset=offset)
    veiculos = {}
    for item in acessos["itens"]:
        veiculos.setdefault(item["placa"], []).append({
            "data_hora_entrada": item["data_hora_entrada"], "data_hora_saida": item["data_hora_saida"],
        })
    return {
        "data": data_relatorio,
        "fuso": REPORT_TIMEZONE.key,
        "veiculos": [{"placa": placa, "acessos": itens} for placa, itens in veiculos.items()],
        "total": acessos["total"], "limit": limit, "offset": offset,
    }
