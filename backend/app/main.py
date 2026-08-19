# app/main.py
from fastapi import FastAPI
import logfire

from app.infrastructure.database.session import init_db
from app.infrastructure.api.report_router import router as report_router
from app.infrastructure.settings.config import settings

app = FastAPI(title="Escuela IA Bot")

# Configurar Pydantic Logfire para observabilidad y tracing
logfire_kwargs = {"environment": settings.LOGFIRE_ENVIRONMENT}
if settings.LOGFIRE_TOKEN:
    logfire_kwargs["token"] = settings.LOGFIRE_TOKEN

logfire.configure(**logfire_kwargs)
logfire.instrument_fastapi(app)

@app.on_event("startup")
def on_startup():
    init_db()

# Registramos la ruta del generador de reportes con IA
app.include_router(report_router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend corriendo dentro de Docker"}