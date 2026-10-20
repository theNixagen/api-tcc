import unittest
from unittest.mock import patch

from app.services.validacao_leitura import avaliar_leitura, placa_valida


class ValidacaoLeituraTest(unittest.TestCase):
    def test_formatos_brasileiros(self):
        for placa in ["ABC1234", "ABC1D23"]:
            self.assertTrue(placa_valida(placa))
        for placa in ["", "ABC", "ABCDEFG", "1234567", "ABC12345", "ABC1D2X"]:
            self.assertFalse(placa_valida(placa))

    def test_formato_e_confiancas_controlam_aceitacao(self):
        with (
            patch("app.services.validacao_leitura.DETECTION_MIN_CONFIDENCE", 0.7),
            patch("app.services.validacao_leitura.OCR_MIN_CONFIDENCE", 0.8),
        ):
            self.assertEqual(avaliar_leitura("ABC1234", 0.7, 0.8), ("aceita", None))
            for placa, det, ocr in [("ABC", 1, 1), ("ABC1234", 0.69, 1), ("ABC1D23", 1, None), ("ABC1D23", 1, 0.79)]:
                self.assertEqual(avaliar_leitura(placa, det, ocr)[0], "revisao")
