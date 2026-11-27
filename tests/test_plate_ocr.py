import runpy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from app.core.config import BASE_DIR


class ConfiancaOCRTest(unittest.TestCase):
    def ler(self, texto, scores):
        probs = np.array(scores) if scores is not None else None
        ocr = SimpleNamespace(run_one=Mock(return_value=SimpleNamespace(plate=texto, char_probs=probs)))
        imagem = np.full((40, 120, 3), (20, 50, 200), dtype=np.uint8)
        with patch.dict("sys.modules", {"fast_plate_ocr": SimpleNamespace(LicensePlateRecognizer=lambda *_, **__: ocr)}):
            modulo = runpy.run_path(str(BASE_DIR / "app/services/plate_ocr.py"))
            resultado = modulo["read_plate"](imagem)
        self.assertEqual(tuple(ocr.run_one.call_args.args[0][0, 0]), (200, 50, 20))
        self.assertTrue(ocr.run_one.call_args.kwargs["return_confidence"])
        return resultado

    def test_confianca_media_usa_apenas_os_caracteres_da_placa(self):
        resultado = self.ler("ABC1D23", [0.9] * 6 + [0.55, 1.0, 1.0])
        self.assertAlmostEqual(resultado["confianca"], 0.85)
        self.assertEqual((resultado["placa"], resultado["texto"]), ("ABC1D23", "ABC1D23"))

    def test_ausencia_de_score_nao_inventa_confianca(self):
        resultado = self.ler("ABC1D23", None)
        self.assertEqual(resultado["placa"], "ABC1D23")
        self.assertIsNone(resultado["confianca"])

    def test_sem_texto_retorna_leitura_vazia(self):
        self.assertEqual(self.ler("", [1.0] * 9), {
            "placa": "", "texto": "", "confianca": None,
        })

    def test_remove_separadores_e_preserva_caracteres_reconhecidos(self):
        resultado = self.ler("ewt-8125", [0.99] * 8)
        self.assertEqual((resultado["placa"], resultado["texto"]), ("EWT8125", "ewt-8125"))
