# app/infrastructure/api/report_router.py
import re
import zipfile
import io
from datetime import date
from typing import Tuple, Dict, Optional
from fastapi import APIRouter, UploadFile, File, Depends

from app.application.services.orquestrator import ProcessDailyReportUseCase, SearchDailySummariesUseCase
from app.ports.llm_service import LLMService
from app.infrastructure.database.dependencies import get_report_use_case, get_search_use_case, get_llm_service

router = APIRouter()

_ZIP_MAGIC = b"PK\x03\x04"
_AUDIO_EXTENSIONS = ('.opus', '.ogg', '.mp3', '.wav', '.m4a')


def _extract_content_from_bytes(raw_bytes: bytes, filename: str) -> Tuple[str, Dict[str, bytes], Dict[str, bytes]]:
    """Rutea internamente el binario si es ZIP o TXT plano y extrae imágenes y audios."""
    filename_lower = filename.lower()
    images = {}
    audios = {}
    
    if raw_bytes[:4] == _ZIP_MAGIC and filename_lower.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            # Extraer texto
            txt_files = [f for f in z.namelist() if f.lower().endswith('.txt')]
            if not txt_files:
                raise ValueError("No se encontró un archivo .txt de historial dentro del ZIP.")
            
            chat_filename = txt_files[0]
            with z.open(chat_filename) as f:
                chat_bytes = f.read()
                decoded_text = None
                for enc in ("utf-8", "cp1252", "latin-1"):
                    try:
                        decoded_text = chat_bytes.decode(enc).strip()
                        break
                    except UnicodeDecodeError:
                        continue
                if decoded_text is None:
                    raise ValueError("No se pudo decodificar el archivo interno del ZIP.")

            # Extraer imágenes y audios
            for f in z.namelist():
                f_lower = f.lower()
                if f_lower.endswith(('.jpg', '.png')):
                    with z.open(f) as img_file:
                        images[f] = img_file.read()
                elif f_lower.endswith(_AUDIO_EXTENSIONS):
                    with z.open(f) as audio_file:
                        audios[f] = audio_file.read()

            return decoded_text, images, audios

    if filename_lower.endswith('.txt'):
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return raw_bytes.decode(enc).strip(), {}, {}
            except UnicodeDecodeError:
                continue
        raise ValueError("No se pudo decodificar el archivo de texto plano.")
        
    try:
        return raw_bytes.decode("utf-8").strip(), {}, {}
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore").strip(), {}, {}


# ── 1. ENDPOINT PARA PROCESAR REPORTE ─────────────────────────────────
@router.post("/reporte/procesar")
async def procesar_reporte(
    file: UploadFile = File(...),
    target_date_str: str = None, # Param opcional para forzar una fecha (YYYY-MM-DD)
    use_case: ProcessDailyReportUseCase = Depends(get_report_use_case)
):
    filename = file.filename
    
    group_name = re.sub(r'^(Chat de WhatsApp con\s+)', '', filename, flags=re.IGNORECASE)
    group_name = re.sub(r'(\.zip|\.txt)$', '', group_name, flags=re.IGNORECASE)
    group_name = group_name.strip()

    raw_bytes = await file.read()
    texto_extraido, images_extraidas, audios_extraidos = _extract_content_from_bytes(raw_bytes, filename)

    # Si nos pasan fecha la usamos, sino usamos hoy
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()

    resultado = use_case.execute(
        target_date=target_date,
        raw_content=texto_extraido,
        group_name=group_name,
        images=images_extraidas,
        audios=audios_extraidos
    )
    
    return {
        "status": "success",
        "group": group_name,
        "data": resultado
    }


# ── 2. ENDPOINT PARA BÚSQUEDA SEMÁNTICA CON AGENTE (RAG) ──────────────
@router.get("/reporte/buscar")
async def buscar_reportes(
    query: str,
    group_name: Optional[str] = None,
    limit: int = 5,
    use_case: SearchDailySummariesUseCase = Depends(get_search_use_case)
):
    """
    Realiza una búsqueda semántica de resúmenes en ChromaDB y sintetiza
    una respuesta redactada en lenguaje natural lista para consumir por Telegram.
    """
    resultado = use_case.execute(
        query=query,
        group_name=group_name,
        limit=limit
    )

    return {
        "status": "success",
        "query": query,
        "group_filter": group_name,
        "answer": resultado.get("answer", ""),
        "sources_count": len(resultado.get("sources", [])),
        "sources": resultado.get("sources", [])
    }


# ── 3. ENDPOINT PARA BÚSQUEDA SEMÁNTICA DESDE AUDIO/VOZ ───────────────
@router.post("/reporte/buscar-audio")
async def buscar_reportes_por_audio(
    file: UploadFile = File(...),
    group_name: Optional[str] = None,
    limit: int = 5,
    llm_service: LLMService = Depends(get_llm_service),
    use_case: SearchDailySummariesUseCase = Depends(get_search_use_case)
):
    """
    Recibe una nota de voz/audio (ej. Telegram), transcribe la consulta usando Gemini
    y ejecuta la búsqueda RAG sintetizando la respuesta.
    """
    filename_lower = file.filename.lower() if file.filename else "audio.ogg"
    mime_type = "audio/ogg"
    if filename_lower.endswith(".mp3"):
        mime_type = "audio/mp3"
    elif filename_lower.endswith(".wav"):
        mime_type = "audio/wav"
    elif filename_lower.endswith(".m4a") or filename_lower.endswith(".mp4"):
        mime_type = "audio/mp4"

    raw_bytes = await file.read()
    transcribed_query = llm_service.transcribe_audio_query(raw_bytes, mime_type=mime_type)

    resultado = use_case.execute(
        query=transcribed_query,
        group_name=group_name,
        limit=limit
    )

    return {
        "status": "success",
        "transcribed_query": transcribed_query,
        "group_filter": group_name,
        "answer": resultado.get("answer", ""),
        "sources_count": len(resultado.get("sources", [])),
        "sources": resultado.get("sources", [])
    }

