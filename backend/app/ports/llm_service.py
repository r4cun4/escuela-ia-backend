# app/ports/llm_service.py
from abc import ABC, abstractmethod

class LLMService(ABC):
    
    @abstractmethod
    def generate_summary(self, raw_content: str) -> str:
        """
        Toma el choclo de texto unificado del día (mails + chats) 
        y devuelve el resumen estructurado por la IA.
        """
        pass