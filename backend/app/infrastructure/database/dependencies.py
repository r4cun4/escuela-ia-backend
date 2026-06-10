from sqlalchemy.orm import Session
from fastapi import Depends

# Capa de Aplicación
from app.application.services.orquestrator import ProcessDailyReportUseCase

# Puertos (Abstracciones)
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService

# Infraestructura (Detalles Concretos)
from app.infrastructure.database.session import get_db
from app.infrastructure.database.repositories import SqliteDailySummaryRepository 
from app.infrastructure.clients.gemini_client import GeminiLLMService

def get_report_use_case(db: Session = Depends(get_db)) -> ProcessDailyReportUseCase:
    """
    Fábrica encargada de resolver las dependencias de infraestructura
    e inyectarlas en el Caso de Uso de Aplicación.
    """
    concrete_repo: DailySummaryRepository = SqliteDailySummaryRepository(db)
    concrete_llm: LLMService = GeminiLLMService()
    
    return ProcessDailyReportUseCase(repo=concrete_repo, llm=concrete_llm)