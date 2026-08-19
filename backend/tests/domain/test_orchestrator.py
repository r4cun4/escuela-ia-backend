# tests/domain/test_orchestrator.py
from datetime import date
from typing import Optional, List, Dict
from app.domain.entities.daily_summary import DailySummary, SummaryState
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService
from app.ports.vector_store import VectorStoreRepository
from app.application.services.orquestrator import ProcessDailyReportUseCase, SearchDailySummariesUseCase

# ─── 1. FABRICAMOS IMPLEMENTACIONES EN MEMORIA PARA EL TEST ───

class FakeDailySummaryRepository(DailySummaryRepository):
    """Una base de datos de mentira que guarda las cosas en un diccionario de Python"""
    def __init__(self):
        self.db = {}

    def save(self, summary: DailySummary) -> DailySummary:
        # Simulamos la asignación de un ID como haría SQLite
        if summary.id is None:
            # Recreamos la entidad pasándole un ID ficticio (1)
            summary = DailySummary(
                id=1,
                target_date=summary.target_date,
                group_name=summary.group_name,
                state=summary.state,
                raw_content_hash=summary.raw_content_hash,
                summary_text=summary.summary_text,
                error_message=summary.error_message
            )
        self.db[summary.target_date] = summary
        return summary

    def get_by_date(self, target_date: date) -> Optional[DailySummary]:
        return self.db.get(target_date)


class FakeLLMService(LLMService):
    """Una IA de mentira que devuelve un texto fijo sin gastar plata ni usar internet"""
    def generate_summary(self, raw_content: str, group_name: str = "", images: Dict[str, bytes] = None) -> str:
        return "Resumen IA: Todo OK en el colegio."


class FakeVectorStoreRepository(VectorStoreRepository):
    """Un vector store en memoria para unit tests"""
    def __init__(self):
        self.indexed_docs = []

    def add_summary(self, summary_id: int, target_date: str, group_name: str, summary_text: str) -> None:
        self.indexed_docs.append({
            "summary_id": summary_id,
            "target_date": target_date,
            "group_name": group_name,
            "summary_text": summary_text
        })

    def search_similar(self, query: str, group_name: Optional[str] = None, limit: int = 4) -> List[Dict]:
        results = []
        for doc in self.indexed_docs:
            if group_name and doc["group_name"] != group_name:
                continue
            results.append({
                "content": doc["summary_text"],
                "metadata": {
                    "summary_id": doc["summary_id"],
                    "target_date": doc["target_date"],
                    "group_name": doc["group_name"]
                },
                "score": 0.95
            })
        return results[:limit]


class FakeSchoolAgent:
    def synthesize_answer(self, query: str, context_documents: List[Dict], group_name: Optional[str] = None) -> str:
        return "Respuesta sintetizada para Telegram: El examen de matemáticas es el viernes."


# ─── 2. LOS TESTS UNITARIOS DEL CASO DE USO ───

def test_orchestrator_should_process_lifecycle_and_index_vector_store():
    # Arrange
    fake_repo = FakeDailySummaryRepository()
    fake_llm = FakeLLMService()
    fake_vector_store = FakeVectorStoreRepository()

    use_case = ProcessDailyReportUseCase(
        repo=fake_repo,
        llm=fake_llm,
        vector_store=fake_vector_store
    )

    hoy = date(2026, 6, 2)
    choclo_texto = "02/06/2026 - WhatsApp de Mamás: Mañana llevar cartulina. Mail dirección: Reunión suspendida."

    # Act
    resultado_final = use_case.execute(target_date=hoy, raw_content=choclo_texto, group_name="4to A")

    # Assert
    assert resultado_final == "Resumen IA: Todo OK en el colegio."

    # Verificamos estado COMPLETADO en repo SQL
    reporte_guardado = fake_repo.get_by_date(hoy)
    assert reporte_guardado is not None
    assert reporte_guardado.state == SummaryState.COMPLETADO
    assert reporte_guardado.summary_text == "Resumen IA: Todo OK en el colegio."

    # Verificamos indexación en Vector Store
    assert len(fake_vector_store.indexed_docs) == 1
    assert fake_vector_store.indexed_docs[0]["summary_id"] == 1
    assert fake_vector_store.indexed_docs[0]["group_name"] == "4to A"
    assert fake_vector_store.indexed_docs[0]["summary_text"] == "Resumen IA: Todo OK en el colegio."


def test_search_use_case_with_pydantic_ai_agent():
    fake_vector_store = FakeVectorStoreRepository()
    fake_vector_store.add_summary(1, "2026-06-02", "4to A", "Examen de matemáticas el viernes.")
    fake_agent = FakeSchoolAgent()

    search_use_case = SearchDailySummariesUseCase(vector_store=fake_vector_store, school_agent=fake_agent)
    res = search_use_case.execute(query="matematicas", group_name="4to A")

    assert res["answer"] == "Respuesta sintetizada para Telegram: El examen de matemáticas es el viernes."
    assert len(res["sources"]) == 1
    assert res["sources"][0]["metadata"]["group_name"] == "4to A"
    assert "matemáticas" in res["sources"][0]["content"]
