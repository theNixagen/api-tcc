from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LeituraAceitaResponse(BaseModel):
    id: int
    status: str


class LeituraFilaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_arquivo: str
    criado_em: datetime


class FilaStatusResponse(BaseModel):
    total: int
    pendentes: int
    concluidas: int
    erros: int
    processando: int = 0
    revisao: int = 0
    primeira_pendente: LeituraFilaResponse | None


class MetadadosLeituraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    evento_id: int | None
    placa: str
    texto_ocr: str
    confianca_deteccao: float
    confianca_ocr: float | None
    bbox: list[int]
    modelo: str
    imgsz: int
    resultado: str
    motivo: str | None
    criado_em: datetime


class LeituraResponse(BaseModel):
    id: int
    status: str
    nome_arquivo: str
    content_type: str | None
    tamanho_bytes: int
    criado_em: datetime
    finalizado_em: datetime | None
    duracao_ms: float | None
    erro: str | None
    detections: list[MetadadosLeituraResponse]
    capturado_em: datetime
    captura_informada: bool
    iniciado_em: datetime | None
    tentativas: int
    tentativas_limite: int
    proxima_tentativa_em: datetime | None
    resultado: str | None
    imagem_disponivel: bool


class RevisaoRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    acao: Literal["aceitar", "rejeitar"]
    placa: str | None = Field(default=None, max_length=20)
    tipo_evento: Literal["entrada", "saida"] | None = None
    motivo: str = Field(min_length=3, max_length=1000, pattern=r"\S")
