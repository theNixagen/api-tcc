import hashlib
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.raspberry_cliente import RaspberryCliente


def gerar_raspberry_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_raspberry_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def buscar_cliente_por_secret(db: Session, secret: str) -> RaspberryCliente | None:
    return db.scalar(
        select(RaspberryCliente).where(
            RaspberryCliente.chave_hash == hash_raspberry_secret(secret),
            RaspberryCliente.ativo.is_(True),
        )
    )


def criar_cliente(db: Session, nome: str, chave_hash: str) -> RaspberryCliente:
    validar_chave_hash(chave_hash)
    cliente = RaspberryCliente(nome=nome, chave_hash=chave_hash)
    db.add(cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Hash ja cadastrado")

    db.refresh(cliente)
    return cliente


def validar_chave_hash(chave_hash: str) -> None:
    try:
        int(chave_hash, 16)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hash invalido")

    if len(chave_hash) != 64:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hash invalido")
