import runpy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2

from app.core.config import BASE_DIR


class ConfiancaOCRTest(unittest.TestCase):
    def ler(self, resultado):
        ocr = SimpleNamespace(predict=Mock(return_value=[SimpleNamespace(json=resultado)]))
        with (
            patch.dict("sys.modules", {"paddleocr": SimpleNamespace(PaddleOCR=lambda **_: ocr)}),
            patch.object(cv2, "resize", return_value=None),
        ):
            modulo = runpy.run_path(str(BASE_DIR / "app/services/plate_ocr.py"))
            return modulo["read_plate"](None)

    def test_confianca_e_texto_correspondem_a_placa_selecionada(self):
        resultado = self.ler({"res": {
            "rec_texts": ["ABC", "abc-1234"], "rec_scores": [0.3, 0.91],
        }})
        self.assertEqual(resultado, {
            "placa": "ABC1234", "texto": "abc-1234", "confianca": 0.91,
        })

    def test_ausencia_de_score_nao_inventa_confianca(self):
        resultado = self.ler({"res": {"rec_texts": ["ABC1234"]}})
        self.assertEqual(resultado["placa"], "ABC1234")
        self.assertIsNone(resultado["confianca"])

    def test_sem_texto_retorna_leitura_vazia(self):
        self.assertEqual(self.ler({"res": {}}), {
            "placa": "", "texto": "", "confianca": None,
        })
