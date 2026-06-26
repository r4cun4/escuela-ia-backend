# app/application/services/orquestrator.py
import re
from datetime import date
from app.domain.entities.daily_summary import DailySummary, DomainException
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService


class ProcessDailyReportUseCase:
    def __init__(self, repo: DailySummaryRepository, llm: LLMService):
        self.repo = repo  # Inyección de interfaces
        self.llm = llm

    def execute(self, target_date: date, raw_content: str, group_name: str) -> str:
        if not raw_content.strip():
            return "No hay contenido para procesar."

        # ✂️ Filtramos el contenido para quedarnos SOLO con los mensajes del día objetivo
        content_filtrado = self._filtrar_chat_por_fecha(raw_content, target_date)

        if not content_filtrado.strip():
            return f"No se encontraron mensajes para la fecha: {target_date}"

        # Creamos la entidad inyectando de forma obligatoria el nombre del grupo
        summary = DailySummary.create_new(target_date, group_name, content_filtrado)
        summary = self.repo.save(summary)

        try:
            summary = summary.transition_to_processing()
            self.repo.save(summary)

            # Le pasamos el nombre del grupo al servicio LLM para contextualizar el prompt de Gemini
            summary_text = self.llm.generate_summary(
                content_filtrado, group_name=group_name
            )

            summary = summary.transition_to_completed(summary_text)
            self.repo.save(summary)
            return summary.summary_text
        except DomainException as e:
            summary = summary.transition_to_failed(str(e))
            self.repo.save(summary)
            return f"Error: {str(e)}"

    def _filtrar_chat_por_fecha(self, raw_content: str, target_date: date) -> str:
        """
        Escanea el log de WhatsApp línea por línea y descarta todo lo que no sea
        de la target_date (o posterior). Soporta formatos de Android e iOS.
        """
        pattern = re.compile(r"^\[?(\d{1,2})/(\d{1,2})/(\d{2,4})")
        filtered_lines = []
        incluir_linea_actual = False

        for line in raw_content.splitlines():
            match = pattern.match(line)

            if match:
                day, month, year = map(int, match.groups())

                # Normalizamos año corto (26 -> 2026)
                if year < 100:
                    year += 2000

                try:
                    msg_date = date(year, month, day)
                    if msg_date >= target_date:
                        incluir_linea_actual = True
                        filtered_lines.append(line)
                    else:
                        incluir_linea_actual = False
                except ValueError:
                    incluir_linea_actual = False
            else:
                # Mantiene las líneas de mensajes largos con saltos de carro
                if incluir_linea_actual:
                    filtered_lines.append(line)

        return "\n".join(filtered_lines)
