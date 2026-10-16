from typing import Literal

from pydantic import BaseModel, Field


class UsuarioCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=1, max_length=200)
    papel: Literal["operador", "admin"]


class UsuarioUpdateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    papel: Literal["operador", "admin"]
    ativo: bool
    senha: str | None = Field(default=None, min_length=1, max_length=200)


class UsuarioResponse(BaseModel):
    id: int
    username: str
    papel: str
    ativo: bool
