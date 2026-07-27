# app/ports/llm_service.py
from abc import ABC, abstractmethod
from typing import Dict

class LLMService(ABC):
    
    @abstractmethod
    def generate_summary(self, raw_content: str, group_name: str = "", images: Dict[str, bytes] = None) -> str:
        """
        Toma el choclo de texto unificado del día (mails + chats) y diccionario opcional de imágenes, 
        y devuelve el resumen estructurado por la IA.
        """
        pass