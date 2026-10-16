from pydantic import BaseModel, Field


class ClienteCreateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    chave_hash: str = Field(min_length=64, max_length=64)


class ClienteUpdateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    ativo: bool


class ClienteResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
