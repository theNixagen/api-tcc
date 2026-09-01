import base64
import hashlib
import hmac
import json
import secrets
from binascii import Error as BinasciiError
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import (
    ACCESS_TOKEN_MINUTES,
    JWT_ALGORITMO,
    JWT_SECRET,
    PAPEIS_VALIDOS,
    REFRESH_TOKEN_DAYS,
)
from app.models.usuario import Usuario

try:
    from redis.exceptions import RedisError
except ModuleNotFoundError:
    RedisError = Exception


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: int
    username: str
    papel: str


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _assinar(data: str) -> str:
    assinatura = hmac.new(JWT_SECRET.encode(), data.encode(), hashlib.sha256).digest()
    return _b64url_encode(assinatura)


def criar_jwt(payload: dict[str, Any], expires_delta: timedelta) -> str:
    header = {"alg": JWT_ALGORITMO, "typ": "JWT"}
    expira_em = agora_utc() + expires_delta
    dados = {**payload, "exp": int(expira_em.timestamp())}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(dados, separators=(",", ":")).encode())
    assinatura = _assinar(f"{header_b64}.{payload_b64}")
    return f"{header_b64}.{payload_b64}.{assinatura}"


def decodificar_jwt(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, assinatura = token.split(".")
        assinado = f"{header_b64}.{payload_b64}"
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except (BinasciiError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    if header.get("alg") != JWT_ALGORITMO or not hmac.compare_digest(
        _assinar(assinado), assinatura
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    if int(payload.get("exp", 0)) < int(agora_utc().timestamp()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")

    return payload


def hash_senha(senha: str) -> str:
    salt = secrets.token_bytes(16)
    iteracoes = 390_000
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, iteracoes)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(iteracoes),
            _b64url_encode(salt),
            _b64url_encode(digest),
        ]
    )


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, iteracoes, salt_b64, digest_b64 = senha_hash.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", senha.encode(), _b64url_decode(salt_b64), int(iteracoes)
        )
        return hmac.compare_digest(_b64url_encode(digest), digest_b64)
    except ValueError:
        return False


def _salvar_token(
    cache: Any, tipo: str, token_id: str, dados: dict[str, Any], ttl: int
) -> None:
    try:
        cache.setex(
            f"auth:{tipo}:{token_id}",
            ttl,
            json.dumps(dados, separators=(",", ":")),
        )
    except RedisError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Redis indisponivel")


def _token_existe(cache: Any, tipo: str, token_id: str) -> bool:
    try:
        return cache.exists(f"auth:{tipo}:{token_id}") == 1
    except RedisError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Redis indisponivel")


def revogar_token(cache: Any, tipo: str, token_id: str) -> None:
    try:
        cache.delete(f"auth:{tipo}:{token_id}")
    except RedisError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Redis indisponivel")


def criar_access_token(cache: Any, usuario: Usuario) -> str:
    token_id = secrets.token_urlsafe(24)
    payload = {
        "typ": "access",
        "sub": str(usuario.id),
        "username": usuario.username,
        "papel": usuario.papel,
        "token_id": token_id,
        "jti": token_id,
    }
    token = criar_jwt(payload, timedelta(minutes=ACCESS_TOKEN_MINUTES))
    _salvar_token(cache, "access", token_id, payload, ACCESS_TOKEN_MINUTES * 60)
    return token


def criar_refresh_token(cache: Any, usuario: Usuario) -> str:
    refresh_token_id = secrets.token_urlsafe(24)
    payload = {
        "typ": "refresh",
        "sub": str(usuario.id),
        "username": usuario.username,
        "papel": usuario.papel,
        "refresh_token_id": refresh_token_id,
        "jti": refresh_token_id,
    }
    token = criar_jwt(payload, timedelta(days=REFRESH_TOKEN_DAYS))
    _salvar_token(
        cache,
        "refresh",
        refresh_token_id,
        payload,
        REFRESH_TOKEN_DAYS * 24 * 60 * 60,
    )
    return token


def validar_access_token(cache: Any, payload: dict[str, Any]) -> UsuarioAutenticado:
    token_id = payload.get("token_id") or payload.get("jti")
    if payload.get("typ") != "access" or not token_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")
    if not _token_existe(cache, "access", token_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revogado")

    try:
        usuario_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    papel = payload.get("papel")
    if papel not in PAPEIS_VALIDOS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    return UsuarioAutenticado(
        id=usuario_id,
        username=str(payload.get("username", "")),
        papel=papel,
    )


def validar_refresh_token(cache: Any, payload: dict[str, Any]) -> str:
    refresh_token_id = payload.get("refresh_token_id") or payload.get("jti")
    if (
        payload.get("typ") != "refresh"
        or not refresh_token_id
        or not payload.get("sub")
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")
    if not _token_existe(cache, "refresh", refresh_token_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revogado")
    return refresh_token_id


def autenticar_usuario(db: Session, username: str, senha: str) -> Usuario | None:
    usuario = db.scalar(select(Usuario).where(Usuario.username == username))
    if (
        usuario is None
        or not usuario.ativo
        or not verificar_senha(senha, usuario.senha_hash)
    ):
        return None
    return usuario


def emitir_tokens(usuario: Usuario, cache: Any) -> dict[str, str]:
    return {
        "access_token": criar_access_token(cache, usuario),
        "refresh_token": criar_refresh_token(cache, usuario),
        "token_type": "bearer",
    }
