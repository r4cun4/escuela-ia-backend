# Bitácora del Proyecto - Escuela IA Backend

## 📌 Estado Actual
- **Fase:** Integración y soporte en producción de flujos n8n y modelos LLM.
- **Madurez:** Proyecto en Python 3.12 gestionado con `uv` aplicando Arquitectura Hexagonal. Integración completa entre n8n (triggers de Gmail e IMAP, bot de Telegram) y FastAPI backend para procesamiento de avisos escolares, RAG y transcripción de audios.
- **Capacidades:** Procesamiento de notificaciones por email/WhatsApp, extracción de texto/adjuntos, consultas RAG sobre ChromaDB, y transcripción de audios con fallback resiliente entre modelos oficiales de Google Gemini (`gemini-flash-latest`, `gemini-3.8-flash`, `gemini-3.5-flash`, etc.).

## 🏗️ Decisiones Técnicas (ADRs)
- **Arquitectura Hexagonal:** Separación estricta entre capa de aplicación, puertos y adaptadores de infraestructura (`GeminiLLMService`, `ChromaAdapter`).
- **Resiliencia y Fallback de Modelos Gemini:** Adopción de la lista oficial de alias (`gemini-flash-latest`, `gemini-flash-lite-latest`) y modelos estables vigentes de Google Gemini en `GeminiLLMService._generate_with_fallback`. Ignora modelos obsoletos/deprecados por Google (`2.0-flash` / `1.5-flash`) y maneja backoff exponencial ante errores `429 RESOURCE_EXHAUSTED`.
- **Exportación / Respaldo de Tableros n8n:** Extracción de flujos desde `database.sqlite` a JSON (`escuela_ia_bot_workflow.json`) para facilitar la portabilidad del tablero en entornos locales nuevos.

## 🚀 Próximos Pasos (Roadmap)
- Validar el flujo end-to-end de envío de mensajes de voz en Telegram con transcripción vía Gemini.
- Probar el comportamiento de los endpoints `/reporte/procesar`, `/reporte/email` y `/reporte/buscar` bajo carga o lote con múltiples adjuntos.
- Monitorear consumo de cuotas de la API de Gemini y alertas en Logfire.

## 🐛 Bugs Conocidos y Limitaciones
- **Modelos obsoletos en API de Gemini:** Resuelto. Se removieron referencias a modelos `1.5-flash` y `2.0-flash` sustituyéndolas por modelos de producción activos.
- **Falta de adjunto en emails n8n:** Resuelto mediante la configuración de manejo de errores (*On Error: Continue*) en el nodo de n8n para emails sin binario `attachment_0`.

## 📝 Historial de Cambios

### [2026-09-25] - Actualización de Modelo en PRReviewerAgent
- **Calidad de análisis en CI/CD:** Se actualizó el modelo por defecto de `PRReviewerAgent` (`pr_reviewer.py`) de `gemini-1.5-pro` a `gemini-2.5-pro` para priorizar la calidad de análisis en revisiones automáticas de Pull Requests.

### [2026-09-24] - Soporte de Modelos Oficiales Gemini & Recuperación de n8n
- **Migración y Respaldo n8n:** Se recuperó el tablero del Bot de Escuela IA desde `database.sqlite` y se exportó a `escuela_ia_bot_workflow.json`.
- **Resiliencia en Gemini Client:** Se actualizó `GeminiLLMService` (`gemini_client.py`) integrando `transcribe_audio_query` con la estrategia `_generate_with_fallback`.
- **Actualización de Modelos Gemini:** Se reemplazaron modelos deprecados por la lista oficial de la API de Google Gemini (`gemini-flash-latest`, `gemini-3.8-flash`, `gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-flash-lite-latest`).
- **Despliegue:** Reinicio exitoso del servicio `fastapi-backend` en Docker.

### [2026-09-24] - Mejora en el Fallback de Gemini Client
- Se refactorizó la lógica de reintentos y fallback en `GeminiLLMService` (`gemini_client.py`).
- Se implementó filtro de excepciones para reintentar con backoff exponencial (1s, 2s, 4s) en errores `429` (Rate limit) o `500`.

### [2026-09-24] - Creación de la Bitácora Inicial
- Relevamiento general de la estructura del repositorio (`pyproject.toml`, `README.md`, componentes en `backend/app`).
- Inicialización del archivo `PROGRESS.md` siguiendo la especificación del skill `project-logger`.
