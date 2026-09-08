# app/application/services/process_daily_report_use_case.py
import re
from datetime import date
from typing import Dict, Optional, Tuple

from app.domain.entities.daily_summary import DailySummary, DomainException
from app.ports.llm_service import LLMService
from app.ports.repositories import DailySummaryRepository
from app.ports.vector_store import VectorStoreRepository


def filter_chat_by_date(raw_content: str, target_date: date) -> str:
    """
    Escanea el log de WhatsApp línea por línea y descarta todo lo que no sea
    de la target_date (o posterior). Soporta formatos de Android e iOS.
    """
    pattern = re.compile(r"^\[?(\d{1,2})/(\d{1,2})/(\d{2,4})")
    filtered_lines = []
    should_include_line = False

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
                    should_include_line = True
                    filtered_lines.append(line)
                else:
                    should_include_line = False
            except ValueError:
                should_include_line = False
        else:
            # Mantiene las líneas de mensajes largos con saltos de carro
            if should_include_line:
                filtered_lines.append(line)

    return "\n".join(filtered_lines)


class ProcessDailyReportUseCase:
    """
    Caso de uso responsable de orquestar el procesamiento de reportes diarios escolares,
    incluyendo filtrado temporal, transición de estados, generación de resumen vía LLM
    e indexación vectorial.
    """

    def __init__(
        self,
        repo: DailySummaryRepository,
        llm: LLMService,
        vector_store: Optional[VectorStoreRepository] = None,
    ):
        self.repo = repo
        self.llm = llm
        self.vector_store = vector_store

    def execute(
        self,
        target_date: date,
        raw_content: str,
        group_name: str,
        images: Optional[Dict[str, bytes]] = None,
        audios: Optional[Dict[str, bytes]] = None,
        documents: Optional[Dict[str, Tuple[bytes, str]]] = None,
        is_chat_log: bool = True,
    ) -> str:
        if not raw_content.strip() and not documents and not images and not audios:
            return "No hay contenido ni adjuntos para procesar."

        if is_chat_log:
            # Filtramos el contenido para quedarnos solo con los mensajes del día objetivo
            filtered_content = filter_chat_by_date(raw_content, target_date)
            if not filtered_content.strip():
                return f"No se encontraron mensajes para la fecha: {target_date}"
        else:
            filtered_content = raw_content.strip()

        # Creamos la entidad inyectando de forma obligatoria el nombre del grupo
        summary = DailySummary.create_new(
            target_date, group_name, filtered_content or "Reporte escolar con adjuntos"
        )
        summary = self.repo.save(summary)

        try:
            summary = summary.transition_to_processing()
            summary = self.repo.save(summary)

            filtered_images = {}
            if images:
                if is_chat_log:
                    for filename, img_bytes in images.items():
                        if filename in filtered_content:
                            filtered_images[filename] = img_bytes
                else:
                    filtered_images = images

            filtered_audios = {}
            if audios:
                if is_chat_log:
                    for filename, audio_bytes in audios.items():
                        if filename in filtered_content:
                            filtered_audios[filename] = audio_bytes
                else:
                    filtered_audios = audios

            filtered_documents = documents or {}

            # Enviamos el contenido y adjuntos al servicio LLM
            summary_text = self.llm.generate_summary(
                filtered_content,
                group_name=group_name,
                images=filtered_images,
                audios=filtered_audios,
                documents=filtered_documents,
            )

            summary = summary.transition_to_completed(summary_text)
            summary = self.repo.save(summary)

            # Indexamos de forma vectorial en ChromaDB si el puerto está disponible
            if self.vector_store:
                self.vector_store.add_summary(
                    summary_id=summary.id,
                    target_date=str(summary.target_date),
                    group_name=summary.group_name,
                    summary_text=summary.summary_text,
                )

            return summary.summary_text
        except DomainException as e:
            summary = summary.transition_to_failed(str(e))
            self.repo.save(summary)
            return f"Error: {str(e)}"
