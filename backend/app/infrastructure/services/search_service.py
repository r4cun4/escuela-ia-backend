# app/infrastructure/services/search_service.py
"""
Módulo puente de compatibilidad retroactiva.
GracefulSearchService ha sido reubicado en app.application.services.search_service
para respetar la Arquitectura Hexagonal (evitando que la capa de aplicación dependa de infraestructura).
"""

from app.application.services.search_service import GracefulSearchService

__all__ = ["GracefulSearchService"]
