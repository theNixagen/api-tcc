from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import Depends, FastAPI, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from detector import PlateDetector
from events import agrupar_eventos_por_veiculo, registrar_evento
from models import Evento
from ocr import read_plate

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

detector = PlateDetector(str(BASE_DIR / "models" / "plateDetector.pt"))


@app.post("/alpr")
async def alpr(
    imagem: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict[str, Any]:
    content = await imagem.read()

    with NamedTemporaryFile(suffix=".jpg") as file:
        file.write(content)
        file.flush()

        plates = detector.detect(file.name, confidence=0.40)

    response: list[dict[str, Any]] = []

    for plate in plates:
        text = read_plate(plate["crop"])
        evento = None

        if text:
            evento = registrar_evento(db, text)

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


@app.get("/eventos")
def listar_eventos(db: Session = Depends(get_db)) -> dict[str, Any]:
    eventos = list(
        db.scalars(
            select(Evento).order_by(Evento.placa, Evento.data_hora, Evento.id)
        ).all()
    )
    return {"veiculos": agrupar_eventos_por_veiculo(eventos)}
