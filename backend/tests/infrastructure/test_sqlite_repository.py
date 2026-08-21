# tests/infrastructure/test_sqlite_repository.py
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities.daily_summary import DailySummary, SummaryState
from app.infrastructure.database.models import Base
from app.infrastructure.database.repositories import SqliteDailySummaryRepository

@pytest.fixture
def db_session():
    # Usamos una base de datos SQLite en memoria para tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_save_and_get_by_date(db_session):
    repo = SqliteDailySummaryRepository(db_session)
    hoy = date(2026, 6, 2)
    
    # 1. Crear y guardar un nuevo resumen diario
    summary = DailySummary.create_new(hoy, "Grupo Test", "Contenido de prueba")
    saved_summary = repo.save(summary)
    
    # Verificar que se asignó un ID autoincremental
    assert saved_summary.id is not None
    assert saved_summary.state == SummaryState.RECIBIDO
    
    # 2. Recuperar el resumen por fecha
    retrieved = repo.get_by_date(hoy)
    assert retrieved is not None
    assert retrieved.id == saved_summary.id
    assert retrieved.raw_content_hash == saved_summary.raw_content_hash
    
    # 3. Transicionar de estado y guardar actualización
    processing_summary = retrieved.transition_to_processing()
    updated_summary = repo.save(processing_summary)
    
    # Verificar que el estado se actualizó en la base de datos
    retrieved_updated = repo.get_by_date(hoy)
    assert retrieved_updated.state == SummaryState.PROCESANDO
    assert retrieved_updated.id == saved_summary.id
