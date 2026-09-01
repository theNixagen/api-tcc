from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.services.auth_service import UsuarioAutenticado
from app.services.evento_service import listar_eventos_agrupados

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.get("")
def listar_eventos(
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("operador", "admin")),
) -> dict[str, Any]:
    return listar_eventos_agrupados(db)
