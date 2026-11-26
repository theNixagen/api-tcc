from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DirecaoCamera = Literal["entrada", "saida"]


class CameraCreateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    chave_hash: str = Field(min_length=64, max_length=64)
    direcao: DirecaoCamera


class CameraUpdateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    ativo: bool
    direcao: DirecaoCamera | None = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    ativo: bool
    direcao: DirecaoCamera | None
