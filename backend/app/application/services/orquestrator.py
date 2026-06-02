# app/application/services/orquestrator.py
from datetime import date
from app.domain.entities.daily_summary import DailySummary, DomainException
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService

class ProcessDailyReportUseCase:
    def __init__(self, repo: DailySummaryRepository, llm: LLMService):
        self.repo = repo  # Inyectamos interfaces
        self.llm = llm

    def execute(self, target_date: date, raw_content: str) -> str:
        if not raw_content.strip():
            return "No hay contenido para procesar."

        summary = DailySummary.create_new(target_date, raw_content)
        summary = self.repo.save(summary)
        
        try:
            summary = summary.transition_to_processing()
            self.repo.save(summary)
            
            summary_text = self.llm.generate_summary(raw_content)
            
            summary = summary.transition_to_completed(summary_text)
            self.repo.save(summary)
            return summary.summary_text
        except DomainException as e:
            summary = summary.transition_to_failed(str(e))
            self.repo.save(summary)
            return f"Error: {str(e)}"