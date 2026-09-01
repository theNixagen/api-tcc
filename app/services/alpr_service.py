from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.services.evento_service import registrar_evento
from app.services.plate_detector import PlateDetector
from app.services.plate_ocr import read_plate

detector = PlateDetector(str(BASE_DIR / "models" / "plateDetector.pt"))


def processar_imagem(db: Session, content: bytes) -> dict[str, Any]:
    with NamedTemporaryFile(suffix=".jpg") as file:
        file.write(content)
        file.flush()
        plates = detector.detect(file.name, confidence=0.40)

    response: list[dict[str, Any]] = []
    for plate in plates:
        text = read_plate(plate["crop"])
        evento = registrar_evento(db, text) if text else None
        response.append(
            {
                "placa": text,
                "evento": None
                if evento is None
                else {
                    "id": evento.id,
                    "tipo_evento": evento.tipo_evento,
                },
                "confidence_detection": plate["confidence"],
                "bbox": plate["bbox"],
            }
        )

    db.commit()
    return {"detections": response}
