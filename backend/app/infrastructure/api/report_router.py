# app/infrastructure/api/report_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.infrastructure.clients.gemini_client import GeminiLLMService

router = APIRouter(prefix="/reporte", tags=["Reportes"])

# Definimos la estructura de lo que esperamos recibir del frontend o n8n
class ReportRequest(BaseModel):
    content: str

@router.post("/procesar")
def procesar_texto_colegio(request: ReportRequest):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="El contenido no puede estar vacío")
    
    try:
        # Inyectamos el cliente real de Gemini que creamos antes
        ai_service = GeminiLLMService()
        
        # Le mandamos el choclo de texto para que lo procese
        resumen = ai_service.generate_summary(request.content)
        
        return {
            "status": "success",
            "summary": resumen
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))