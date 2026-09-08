# app/application/services/search_service.py
import asyncio
import logging
from typing import Dict, List, Optional

from app.infrastructure.agents.school_agent import SchoolAgentDeps
from app.ports.school_agent import SchoolAgentPort
from app.ports.vector_store import VectorStoreRepository

logger = logging.getLogger(__name__)


class GracefulSearchService:
    """
    Servicio de aplicación para búsqueda semántica con degradación en capas (Graceful Degradation).

    Niveles de degradación:
        0 — RAG Agéntico: el agente decide autónomamente cómo buscar (tools + razonamiento).
        1 — RAG Lineal: retrieve directo de ChromaDB + síntesis en un solo LLM call.
        2 — Resultados crudos: documentos de ChromaDB formateados sin intervención del LLM.
        3 — Error amigable: mensaje estático cuando todo falla.
    """

    def __init__(self, school_agent: SchoolAgentPort, vector_store: VectorStoreRepository):
        self.school_agent = school_agent
        self.vector_store = vector_store

    async def search(self, query: str, group_name: Optional[str] = None, limit: int = 5) -> Dict:
        """
        Ejecuta la búsqueda intentando cada nivel de degradación secuencialmente.
        Retorna un dict con 'answer', 'sources' y 'degradation_level'.
        """

        # ── Nivel 0: Agéntico (tools + razonamiento) ──────────────
        try:
            deps = SchoolAgentDeps(
                vector_store=self.vector_store,
                group_name=group_name,
            )
            answer = await self.school_agent.run_agentic(query, deps)
            return {"answer": answer, "sources": [], "degradation_level": 0}
        except (TimeoutError, asyncio.TimeoutError) as e:
            logger.warning("Agéntico timeout, degradando a Nivel 1: %s", e)
        except Exception as e:
            logger.warning("Agéntico falló, degradando a Nivel 1: %s", e)

        # ── Nivel 1: RAG lineal (retrieve directo + síntesis) ─────
        try:
            docs = self.vector_store.search_similar(
                query=query, group_name=group_name, limit=limit
            )
            answer = await self.school_agent.synthesize_answer(
                query=query, context_documents=docs, group_name=group_name
            )
            return {"answer": answer, "sources": docs, "degradation_level": 1}
        except Exception as e:
            logger.warning("Síntesis lineal falló, degradando a Nivel 2: %s", e)

        # ── Nivel 2: Resultados crudos sin LLM ────────────────────
        try:
            docs = self.vector_store.search_similar(
                query=query, group_name=group_name, limit=3
            )
            if docs:
                formatted = self._format_raw_results(docs)
                return {"answer": formatted, "sources": docs, "degradation_level": 2}
        except Exception as e:
            logger.error("ChromaDB falló en Nivel 2: %s", e)

        # ── Nivel 3: Error amigable ───────────────────────────────
        return {
            "answer": "El servicio está momentáneamente saturado. Intentá de nuevo en unos minutos.",
            "sources": [],
            "degradation_level": 3,
        }

    @staticmethod
    def _format_raw_results(docs: List[Dict]) -> str:
        """Formatea los documentos crudos de ChromaDB en texto legible para el usuario."""
        lines = ["📋 Encontré estos resúmenes relevantes:\n"]
        for i, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            target_date = meta.get("target_date", "Fecha no especificada")
            group_name_val = meta.get("group_name", "Grupo no especificado")
            content = doc.get("content", "")
            # Truncamos a 300 caracteres para no saturar el chat de Telegram
            preview = content[:300] + "..." if len(content) > 300 else content
            lines.append(f"**{i}. [{group_name_val} — {target_date}]**\n{preview}\n")
        return "\n".join(lines)
