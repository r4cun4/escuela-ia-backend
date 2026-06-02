# app/ports/repositories.py
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
from app.domain.entities.daily_summary import DailySummary

class DailySummaryRepository(ABC):
    
    @abstractmethod
    def save(self, summary: DailySummary) -> DailySummary:
        """Guarda o actualiza un DailySummary en la persistencia."""
        pass

    @abstractmethod
    def get_by_date(self, target_date: date) -> Optional[DailySummary]:
        """Recupera el resumen de una fecha específica."""
        pass