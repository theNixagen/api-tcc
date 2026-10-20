from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.db.session import get_db
from app.services.auth_service import UsuarioAutenticado
from app.services.evento_service import listar_eventos_agrupados, listar_acessos

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.get("")
def listar_eventos(
    placa: str | None = Query(None, max_length=10), inicio: datetime | None = None, fim: datetime | None = None,
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("operador", "admin")),
) -> dict[str, Any]:
    return listar_eventos_agrupados(db, placa, inicio, fim, limit, offset)


@router.get("/acessos")
def acessos(
    placa: str | None = Query(None, max_length=10),
    entrada_inicio: datetime | None = None, entrada_fim: datetime | None = None,
    saida_inicio: datetime | None = None, saida_fim: datetime | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: UsuarioAutenticado = Depends(exigir_papeis("operador", "admin")),
):
    return listar_acessos(db, placa, entrada_inicio, entrada_fim, saida_inicio, saida_fim, limit, offset)
