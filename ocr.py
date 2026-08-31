import re
from typing import Any

import cv2
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    # Importante para CPU
    enable_mkldnn=False,
)


def normalize_plate(text: str) -> str:
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def read_plate(image: Any) -> str:
    image = cv2.resize(image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    result = ocr.predict(image)

    texts: list[str] = []

    for item in result:
        data = item.json

        if "res" not in data:
            continue

        rec_texts = data["res"].get("rec_texts", [])

        for text in rec_texts:
            plate = normalize_plate(text)

            if plate:
                texts.append(plate)

    if not texts:
        return ""

    return max(texts, key=len)
