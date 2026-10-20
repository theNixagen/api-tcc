import re

from app.core.config import DETECTION_MIN_CONFIDENCE, OCR_MIN_CONFIDENCE


def placa_valida(placa: str) -> bool:
    return re.fullmatch(r"[A-Z]{3}(?:[0-9]{4}|[0-9][A-Z][0-9]{2})", placa) is not None


def avaliar_leitura(placa: str, deteccao: float, ocr: float | None) -> tuple[str, str | None]:
    if not placa_valida(placa):
        return "revisao", "Placa ausente ou fora do formato brasileiro"
    if deteccao < DETECTION_MIN_CONFIDENCE:
        return "revisao", "Confianca do detector abaixo do limite"
    if ocr is None or ocr < OCR_MIN_CONFIDENCE:
        return "revisao", "Confianca do OCR ausente ou abaixo do limite"
    return "aceita", None
