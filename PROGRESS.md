# Bitácora del Proyecto - Escuela IA Backend

## 📌 Estado Actual
- **Fase:** Desarrollo inicial y estructuración de la arquitectura base.
- **Madurez:** Proyecto en Python 3.12 utilizando la herramienta de gestión `uv`. El sistema implementa los principios de Arquitectura Hexagonal (Clean Architecture) organizados en `backend/app/` (`domain`, `application`, `ports`, `infrastructure`).
- **Capacidades:** Asistente inteligente (Jarvis escolar) para procesar exportaciones de WhatsApp, PDFs, imágenes de pizarrones/cuadernos y notas de voz. Genera resúmenes diarios estructurados utilizando Google Gemini 3.6 Flash, RAG sobre ChromaDB, FastAPI y flujos n8n + Telegram.

## 🏗️ Decisiones Técnicas (ADRs)
- **Arquitectura Hexagonal:** Separación estricta de puertos y adaptadores para desacoplar la lógica de negocio de los proveedores externos de modelos LLM (Gemini API) y persistenia relacional/vectorial.
- **Gestión de dependencias con UV:** Definición del entorno en `pyproject.toml` y empaquetamiento optimizado para acelerar la instalación y resolución de dependencias.
- **Pydantic AI y Logfire:** Adopción de Pydantic AI para agentes con tipado estricto e integración de Logfire para trazabilidad y observabilidad en tiempo real.
- **Base Vectorial ChromaDB:** Almacenamiento vectorial persistente con embeddings `gemini-embedding-001` para consultas RAG contextuales sobre historiales escolares.

## 🚀 Próximos Pasos (Roadmap)
- Validar la ejecución de la suite de pruebas unitarias/integración con `pytest`.
- Verificar el funcionamiento de los adaptadores de infraestructura (`GeminiLLMService`, `ChromaAdapter`, `SqliteDailySummaryRepository`).
- Probar el despliegue multi-contenedor con `docker-compose.yaml` (backend, n8n y túnel ngrok).

## 🐛 Bugs Conocidos y Limitaciones
- Sin problemas bloqueantes detectados durante el relevamiento inicial.

## 📝 Historial de Cambios

### [2026-09-24] - Creación de la Bitácora Inicial
- Relevamiento general de la estructura del repositorio (`pyproject.toml`, `README.md`, componentes en `backend/app`).
- Inicialización del archivo `PROGRESS.md` siguiendo la especificación del skill `project-logger`.
