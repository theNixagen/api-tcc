from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
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
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("operador", "admin")),
) -> dict[str, Any]:
    return relatorio_acessos_diarios(db, data or date.today(), placa)
