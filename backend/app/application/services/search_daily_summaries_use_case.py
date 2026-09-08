# app/application/services/search_daily_summaries_use_case.py
from typing import Dict, Optional

from app.application.services.search_service import GracefulSearchService
from app.ports.school_agent import SchoolAgentPort
from app.ports.vector_store import VectorStoreRepository


class SearchDailySummariesUseCase:
    """
    Caso de uso de búsqueda semántica de resúmenes diarios escolares
    con degradación progresiva (Graceful Degradation).
    """

    def __init__(
        self,
        search_service: Optional[GracefulSearchService] = None,
        vector_store: Optional[VectorStoreRepository] = None,
        school_agent: Optional[SchoolAgentPort] = None,
    ):
        if search_service is not None:
            self.search_service = search_service
        elif vector_store is not None and school_agent is not None:
            self.search_service = GracefulSearchService(
                school_agent=school_agent, vector_store=vector_store
            )
        else:
            raise ValueError("Se requiere 'search_service' o ambos ('vector_store' y 'school_agent').")

    async def execute(
        self, query: str, group_name: Optional[str] = None, limit: int = 4
    ) -> Dict:
        """
        Ejecuta la búsqueda semántica delegando en el servicio de degradación graceful.
        """
        if not query or not query.strip():
            return {
                "answer": "La consulta no puede estar vacía.",
                "sources": [],
            }

        return await self.search_service.search(
            query=query.strip(),
            group_name=group_name,
            limit=limit,
        )
