from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

class LLMService(ABC):
    
    @abstractmethod
    def generate_summary(
        self,
        raw_content: str,
        group_name: str = "",
        images: Optional[Dict[str, bytes]] = None,
        audios: Optional[Dict[str, bytes]] = None,
        documents: Optional[Dict[str, Tuple[bytes, str]]] = None
    ) -> str:
        """
        Toma el choclo de texto unificado del día (mails + chats) y diccionarios opcionales de imágenes, audios y documentos, 
        y devuelve el resumen estructurado por la IA.
        """
        pass

    @abstractmethod
    def transcribe_audio_query(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
        """
        Toma los bytes de una nota de voz de consulta y la transcribe/extrae en texto plano.
        """
        pass