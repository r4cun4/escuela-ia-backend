from sqlalchemy.orm import Session
from fastapi import Depends

# Capa de Aplicación
from app.application.services.orquestrator import ProcessDailyReportUseCase, SearchDailySummariesUseCase

# Puertos (Abstracciones)
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService
from app.ports.vector_store import VectorStoreRepository

# Infraestructura (Detalles Concretos)
from app.infrastructure.database.session import get_db
from app.infrastructure.database.repositories import SqliteDailySummaryRepository 
from app.infrastructure.clients.gemini_client import GeminiLLMService
from app.infrastructure.clients.chroma_adapter import ChromaVectorStoreRepository
from app.infrastructure.agents.school_agent import SchoolAgent

def get_vector_store() -> VectorStoreRepository:
    return ChromaVectorStoreRepository()

def get_school_agent() -> SchoolAgent:
    return SchoolAgent()

def get_llm_service() -> LLMService:
    return GeminiLLMService()

def get_report_use_case(
    db: Session = Depends(get_db),
    vector_store: VectorStoreRepository = Depends(get_vector_store),
    llm_service: LLMService = Depends(get_llm_service)
) -> ProcessDailyReportUseCase:
    """
    Fábrica encargada de resolver las dependencias de infraestructura
    e inyectarlas en el Caso de Uso de Aplicación.
    """
    concrete_repo: DailySummaryRepository = SqliteDailySummaryRepository(db)
    
    return ProcessDailyReportUseCase(repo=concrete_repo, llm=llm_service, vector_store=vector_store)

def get_search_use_case(
    vector_store: VectorStoreRepository = Depends(get_vector_store),
    school_agent: SchoolAgent = Depends(get_school_agent)
) -> SearchDailySummariesUseCase:
    return SearchDailySummariesUseCase(vector_store=vector_store, school_agent=school_agent)
