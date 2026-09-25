import asyncio
import logging
import os
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent

logger = logging.getLogger(__name__)

# ── Modelos de Salida (Consumidos por el LLM, en inglés) ──────────────
class PRReviewResult(BaseModel):
    """Structured output expected from the LLM after reviewing the PR."""
    approved: bool = Field(
        description="True if the PR meets all acceptance criteria and architectural rules, False otherwise."
    )
    comments: list[str] = Field(
        description="List of actionable feedback or reasons for rejection. Empty if approved."
    )


# ── Dependencias del Agente ───────────────────────────────────────────
@dataclass
class PRReviewDeps:
    """Dependencias que el agente recibe en tiempo de ejecución (contexto del PR)."""
    issue_acceptance_criteria: str
    pr_diff: str


# ── System Prompt ─────────────────────────────────────────────────────
REVIEWER_SYSTEM_PROMPT = (
    "You are an expert Tech Lead specializing in Python, FastAPI, and Hexagonal Architecture.\n"
    "Your task is to review a Pull Request diff against the Acceptance Criteria of its associated Issue.\n\n"
    "RULES:\n"
    "1. Evaluate if the code changes fulfill the Issue's requirements.\n"
    "2. Ensure the code respects Hexagonal Architecture (e.g., no business logic in routers, no DB calls in domain).\n"
    "3. Ensure SOLID principles and DRY are respected.\n"
    "4. If the PR fails any rule or criteria, set 'approved' to false and list the exact reasons in 'comments'.\n"
    "5. Be direct, objective, and constructive."
)


class PRReviewerAgent:
    """
    Agente encargado de validar Pull Requests en CI/CD.
    Evalúa el diff del código contra los criterios de aceptación del issue.
    """

    def __init__(self, model_name: str = "google:gemini-2.5-pro"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

        os.environ["GOOGLE_API_KEY"] = api_key

        self.agent = Agent(
            model_name,
            deps_type=PRReviewDeps,
            result_type=PRReviewResult,  # PydanticAI fuerza esta salida estructurada
            system_prompt=REVIEWER_SYSTEM_PROMPT,
        )

    async def review_pr(self, deps: PRReviewDeps) -> PRReviewResult:
        """
        Ejecuta la revisión del PR.
        Retorna un objeto PRReviewResult con el veredicto y los comentarios.
        """
        prompt = (
            f"--- ACCEPTANCE CRITERIA ---\n{deps.issue_acceptance_criteria}\n\n"
            f"--- PULL REQUEST DIFF ---\n{deps.pr_diff}\n\n"
            "Review the diff against the criteria and architectural rules."
        )

        try:
            result = await self.agent.run(prompt, deps=deps)
            return result.data  # Retorna la instancia de PRReviewResult parseada
        except Exception as e:
            logger.error("Error durante la revisión del PR: %s", e)
            # Fallback seguro: si el LLM falla, rechazamos el PR por precaución
            return PRReviewResult(
                approved=False,
                comments=[f"Error interno al evaluar el PR con PydanticAI: {str(e)}"]
            )