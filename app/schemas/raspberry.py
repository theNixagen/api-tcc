from pydantic import BaseModel


class RaspberryClienteCreateRequest(BaseModel):
    nome: str
    chave_hash: str


class RaspberryClienteResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
