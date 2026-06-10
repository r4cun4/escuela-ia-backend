# app/infrastructure/clients/gemini_client.py
import os
from google import genai
from app.ports.llm_service import LLMService


class GeminiLLMService(LLMService):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"

    def generate_summary(self, raw_content: str) -> str:
        prompt = (
            "Actuás como un asistente escolar inteligente. Tu tarea es procesar un texto caótico extraído "
            "de notificaciones, mails y grupos de WhatsApp de mamás/papás de un colegio.\n\n"
            "Generá un resumen ejecutivo, claro, organizado por prioridades, tareas pendientes y fechas "
            "importantes de forma humana y directa. Si hay cosas irrelevantes o quejas, ignoralas.\n\n"
            f"Texto a procesar:\n{raw_content}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Error al conectar con la API de Gemini: {str(e)}")