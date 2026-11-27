from typing import Any, TypedDict

import cv2
from fast_plate_ocr import LicensePlateRecognizer
from app.services.validacao_leitura import normalizar_texto_ocr

ocr = LicensePlateRecognizer("cct-s-v2-global-model", device="cpu")


class LeituraOCR(TypedDict):
    placa: str
    texto: str
    confianca: float | None


def read_plate(image: Any) -> LeituraOCR:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    prediction = ocr.run_one(rgb, return_confidence=True)
    texto = prediction.plate
    placa = normalizar_texto_ocr(texto)
    scores = prediction.char_probs
    confianca = None
    if placa and scores is not None and len(scores) >= len(texto):
        confianca = float(scores[:len(texto)].mean())
    return {"placa": placa, "texto": texto, "confianca": confianca}
