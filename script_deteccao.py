"""Detector de veiculos para camera USB ou RTSP.

Leitura independente da inferencia (sempre usa o frame mais recente).
ByteTrack acompanha veiculos; captura uma vez por ID quando atingem
uma regiao de interesse (ROI). Salva frame original, recorte e JSON,
e envia o original a fila da API em outra thread.

Instalacao: python -m pip install ultralytics opencv-python requests python-dotenv
Configure API_URL e CLIENTE_SECRET no .env.deteccao ao lado deste script.
Execucao:   python script_deteccao.py
Teclas:     Q ou ESC = sair | S = salvar frame manualmente
"""

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import cv2
import requests
from dotenv import dotenv_values
from ultralytics import YOLO

# ---------- CONFIGURACOES ----------
CAMERA_SOURCE = 0  # USB 0/1... ou "rtsp://usuario:senha@ip:554/caminho"
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = None  # Ex.: 30 (somente se camera aceitar)

MODEL_PATH = "yolo26s.pt"
CONFIDENCE = 0.35
INFERENCE_SIZE = 640
VEHICLE_CLASSES = {2: "carro", 3: "moto", 5: "onibus", 7: "caminhao"}

# ROI normalizada: esquerda, topo, direita, base (0.0 a 1.0).
# Ajuste para cobrir o trecho da imagem onde o carro se aproxima da cancela.
CAPTURE_ZONE = (0.12, 0.42, 0.88, 0.95)
MIN_BOX_AREA_FRACTION = 0.035  # bbox ocupa pelo menos 3.5% da imagem
CONFIRM_FRAMES = 3             # confirmado em 3 inferencias consecutivas
REQUIRE_APPROACH = False       # True exige crescimento de bbox (mais restritivo)
MIN_GROWTH = 1.06              # >=6% de crescimento durante confirmacao

OUTPUT_DIR = Path("capturas_portaria")
config = dotenv_values(Path(__file__).with_name(".env.deteccao"), interpolate=False)
API_URL = config.get("API_URL") or "http://localhost:8000/alpr"
CLIENTE_SECRET = config.get("CLIENTE_SECRET") or ""
# ------------------------------------


class LatestCamera:
    """Le da camera em outra thread, sem acumular uma fila de frames."""

    def __init__(self, source):
        self.source = source
        backend = cv2.CAP_V4L2 if isinstance(source, int) and sys.platform.startswith("linux") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(source, backend)
        if not self.cap.isOpened():
            raise RuntimeError(f"Nao foi possivel abrir a camera: {source}")

        if isinstance(source, int):
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            if CAMERA_FPS is not None:
                self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

        print("Resolucao efetiva:", int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
              "x", int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self.lock = threading.Lock()
        self.frame = None
        self.sequence = 0
        self.running = True
        self.error = None
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _run(self):
        try:
            while self.running:
                ok, frame = self.cap.read()
                if not ok:
                    self.error = "Nao foi possivel ler frame (camera desconectada ou fim do video)."
                    break
                with self.lock:
                    self.frame = frame
                    self.sequence += 1
        finally:
            self.running = False
            self.cap.release()

    def get_latest(self):
        with self.lock:
            if self.frame is None:
                return self.sequence, None
            return self.sequence, self.frame.copy()

    def stop(self):
        self.running = False
        self.worker.join(timeout=1.0)


def send_capture(original_path, json_path, metadata):
    try:
        with original_path.open("rb") as image:
            response = requests.post(
                API_URL,
                headers={"X-Cliente-Secret": CLIENTE_SECRET},
                files={"imagem": (original_path.name, image, "image/jpeg")},
                data={"capturado_em": metadata["capturado_em"]},
                timeout=(5, 20),
            )
        response.raise_for_status()
        if response.status_code != 202:
            raise ValueError(f"Resposta inesperada da API: HTTP {response.status_code}")
        leitura = response.json()
        if not isinstance(leitura, dict) or not isinstance(leitura.get("id"), int):
            raise ValueError("Resposta da API sem ID de leitura valido")
        metadata["envio"] = {"status": "aceita", "leitura_id": leitura["id"]}
        print(f"[FILA] Leitura {leitura['id']} aceita -> {original_path}")
    except (requests.RequestException, ValueError, KeyError, OSError) as error:
        # Um timeout pode ocorrer depois da aceitacao; reenviar poderia duplicar a leitura.
        metadata["envio"] = {"status": "erro", "erro": str(error)}
        print(f"[ENVIO FALHOU] {original_path}: {error}. Captura preservada no disco.")
    try:
        json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as error:
        print(f"[JSON FALHOU] {json_path}: {error}")


def save_capture(frame, box, vehicle_id, vehicle_name, confidence, sender):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    prefix = f"{now:%Y%m%d_%H%M%S_%f}_id{vehicle_id}_{vehicle_name}"
    original_path = OUTPUT_DIR / f"{prefix}.jpg"
    crop_path = OUTPUT_DIR / f"{prefix}_recorte.jpg"
    json_path = OUTPUT_DIR / f"{prefix}.json"

    if not cv2.imwrite(str(original_path), frame):
        print("Falha ao salvar:", original_path)
        return False

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = box
    margin_x = int((x2 - x1) * 0.08)
    margin_y = int((y2 - y1) * 0.08)
    x1c, x2c = max(0, x1 - margin_x), min(width, x2 + margin_x)
    y1c, y2c = max(0, y1 - margin_y), min(height, y2 + margin_y)
    crop = frame[y1c:y2c, x1c:x2c]
    saved_crop = bool(crop.size and cv2.imwrite(str(crop_path), crop))

    metadata = {
        "capturado_em": now.isoformat(),
        "track_id": vehicle_id,
        "classe": vehicle_name,
        "confianca": round(confidence, 4),
        "bbox_xyxy": [int(v) for v in box],
        "imagem_original": str(original_path),
        "recorte": str(crop_path) if saved_crop else None,
        "resolucao_original": [width, height],
        "envio": {"status": "pendente"},
    }
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CAPTURA] ID={vehicle_id} {vehicle_name} {confidence:.0%} -> {original_path}")
    sender.submit(send_capture, original_path, json_path, metadata)
    return True


