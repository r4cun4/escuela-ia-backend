# app/infrastructure/database/repositories.py
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.entities.daily_summary import DailySummary
from app.ports.repositories import DailySummaryRepository
from app.infrastructure.database.models import DailySummaryModel

class SqliteDailySummaryRepository(DailySummaryRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, summary: DailySummary) -> DailySummary:
        """Guarda o actualiza un DailySummary en la persistencia."""
        if summary.id is None:
            # Es un nuevo resumen diario
            model = DailySummaryModel.from_domain(summary)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return model.to_domain()
        else:
            # Es una actualización de un resumen existente
            model = self.session.query(DailySummaryModel).filter_by(id=summary.id).first()
            if model:
                model.state = summary.state.value
                model.raw_content_hash = summary.raw_content_hash
                model.summary_text = summary.summary_text
                model.error_message = summary.error_message
                self.session.commit()
                self.session.refresh(model)
                return model.to_domain()
            else:
                # No se encontró pero tiene ID, lo creamos
                model = DailySummaryModel.from_domain(summary)
                self.session.add(model)
                self.session.commit()
                self.session.refresh(model)
                return model.to_domain()

    def get_by_date(self, target_date: date) -> Optional[DailySummary]:
        """Recupera el resumen de una fecha específica."""
        model = self.session.query(DailySummaryModel).filter_by(target_date=target_date).first()
        if model:
            return model.to_domain()
        return None
