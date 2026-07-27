# domain/models/daily_summary.py
from enum import Enum
from dataclasses import dataclass
from datetime import date
from typing import Optional

class SummaryState(Enum):
    RECIBIDO = "recibido"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"

class DomainException(Exception):
    pass

@dataclass(frozen=True)  # Inmutable para asegurar que las transiciones generen nuevos estados
class DailySummary:
    id: Optional[int]
    target_date: date
    group_name: str
    state: SummaryState
    raw_content_hash: str
    summary_text: Optional[str] = None
    error_message: Optional[str] = None

    @staticmethod
    def create_new(target_date: date, group_name: str, raw_content: str) -> "DailySummary":
        """Estado inicial: Crea el registro del día a procesar."""
        import hashlib
        content_hash = hashlib.sha256(raw_content.encode()).hexdigest()
        
        return DailySummary(
            id=None,
            target_date=target_date,
            group_name=group_name,
            state=SummaryState.RECIBIDO,
            raw_content_hash=content_hash
        )

    def transition_to_processing(self) -> "DailySummary":
        """Transición: El sistema empieza a hablar con el LLM."""
        if self.state != SummaryState.RECIBIDO and self.state != SummaryState.FALLIDO:
            raise DomainException(f"No se puede procesar un resumen en estado {self.state}")
        
        return DailySummary(
            id=self.id,
            target_date=self.target_date,
            group_name=self.group_name,
            state=SummaryState.PROCESANDO,
            raw_content_hash=self.raw_content_hash
        )

    def transition_to_completed(self, summary_text: str) -> "DailySummary":
        """Transición exitosa: Se guarda el resumen final."""
        if self.state != SummaryState.PROCESANDO:
            raise DomainException("Solo se puede completar un resumen que esté en procesamiento")
        if not summary_text.strip():
            raise DomainException("El texto del resumen no puede estar vacío")

        return DailySummary(
            id=self.id,
            target_date=self.target_date,
            group_name=self.group_name,
            state=SummaryState.COMPLETADO,
            raw_content_hash=self.raw_content_hash,
            summary_text=summary_text
        )

    def transition_to_failed(self, reason: str) -> "DailySummary":
        """Transición de error."""
        if self.state != SummaryState.PROCESANDO:
            raise DomainException("Estado de error inválido")
            
        return DailySummary(
            id=self.id,
            target_date=self.target_date,
            group_name=self.group_name,
            state=SummaryState.FALLIDO,
            raw_content_hash=self.raw_content_hash,
            error_message=reason
        )