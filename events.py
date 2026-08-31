from datetime import datetime
from typing import TYPE_CHECKING, Protocol, TypedDict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from models import Evento


class EventoLike(Protocol):
    id: int
    placa: str
    tipo_evento: str
    data_hora: datetime


class EventoResponse(TypedDict):
    id: int
    tipo_evento: str
    data_hora: datetime


class VeiculoEventosResponse(TypedDict):
    placa: str
    eventos: list[EventoResponse]


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


def registrar_evento(db: "Session", placa: str) -> "Evento":
    from sqlalchemy import select

    from models import Evento

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
