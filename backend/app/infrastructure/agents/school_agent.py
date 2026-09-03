import asyncio
import os
from typing import List, Dict, Optional
from pydantic_ai import Agent

SYSTEM_PROMPT = (
    "Actuás como un asistente escolar inteligente especializado en responder consultas de padres "
    "de un colegio. Tu objetivo es redactar respuestas claras, amables, concisas y directas en lenguaje natural, "
    "listas para ser enviadas a través de un bot de Telegram.\n\n"
    "Basate ÚNICAMENTE en la información proporcionada en los resúmenes del historial escolar recuperados.\n"
    "Si no encuentras información relevante en los resúmenes para responder la pregunta, indícalo de manera "
    "educada sin inventar datos."
)


class SchoolAgent:
    def __init__(self, model_name: str = "google:gemini-3.6-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")
        
        # Seteamos la variable GOOGLE_API_KEY por compatibilidad con pydantic-ai
        os.environ["GOOGLE_API_KEY"] = api_key

        self.agent = Agent(
            model_name,
            system_prompt=SYSTEM_PROMPT
        )

    async def synthesize_answer(self, query: str, context_documents: List[Dict], group_name: Optional[str] = None) -> str:
        if not context_documents:
            return "No se encontró información relevante en los resúmenes escolares para responder a tu consulta."

        formatted_context = []
        for i, doc in enumerate(context_documents, 1):
            meta = doc.get("metadata", {})
            fecha = meta.get("target_date", "Fecha no especificada")
            grupo = meta.get("group_name", "Grupo no especificado")
            content = doc.get("content", "")
            formatted_context.append(f"--- Resumen {i} [Grupo: {grupo} | Fecha: {fecha}] ---\n{content}")

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
                result = await self.agent.run(prompt)
                answer = getattr(result, "output", None) or getattr(result, "data", None)
                return str(answer) if answer is not None else str(result)
            except Exception as e:
                last_error = e
                # Reintento con backoff exponencial para absorber picos temporales 503
                await asyncio.sleep(2 * (attempt + 1))

        return f"No se pudo generar la respuesta redactada debido a un error: {str(last_error)}"
