from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.schemas.cliente import (
    ClienteCreateRequest,
    ClienteResponse,
    ClienteUpdateRequest,
)
from app.services.auth_service import UsuarioAutenticado
from app.services.cliente_service import (
    criar_cliente as criar_cliente_service,
    editar_cliente as editar_cliente_service,
    excluir_cliente as excluir_cliente_service,
    listar_clientes as listar_clientes_service,
)

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


@router.get("", response_model=list[ClienteResponse])
def listar_clientes(
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> list[ClienteResponse]:
    return [
        ClienteResponse(id=cliente.id, nome=cliente.nome, ativo=cliente.ativo)
        for cliente in listar_clientes_service(db)
    ]


@router.put("/{cliente_id}", response_model=ClienteResponse)
def editar_cliente(
    cliente_id: int,
    dados: ClienteUpdateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> ClienteResponse:
    cliente = editar_cliente_service(db, cliente_id, dados.nome, dados.ativo)
    return ClienteResponse(id=cliente.id, nome=cliente.nome, ativo=cliente.ativo)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> None:
    excluir_cliente_service(db, cliente_id)
