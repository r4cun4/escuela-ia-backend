# tests/domain/test_orchestrator.py
from datetime import date
from typing import Optional
from app.domain.entities.daily_summary import DailySummary, SummaryState
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService
from app.application.services.orquestrator import ProcessDailyReportUseCase

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
    def generate_summary(self, raw_content: str) -> str:
        return "Resumen IA: Todo OK en el colegio."


# ─── 2. EL TEST UNITARIO DEL CASO DE USO ───

def test_orchestrator_should_process_lifecycle_correctly():
    # Arrange (Preparar el escenario)
    fake_repo = FakeDailySummaryRepository()
    fake_llm = FakeLLMService()
    
    # Inyectamos los fakes en nuestro caso de uso real
    use_case = ProcessDailyReportUseCase(repo=fake_repo, llm=fake_llm)
    
    hoy = date(2026, 6, 2)
    choclo_texto = "WhatsApp de Mamás: Mañana llevar cartulina. Mail dirección: Reunión suspendida."

    # Act (Ejecutar la acción)
    resultado_final = use_case.execute(target_date=hoy, raw_content=choclo_texto)

    # Assert (Verificar que todo el hexágono se comportó como queríamos)
    # A. Verificamos que el output del caso de uso es el que generó la "IA"
    assert resultado_final == "Resumen IA: Todo OK en el colegio."
    
    # B. Verificamos que en nuestra "base de datos" quedó guardado el estado final COMPLETADO
    reporte_guardado = fake_repo.get_by_date(hoy)
    assert reporte_guardado is not None
    assert reporte_guardado.state == SummaryState.COMPLETADO
    assert reporte_guardado.summary_text == "Resumen IA: Todo OK en el colegio."
    assert reporte_guardado.id == 1  # Validamos que pasó por el método save