def main():
    if not CLIENTE_SECRET:
        raise RuntimeError("Defina CLIENTE_SECRET no .env.deteccao com o secret de um cliente cadastrado na API.")
    model = YOLO(MODEL_PATH)
    camera = LatestCamera(CAMERA_SOURCE)
    sender = ThreadPoolExecutor(max_workers=1)

    # Estados por ID. ByteTrack pode trocar o ID apos perder o objeto.
    # Capturados permanece durante esta execucao; contadores antigos sao limpos.
    captured_ids = set()
    pending = {}  # id -> {"count", "initial_area", "last_seen"}
    last_sequence = -1
    previous = time.perf_counter()
    fps_smooth = 0.0
    processed = 0

    print("S=salvar frame manual | Q/ESC=sair")
    try:
        while True:
            sequence, frame = camera.get_latest()
            if frame is None or sequence == last_sequence:
                if not camera.running:
                    print(camera.error or "Captura finalizada.")
                    break
                time.sleep(0.005)
                continue
            last_sequence = sequence
            processed += 1
            height, width = frame.shape[:2]
            original = frame.copy()

            # Persistencia dos IDs entre frames da MESMA camera.
            result = model.track(
                source=frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=list(VEHICLE_CLASSES),
                conf=CONFIDENCE,
                imgsz=INFERENCE_SIZE,
                device="cpu",
                verbose=False,
            )[0]

            display = frame.copy()
            left, top, right, bottom = CAPTURE_ZONE
            zx1, zy1 = int(left * width), int(top * height)
            zx2, zy2 = int(right * width), int(bottom * height)
            cv2.rectangle(display, (zx1, zy1), (zx2, zy2), (0, 210, 255), 2)
            cv2.putText(display, "ZONA DE CAPTURA", (zx1 + 5, max(20, zy1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 210, 255), 2)

            active_ids = set()
            if result.boxes is not None and result.boxes.is_track:
                for detected in result.boxes:
                    if detected.id is None:
                        continue
                    vehicle_id = int(detected.id.item())
                    class_id = int(detected.cls.item())
                    confidence = float(detected.conf.item())
                    if class_id not in VEHICLE_CLASSES:
                        continue
                    box = [int(v) for v in detected.xyxy[0].tolist()]
                    x1, y1, x2, y2 = box
                    area_fraction = max(0, x2 - x1) * max(0, y2 - y1) / (width * height)
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    inside = zx1 <= center_x <= zx2 and zy1 <= center_y <= zy2
                    near_enough = inside and area_fraction >= MIN_BOX_AREA_FRACTION
                    active_ids.add(vehicle_id)

                    if vehicle_id not in captured_ids:
                        if near_enough:
                            state = pending.setdefault(vehicle_id, {
                                "count": 0, "initial_area": area_fraction, "last_seen": processed,
                            })
                            # Apenas observacoes consecutivas contam.
                            if state["last_seen"] != processed - 1:
                                state["count"] = 0
                                state["initial_area"] = area_fraction
                            state["count"] += 1
                            state["last_seen"] = processed
                            grown = area_fraction >= state["initial_area"] * MIN_GROWTH
                            if state["count"] >= CONFIRM_FRAMES and (not REQUIRE_APPROACH or grown):
                                if save_capture(original, box, vehicle_id,
                                                VEHICLE_CLASSES[class_id], confidence, sender):
                                    captured_ids.add(vehicle_id)
                                    pending.pop(vehicle_id, None)
                        else:
                            pending.pop(vehicle_id, None)

                    if vehicle_id in captured_ids:
                        color, status = (60, 190, 60), "SALVO"
                    elif near_enough:
                        color, status = (0, 210, 255), "PRONTO"
                    else:
                        color, status = (255, 170, 30), "ACOMPANHANDO"
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                    label = f"{VEHICLE_CLASSES[class_id]} #{vehicle_id} {confidence:.0%} {status}"
                    cv2.putText(display, label, (max(0, x1), max(20, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            # Evita crescimento ilimitado dos estados pendentes.
            for vehicle_id in list(pending):
                if processed - pending[vehicle_id]["last_seen"] > 15:
                    del pending[vehicle_id]

            now = time.perf_counter()
            instantaneous = 1.0 / max(now - previous, 1e-6)
            previous = now
            fps_smooth = instantaneous if not fps_smooth else 0.85 * fps_smooth + 0.15 * instantaneous
            cv2.rectangle(display, (0, 0), (width, 42), (20, 20, 20), -1)
            cv2.putText(display,
                        f"YOLO26s + ByteTrack | {fps_smooth:.1f} FPS | Capturas: {len(captured_ids)} | S/Q",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imshow("Portaria - YOLO26s", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("s"):
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                name = OUTPUT_DIR / f"manual_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg"
                cv2.imwrite(str(name), original)
                print("Frame manual:", name)
            elif key in (ord("q"), 27):
                break
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        sender.shutdown(wait=True)


if __name__ == "__main__":
    main()
