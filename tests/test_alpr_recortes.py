import runpy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from app.core.config import BASE_DIR


class RecortesALPRTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.crop = np.zeros((8, 12, 3), dtype=np.uint8)
        self.detector = Mock()
        self.detector.detect.return_value = [{
            "crop": self.crop, "confidence": 0.94, "bbox": [1, 2, 13, 10],
        }]
        self.ocr = Mock(return_value={
            "placa": "ABC1234", "texto": "ABC1234", "confianca": 0.87,
        })
        with patch.dict("sys.modules", {
            "app.services.plate_detector": SimpleNamespace(PlateDetector=Mock(return_value=self.detector)),
            "app.services.plate_ocr": SimpleNamespace(read_plate=self.ocr),
        }):
            modulo = runpy.run_path(str(BASE_DIR / "app/services/alpr_service.py"))
        self.processar = modulo["inferir_imagem"]
        self.processar.__globals__["BASE_DIR"] = Path(self.temp.name)
        self.leitura = SimpleNamespace(id=7, nome_arquivo="foto.jpg", imagem=b"foto")
        self.recorte = Path(self.temp.name) / "logs/recortes/leitura_7_placa_1.jpg"
        self.db = Mock()

    def test_exporta_recortes_e_mostra_confiancas_no_log(self):
        self.detector.detect.return_value *= 2
        with self.assertLogs("uvicorn.error.alpr", level="INFO") as logs:
            resultado = self.processar(self.leitura.id, self.leitura.nome_arquivo, self.leitura.imagem)
        imagem = cv2.imread(str(self.recorte))
        self.assertEqual(imagem.shape, self.crop.shape)
        self.assertTrue(self.recorte.with_name("leitura_7_placa_2.jpg").exists())
        saida = "\n".join(logs.output)
        self.assertIn("confianca deteccao=94.00%", saida)
        self.assertIn("confianca OCR=87.00%", saida)
        self.assertIn("foto.jpg", saida)
        self.assertEqual(len(resultado), 2)

    def test_sem_deteccao_informa_no_terminal_sem_criar_recorte(self):
        self.detector.detect.return_value = []
        with self.assertLogs("uvicorn.error.alpr", level="INFO") as logs:
            resultado = self.processar(self.leitura.id, self.leitura.nome_arquivo, self.leitura.imagem)
        self.assertIn("nenhuma placa detectada", "\n".join(logs.output))
        self.assertFalse(self.recorte.exists())
        self.ocr.assert_not_called()
        self.assertEqual(resultado, [])

    def test_falha_na_exportacao_nao_interrompe_persistencia(self):
        with (
            patch.object(cv2, "imwrite", return_value=False),
            self.assertLogs("uvicorn.error.alpr", level="ERROR") as logs,
        ):
            resultado = self.processar(self.leitura.id, self.leitura.nome_arquivo, self.leitura.imagem)
        self.assertIn("falha ao salvar recorte", "\n".join(logs.output))
        self.assertEqual(resultado[0]["placa"], "ABC1234")

    def test_recorte_fica_disponivel_mesmo_se_ocr_falhar(self):
        self.ocr.side_effect = ValueError("OCR falhou")
        with self.assertRaisesRegex(ValueError, "OCR falhou"):
            self.processar(self.leitura.id, self.leitura.nome_arquivo, self.leitura.imagem)
        self.assertTrue(self.recorte.exists())
        self.db.add.assert_not_called()
