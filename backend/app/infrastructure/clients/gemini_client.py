# app/infrastructure/clients/gemini_client.py
import os
from typing import Dict, Optional, Tuple
from google import genai
from google.genai import types
from app.ports.llm_service import LLMService


def _get_audio_mime_type(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".mp3"):
        return "audio/mp3"
    elif fn.endswith(".wav"):
        return "audio/wav"
    elif fn.endswith(".m4a") or fn.endswith(".mp4"):
        return "audio/mp4"
    return "audio/ogg"  # .opus, .ogg por defecto


class GeminiLLMService(LLMService):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3.6-flash"

    def generate_summary(
        self,
        raw_content: str,
        group_name: str = "",
        images: Optional[Dict[str, bytes]] = None,
        audios: Optional[Dict[str, bytes]] = None,
        documents: Optional[Dict[str, Tuple[bytes, str]]] = None
    ) -> str:
        prompt = (
            "Actuás como un asistente escolar inteligente. Tu tarea es procesar un texto extraído "
            f"de notificaciones, mails o grupos del colegio, específicamente del grupo o tema '{group_name}'.\n\n"
            "Generá un resumen ejecutivo, claro, organizado por prioridades, tareas pendientes y fechas "
            "importantes de forma humana y directa. Si hay cosas irrelevantes o quejas, ignoralas. "
            "Si te adjuntan imágenes (como circulares o fotos del pizarrón), notas de voz/audios, o "
            "documentos y adjuntos (PDFs, etc.), extrae la información relevante de ellos y sumala al resumen.\n\n"
            f"Texto a procesar:\n{raw_content}"
        )

        contents = [prompt]
        if images:
            for filename, img_bytes in images.items():
                mime_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                )

        if audios:
            for filename, audio_bytes in audios.items():
                mime_type = _get_audio_mime_type(filename)
                contents.append(
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                )

        if documents:
            for filename, (doc_bytes, mime_type) in documents.items():
                contents.append(
                    types.Part.from_bytes(data=doc_bytes, mime_type=mime_type)
                )

        import time
        models_to_try = [self.model_name, "gemini-2.0-flash", "gemini-1.5-flash"]
        last_exception = None

        for model in models_to_try:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_exception = e
                    time.sleep(1 * (attempt + 1))
                    continue

        raise RuntimeError(f"Error al conectar con la API de Gemini: {str(last_exception)}")

    def transcribe_audio_query(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
        prompt = (
            "Escuchá la siguiente nota de voz y transcribí o sintetizá en una sola frase limpia "
            "la pregunta o consulta hecha por el usuario, sin agregar introducciones ni explicaciones."
        )
        part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, part],
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Error al procesar el audio de consulta con la API de Gemini: {str(e)}")

