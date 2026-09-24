from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import cliente_atual
from app.db.session import get_db
from app.models.cliente import Cliente
from app.services.alpr_service import processar_imagem

router = APIRouter(tags=["alpr"])


@router.post("/alpr")
async def alpr(
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: Cliente = Depends(cliente_atual),
) -> dict[str, Any]:
    return processar_imagem(db, await imagem.read())
