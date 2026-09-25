import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Optional

from pydantic_ai import Agent, RunContext

from app.ports.school_agent import SchoolAgentPort
from app.ports.vector_store import VectorStoreRepository

logger = logging.getLogger(__name__)

# ── Dependencias inyectadas al agente via RunContext ───────────────────
@dataclass
class SchoolAgentDeps:
    """Dependencias que el agente recibe en tiempo de ejecución."""
    vector_store: VectorStoreRepository
    group_name: Optional[str] = None


# ── System Prompt para el modo agéntico ───────────────────────────────
AGENTIC_SYSTEM_PROMPT = (
    "Actuás como un asistente escolar inteligente especializado en responder consultas de padres "
    "de un colegio. Tu objetivo es redactar respuestas claras, amables, concisas y directas en lenguaje natural, "
    "listas para ser enviadas a través de un bot de Telegram.\n\n"
    "FLUJO DE TRABAJO:\n"
    "1. Usá la herramienta 'get_current_date' para obtener la fecha de hoy y resolver referencias "
    "temporales como 'esta semana', 'ayer', 'mañana', etc.\n"
    "2. Usá la herramienta 'search_school_summaries' para buscar información relevante en los "
    "resúmenes del historial escolar, incluyendo filtros de fecha cuando corresponda.\n"
    "3. Basándote ÚNICAMENTE en la información recuperada, redactá una respuesta ejecutiva y cordial.\n\n"
    "REGLAS:\n"
    "- Si no encontrás información relevante, indicálo de manera educada sin inventar datos.\n"
    "- Usá filtros de fecha siempre que la consulta implique un período temporal.\n"
    "- No hagas más de 3 búsquedas para una misma consulta.\n"
    "- Las fechas siempre van en formato YYYY-MM-DD para los filtros."
)

# ── System Prompt para el modo lineal (fallback Nivel 1) ──────────────
LINEAR_SYSTEM_PROMPT = (
    "Actuás como un asistente escolar inteligente especializado en responder consultas de padres "
    "de un colegio. Tu objetivo es redactar respuestas claras, amables, concisas y directas en lenguaje natural, "
    "listas para ser enviadas a través de un bot de Telegram.\n\n"
    "Basate ÚNICAMENTE en la información proporcionada en los resúmenes del historial escolar recuperados.\n"
    "Si no encuentras información relevante en los resúmenes para responder la pregunta, indícalo de manera "
    "educada sin inventar datos."
)

# ── Timeout global para el flujo agéntico (segundos) ──────────────────
AGENTIC_TIMEOUT_SECONDS = 15


class SchoolAgent(SchoolAgentPort):
    """
    Agente escolar con dos modos de operación:
    - Agéntico (run_agentic): usa tools de pydantic-ai para buscar autónomamente en ChromaDB.
    - Lineal (synthesize_answer): recibe documentos pre-recuperados y sintetiza (fallback Nivel 1).
    """

    def __init__(self, model_name: str = "google:gemini-3.8-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

        # Seteamos la variable GOOGLE_API_KEY por compatibilidad con pydantic-ai
        os.environ["GOOGLE_API_KEY"] = api_key

        # ── Agente agéntico (con tools) ───────────────────────────
        self.agentic_agent = Agent(
            model_name,
            deps_type=SchoolAgentDeps,
            system_prompt=AGENTIC_SYSTEM_PROMPT,
            retries={'tools': 1},
        )
        self._register_tools()

        # ── Agente lineal (sin tools, fallback Nivel 1) ───────────
        self.linear_agent = Agent(
            model_name,
            system_prompt=LINEAR_SYSTEM_PROMPT,
        )

    def _register_tools(self) -> None:
        """Registra los tools disponibles para el agente agéntico."""

        @self.agentic_agent.tool
        async def get_current_date(ctx: RunContext[SchoolAgentDeps]) -> str:
            """Return current date in YYYY-MM-DD format. Use it to resolve
            relative temporal references such as 'this week', 'yesterday', 'today', 'tomorrow'."""
            return str(date.today())

        @self.agentic_agent.tool
        async def search_school_summaries(
            ctx: RunContext[SchoolAgentDeps],
            query: str,
            group_name: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            limit: int = 5,
        ) -> List[Dict]:
            """Search school summaries in the school knowledge base.

            Args:
                query: Semantic search query string.
                group_name: Optional filter by school class or group name (e.g., '4to A').
                date_from: Start date filter in YYYY-MM-DD format (inclusive).
                date_to: End date filter in YYYY-MM-DD format (inclusive).
                limit: Maximum number of results to return.
            """
            # Usamos el group_name del contexto si no se provee uno explícito
            effective_group = group_name or ctx.deps.group_name
            return ctx.deps.vector_store.search_similar(
                query=query,
                group_name=effective_group,
                limit=limit,
                date_from=date_from,
                date_to=date_to,
            )

    async def run_agentic(self, query: str, deps: SchoolAgentDeps) -> str:
        """
        Ejecuta el flujo agéntico completo (Nivel 0).
        El agente decide autónomamente qué tools usar y con qué parámetros.
        Tiene un timeout global para evitar loops excesivos.
        """
        result = await asyncio.wait_for(
            self.agentic_agent.run(query, deps=deps),
            timeout=AGENTIC_TIMEOUT_SECONDS,
        )
        answer = getattr(result, "output", None) or getattr(result, "data", None)
        return str(answer) if answer is not None else str(result)

    async def synthesize_answer(
        self, query: str, context_documents: List[Dict], group_name: Optional[str] = None
    ) -> str:
        """
        Fallback lineal sin tools — Nivel 1.
        Recibe documentos pre-recuperados y sintetiza una respuesta redactada.
        """
        if not context_documents:
            return "No se encontró información relevante en los resúmenes escolares para responder a tu consulta."

        formatted_context = []
        for i, doc in enumerate(context_documents, 1):
            meta = doc.get("metadata", {})
            target_date = meta.get("target_date", "Fecha no especificada")
            group_name_val = meta.get("group_name", "Grupo no especificado")
            content = doc.get("content", "")
            formatted_context.append(
                f"--- Resumen {i} [Grupo: {group_name_val} | Fecha: {target_date}] ---\n{content}"
            )

        context_str = "\n\n".join(formatted_context)

        prompt = (
            f"Pregunta del padre/madre: {query}\n"
            f"Filtro de grupo: {group_name or 'Todos'}\n\n"
            f"Información de contexto recuperada del historial escolar:\n{context_str}\n\n"
            "Redactá una respuesta ejecutiva y cordial en lenguaje natural lista para enviar por Telegram."
        )

        last_error = None
        for attempt in range(4):
            try:
                result = await self.linear_agent.run(prompt)
                answer = getattr(result, "output", None) or getattr(result, "data", None)
                return str(answer) if answer is not None else str(result)
            except Exception as e:
                last_error = e
                # Reintento con backoff exponencial para absorber picos temporales 503
                await asyncio.sleep(2 * (attempt + 1))

        return f"No se pudo generar la respuesta redactada debido a un error: {str(last_error)}"
