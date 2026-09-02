from datetime import datetime
from typing import Protocol, TypedDict


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


class AcessoDiarioParResponse(TypedDict):
    data_hora_entrada: datetime
    data_hora_saida: datetime | None


class VeiculoAcessosDiariosResponse(TypedDict):
    placa: str
    acessos: list[AcessoDiarioParResponse]
