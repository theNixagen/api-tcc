import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alpr, auth, eventos, clientes, relatorios, usuarios, leituras
from app.core.config import CORS_ORIGINS
from app.db.session import SessionLocal
from app.services.fila_imagens import FilaImagens
from app.services.usuario_service import criar_admin_inicial


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        criar_admin_inicial(db)
    app.state.fila_imagens = FilaImagens()
    try:
        yield
    finally:
        await asyncio.to_thread(app.state.fila_imagens.fechar)


app = FastAPI(title="ALPR API", lifespan=lifespan)

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
app.include_router(leituras.router)
