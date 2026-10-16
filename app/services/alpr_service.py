from tempfile import NamedTemporaryFile

from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.models.leitura import Leitura, MetadadosLeitura
from app.services.evento_service import registrar_evento
from app.services.plate_detector import PlateDetector
from app.services.plate_ocr import read_plate

detector = PlateDetector(str(BASE_DIR / "models" / "plateDetector.onnx"))


def processar_imagem(db: Session, leitura: Leitura) -> None:
    with NamedTemporaryFile(suffix=".jpg") as file:
        file.write(leitura.imagem)
        file.flush()
        plates = detector.detect(file.name, confidence=0.40)

    for plate in plates:
        ocr = read_plate(plate["crop"])
        text = ocr["placa"]
        evento = registrar_evento(db, text) if text else None
        db.add(
            MetadadosLeitura(
                leitura_id=leitura.id,
                evento_id=evento.id if evento else None,
                placa=text,
                texto_ocr=ocr["texto"],
                confianca_deteccao=plate["confidence"],
                confianca_ocr=ocr["confianca"],
                bbox=plate["bbox"],
                modelo="plateDetector.onnx",
                imgsz=640,
            )
        )
