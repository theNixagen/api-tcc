from pydantic import BaseModel


class ClienteCreateRequest(BaseModel):
    nome: str
    chave_hash: str


class ClienteResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
