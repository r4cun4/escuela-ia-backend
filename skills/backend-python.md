# Skill: Backend Python & FastAPI

## Stack y Herramientas
- **Ecosistema:** Python, FastAPI, SQLAlchemy, Alembic, Celery, Docker.
- **Herramientas:** Ruff (linter/formateador), PydanticAI, Gestor uv.

## Arquitectura y Clean Code
- **Arquitectura:** Hexagonal / Puertos y Adaptadores (domain, pplication, ports, infrastructure).
- **SRP:** Mantener domain y pplication (casos de uso) enfocados en una sola regla de negocio.
- **DIP:** Inyectar dependencias de infrastructure a través de abstracciones en ports. Usar Depends de FastAPI.
- **DRY & Estilo:** Priorizar *early returns* para reducir anidamiento. Funciones cortas y descriptivas.

## Reglas de IA (PydanticAI)
- **EXCEPCIÓN DE IDIOMA:** Los docstrings de funciones decoradas con @tool de PydanticAI y descripciones de Field(description="...") DEBEN estar en **inglés** para el function calling del LLM.

## Bases de Datos
- **Alembic:** NUNCA ejecutar comandos que apliquen migraciones (lembic upgrade); las aplico manualmente. Evitar colisiones de evision_id.