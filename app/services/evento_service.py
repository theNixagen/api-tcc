from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento import Evento
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


def registrar_evento(db: Session, placa: str) -> Evento:
    ultimo_tipo_evento = db.scalars(
        select(Evento.tipo_evento)
        .where(Evento.placa == placa)
        .order_by(Evento.data_hora.desc(), Evento.id.desc())
        .limit(1)
    ).first()

    evento = Evento(placa=placa, tipo_evento=proximo_tipo_evento(ultimo_tipo_evento))
    db.add(evento)
    db.flush()

    return evento


def listar_eventos_agrupados(db: Session) -> dict[str, list[VeiculoEventosResponse]]:
    eventos = list(
        db.scalars(
            select(Evento).order_by(Evento.placa, Evento.data_hora, Evento.id)
        ).all()
    )
    return {"veiculos": agrupar_eventos_por_veiculo(eventos)}


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
    db: Session, data_relatorio: date, placa: str | None = None
) -> dict[str, date | list[VeiculoAcessosDiariosResponse]]:
    inicio = datetime.combine(data_relatorio, time.min)
    filtros = [Evento.data_hora >= inicio]
    if placa:
        filtros.append(Evento.placa == placa.upper())

    eventos = list(
        db.scalars(
            select(Evento)
            .where(*filtros)
            .order_by(Evento.placa, Evento.data_hora, Evento.id)
        ).all()
    )
    return {
        "data": data_relatorio,
        "veiculos": gerar_acessos_diarios(eventos, data_relatorio),
    }
