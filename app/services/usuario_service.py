from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import ADMIN_PASSWORD, ADMIN_USERNAME, PAPEIS_VALIDOS
from app.models.usuario import Usuario
from app.services.auth_service import hash_senha


def criar_admin_inicial(db: Session) -> None:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        return

    if db.scalar(select(Usuario).where(Usuario.username == ADMIN_USERNAME)) is None:
        db.add(
            Usuario(
                username=ADMIN_USERNAME,
                senha_hash=hash_senha(ADMIN_PASSWORD),
                papel="admin",
            )
        )
        db.commit()


def criar_usuario(db: Session, username: str, senha: str, papel: str) -> Usuario:
    if papel not in PAPEIS_VALIDOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Papel invalido")

    usuario = Usuario(username=username, senha_hash=hash_senha(senha), papel=papel)
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Usuario ja existe")

    db.refresh(usuario)
    return usuario
