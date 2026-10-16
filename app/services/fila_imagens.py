import logging
from datetime import datetime, timezone
from threading import Event, Thread
from time import perf_counter

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.leitura import Leitura

logger = logging.getLogger(__name__)


class FilaImagens:
    def __init__(self) -> None:
        self.parar = Event()
        self.worker = Thread(target=self._executar, name="alpr", daemon=True)
        self.worker.start()

    def _executar(self) -> None:
        while not self.parar.is_set():
            try:
                if self._processar_proxima():
                    continue
            except Exception:
                logger.exception("Falha ao consultar a fila de imagens")
            self.parar.wait(1)

    @staticmethod
    def _processar_proxima() -> bool:
        with SessionLocal() as db:
            # O lock transacional serializa a leitura mesmo com varias instancias da API.
            if not db.scalar(text("SELECT pg_try_advisory_xact_lock(715640)")):
                return False
            leitura = db.scalar(
                select(Leitura)
                .where(Leitura.status == "pendente")
                .order_by(Leitura.id)
                .limit(1)
                .with_for_update()
            )
            if leitura is None:
                return False

            inicio = perf_counter()
            try:
                # O savepoint evita eventos parciais e mantem o lock ate salvar o erro.
                with db.begin_nested():
                    from app.services.alpr_service import processar_imagem

                    processar_imagem(db, leitura)
                leitura.status = "concluida"
            except Exception as error:
                logger.exception("Falha ao processar leitura %s", leitura.id)
                leitura.status = "erro"
                leitura.erro = str(error)[:2000]
            leitura.finalizado_em = datetime.now(timezone.utc)
            leitura.duracao_ms = (perf_counter() - inicio) * 1000
            db.commit()
            return True

    def fechar(self) -> None:
        self.parar.set()
        self.worker.join()
