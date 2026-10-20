import logging
from tempfile import NamedTemporaryFile

import cv2
from app.core.config import BASE_DIR
from app.services.plate_detector import PlateDetector
from app.services.plate_ocr import read_plate

detector = PlateDetector(str(BASE_DIR / "models" / "plateDetector.onnx"))
logger = logging.getLogger("uvicorn.error.alpr")


def inferir_imagem(leitura_id: int, nome_arquivo: str, content: bytes) -> list[dict]:
    with NamedTemporaryFile(suffix=".jpg") as file:
        file.write(content)
        file.flush()
        plates = detector.detect(file.name, confidence=0.40)

    if not plates:
        logger.info(
            "Leitura %s arquivo=%r: nenhuma placa detectada (confianca minima=40%%)",
            leitura_id, nome_arquivo,
        )

    detections = []
    for index, plate in enumerate(plates, start=1):
        recorte = BASE_DIR / "logs" / "recortes" / f"leitura_{leitura_id}_placa_{index}.jpg"
        logger.info(
            "Leitura %s placa %s: confianca deteccao=%.2f%% bbox=%s arquivo=%r",
            leitura_id, index, plate["confidence"] * 100, plate["bbox"], nome_arquivo,
        )
        try:
            recorte.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(recorte), plate["crop"]):
                raise OSError("OpenCV nao conseguiu gravar o recorte")
            logger.info("Leitura %s placa %s: recorte salvo em %s", leitura_id, index, recorte)
        except (OSError, cv2.error):
            logger.exception("Leitura %s placa %s: falha ao salvar recorte", leitura_id, index)

        ocr = read_plate(plate["crop"])
        text = ocr["placa"]
        logger.info(
            "Leitura %s placa %s: texto=%r confianca OCR=%s",
            leitura_id, index, text,
            f"{ocr['confianca'] * 100:.2f}%" if ocr["confianca"] is not None else "indisponivel",
        )
        detections.append({
            "placa": text, "texto_ocr": ocr["texto"],
            "confianca_deteccao": plate["confidence"], "confianca_ocr": ocr["confianca"],
            "bbox": plate["bbox"], "modelo": "plateDetector.onnx", "imgsz": 640,
        })
    return detections
