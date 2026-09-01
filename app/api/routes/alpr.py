from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import raspberry_atual
from app.db.session import get_db
from app.models.raspberry_cliente import RaspberryCliente
from app.services.alpr_service import processar_imagem

router = APIRouter(tags=["alpr"])


@router.post("/alpr")
async def alpr(
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: RaspberryCliente = Depends(raspberry_atual),
) -> dict[str, Any]:
    return processar_imagem(db, await imagem.read())
