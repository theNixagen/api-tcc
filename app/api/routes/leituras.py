from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import exigir_papeis
from app.api.routes.alpr import resposta_leitura, resumo_fila
from app.db.session import get_db
from app.models.leitura import Leitura, MetadadosLeitura, RevisaoLeitura
from app.schemas.leitura import LeituraResponse, RevisaoRequest
from app.services.auth_service import UsuarioAutenticado
from app.services.leitura_service import reprocessar, revisar_metadado, revisar_sem_deteccao

router = APIRouter(prefix="/leituras", tags=["leituras"], dependencies=[Depends(exigir_papeis("admin", "operador"))])


@router.get("")
def listar(
    status: Literal["pendente", "processando", "concluida", "erro"] | None = None,
    resultado: Literal["aceita", "revisao", "sem_placa", "rejeitada"] | None = None,
    placa: str | None = Query(default=None, max_length=10),
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    filtros = []
    if status:
        filtros.append(Leitura.status == status)
    if resultado:
        filtros.append(Leitura.resultado == resultado)
    if placa:
        filtros.append(Leitura.id.in_(select(MetadadosLeitura.leitura_id).where(MetadadosLeitura.placa == placa.upper())))
    total = db.scalar(select(func.count(Leitura.id)).where(*filtros))
    leituras = db.execute(select(
        Leitura.id, Leitura.nome_arquivo, Leitura.status, Leitura.resultado,
        Leitura.capturado_em, Leitura.criado_em, Leitura.iniciado_em,
        Leitura.tentativas, Leitura.erro,
    ).where(*filtros).order_by(Leitura.id.desc()).limit(limit).offset(offset)).mappings().all()
    return {"itens": [dict(item) for item in leituras], "total": total, "limit": limit, "offset": offset}


@router.get("/fila")
def fila(db: Session = Depends(get_db)):
    return resumo_fila(db)


@router.get("/{leitura_id}", response_model=LeituraResponse)
def detalhe(leitura_id: int, db: Session = Depends(get_db)):
    leitura = db.get(Leitura, leitura_id)
    if leitura is None:
        raise HTTPException(404, "Leitura nao encontrada")
    return resposta_leitura(db, leitura)


@router.get("/{leitura_id}/imagem")
def imagem(leitura_id: int, db: Session = Depends(get_db)):
    content = db.scalar(select(Leitura.imagem).where(Leitura.id == leitura_id))
    if content is None:
        raise HTTPException(404, "Imagem nao disponivel ou removida pela retencao")
    # Nao reproduz Content-Type enviado pelo cliente (poderia servir HTML ativo).
    mime = "application/octet-stream"
    if content.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        mime = "image/webp"
    return Response(content, media_type=mime, headers={
        "Content-Disposition": f'inline; filename="leitura_{leitura_id}.jpg"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
    })


@router.post("/{leitura_id}/reprocessar", status_code=202)
def reenviar(leitura_id: int, db: Session = Depends(get_db)):
    leitura = reprocessar(db, leitura_id)
    return {"id": leitura.id, "status": leitura.status}


@router.post("/deteccoes/{metadado_id}/revisar")
def revisar(
    metadado_id: int, dados: RevisaoRequest, db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(exigir_papeis("admin", "operador")),
):
    revisar_metadado(db, metadado_id, dados, usuario)
    return {"detail": "Revisao registrada"}


@router.post("/{leitura_id}/revisar")
def revisar_imagem(
    leitura_id: int, dados: RevisaoRequest, db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(exigir_papeis("admin", "operador")),
):
    revisar_sem_deteccao(db, leitura_id, dados, usuario)
    return {"detail": "Revisao registrada"}


@router.get("/{leitura_id}/revisoes")
def auditoria(leitura_id: int, db: Session = Depends(get_db)):
    return [dict(item) for item in db.execute(select(
        RevisaoLeitura.id, RevisaoLeitura.metadado_id, RevisaoLeitura.username, RevisaoLeitura.acao,
        RevisaoLeitura.placa_anterior, RevisaoLeitura.placa_corrigida,
        RevisaoLeitura.motivo, RevisaoLeitura.evento_id, RevisaoLeitura.criado_em,
    ).where(RevisaoLeitura.leitura_id == leitura_id).order_by(RevisaoLeitura.id)).mappings()]
