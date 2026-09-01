from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.schemas.usuario import UsuarioCreateRequest, UsuarioResponse
from app.services.auth_service import UsuarioAutenticado
from app.services.usuario_service import criar_usuario as criar_usuario_service

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    dados: UsuarioCreateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> UsuarioResponse:
    usuario = criar_usuario_service(db, dados.username, dados.senha, dados.papel)
    return UsuarioResponse(id=usuario.id, username=usuario.username, papel=usuario.papel)
