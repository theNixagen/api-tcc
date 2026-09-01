from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.schemas.raspberry import (
    RaspberryClienteCreateRequest,
    RaspberryClienteResponse,
)
from app.services.auth_service import UsuarioAutenticado
from app.services.raspberry_service import criar_cliente

router = APIRouter(prefix="/raspberry-clientes", tags=["raspberry-clientes"])


@router.post(
    "", response_model=RaspberryClienteResponse, status_code=status.HTTP_201_CREATED
)
def criar_raspberry_cliente(
    dados: RaspberryClienteCreateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> RaspberryClienteResponse:
    cliente = criar_cliente(db, dados.nome, dados.chave_hash)
    return RaspberryClienteResponse(
        id=cliente.id,
        nome=cliente.nome,
        ativo=cliente.ativo,
    )
