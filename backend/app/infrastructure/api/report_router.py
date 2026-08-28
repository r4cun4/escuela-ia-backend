import os
import re
import zipfile
import io
import mimetypes
from datetime import date
from typing import Tuple, Dict, Optional, List, Union
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request

try:
    from markitdown import MarkItDown
    _markitdown = MarkItDown()
except Exception:
    _markitdown = None

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


# ── 1. ENDPOINT PARA PROCESAR REPORTE WHATSAPP (.ZIP / .TXT) ─────────
@router.post("/reporte/procesar")
async def procesar_reporte(
    file: UploadFile = File(...),
    group_name: Optional[str] = None,
    target_date_str: Optional[str] = None, # Param opcional para forzar una fecha (YYYY-MM-DD)
    use_case: ProcessDailyReportUseCase = Depends(get_report_use_case)
):
    filename = file.filename or "chat.zip"
    
    if not group_name or not group_name.strip():
        derived_group = re.sub(r'^(Chat de WhatsApp con\s+)', '', filename, flags=re.IGNORECASE)
        derived_group = re.sub(r'(\.zip|\.txt)$', '', derived_group, flags=re.IGNORECASE)
        group_name = derived_group.strip()
    else:
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
        audios=audios_extraidos,
        is_chat_log=True
    )
    
    return {
        "status": "success",
        "group": group_name,
        "data": resultado
    }


# ── 2. ENDPOINT PARA PROCESAR CORREOS DEL COLEGIO (BODY + ADJUNTOS) ───
@router.post("/reporte/email")
async def procesar_reporte_email(
    request: Request,
    subject: str = Form(""),
    body: str = Form(""),
    group_name: Optional[str] = Form(None),
    target_date_str: Optional[str] = Form(None),
    use_case: ProcessDailyReportUseCase = Depends(get_report_use_case)
):
    """
    Recibe correos del colegio con texto en el cuerpo y/o archivos adjuntos (PDFs, imágenes, etc.).
    Extrae la información mediante Gemini multimodal y guarda el resumen.
    """
    form_data = await request.form()
    all_files: List[UploadFile] = []

    # Usamos hasattr (duck typing) porque request.form() devuelve starlette.UploadFile,
    # que es la clase padre de fastapi.UploadFile — isinstance(padre, Hijo) daría False.
    for _, value in form_data.multi_items():
        if hasattr(value, 'filename') and hasattr(value, 'read') and getattr(value, 'filename', None):
            all_files.append(value)


    images: Dict[str, bytes] = {}
    audios: Dict[str, bytes] = {}
    documents: Dict[str, Tuple[bytes, str]] = {}
    extracted_doc_texts: List[str] = []

    for uploaded_file in all_files:
        if not uploaded_file.filename:
            continue
        fn = uploaded_file.filename
        fn_lower = fn.lower()
        content = await uploaded_file.read()
        if not content:
            continue

        guessed_type, _ = mimetypes.guess_type(fn)

        if fn_lower.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            images[fn] = content
        elif fn_lower.endswith(_AUDIO_EXTENSIONS):
            audios[fn] = content
        else:
            if fn_lower.endswith('.pdf'):
                resolved_mime = "application/pdf"
            elif fn_lower.endswith('.txt'):
                resolved_mime = "text/plain"
            elif fn_lower.endswith('.csv'):
                resolved_mime = "text/csv"
            else:
                resolved_mime = guessed_type or "application/octet-stream"
            
            documents[fn] = (content, resolved_mime)

            if _markitdown:
                try:
                    ext = os.path.splitext(fn_lower)[1] or ".pdf"
                    res = _markitdown.convert_stream(io.BytesIO(content), file_extension=ext)
                    if res and res.text_content and res.text_content.strip():
                        extracted_doc_texts.append(f"--- Contenido extraído del adjunto '{fn}' ---\n{res.text_content.strip()}")
                except Exception:
                    pass

    raw_content = ""
    if subject.strip():
        raw_content += f"Asunto: {subject.strip()}\n\n"
    if body.strip():
        raw_content += f"Cuerpo:\n{body.strip()}\n\n"
    if extracted_doc_texts:
        raw_content += "\n\n".join(extracted_doc_texts)
    raw_content = raw_content.strip()

    if not raw_content and not images and not audios and not documents:
        raise HTTPException(status_code=400, detail="No se recibió ningún texto ni archivo adjunto en el correo.")

    final_group = group_name.strip() if group_name and group_name.strip() else "Colegio Oficial"
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()

    resultado = use_case.execute(
        target_date=target_date,
        raw_content=raw_content,
        group_name=final_group,
        images=images,
        audios=audios,
        documents=documents,
        is_chat_log=False
    )

    return {
        "status": "success",
        "group": final_group,
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
    resultado = await use_case.execute(
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

    resultado = await use_case.execute(
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

