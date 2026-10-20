import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from threading import Event
from time import monotonic

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import cliente_atual, usuario_atual
from app.api.routes.alpr import router
from app.api.routes.leituras import router as leituras_router
from app.db.session import Base, get_db
from app.models.cliente import Cliente
from app.models.evento import Evento
from app.models.leitura import Leitura, MetadadosLeitura
from app.models.usuario import Usuario
from app.models.leitura import RevisaoLeitura
from app.services.fila_imagens import FilaImagens, Processador, limpar_imagens
from app.services.evento_service import listar_acessos, relatorio_acessos_diarios


class FilaImagensTest(unittest.TestCase):
    def setUp(self):
        self.schema = None
        if os.getenv("TEST_POSTGRES_URL"):
            self.schema = "alpr_test_" + uuid4().hex
            self.engine = create_engine(os.environ["TEST_POSTGRES_URL"])
            with self.engine.begin() as conn:
                conn.exec_driver_sql(f'CREATE SCHEMA "{self.schema}"')
            self.engine = self.engine.execution_options(schema_translate_map={None: self.schema})
        else:
            self.engine = create_engine(
                "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
            )

            @event.listens_for(self.engine, "connect")
            def configurar_sqlite(conn, _record):
                conn.execute("PRAGMA foreign_keys=ON")
                conn.create_function("NOW", 0, lambda: datetime.now(timezone.utc).isoformat())
                conn.create_function("pg_try_advisory_xact_lock", 1, lambda _: 1)
                conn.create_function("pg_advisory_xact_lock", 1, lambda _: 1)
                conn.create_function("pg_try_advisory_lock", 1, lambda _: 1)
                conn.create_function("pg_advisory_unlock", 1, lambda _: 1)

        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        with self.session() as db:
            cliente = Cliente(nome="Camera", chave_hash="a" * 64)
            db.add(cliente)
            usuario = Usuario(username="operador", senha_hash="hash", papel="operador")
            db.add(usuario)
            db.commit()
            self.cliente_id = cliente.id
            self.usuario = SimpleNamespace(id=usuario.id, username=usuario.username, papel=usuario.papel)

        app = FastAPI()
        app.include_router(router)
        app.include_router(leituras_router)

        def get_test_db():
            with self.session() as db:
                yield db

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[cliente_atual] = lambda: SimpleNamespace(id=self.cliente_id)
        app.dependency_overrides[usuario_atual] = lambda: self.usuario
        self.client = TestClient(app)
        self.worker = FilaImagens.__new__(FilaImagens)
        self.worker.parar = Event()
        self.worker.processador = Mock()
        self.worker.ultima_limpeza = monotonic()

    def processar(self, detections):
        self.worker.processador.processar.return_value = detections
        with (
            patch("app.services.fila_imagens.SessionLocal", self.session),
            patch("app.services.fila_imagens.engine", self.engine),
        ):
            return self.worker._processar_proxima()

    def deteccao(self, confianca=0.95, placa="ABC1234"):
        return {"placa": placa, "texto_ocr": placa,
            "confianca_deteccao": 0.94, "confianca_ocr": confianca,
            "bbox": [1, 2, 3, 4], "modelo": "plateDetector.onnx", "imgsz": 640}

    def tearDown(self):
        self.client.close()
        if self.schema:
            with self.engine.begin() as conn:
                conn.exec_driver_sql(f'DROP SCHEMA "{self.schema}" CASCADE')
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

        def processar(leitura_id, _nome, _content, _parar):
            ordem.append(leitura_id)
            with self.session() as db:
                self.assertEqual(db.get(Leitura, leitura_id).status, "processando")
            return [{"placa": "ABC1234", "texto_ocr": "ABC-1234",
                "confianca_deteccao": 0.94, "confianca_ocr": 0.87,
                "bbox": [1, 2, 3, 4], "modelo": "plateDetector.onnx", "imgsz": 640}]

        self.worker.processador.processar.side_effect = processar
        with (
            patch("app.services.fila_imagens.SessionLocal", self.session),
            patch("app.services.fila_imagens.engine", self.engine),
        ):
            self.assertTrue(self.worker._processar_proxima())
            self.assertTrue(self.worker._processar_proxima())
            self.assertFalse(self.worker._processar_proxima())
        self.assertEqual(ordem, [primeira, segunda])
        resultado = self.client.get(f"/alpr/{primeira}").json()
        self.assertEqual(resultado["status"], "concluida")
        self.assertEqual(resultado["nome_arquivo"], "primeira.jpg")
        self.assertEqual(resultado["detections"][0]["confianca_deteccao"], 0.94)
        self.assertEqual(resultado["detections"][0]["confianca_ocr"], 0.87)
        self.assertIsNotNone(resultado["duracao_ms"])

    def test_falha_reverte_evento_parcial_e_preserva_erro_no_banco(self):
        leitura_id = self.enviar()

        self.worker.processador.processar.side_effect = ValueError("Imagem invalida")
        with self.session() as db:
            db.get(Leitura, leitura_id).tentativas_limite = 1
            db.commit()
        with (
            patch("app.services.fila_imagens.SessionLocal", self.session),
            patch("app.services.fila_imagens.engine", self.engine),
            self.assertLogs("uvicorn.error.fila", level="ERROR"),
        ):
            self.assertTrue(self.worker._processar_proxima())
            self.assertFalse(self.worker._processar_proxima())
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
            "processando": 0, "revisao": 0,
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

    def test_baixa_confianca_persiste_revisao_sem_evento(self):
        leitura_id = self.enviar()
        self.processar([self.deteccao(0.2)])
        detalhe = self.client.get(f"/leituras/{leitura_id}").json()
        self.assertEqual(detalhe["resultado"], "revisao")
        self.assertIsNone(detalhe["detections"][0]["evento_id"])
        with self.session() as db:
            self.assertIsNone(db.scalar(select(Evento)))

    def test_sem_deteccao_vai_para_revisao_sem_inventar_metadados(self):
        leitura_id = self.enviar()
        self.processar([])
        detalhe = self.client.get(f"/alpr/{leitura_id}").json()
        self.assertEqual(detalhe["resultado"], "revisao")
        self.assertEqual(detalhe["detections"], [])
        self.assertEqual(self.client.get("/leituras/fila").json()["revisao"], 1)

    def test_aceita_imagem_sem_deteccao_com_auditoria_e_sem_duplicar_evento(self):
        leitura_id = self.enviar()
        self.processar([])
        dados = {"acao": "aceitar", "placa": "ABC1D23", "tipo_evento": "entrada", "motivo": "Placa conferida na imagem"}
        response = self.client.post(f"/leituras/{leitura_id}/revisar", json=dados)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.post(f"/leituras/{leitura_id}/revisar", json=dados).status_code, 409)
        auditoria = self.client.get(f"/leituras/{leitura_id}/revisoes").json()
        self.assertEqual(len(auditoria), 1)
        self.assertIsNone(auditoria[0]["metadado_id"])
        self.assertEqual(auditoria[0]["placa_corrigida"], "ABC1D23")
        with self.session() as db:
            evento = db.scalar(select(Evento))
            leitura = db.get(Leitura, leitura_id)
            self.assertEqual(evento.placa, "ABC1D23")
            self.assertEqual(evento.data_hora, leitura.capturado_em)
            self.assertEqual(leitura.resultado, "aceita")
            self.assertIsNone(db.scalar(select(MetadadosLeitura)))

    def test_rejeita_imagem_sem_deteccao_com_auditoria_e_sem_evento(self):
        leitura_id = self.enviar()
        self.processar([])
        response = self.client.post(f"/leituras/{leitura_id}/revisar", json={"acao": "rejeitar", "motivo": "Imagem sem placa visivel"})
        self.assertEqual(response.status_code, 200, response.text)
        with self.session() as db:
            self.assertIsNone(db.scalar(select(Evento)))
            self.assertEqual(db.get(Leitura, leitura_id).resultado, "rejeitada")
            self.assertEqual(db.scalar(select(RevisaoLeitura)).leitura_id, leitura_id)

    def test_revisao_sem_deteccao_rejeita_placa_invalida_ou_imagem_ausente(self):
        leitura_id = self.enviar()
        self.processar([])
        dados = {"acao": "aceitar", "placa": "BRASIL", "tipo_evento": "entrada", "motivo": "Conferido na imagem"}
        self.assertEqual(self.client.post(f"/leituras/{leitura_id}/revisar", json=dados).status_code, 422)
        with self.session() as db:
            db.get(Leitura, leitura_id).imagem = None
            db.commit()
        dados["placa"] = "ABC1234"
        self.assertEqual(self.client.post(f"/leituras/{leitura_id}/revisar", json=dados).status_code, 409)
        with self.session() as db:
            self.assertIsNone(db.scalar(select(Evento)))
            self.assertIsNone(db.scalar(select(RevisaoLeitura)))

    def test_rota_de_revisao_sem_deteccao_nao_aceita_leitura_com_deteccoes(self):
        leitura_id = self.enviar()
        self.processar([self.deteccao(0.2)])
        response = self.client.post(f"/leituras/{leitura_id}/revisar", json={"acao": "rejeitar", "motivo": "Precisa revisar a deteccao"})
        self.assertEqual(response.status_code, 409)

    def test_revisao_cria_evento_auditado_uma_unica_vez(self):
        leitura_id = self.enviar()
        self.processar([self.deteccao(0.2)])
        detalhe = self.client.get(f"/leituras/{leitura_id}").json()
        metadado = detalhe["detections"][0]["id"]
        dados = {"acao": "aceitar", "placa": "ABC1D23", "tipo_evento": "saida", "motivo": "Conferido na foto"}
        response = self.client.post(f"/leituras/deteccoes/{metadado}/revisar", json=dados)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.post(f"/leituras/deteccoes/{metadado}/revisar", json=dados).status_code, 409)
        with self.session() as db:
            evento = db.scalar(select(Evento))
            self.assertEqual((evento.placa, evento.tipo_evento), ("ABC1D23", "saida"))
            auditoria = db.scalar(select(RevisaoLeitura))
            self.assertEqual(auditoria.username, "operador")
            self.assertEqual(auditoria.placa_anterior, "ABC1234")
            self.assertEqual(db.get(Leitura, leitura_id).resultado, "aceita")

    def test_rejeicao_auditada_nao_cria_evento(self):
        leitura_id = self.enviar()
        self.processar([self.deteccao(0.2)])
        metadado = self.client.get(f"/leituras/{leitura_id}").json()["detections"][0]["id"]
        response = self.client.post(f"/leituras/deteccoes/{metadado}/revisar", json={"acao": "rejeitar", "motivo": "Nao e uma placa"})
        self.assertEqual(response.status_code, 200, response.text)
        with self.session() as db:
            self.assertIsNone(db.scalar(select(Evento)))
            self.assertEqual(db.get(Leitura, leitura_id).resultado, "rejeitada")

    def test_captura_e_preservada_no_evento_mesmo_com_fila_atrasada(self):
        response = self.client.post("/alpr", files={"imagem": ("foto.jpg", b"foto")},
            data={"capturado_em": "2026-01-01T23:00:00-04:00"})
        self.assertEqual(response.status_code, 202, response.text)
        self.processar([self.deteccao()])
        with self.session() as db:
            evento = db.scalar(select(Evento))
            self.assertEqual(evento.data_hora.replace(tzinfo=timezone.utc), datetime(2026, 1, 2, 3, tzinfo=timezone.utc))
            self.assertTrue(db.get(Leitura, response.json()["id"]).captura_informada)

    def test_captura_sem_fuso_e_rejeitada(self):
        response = self.client.post("/alpr", files={"imagem": ("foto.jpg", b"foto")}, data={"capturado_em": "2026-01-01T12:00:00"})
        self.assertEqual(response.status_code, 422)

    def test_falha_parcial_reverte_eventos_e_metadados(self):
        leitura_id = self.enviar()
        with self.session() as db:
            db.get(Leitura, leitura_id).tentativas_limite = 1
            db.commit()
        with self.assertLogs("uvicorn.error.fila", level="ERROR"):
            self.processar([self.deteccao(), {"placa": "invalida"}])
        with self.session() as db:
            self.assertEqual(db.get(Leitura, leitura_id).status, "erro")
            self.assertIsNone(db.scalar(select(Evento)))
            self.assertIsNone(db.scalar(select(MetadadosLeitura)))

    def test_reprocessar_preserva_contador_e_renova_limite(self):
        leitura_id = self.enviar()
        with self.session() as db:
            leitura = db.get(Leitura, leitura_id)
            leitura.status, leitura.tentativas = "erro", 3
            db.commit()
        response = self.client.post(f"/leituras/{leitura_id}/reprocessar")
        self.assertEqual(response.status_code, 202, response.text)
        with self.session() as db:
            leitura = db.get(Leitura, leitura_id)
            self.assertEqual((leitura.status, leitura.tentativas, leitura.tentativas_limite), ("pendente", 3, 6))

    def test_recupera_tarefa_abandonada_e_reagenda_falha(self):
        leitura_id = self.enviar()
        with self.session() as db:
            leitura = db.get(Leitura, leitura_id)
            leitura.status, leitura.tentativas = "processando", 1
            db.commit()
        self.processar([])
        with self.session() as db:
            leitura = db.get(Leitura, leitura_id)
            self.assertEqual(leitura.status, "pendente")
            self.assertIsNotNone(leitura.proxima_tentativa_em)
            self.assertIn("recuperada", leitura.erro)

    def test_cota_da_fila_rejeita_novo_envio(self):
        self.enviar()
        with patch("app.services.leitura_service.ALPR_MAX_PENDING", 1):
            response = self.client.post("/alpr", files={"imagem": ("foto.jpg", b"foto")})
        self.assertEqual(response.status_code, 503)

    def test_operador_nao_autorizado_nao_consulta_fotos(self):
        leitura_id = self.enviar()
        self.usuario.papel = "sem_permissao"
        self.assertEqual(self.client.get(f"/leituras/{leitura_id}/imagem").status_code, 403)

    def test_paginacao_de_acessos_nao_separa_entrada_da_saida(self):
        inicio = datetime(2026, 1, 2, 3, tzinfo=timezone.utc)
        with self.session() as db:
            for placa in ["ABC1234", "XYZ9876"]:
                db.add_all([
                    Evento(placa=placa, tipo_evento="entrada", data_hora=inicio),
                    Evento(placa=placa, tipo_evento="saida", data_hora=inicio + timedelta(hours=2)),
                ])
            db.commit()
            pagina = listar_acessos(db, limit=1)
            self.assertEqual((pagina["total"], len(pagina["itens"])), (2, 1))
            self.assertIsNotNone(pagina["itens"][0]["data_hora_saida"])
            relatorio = relatorio_acessos_diarios(db, inicio.date() - timedelta(days=1))
            self.assertEqual(relatorio["total"], 2)
            self.assertEqual(relatorio["fuso"], "America/Cuiaba")

    def test_retencao_remove_bytes_mas_preserva_revisoes_e_historico(self):
        ids = [self.enviar() for _ in range(2)]
        with self.session() as db:
            for leitura_id, resultado in zip(ids, ["aceita", "revisao"]):
                leitura = db.get(Leitura, leitura_id)
                leitura.status, leitura.resultado = "concluida", resultado
                leitura.finalizado_em = datetime.now(timezone.utc) - timedelta(days=31)
            db.commit()
            with (
                TemporaryDirectory() as pasta,
                patch("app.services.fila_imagens.IMAGE_RETENTION_DAYS", 30),
                patch("app.services.fila_imagens.BASE_DIR", Path(pasta)),
            ):
                recortes = Path(pasta) / "logs/recortes"
                recortes.mkdir(parents=True)
                recorte = recortes / "leitura_1_placa_1.jpg"
                recorte.write_bytes(b"imagem")
                antigo = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()
                os.utime(recorte, (antigo, antigo))
                limpar_imagens(db)
                self.assertFalse(recorte.exists())
        with self.session() as db:
            self.assertIsNone(db.get(Leitura, ids[0]).imagem)
            self.assertEqual(db.get(Leitura, ids[1]).imagem, b"imagem")
            self.assertEqual(db.get(Leitura, ids[0]).nome_arquivo, "foto.jpg")


class TimeoutProcessadorTest(unittest.TestCase):
    def test_timeout_termina_o_processo_de_inferencia(self):
        processador = Processador()
        processo = Mock()
        processo.is_alive.return_value = True
        processo.terminate.side_effect = lambda: setattr(processo.is_alive, "return_value", False)
        processador.processo = processo
        processador.pipe = Mock()
        processador.pipe.poll.return_value = False
        with (
            patch("app.services.fila_imagens.ALPR_TIMEOUT_SECONDS", 1),
            patch("app.services.fila_imagens.monotonic", side_effect=[0, 2]),
            self.assertRaises(TimeoutError),
        ):
            processador.processar(1, "foto.jpg", b"foto", Event())
        processo.terminate.assert_called_once()
        self.assertIsNone(processador.processo)
