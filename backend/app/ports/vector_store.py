# app/ports/vector_store.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class VectorStoreRepository(ABC):
    
    @abstractmethod
    def add_summary(self, summary_id: int, target_date: str, group_name: str, summary_text: str) -> None:
        """
        Indexa un resumen diario completado en la base de datos vectorial.
        """
        pass

    @abstractmethod
    def search_similar(self, query: str, group_name: Optional[str] = None, limit: int = 4) -> List[Dict]:
        """
        Realiza una búsqueda semántica por similitud con filtrado opcional por grupo.
        """
        pass
