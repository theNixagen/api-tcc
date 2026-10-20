import logging
import multiprocessing
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from time import monotonic

from sqlalchemy import func, or_, select, update

from app.core.config import ALPR_TIMEOUT_SECONDS, BASE_DIR, IMAGE_RETENTION_DAYS
from app.db.session import SessionLocal, engine
from app.models.leitura import Leitura
from app.services.leitura_service import salvar_deteccoes

logger = logging.getLogger("uvicorn.error.fila")


def _inferir_worker(pipe):
    logging.basicConfig(level=logging.INFO)
    try:
        while True:
            tarefa = pipe.recv()
            if tarefa is None:
                break
            leitura_id, nome, content = tarefa
            try:
                from app.services.alpr_service import inferir_imagem

                pipe.send((True, inferir_imagem(leitura_id, nome, content)))
            except Exception as error:
                logger.exception("Falha de inferencia na leitura %s", leitura_id)
                pipe.send((False, str(error)[:2000]))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        pipe.close()


class Processador:
    """Mantem o modelo carregado; um timeout encerra o processo, nao apenas uma thread."""

    def __init__(self):
        self.processo = None
        self.pipe = None

    def processar(self, leitura_id, nome, content, parar):
        if self.processo is None or not self.processo.is_alive():
            self.fechar()
            contexto = multiprocessing.get_context("spawn")
            self.pipe, remoto = contexto.Pipe()
            self.processo = contexto.Process(target=_inferir_worker, args=(remoto,), daemon=True)
            self.processo.start()
            remoto.close()
        try:
            self.pipe.send((leitura_id, nome, content))
            limite = monotonic() + ALPR_TIMEOUT_SECONDS
            while not self.pipe.poll(0.2):
                if parar.is_set():
                    raise RuntimeError("Worker encerrado durante a inferencia")
                if monotonic() >= limite:
                    raise TimeoutError(f"Inferencia excedeu {ALPR_TIMEOUT_SECONDS}s")
                if not self.processo.is_alive():
                    raise RuntimeError("Processo de inferencia terminou inesperadamente")
            sucesso, resultado = self.pipe.recv()
        except Exception:
            self.fechar(forcar=True)
            raise
        if not sucesso:
            raise RuntimeError(resultado)
        return resultado

    def fechar(self, forcar=False):
        if self.processo is not None:
            if self.processo.is_alive() and not forcar:
                try:
                    self.pipe.send(None)
                    self.processo.join(timeout=2)
                except (OSError, EOFError):
                    pass
            if self.processo.is_alive():
                self.processo.terminate()
            self.processo.join(timeout=5)
            if self.processo.is_alive():
                self.processo.kill()
                self.processo.join(timeout=5)
            self.processo.close()
            self.processo = None
        if self.pipe is not None:
            self.pipe.close()
            self.pipe = None


def registrar_falha(leitura, erro):
    leitura.erro = str(erro)[:2000]
    leitura.finalizado_em = datetime.now(timezone.utc)
    leitura.status = "pendente" if leitura.tentativas < leitura.tentativas_limite else "erro"
    leitura.proxima_tentativa_em = (
        leitura.finalizado_em + timedelta(seconds=5) if leitura.status == "pendente" else None
    )


def limpar_imagens(db):
    if IMAGE_RETENTION_DAYS == 0:
        return
    limite = datetime.now(timezone.utc) - timedelta(days=IMAGE_RETENTION_DAYS)
    # Preserva historico e imagens que ainda precisam de processamento ou revisao.
    db.execute(update(Leitura).where(
        Leitura.status.in_(["concluida", "erro"]),
        or_(Leitura.resultado.is_(None), Leitura.resultado != "revisao"),
        Leitura.finalizado_em < limite, Leitura.imagem.is_not(None),
    ).values(imagem=None))
    db.commit()
    pasta = BASE_DIR / "logs" / "recortes"
    for arquivo in pasta.glob("leitura_*_placa_*.jpg"):
        try:
            if arquivo.is_file() and arquivo.stat().st_mtime < limite.timestamp():
                arquivo.unlink()
        except OSError:
            logger.exception("Nao foi possivel remover recorte expirado %s", arquivo)


class FilaImagens:
    def __init__(self):
        self.parar = Event()
        self.processador = Processador()
        self.ultima_limpeza = 0
        self.worker = Thread(target=self._executar, name="alpr", daemon=True)
        self.worker.start()

    def _executar(self):
        try:
            while not self.parar.is_set():
                try:
                    if self._processar_proxima():
                        continue
                except Exception:
                    logger.exception("Falha no worker da fila")
                self.parar.wait(1)
        finally:
            self.processador.fechar()

    def _processar_proxima(self):
        # Lock de sessao em conexao dedicada, liberado explicitamente antes do pool.
        with engine.connect() as lock:
            if not lock.scalar(select(func.pg_try_advisory_lock(715640))):
                return False
            try:
                return self._processar_com_lock()
            finally:
                lock.execute(select(func.pg_advisory_unlock(715640)))

    def _processar_com_lock(self):
        with SessionLocal() as db:
            if monotonic() - self.ultima_limpeza > 3600:
                limpar_imagens(db)
                self.ultima_limpeza = monotonic()
            # Quem adquiriu o lock global nao tem outro worker legitimo em atividade.
            for abandonada in db.scalars(select(Leitura).where(Leitura.status == "processando").with_for_update()):
                registrar_falha(abandonada, "Processamento interrompido; tarefa recuperada")
            db.commit()
            leitura = db.scalar(select(Leitura).where(
                Leitura.status == "pendente",
                or_(Leitura.proxima_tentativa_em.is_(None), Leitura.proxima_tentativa_em <= datetime.now(timezone.utc)),
            ).order_by(Leitura.id).limit(1).with_for_update())
            if leitura is None:
                return False
            leitura.status = "processando"
            leitura.iniciado_em = datetime.now(timezone.utc)
            leitura.finalizado_em = None
            leitura.proxima_tentativa_em = None
            leitura.tentativas += 1
            leitura.erro = None
            db.commit()
            leitura_id, tentativa = leitura.id, leitura.tentativas
            nome, content = leitura.nome_arquivo, leitura.imagem

        inicio = monotonic()
        try:
            if content is None:
                raise ValueError("Imagem nao disponivel")
            detections = self.processador.processar(leitura_id, nome, content, self.parar)
            with SessionLocal() as db:
                leitura = db.scalar(select(Leitura).where(
                    Leitura.id == leitura_id, Leitura.status == "processando", Leitura.tentativas == tentativa,
                ).with_for_update())
                if leitura is None:
                    return True
                salvar_deteccoes(db, leitura, detections)
                leitura.status, leitura.erro = "concluida", None
                leitura.finalizado_em = datetime.now(timezone.utc)
                leitura.duracao_ms = (monotonic() - inicio) * 1000
                db.commit()
        except Exception as error:
            logger.exception("Falha na leitura %s, tentativa %s", leitura_id, tentativa)
            with SessionLocal() as db:
                leitura = db.scalar(select(Leitura).where(
                    Leitura.id == leitura_id, Leitura.status == "processando", Leitura.tentativas == tentativa,
                ).with_for_update())
                if leitura is not None:
                    registrar_falha(leitura, error)
                    leitura.duracao_ms = (monotonic() - inicio) * 1000
                    db.commit()
        return True

    def fechar(self):
        self.parar.set()
        self.worker.join(timeout=15)
