from datetime import date
from typing import Optional
from sqlalchemy import String, Date, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.entities.daily_summary import DailySummary, SummaryState


class Base(DeclarativeBase):
    pass


class DailySummaryModel(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )  # 1. unique=True REMOVIDO
    group_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # 2. NUEVO CAMPO (Soporta emojis largos)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 3. Restricción única compuesta: evita duplicados del MISMO grupo el MISMO día
    __table_args__ = (
        UniqueConstraint("target_date", "group_name", name="uq_target_date_group"),
    )

    def to_domain(self) -> DailySummary:
        """Convierte este modelo de base de datos a la entidad de dominio."""
        return DailySummary(
            id=self.id,
            target_date=self.target_date,
            group_name=self.group_name,  # 4. Mapeo inyectado al dominio
            state=SummaryState(self.state),
            raw_content_hash=self.raw_content_hash,
            summary_text=self.summary_text,
            error_message=self.error_message,
        )

    @classmethod
    def from_domain(cls, domain: DailySummary) -> "DailySummaryModel":
        """Crea una instancia de este modelo a partir de la entidad de dominio."""
        return cls(
            id=domain.id,
            target_date=domain.target_date,
            group_name=domain.group_name,  # 5. Mapeo inyectado desde el dominio
            state=domain.state.value,
            raw_content_hash=domain.raw_content_hash,
            summary_text=domain.summary_text,
            error_message=domain.error_message,
        )
