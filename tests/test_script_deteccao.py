import json
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import requests


class EnvioCapturaTest(unittest.TestCase):
    def setUp(self):
        with patch.dict("sys.modules", {
            "cv2": Mock(), "ultralytics": SimpleNamespace(YOLO=Mock()),
        }):
            self.script = runpy.run_path(str(Path(__file__).resolve().parents[1] / "script_deteccao.py"))
        self.send = self.script["send_capture"]
        self.send.__globals__["CLIENTE_SECRET"] = "secret-teste"
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "veiculo.jpg"
        self.image.write_bytes(b"imagem-original")
        self.report = self.image.with_suffix(".json")
        self.metadata = {"capturado_em": "2026-11-09T10:00:00-04:00"}

    def test_envia_original_com_secret_e_horario_e_salva_id_da_fila(self):
        response = Mock(status_code=202)
        response.json.return_value = {"id": 42, "status": "pendente"}

        def post(url, **kwargs):
            self.assertEqual(url, self.send.__globals__["API_URL"])
            self.assertEqual(kwargs["headers"], {"X-Cliente-Secret": "secret-teste"})
            self.assertEqual(kwargs["data"], {"capturado_em": self.metadata["capturado_em"]})
            name, image, content_type = kwargs["files"]["imagem"]
            self.assertEqual((name, image.read(), content_type),
                             ("veiculo.jpg", b"imagem-original", "image/jpeg"))
            self.assertEqual(kwargs["timeout"], (5, 20))
            return response

        with patch.object(requests, "post", side_effect=post):
            self.send(self.image, self.report, self.metadata)
        self.assertEqual(json.loads(self.report.read_text())["envio"],
                         {"status": "aceita", "leitura_id": 42})

    def test_configuracao_usa_arquivo_exclusivo_ao_lado_do_script(self):
        script_path = Path(__file__).resolve().parents[1] / "script_deteccao.py"
        with (
            patch.dict("sys.modules", {
                "cv2": Mock(), "ultralytics": SimpleNamespace(YOLO=Mock()),
            }),
            patch("dotenv.dotenv_values", return_value={
                "API_URL": "http://api-teste:8000/alpr", "CLIENTE_SECRET": "secret-arquivo",
            }) as load,
        ):
            script = runpy.run_path(str(script_path))
        load.assert_called_once_with(script_path.with_name(".env.deteccao"), interpolate=False)
        self.assertEqual(script["API_URL"], "http://api-teste:8000/alpr")
        self.assertEqual(script["CLIENTE_SECRET"], "secret-arquivo")

    def test_falhas_preservam_original_e_registram_erro_sem_reenvio(self):
        for error in (requests.Timeout("timeout"), requests.HTTPError("HTTP 429")):
            with self.subTest(error=error), patch.object(requests, "post", side_effect=error) as post:
                self.send(self.image, self.report, self.metadata)
                post.assert_called_once()
                self.assertEqual(self.image.read_bytes(), b"imagem-original")
                self.assertEqual(json.loads(self.report.read_text())["envio"]["status"], "erro")

    def test_captura_salva_e_agenda_envio_sem_esperar_upload(self):
        save = self.script["save_capture"]
        save.__globals__["OUTPUT_DIR"] = Path(self.temp.name)
        save.__globals__["cv2"].imwrite.return_value = True
        frame = MagicMock(shape=(720, 1280, 3))
        frame.__getitem__.return_value.size = 0
        sender = Mock()
        self.assertTrue(save(frame, [10, 10, 200, 200], 7, "carro", 0.9, sender))
        send, original, report, metadata = sender.submit.call_args.args
        self.assertIs(send, self.send)
        self.assertEqual(original.suffix, ".jpg")
        self.assertEqual(json.loads(report.read_text())["envio"], {"status": "pendente"})
        self.assertEqual(metadata["track_id"], 7)


if __name__ == "__main__":
    unittest.main()
