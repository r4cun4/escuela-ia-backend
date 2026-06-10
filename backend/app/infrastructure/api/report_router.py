from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from datetime import date
import io
import re

# Importamos exclusivamente el Caso de Uso (Negocio) y su Fábrica
from app.application.services.orquestrator import ProcessDailyReportUseCase
from app.infrastructure.database.dependencies import get_report_use_case

router = APIRouter(prefix="/reporte", tags=["Reportes"])

# Magic bytes para detección de tipo de archivo
_PDF_MAGIC  = b"%PDF"
_ZIP_MAGIC  = b"PK\x03\x04"           # DOCX/XLSX/PPTX son ZIP
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # DOC/XLS viejo (Word 97-2003)


def _extract_text_from_bytes(raw_bytes: bytes) -> str:
    """
    Detecta el tipo de archivo por magic bytes y extrae texto legible.
    Soporta: PDF, DOCX (ZIP/OOXML), DOC (OLE2 Word 97-2003), texto plano.
    """
    if not raw_bytes:
        return ""

    # ── PDF ────────────────────────────────────────────────────────────────
    if raw_bytes[:4] == _PDF_MAGIC:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()
        except Exception as exc:
            raise ValueError(f"Error al extraer texto del PDF: {exc}")

    # ── DOCX (ZIP/OOXML) ──────────────────────────────────────────────────
    if raw_bytes[:4] == _ZIP_MAGIC:
        try:
            import docx2txt
            return docx2txt.process(io.BytesIO(raw_bytes)).strip()
        except Exception as exc:
            raise ValueError(f"Error al extraer texto del DOCX: {exc}")

    # ── DOC viejo (OLE2 – Word 97-2003) ──────────────────────────────────
    if raw_bytes[:8] == _OLE2_MAGIC:
        # El texto está embebido en el stream binario OLE2.
        # Decodificamos en cp1252 (Windows Latin), limpiamos chars de control
        # y filtramos solo las líneas con contenido real.
        try:
            decoded = raw_bytes.decode("cp1252", errors="replace")
        except Exception:
            decoded = raw_bytes.decode("latin-1", errors="replace")

        # Eliminar chars de control (no espacios ni saltos de línea)
        decoded = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", decoded)

        meaningful_lines = []
        for line in re.split(r"[\r\n]+", decoded):
            line = line.strip()
            # Solo conservar líneas que tengan al menos 3 letras seguidas
            if not line or not re.search(r"[A-Za-záéíóúüñÁÉÍÓÚÜÑ]{3,}", line):
                continue
            # Colapsar bloques de símbolos/basura binaria
            line = re.sub(r"[^\x20-\x7eáéíóúüñÁÉÍÓÚÜÑ°ºª.,;:¿?¡!()\"\'\-\n\r\t]{3,}", " ", line)
            line = " ".join(line.split())
            if len(line) > 5:
                meaningful_lines.append(line)

        return "\n".join(meaningful_lines).strip()

    # ── Texto plano ────────────────────────────────────────────────────────
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1", errors="replace").strip()


@router.post("/procesar")
async def procesar_archivo_colegio(
    file: UploadFile = File(...),
    use_case: ProcessDailyReportUseCase = Depends(get_report_use_case),
):
    """
    Recibe un archivo adjunto enviado por n8n via multipart/form-data.
    Detecta el tipo por magic bytes (PDF, DOCX, DOC, texto) y extrae
    el contenido legible antes de pasarlo a Gemini.
    """
    raw_bytes = await file.read()

    if not raw_bytes:
        raise HTTPException(status_code=400, detail="El archivo recibido está vacío")

    try:
        content = _extract_text_from_bytes(raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not content:
        raise HTTPException(
            status_code=400,
            detail="No se pudo extraer texto legible del archivo",
        )

    try:
        resumen = use_case.execute(target_date=date.today(), raw_content=content)

        if resumen.startswith("Error:"):
            raise HTTPException(status_code=500, detail=resumen)

        return {
            "status": "success",
            "summary": resumen,
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/procesar-texto")
async def procesar_texto_colegio(
    request: dict,
    use_case: ProcessDailyReportUseCase = Depends(get_report_use_case),
):
    """
    Endpoint alternativo que acepta JSON con { "content": "..." }.
    Útil para testing manual desde el swagger o desde scripts.
    """
    content = request.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="El contenido no puede estar vacío")

    try:
        resumen = use_case.execute(target_date=date.today(), raw_content=content)

        if resumen.startswith("Error:"):
            raise HTTPException(status_code=500, detail=resumen)

        return {
            "status": "success",
            "summary": resumen,
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))