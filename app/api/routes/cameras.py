from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.schemas.camera import (
    CameraCreateRequest,
    CameraResponse,
    CameraUpdateRequest,
)
from app.services.auth_service import UsuarioAutenticado
from app.services.camera_service import (
    criar_camera as criar_camera_service,
    editar_camera as editar_camera_service,
    excluir_camera as excluir_camera_service,
    listar_cameras as listar_cameras_service,
)

router = APIRouter(tags=["cameras"])


@router.post(
    "", response_model=CameraResponse, status_code=status.HTTP_201_CREATED
)
def criar_camera_rota(
    dados: CameraCreateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> CameraResponse:
    camera = criar_camera_service(db, dados.nome, dados.chave_hash, dados.direcao)
    return CameraResponse.model_validate(camera)


@router.get("", response_model=list[CameraResponse])
def listar_cameras(
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> list[CameraResponse]:
    return [CameraResponse.model_validate(camera) for camera in listar_cameras_service(db)]


@router.put("/{camera_id}", response_model=CameraResponse)
def editar_camera(
    camera_id: int,
    dados: CameraUpdateRequest,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> CameraResponse:
    camera = editar_camera_service(db, camera_id, dados.nome, dados.ativo, dados.direcao)
    return CameraResponse.model_validate(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("admin")),
) -> None:
    excluir_camera_service(db, camera_id)
