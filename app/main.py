from fastapi import FastAPI

from app.api.routes import alpr, auth, eventos, raspberry_clientes, usuarios
from app.db.session import get_db
from app.services.usuario_service import criar_admin_inicial

app = FastAPI(title="ALPR API")

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(raspberry_clientes.router)
app.include_router(alpr.router)
app.include_router(eventos.router)


@app.on_event("startup")
def startup() -> None:
    db = next(get_db())
    try:
        criar_admin_inicial(db)
    finally:
        db.close()
