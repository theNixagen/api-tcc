from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alpr, auth, eventos, clientes, relatorios, usuarios
from app.core.config import CORS_ORIGINS
from app.db.session import get_db
from app.services.usuario_service import criar_admin_inicial

app = FastAPI(title="ALPR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(clientes.router)
app.include_router(alpr.router)
app.include_router(eventos.router)
app.include_router(relatorios.router)


@app.on_event("startup")
def startup() -> None:
    db = next(get_db())
    try:
        criar_admin_inicial(db)
    finally:
        db.close()
