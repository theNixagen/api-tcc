from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from app.core.config import REPORT_TIMEZONE
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.services.auth_service import UsuarioAutenticado
from app.services.evento_service import relatorio_acessos_diarios

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


@router.get("/acessos-diarios")
def acessos_diarios(
    data: date | None = None,
    placa: str | None = None,
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("operador", "admin")),
) -> dict[str, Any]:
    return relatorio_acessos_diarios(db, data or datetime.now(REPORT_TIMEZONE).date(), placa, limit, offset)
