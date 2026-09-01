from typing import Any

from app.core.config import REDIS_URL

try:
    from redis import Redis
except ModuleNotFoundError:
    Redis = None


def get_redis() -> Any:
    if Redis is None:
        raise RuntimeError("Instale a dependencia redis para usar autenticacao")
    return Redis.from_url(REDIS_URL, decode_responses=True)
