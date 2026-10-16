from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import cliente_atual
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.leitura import Leitura, MetadadosLeitura
from app.schemas.leitura import (
    FilaStatusResponse, LeituraFilaResponse,
    LeituraAceitaResponse, LeituraResponse, MetadadosLeituraResponse,
)

router = APIRouter(tags=["alpr"])


@router.post(
    "/alpr", status_code=status.HTTP_202_ACCEPTED, response_model=LeituraAceitaResponse
)
async def alpr(
    response: Response,
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
    cliente: Cliente = Depends(cliente_atual),
) -> LeituraAceitaResponse:
    content = await imagem.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Imagem excede 10 MiB")
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Imagem vazia")
    leitura = Leitura(
        cliente_id=cliente.id,
        nome_arquivo=imagem.filename or "imagem",
        content_type=imagem.content_type,
        imagem=content,
        tamanho_bytes=len(content),
    )
    db.add(leitura)
    db.commit()
    db.refresh(leitura)
    response.headers["Location"] = f"/alpr/{leitura.id}"
    return LeituraAceitaResponse(id=leitura.id, status=leitura.status)


@router.get("/alpr/fila", response_model=FilaStatusResponse)
def consultar_fila(
    db: Session = Depends(get_db),
    cliente: Cliente = Depends(cliente_atual),
) -> FilaStatusResponse:
    contagens = dict(db.execute(
        select(Leitura.status, func.count(Leitura.id))
        .where(Leitura.cliente_id == cliente.id)
        .group_by(Leitura.status)
    ).all())
    primeira = db.scalar(
        select(Leitura)
        .where(Leitura.cliente_id == cliente.id, Leitura.status == "pendente")
        .order_by(Leitura.id)
        .limit(1)
    )
    return FilaStatusResponse(
        total=sum(contagens.values()),
        pendentes=contagens.get("pendente", 0),
        concluidas=contagens.get("concluida", 0),
        erros=contagens.get("erro", 0),
        primeira_pendente=LeituraFilaResponse.model_validate(primeira) if primeira else None,
    )


@router.get("/alpr/{leitura_id}", response_model=LeituraResponse)
def consultar_leitura(
    leitura_id: int,
    db: Session = Depends(get_db),
    cliente: Cliente = Depends(cliente_atual),
) -> LeituraResponse:
    leitura = db.scalar(
        select(Leitura).where(Leitura.id == leitura_id, Leitura.cliente_id == cliente.id)
    )
    if leitura is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leitura nao encontrada")
    metadados = db.scalars(
        select(MetadadosLeitura)
        .where(MetadadosLeitura.leitura_id == leitura.id)
        .order_by(MetadadosLeitura.id)
    ).all()
    return LeituraResponse(
        id=leitura.id,
        status=leitura.status,
        nome_arquivo=leitura.nome_arquivo,
        content_type=leitura.content_type,
        tamanho_bytes=leitura.tamanho_bytes,
        criado_em=leitura.criado_em,
        finalizado_em=leitura.finalizado_em,
        duracao_ms=leitura.duracao_ms,
        erro=leitura.erro,
        detections=[MetadadosLeituraResponse.model_validate(item) for item in metadados],
    )
