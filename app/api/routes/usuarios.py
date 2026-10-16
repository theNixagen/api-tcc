from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.schemas.usuario import (
    UsuarioCreateRequest,
    UsuarioResponse,
    UsuarioUpdateRequest,
)
from app.services.auth_service import UsuarioAutenticado
from app.services.usuario_service import (
    criar_usuario as criar_usuario_service,
    editar_usuario as editar_usuario_service,
    excluir_usuario as excluir_usuario_service,
    listar_usuarios as listar_usuarios_service,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    dados: UsuarioCreateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> UsuarioResponse:
    usuario = criar_usuario_service(db, dados.username, dados.senha, dados.papel)
    return UsuarioResponse(
        id=usuario.id,
        username=usuario.username,
        papel=usuario.papel,
        ativo=usuario.ativo,
    )


@router.get("", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> list[UsuarioResponse]:
    return [
        UsuarioResponse(
            id=usuario.id,
            username=usuario.username,
            papel=usuario.papel,
            ativo=usuario.ativo,
        )
        for usuario in listar_usuarios_service(db)
    ]


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def editar_usuario(
    usuario_id: int,
    dados: UsuarioUpdateRequest,
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> UsuarioResponse:
    if usuario_id == usuario_atual.id and (
        dados.papel != "admin" or not dados.ativo
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Nao e possivel remover o proprio acesso de administrador",
        )
    usuario = editar_usuario_service(
        db, usuario_id, dados.username, dados.papel, dados.ativo, dados.senha
    )
    return UsuarioResponse(
        id=usuario.id,
        username=usuario.username,
        papel=usuario.papel,
        ativo=usuario.ativo,
    )


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> None:
    if usuario_id == usuario_atual.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Nao e possivel excluir o proprio usuario",
        )
    excluir_usuario_service(db, usuario_id)
