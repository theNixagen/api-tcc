import time
from typing import Any

import cv2
import requests

SERVER_URL = "http://192.168.1.100:8000/alpr"

camera = cv2.VideoCapture(0)


def main() -> None:
    while True:
        success, frame = camera.read()

        if not success:
            continue

        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            continue

        response = requests.post(
            SERVER_URL,
            files={"imagem": ("camera.jpg", buffer.tobytes(), "image/jpeg")},
            timeout=10,
        )

        data: Any = response.json()
        print(data)

        time.sleep(1)


if __name__ == "__main__":
    main()
