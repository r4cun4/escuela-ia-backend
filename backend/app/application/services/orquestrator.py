import inspect
import re
from typing import Dict, Optional, List, Tuple
from datetime import date
from app.domain.entities.daily_summary import DailySummary, DomainException
from app.ports.repositories import DailySummaryRepository
from app.ports.llm_service import LLMService
from app.ports.vector_store import VectorStoreRepository


class ProcessDailyReportUseCase:
    def __init__(
        self,
        repo: DailySummaryRepository,
        llm: LLMService,
        vector_store: Optional[VectorStoreRepository] = None
    ):
        self.repo = repo  # Inyección de interfaces
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
        is_chat_log: bool = True
    ) -> str:
        if not raw_content.strip() and not documents and not images and not audios:
            return "No hay contenido ni adjuntos para procesar."

        if is_chat_log:
            # ✂️ Filtramos el contenido para quedarnos SOLO con los mensajes del día objetivo
            content_filtrado = self._filtrar_chat_por_fecha(raw_content, target_date)
            if not content_filtrado.strip():
                return f"No se encontraron mensajes para la fecha: {target_date}"
        else:
            content_filtrado = raw_content.strip()

        # Creamos la entidad inyectando de forma obligatoria el nombre del grupo
        summary = DailySummary.create_new(target_date, group_name, content_filtrado or "Reporte escolar con adjuntos")
        summary = self.repo.save(summary)

        try:
            summary = summary.transition_to_processing()
            summary = self.repo.save(summary)

            filtered_images = {}
            if images:
                if is_chat_log:
                    for filename, img_bytes in images.items():
                        if filename in content_filtrado:
                            filtered_images[filename] = img_bytes
                else:
                    filtered_images = images

            filtered_audios = {}
            if audios:
                if is_chat_log:
                    for filename, audio_bytes in audios.items():
                        if filename in content_filtrado:
                            filtered_audios[filename] = audio_bytes
                else:
                    filtered_audios = audios

            filtered_documents = documents or {}

            # Le pasamos el nombre del grupo, las imágenes, audios y documentos al servicio LLM
            summary_text = self.llm.generate_summary(
                content_filtrado,
                group_name=group_name,
                images=filtered_images,
                audios=filtered_audios,
                documents=filtered_documents
            )

            summary = summary.transition_to_completed(summary_text)
            summary = self.repo.save(summary)

            # Indexamos de forma vectorial en ChromaDB si el puerto está disponible
            if self.vector_store:
                self.vector_store.add_summary(
                    summary_id=summary.id,
                    target_date=str(summary.target_date),
                    group_name=summary.group_name,
                    summary_text=summary.summary_text
                )

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


class SearchDailySummariesUseCase:
    def __init__(self, vector_store: VectorStoreRepository, school_agent: Optional[object] = None):
        self.vector_store = vector_store
        self.school_agent = school_agent

    async def execute(self, query: str, group_name: Optional[str] = None, limit: int = 4) -> Dict:
        if not query or not query.strip():
            return {
                "answer": "La consulta no puede estar vacía.",
                "sources": []
            }

        # 1. Recuperamos fragmentos más relevantes desde la base vectorial ChromaDB
        docs = self.vector_store.search_similar(
            query=query.strip(),
            group_name=group_name,
            limit=limit
        )

        # 2. Sintetizamos la respuesta redactada en lenguaje natural con el Agente escolar de Pydantic AI
        if self.school_agent and hasattr(self.school_agent, "synthesize_answer"):
            if inspect.iscoroutinefunction(self.school_agent.synthesize_answer):
                answer_text = await self.school_agent.synthesize_answer(
                    query=query.strip(),
                    context_documents=docs,
                    group_name=group_name
                )
            else:
                answer_text = self.school_agent.synthesize_answer(
                    query=query.strip(),
                    context_documents=docs,
                    group_name=group_name
                )
        else:
            answer_text = (
                f"Se encontraron {len(docs)} fragmentos relevantes en los resúmenes del colegio."
            )

        return {
            "answer": answer_text,
            "sources": docs
        }


