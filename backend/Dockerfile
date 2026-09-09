FROM python:3.12-slim

# Instalar uv dentro del contenedor de forma eficiente
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Evitar que Python escriba archivos .pyc y asegurar que los logs salgan directo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"

# Copiar primero archivos de dependencias para aprovechar la caché de Docker
COPY pyproject.toml uv.lock ./

# Instalar dependencias del proyecto de forma reproducible sin paquetes de desarrollo
RUN uv sync --frozen --no-install-project --no-dev

# Copiar el código del backend
COPY backend/ /app/

# Comando por defecto para levantar FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]