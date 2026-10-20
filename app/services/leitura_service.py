from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import ALPR_MAX_ATTEMPTS, ALPR_MAX_PENDING, ALPR_MAX_PENDING_BYTES
from app.models.evento import Evento
from app.models.leitura import Leitura, MetadadosLeitura, RevisaoLeitura
from app.services.evento_service import registrar_evento
from app.services.validacao_leitura import avaliar_leitura, placa_valida


def verificar_cota(db: Session, tamanho: int) -> None:
    # Serializa admissao e reenvios sem bloquear o lock usado pela inferencia.
    db.execute(select(func.pg_advisory_xact_lock(715641)))
    quantidade, total_bytes = db.execute(
        select(func.count(Leitura.id), func.coalesce(func.sum(Leitura.tamanho_bytes), 0))
        .where(Leitura.status.in_(["pendente", "processando"]))
    ).one()
    if quantidade >= ALPR_MAX_PENDING or total_bytes + tamanho > ALPR_MAX_PENDING_BYTES:
        raise HTTPException(503, "Cota da fila atingida. Tente novamente mais tarde.", headers={"Retry-After": "10"})


def salvar_deteccoes(db: Session, leitura: Leitura, detections: list[dict]) -> None:
    resultados = []
    for dados in detections:
        resultado, motivo = avaliar_leitura(
            dados["placa"], dados["confianca_deteccao"], dados["confianca_ocr"]
        )
        evento = registrar_evento(db, dados["placa"], leitura.capturado_em) if resultado == "aceita" else None
        db.add(MetadadosLeitura(
            leitura_id=leitura.id, evento_id=evento.id if evento else None,
            resultado=resultado, motivo=motivo, **dados,
        ))
        resultados.append(resultado)
    leitura.resultado = "aceita" if resultados and "revisao" not in resultados else "revisao"


def revisar_metadado(db: Session, metadado_id: int, dados, usuario) -> None:
    # A mesma ordem de locks e usada em todas as revisoes da leitura.
    leitura_id = db.scalar(select(MetadadosLeitura.leitura_id).where(MetadadosLeitura.id == metadado_id))
    if leitura_id is None:
        raise HTTPException(404, "Deteccao nao encontrada")
    leitura = db.scalar(select(Leitura).where(Leitura.id == leitura_id).with_for_update())
    metadado = db.get(MetadadosLeitura, metadado_id)
    if leitura.status != "concluida" or metadado.resultado != "revisao":
        raise HTTPException(409, "Deteccao nao esta pendente de revisao")
    registrar_revisao(db, leitura, dados, usuario, metadado)


def revisar_sem_deteccao(db: Session, leitura_id: int, dados, usuario) -> None:
    leitura = db.scalar(select(Leitura).where(Leitura.id == leitura_id).with_for_update())
    if leitura is None:
        raise HTTPException(404, "Leitura nao encontrada")
    tem_deteccao = db.scalar(select(MetadadosLeitura.id).where(MetadadosLeitura.leitura_id == leitura.id).limit(1))
    if leitura.status != "concluida" or leitura.resultado not in ("revisao", "sem_placa") or tem_deteccao is not None:
        raise HTTPException(409, "Leitura nao esta pendente de revisao sem deteccao")
    if dados.acao == "aceitar" and leitura.imagem is None:
        raise HTTPException(409, "Imagem original indisponivel para conferir a placa")
    registrar_revisao(db, leitura, dados, usuario)


def registrar_revisao(db: Session, leitura: Leitura, dados, usuario, metadado=None) -> None:
    placa = (dados.placa or "").strip().upper().replace("-", "")
    evento = None
    if dados.acao == "aceitar":
        if not placa_valida(placa) or dados.tipo_evento is None:
            raise HTTPException(422, "Informe uma placa valida e o tipo de evento")
        evento = Evento(placa=placa, tipo_evento=dados.tipo_evento, data_hora=leitura.capturado_em)
        db.add(evento)
        db.flush()
    db.add(RevisaoLeitura(
        leitura_id=leitura.id, metadado_id=metadado.id if metadado else None,
        usuario_id=usuario.id, username=usuario.username,
        acao=dados.acao, placa_anterior=metadado.placa if metadado else "",
        placa_corrigida=placa if evento else None, motivo=dados.motivo,
        evento_id=evento.id if evento else None,
    ))
    if metadado:
        metadado.resultado = "aceita" if evento else "rejeitada"
        metadado.motivo = dados.motivo
        if evento:
            metadado.placa, metadado.evento_id = placa, evento.id
        db.flush()
        resultados = list(db.scalars(select(MetadadosLeitura.resultado).where(MetadadosLeitura.leitura_id == leitura.id)))
        leitura.resultado = "revisao" if "revisao" in resultados else ("aceita" if "aceita" in resultados else "rejeitada")
    else:
        leitura.resultado = "aceita" if evento else "rejeitada"
    db.commit()


def reprocessar(db: Session, leitura_id: int) -> Leitura:
    # A cota e adquirida antes do lock da leitura, como na admissao normal.
    verificar_cota(db, 0)
    leitura = db.scalar(select(Leitura).where(Leitura.id == leitura_id).with_for_update())
    if leitura is None:
        raise HTTPException(404, "Leitura nao encontrada")
    if leitura.status != "erro" or leitura.imagem is None:
        raise HTTPException(409, "Somente erros com imagem disponivel podem ser reprocessados")
    # Revalida os bytes da imagem que voltara para a fila.
    quantidade_bytes = db.scalar(select(func.coalesce(func.sum(Leitura.tamanho_bytes), 0)).where(Leitura.status.in_(["pendente", "processando"])))
    if quantidade_bytes + leitura.tamanho_bytes > ALPR_MAX_PENDING_BYTES:
        raise HTTPException(503, "Cota de bytes da fila atingida")
    leitura.status, leitura.erro, leitura.resultado = "pendente", None, None
    leitura.proxima_tentativa_em = None
    leitura.finalizado_em = None
    leitura.iniciado_em = None
    leitura.duracao_ms = None
    # Tentativas totais permanecem auditaveis; o limite automatico e renovado por lote.
    leitura.tentativas_limite = leitura.tentativas + ALPR_MAX_ATTEMPTS
    db.commit()
    return leitura
