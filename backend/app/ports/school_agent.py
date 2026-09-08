# app/ports/school_agent.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SchoolAgentPort(ABC):
    """
    Puerto que define las operaciones requeridas para el agente inteligente escolar.
    """

    @abstractmethod
    async def run_agentic(self, query: str, deps: Any) -> str:
        """
        Ejecuta el flujo agéntico con razonamiento autónomo y uso de herramientas.
        """
        pass

    @abstractmethod
    async def synthesize_answer(
        self, query: str, context_documents: List[Dict], group_name: Optional[str] = None
    ) -> str:
        """
        Sintetiza una respuesta en lenguaje natural basada en documentos de contexto.
        """
        pass
