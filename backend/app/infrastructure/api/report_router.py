# app/infrastructure/api/report_router.py
import re
import zipfile
import io
from datetime import date
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.application.services.orquestrator import ProcessDailyReportUseCase
from app.infrastructure.database.session import get_db

# ── 1. IMPORTÁ TUS IMPLEMENTACIONES CONCRETAS ─────────────────────────
# Ajustá estas rutas según los nombres reales de tus archivos de infraestructura
from app.infrastructure.database.repositories import SqliteDailySummaryRepository 
from app.infrastructure.clients.gemini_client import GeminiLLMService

router = APIRouter()

_ZIP_MAGIC = b"PK\x03\x04"

# ── 2. FUNCIÓN FÁBRICA PARA INYECTAR DEPENDENCIAS ────────────────────
def get_process_daily_report_use_case(db: Session = Depends(get_db)) -> ProcessDailyReportUseCase:
    """
    Acopla las implementaciones de infraestructura a los puertos del dominio
    y expone el caso de uso completamente armado para FastAPI.
    """
    repo = SQLiteDailySummaryRepository(db) # Tu repo real que implementa DailySummaryRepository
    llm = GeminiLLMService()                # Tu servicio real que implementa LLMService
    return ProcessDailyReportUseCase(repo=repo, llm=llm)


def _extract_text_from_bytes(raw_bytes: bytes, filename: str) -> str:
    """Rutea internamente el binario si es ZIP o TXT plano."""
    filename_lower = filename.lower()
    
    if raw_bytes[:4] == _ZIP_MAGIC and filename_lower.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            txt_files = [f for f in z.namelist() if f.lower().endswith('.txt')]
            if not txt_files:
                raise ValueError("No se encontró un archivo .txt de historial dentro del ZIP.")
            
            chat_filename = txt_files[0]
            with z.open(chat_filename) as f:
                chat_bytes = f.read()
                for enc in ("utf-8", "cp1252", "latin-1"):
                    try:
                        return chat_bytes.decode(enc).strip()
                    except UnicodeDecodeError:
                        continue
                raise ValueError("No se pudo decodificar el archivo interno del ZIP.")

    if filename_lower.endswith('.txt'):
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return raw_bytes.decode(enc).strip()
            except UnicodeDecodeError:
                continue
        raise ValueError("No se pudo decodificar el archivo de texto plano.")
        
    try:
        return raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore").strip()


# ── 3. EL ENDPOINT ACTUALIZADO ────────────────────────────────────────
@router.post("/reporte/procesar")
async def procesar_reporte(
    file: UploadFile = File(...),
    # Clavamos la función fábrica dentro del Depends para blindar el caso de uso
    use_case: ProcessDailyReportUseCase = Depends(get_process_daily_report_use_case)
):
    filename = file.filename
    
    group_name = re.sub(r'^(Chat de WhatsApp con\s+)', '', filename, flags=re.IGNORECASE)
    group_name = re.sub(r'(\.zip|\.txt)$', '', group_name, flags=re.IGNORECASE)
    group_name = group_name.strip()

    raw_bytes = await file.read()
    texto_extraido = _extract_text_from_bytes(raw_bytes, filename)

    resultado = use_case.execute(
        target_date=date.today(),
        raw_content=texto_extraido,
        group_name=group_name
    )
    
    return {
        "status": "success",
        "group": group_name,
        "data": resultado
    }