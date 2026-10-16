import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import cliente_atual
from app.api.routes.alpr import router
from app.db.session import Base, get_db
from app.models.cliente import Cliente
from app.models.evento import Evento
from app.models.leitura import Leitura, MetadadosLeitura
from app.services.fila_imagens import FilaImagens


class FilaImagensTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(self.engine, "connect")
        def configurar_sqlite(conn, _record):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.create_function("NOW", 0, lambda: datetime.now(timezone.utc).isoformat())
            conn.create_function("pg_try_advisory_xact_lock", 1, lambda _: 1)

        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        with self.session() as db:
            cliente = Cliente(nome="Camera", chave_hash="a" * 64)
            db.add(cliente)
            db.commit()
            self.cliente_id = cliente.id

        app = FastAPI()
        app.include_router(router)

        def get_test_db():
            with self.session() as db:
                yield db

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[cliente_atual] = lambda: SimpleNamespace(id=self.cliente_id)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def enviar(self, nome="foto.jpg"):
        response = self.client.post(
            "/alpr", files={"imagem": (nome, b"imagem", "image/jpeg")}
        )
        self.assertEqual(response.status_code, 202)
        return response.json()["id"]

    def test_post_persiste_foto_e_responde_sem_inferencia(self):
        with patch("app.services.fila_imagens.FilaImagens._processar_proxima") as processar:
            leitura_id = self.enviar()
            processar.assert_not_called()
        with self.session() as db:
            leitura = db.get(Leitura, leitura_id)
            self.assertEqual(leitura.imagem, b"imagem")
            self.assertEqual(leitura.nome_arquivo, "foto.jpg")
            self.assertEqual(leitura.status, "pendente")

    def test_processa_fifo_e_persiste_metadados_sem_perder_pendentes(self):
        primeira = self.enviar("primeira.jpg")
        segunda = self.enviar("segunda.jpg")
        ordem = []

        def processar(db, leitura):
            ordem.append(leitura.id)
            db.add(MetadadosLeitura(
                leitura_id=leitura.id, placa="ABC1234", texto_ocr="ABC-1234",
                confianca_deteccao=0.94, confianca_ocr=0.87,
                bbox=[1, 2, 3, 4], modelo="plateDetector.onnx", imgsz=640,
            ))

        with (
            patch("app.services.fila_imagens.SessionLocal", self.session),
            patch.dict("sys.modules", {
                "app.services.alpr_service": SimpleNamespace(processar_imagem=processar)
            }),
        ):
            self.assertTrue(FilaImagens._processar_proxima())
            self.assertTrue(FilaImagens._processar_proxima())
            self.assertFalse(FilaImagens._processar_proxima())
        self.assertEqual(ordem, [primeira, segunda])
        resultado = self.client.get(f"/alpr/{primeira}").json()
        self.assertEqual(resultado["status"], "concluida")
        self.assertEqual(resultado["nome_arquivo"], "primeira.jpg")
        self.assertEqual(resultado["detections"][0]["confianca_deteccao"], 0.94)
        self.assertEqual(resultado["detections"][0]["confianca_ocr"], 0.87)
        self.assertIsNotNone(resultado["duracao_ms"])

    def test_falha_reverte_evento_parcial_e_preserva_erro_no_banco(self):
        leitura_id = self.enviar()

        def processar(db, leitura):
            db.add(Evento(placa="ABC1234", tipo_evento="entrada"))
            db.flush()
            raise ValueError("Imagem invalida")

        with (
            patch("app.services.fila_imagens.SessionLocal", self.session),
            patch.dict("sys.modules", {
                "app.services.alpr_service": SimpleNamespace(processar_imagem=processar)
            }),
            self.assertLogs("app.services.fila_imagens", level="ERROR"),
        ):
            self.assertTrue(FilaImagens._processar_proxima())
            self.assertFalse(FilaImagens._processar_proxima())
        resultado = self.client.get(f"/alpr/{leitura_id}").json()
        self.assertEqual(resultado["status"], "erro")
        self.assertEqual(resultado["erro"], "Imagem invalida")
        with self.session() as db:
            self.assertIsNone(db.scalar(select(Evento)))

    def test_cliente_nao_consulta_envio_de_outro_cliente(self):
        leitura_id = self.enviar()
        self.cliente_id = 999
        self.assertEqual(self.client.get(f"/alpr/{leitura_id}").status_code, 404)

    def test_rejeita_imagem_vazia_e_maior_que_limite(self):
        for content, codigo in [(b"", 400), (b"x" * (10 * 1024 * 1024 + 1), 413)]:
            response = self.client.post("/alpr", files={"imagem": ("foto.jpg", content)})
            self.assertEqual(response.status_code, codigo)

    def test_consulta_fila_vazia(self):
        response = self.client.get("/alpr/fila")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "total": 0, "pendentes": 0, "concluidas": 0, "erros": 0,
            "primeira_pendente": None,
        })

    def test_resumo_da_fila_separa_status_e_clientes(self):
        concluida = self.enviar()
        erro = self.enviar()
        pendente = self.enviar("pendente.jpg")
        with self.session() as db:
            db.get(Leitura, concluida).status = "concluida"
            db.get(Leitura, erro).status = "erro"
            outro = Cliente(nome="Outra camera", chave_hash="b" * 64)
            db.add(outro)
            db.flush()
            db.add(Leitura(
                cliente_id=outro.id, nome_arquivo="privado.jpg",
                imagem=b"foto", tamanho_bytes=4,
            ))
            db.commit()
        response = self.client.get("/alpr/fila")
        self.assertEqual(response.status_code, 200)
        resultado = response.json()
        self.assertEqual(
            [resultado[campo] for campo in ("total", "pendentes", "concluidas", "erros")],
            [3, 1, 1, 1],
        )
        self.assertEqual(resultado["primeira_pendente"]["id"], pendente)
        self.assertEqual(resultado["primeira_pendente"]["nome_arquivo"], "pendente.jpg")
        self.assertNotIn("imagem", resultado["primeira_pendente"])
