import re
from typing import Any, TypedDict

import cv2
from paddleocr import PaddleOCR
from app.services.validacao_leitura import placa_valida

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,
)


def normalize_plate(text: str) -> str:
    text = text.upper()
    return re.sub(r"[^A-Z0-9]", "", text)


class LeituraOCR(TypedDict):
    placa: str
    texto: str
    confianca: float | None


def read_plate(image: Any) -> LeituraOCR:
    image = cv2.resize(image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    result = ocr.predict(image)
    texts: list[LeituraOCR] = []

    for item in result:
        data = item.json
        if "res" not in data:
            continue

        scores = data["res"].get("rec_scores", [])
        for index, text in enumerate(data["res"].get("rec_texts", [])):
            plate = normalize_plate(text)
            if plate:
                texts.append(
                    {
                        "placa": plate,
                        "texto": text,
                        "confianca": float(scores[index]) if index < len(scores) else None,
                    }
                )

    if not texts:
        return {"placa": "", "texto": "", "confianca": None}
    return max(texts, key=lambda item: (
        placa_valida(item["placa"]),
        item["confianca"] if item["confianca"] is not None else -1,
    ))
