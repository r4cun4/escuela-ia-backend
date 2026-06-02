FROM python:3.11-slim

# Instalar uv dentro del contenedor de forma eficiente
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Evitar que Python escriba archivos .pyc y asegurar que los logs salgan directo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copiar e instalar las dependencias usando uv
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copiar el resto del código del backend
COPY . .

# Comando por defecto para cuando levantemos FastAPI más adelante
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]