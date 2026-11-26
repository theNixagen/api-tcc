import hashlib
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.camera import Camera


def gerar_camera_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_camera_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def buscar_camera_por_secret(db: Session, secret: str) -> Camera | None:
    return db.scalar(
        select(Camera).where(
            Camera.chave_hash == hash_camera_secret(secret),
            Camera.ativo.is_(True),
        )
    )


def criar_camera(db: Session, nome: str, chave_hash: str, direcao: str) -> Camera:
    validar_chave_hash(chave_hash)
    camera = Camera(nome=nome, chave_hash=chave_hash, direcao=direcao)
    db.add(camera)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Hash ja cadastrado")

    db.refresh(camera)
    return camera


def listar_cameras(db: Session) -> list[Camera]:
    return list(db.scalars(select(Camera).order_by(Camera.id)).all())


def editar_camera(
    db: Session, camera_id: int, nome: str, ativo: bool, direcao: str | None = None
) -> Camera:
    camera = buscar_camera(db, camera_id)
    camera.nome = nome
    camera.ativo = ativo
    if direcao is not None:
        camera.direcao = direcao
    db.commit()
    db.refresh(camera)
    return camera


def excluir_camera(db: Session, camera_id: int) -> None:
    db.delete(buscar_camera(db, camera_id))
    db.commit()


def buscar_camera(db: Session, camera_id: int) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Câmera não encontrada")
    return camera


def validar_chave_hash(chave_hash: str) -> None:
    try:
        int(chave_hash, 16)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hash invalido")

    if len(chave_hash) != 64:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hash invalido")
