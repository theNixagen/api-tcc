from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.schemas.evento import EventoLike, VeiculoEventosResponse


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
