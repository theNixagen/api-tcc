from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
