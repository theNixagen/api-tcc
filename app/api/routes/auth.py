from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.services.auth_service import (
    autenticar_usuario,
    decodificar_jwt,
    emitir_tokens,
    revogar_token,
    validar_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    dados: LoginRequest,
    db: Session = Depends(get_db),
    cache: Any = Depends(get_redis),
) -> dict[str, str]:
    usuario = autenticar_usuario(db, dados.username, dados.senha)
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais invalidas")
    return emitir_tokens(usuario, cache)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    dados: RefreshRequest,
    db: Session = Depends(get_db),
    cache: Any = Depends(get_redis),
) -> dict[str, str]:
    payload = decodificar_jwt(dados.refresh_token)
    refresh_token_id = validar_refresh_token(cache, payload)

    try:
        usuario_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario invalido")

    revogar_token(cache, "refresh", refresh_token_id)
    return emitir_tokens(usuario, cache)


@router.post("/logout")
def logout(
    dados: RefreshRequest,
    cache: Any = Depends(get_redis),
) -> dict[str, str]:
    payload = decodificar_jwt(dados.refresh_token)
    refresh_token_id = payload.get("refresh_token_id") or payload.get("jti")
    if refresh_token_id:
        revogar_token(cache, "refresh", str(refresh_token_id))
    return {"detail": "logout realizado"}
