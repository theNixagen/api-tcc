import os
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parents[2]


def _load_env_files() -> None:
    for env_path in (BASE_DIR / ".env.development.local", BASE_DIR / ".env"):
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env_files()


def _database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    user = os.getenv("POSTGRES_USER", "alpr")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "alpr"))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "alpr")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL = _database_url()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6377/0")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

PAPEIS_VALIDOS = {"operador", "admin"}
JWT_ALGORITMO = "HS256"

# Valores iniciais: calibrar as confiancas com imagens rotuladas do ambiente real.
DETECTION_MIN_CONFIDENCE = float(os.getenv("DETECTION_MIN_CONFIDENCE", "0.70"))
OCR_MIN_CONFIDENCE = float(os.getenv("OCR_MIN_CONFIDENCE", "0.80"))
REPORT_TIMEZONE = ZoneInfo(os.getenv("REPORT_TIMEZONE", "America/Cuiaba"))
ALPR_TIMEOUT_SECONDS = int(os.getenv("ALPR_TIMEOUT_SECONDS", "120"))
ALPR_MAX_ATTEMPTS = int(os.getenv("ALPR_MAX_ATTEMPTS", "3"))
ALPR_MAX_PENDING = int(os.getenv("ALPR_MAX_PENDING", "1000"))
ALPR_MAX_PENDING_BYTES = int(os.getenv("ALPR_MAX_PENDING_BYTES", str(256 * 1024 * 1024)))
IMAGE_RETENTION_DAYS = int(os.getenv("IMAGE_RETENTION_DAYS", "30"))
if not (0 <= DETECTION_MIN_CONFIDENCE <= 1 and 0 <= OCR_MIN_CONFIDENCE <= 1):
    raise ValueError("Confiancas devem estar entre 0 e 1")
if min(ALPR_TIMEOUT_SECONDS, ALPR_MAX_ATTEMPTS, ALPR_MAX_PENDING, ALPR_MAX_PENDING_BYTES) < 1:
    raise ValueError("Limites da fila devem ser positivos")
if IMAGE_RETENTION_DAYS < 0:
    raise ValueError("IMAGE_RETENTION_DAYS deve ser zero ou positivo")
