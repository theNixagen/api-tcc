import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://alpr:alpr@postgres:5432/alpr")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

PAPEIS_VALIDOS = {"operador", "admin"}
JWT_ALGORITMO = "HS256"
