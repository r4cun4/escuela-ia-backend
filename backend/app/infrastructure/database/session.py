# app/infrastructure/database/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.settings.config import settings
from app.infrastructure.database.models import Base

DATABASE_URL = settings.DATABASE_URL

# Configuración especial para SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crea todas las tablas necesarias si no existen."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency para obtener una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
