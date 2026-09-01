from collections.abc import Callable
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.raspberry_cliente import RaspberryCliente
from app.services.auth_service import (
    UsuarioAutenticado,
    decodificar_jwt,
    validar_access_token,
)
from app.services.raspberry_service import buscar_cliente_por_secret

bearer = HTTPBearer(auto_error=False)


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer),
    cache: Any = Depends(get_redis),
) -> UsuarioAutenticado:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente")

    return validar_access_token(cache, decodificar_jwt(credenciais.credentials))


def exigir_papeis(*papeis: str) -> Callable[[UsuarioAutenticado], UsuarioAutenticado]:
    def dependency(
        usuario: UsuarioAutenticado = Depends(usuario_atual),
    ) -> UsuarioAutenticado:
        if usuario.papel not in papeis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente")
        return usuario

    return dependency


def raspberry_atual(
    x_raspberry_secret: str | None = Header(default=None, alias="X-Raspberry-Secret"),
    db: Session = Depends(get_db),
) -> RaspberryCliente:
    if not x_raspberry_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave do Raspberry ausente")

    cliente = buscar_cliente_por_secret(db, x_raspberry_secret)
    if cliente is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave do Raspberry invalida")

    return cliente
