from collections.abc import Callable
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.camera import Camera
from app.models.usuario import Usuario
from app.services.auth_service import (
    UsuarioAutenticado,
    decodificar_jwt,
    validar_access_token,
)
from app.services.camera_service import buscar_camera_por_secret

bearer = HTTPBearer(auto_error=False)


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer),
    cache: Any = Depends(get_redis),
    db: Session = Depends(get_db),
) -> UsuarioAutenticado:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente")

    autenticado = validar_access_token(cache, decodificar_jwt(credenciais.credentials))
    usuario = db.get(Usuario, autenticado.id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inativo")
    return UsuarioAutenticado(
        id=usuario.id,
        username=usuario.username,
        papel=usuario.papel,
    )


def exigir_papeis(*papeis: str) -> Callable[[UsuarioAutenticado], UsuarioAutenticado]:
    def dependency(
        usuario: UsuarioAutenticado = Depends(usuario_atual),
    ) -> UsuarioAutenticado:
        if usuario.papel not in papeis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente")
        return usuario

    return dependency


def camera_atual(
    x_camera_secret: str | None = Header(default=None, alias="X-Camera-Secret"),
    db: Session = Depends(get_db),
    x_cliente_secret: str | None = Header(
        default=None, alias="X-Cliente-Secret", include_in_schema=False
    ),
) -> Camera:
    secret = x_camera_secret if x_camera_secret is not None else x_cliente_secret
    if not secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave da câmera ausente")

    camera = buscar_camera_por_secret(db, secret)
    if camera is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave da câmera inválida")

    return camera
