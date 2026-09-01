from typing import Any, TypedDict

import cv2
from ultralytics import YOLO


class PlateDetection(TypedDict):
    confidence: float
    bbox: list[int]
    crop: Any


class PlateDetector:
    def __init__(self, model_path: str) -> None:
        self.model = YOLO(model_path)

    def detect(self, image_path: str, confidence: float = 0.5) -> list[PlateDetection]:
        results = self.model(image_path, device="cpu", conf=confidence, verbose=False)
        image = cv2.imread(image_path)
        plates: list[PlateDetection] = []

        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                plates.append(
                    {
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "crop": image[y1:y2, x1:x2],
                    }
                )

        return plates
