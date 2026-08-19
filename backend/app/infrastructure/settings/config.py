# app/infrastructure/settings/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/escuela.db"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    
    # Pydantic Logfire Observabilidad
    LOGFIRE_TOKEN: str = ""
    LOGFIRE_ENVIRONMENT: str = "development"
    
    # Permitir sobreescribir desde variables de entorno y archivo .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()


