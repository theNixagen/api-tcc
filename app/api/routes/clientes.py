from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.schemas.cliente import (
    ClienteCreateRequest,
    ClienteResponse,
)
from app.services.auth_service import UsuarioAutenticado
from app.services.cliente_service import criar_cliente as criar_cliente_service

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post(
    "", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED
)
def criar_cliente_rota(
    dados: ClienteCreateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> ClienteResponse:
    cliente = criar_cliente_service(db, dados.nome, dados.chave_hash)
    return ClienteResponse(
        id=cliente.id,
        nome=cliente.nome,
        ativo=cliente.ativo,
    )
