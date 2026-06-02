# app/main.py
from fastapi import FastAPI
from app.infrastructure.database.session import init_db
from app.infrastructure.api.report_router import router as report_router  # <-- NUEVO

app = FastAPI(title="Escuela IA Bot")

@app.on_event("startup")
def on_startup():
    init_db()

# Registramos la ruta del generador de reportes con IA
app.include_router(report_router)  # <-- NUEVO

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend corriendo dentro de Docker"}