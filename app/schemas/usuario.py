from pydantic import BaseModel


class UsuarioCreateRequest(BaseModel):
    username: str
    senha: str
    papel: str


class UsuarioResponse(BaseModel):
    id: int
    username: str
    papel: str
