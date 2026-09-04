# Escuela IA Bot 🤖

> **Asistente Inteligente de Comunicaciones Escolares**  
> Procesa exportaciones de WhatsApp, correos institucionales, adjuntos PDF, imágenes de cuadernos/pizarrones y notas de voz para generar resúmenes diarios estructurados y priorizados para los padres mediante **Google Gemini 3.6 Flash**, **RAG en ChromaDB**, **FastAPI** y **n8n + Telegram**.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)
![Gemini AI](https://img.shields.io/badge/Google_Gemini-3.6_Flash-8E44AD.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)
![Architecture](https://img.shields.io/badge/Architecture-Hexagonal-orange.svg)

---

## 📌 Tabla de Contenidos

- [Acerca del Proyecto](#-acerca-del-proyecto)
- [Características Principales](#-características-principales)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Stack Tecnológico](#-stack-tecnológico)
- [Prerrequisitos](#-prerrequisitos)
- [Configuración y Variables de Entorno](#-configuración-y-variables-de-entorno)
- [Despliegue con Docker](#-despliegue-con-docker)
- [Uso y API Endpoints](#-uso-y-api-endpoints)
- [Ejecución de Tests](#-ejecución-de-tests)
- [Licencia](#-licencia)

---

## 💡 Acerca del Proyecto

> *"La verdad es que necesito un Jarvis que me ayude a estar al día con la rutina escolar sin tener que revisar constantemente miles de mensajes en los grupos de padres."*

En el contexto escolar actual, la gran cantidad de mensajes diarios en grupos de WhatsApp, notas en cuadernos de comunicaciones, fotos de pizarras, circulares y correos electrónicos puede ser abrumadora para cualquier familia.

**Escuela IA Bot** nace para resolver este problema actuando como ese asistente inteligente personal (estilo Jarvis):
1. **Recibe** archivos de exportación de chat (`.zip` o `.txt`), correos y notas de voz.
2. **Filtra y extrae** la información relevante para una fecha u objetivo específico.
3. **Analiza imágenes y documentos adjuntos** utilizando visión artificial multimodal.
4. **Almacena vectores e incrustaciones (RAG)** en ChromaDB para búsquedas contextuales avanzadas.
5. **Genera un resumen diario claro, priorizado y accionable** (tareas, eventos, evaluaciones, recordatorios).

---

## ✨ Características Principales

* 💬 **Procesamiento de Chats de WhatsApp**: Limpieza y parseo de historiales con soporte para formatos de fecha Android e iOS (`DD/MM/YYYY`, `D/M/YY`).
* 🖼️ **Visión Multimodal**: Lectura automática de imágenes de notas, cuadernos y pizarrones adjuntas en el chat.
* 🎙️ **Notas de Voz & Audio**: Transcripción y consulta de audios utilizando búsqueda por voz y RAG.
* 📧 **Adjuntos PDF y Mails**: Extracción de datos importantes de circulares oficiales e información enviada por email.
* 🧠 **RAG Nativo (ChromaDB)**: Indexado vectorial alimentado con `gemini-embedding-001` para consultas de contexto histórico.
* 🤖 **Agente Inteligente con Pydantic AI**: Orquestación estructurada de agentes e integración con **Logfire** para observabilidad en tiempo real.
* ⚡ **Integración n8n + Telegram**: Flujos automáticos que reciben mensajes de Telegram y los envían al backend a través de un túnel persistente con **ngrok**.

---

## 🏗️ Arquitectura del Sistema

El proyecto sigue los principios de **Arquitectura Hexagonal (Clean Architecture)** para desacoplar totalmente la lógica del dominio de la infraestructura y servicios de IA.

```mermaid
graph TD
    Client[Cliente / Telegram / n8n] -->|POST /reporte/procesar| Router[report_router.py]
    Router -->|Inyecta dependencias| UseCase[ProcessDailyReportUseCase]
    
    subgraph Aplicación / Dominio
        UseCase -->|Entidad| Entity[DailySummary]
        UseCase -->|Puerto Repo| RepoPort[DailySummaryRepository]
        UseCase -->|Puerto LLM| LLMPort[LLMService]
        UseCase -->|Puerto Vectorial| VectorPort[VectorStorePort]
    end
    
    subgraph Infraestructura
        RepoPort <|.. SqliteRepo[SqliteDailySummaryRepository]
        LLMPort <|.. GeminiClient[GeminiLLMService]
        VectorPort <|.. ChromaAdapter[ChromaAdapter]
        
        SqliteRepo -->|Persistencia| DB[(SQLite DB)]
        GeminiClient -->|SDK google-genai| GeminiAPI[Google Gemini 3.6 Flash]
        ChromaAdapter -->|Vector DB| Chroma[(ChromaDB)]
    end
```

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Backend** | Python 3.11+, FastAPI | API REST asíncrona de alto rendimiento |
| **Modelos de IA** | Google Gemini 3.6 Flash | Procesamiento multimodal de texto, visión e imágenes |
| **Embeddings & RAG**| ChromaDB + Gemini Embeddings | Base de datos vectorial persistente |
| **Agentes & Tracing**| Pydantic AI, Pydantic Logfire | Estructuración de agentes y trazabilidad |
| **Persistencia** | SQLAlchemy + SQLite | Registro relacional de historiales y estados |
| **Automatización** | n8n + ngrok | Integración de flujos de trabajo y túnel persistente para webhooks |
| **Contenedores** | Docker & Docker Compose | Entorno encapsulado multilabor |

---

## 📋 Prerrequisitos

Antes de comenzar, asegúrate de contar con:
* [Python 3.11+](https://www.python.org/downloads/)
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* Una **API Key de Google Gemini** (obtenible en [Google AI Studio](https://aistudio.google.com/))
* Una cuenta y **Authtoken de ngrok** (con un dominio estático gratuito configurado en [ngrok Dashboard](https://dashboard.ngrok.com/))
* (Opcional) Token de [Logfire](https://logfire.pydantic.dev/) para observabilidad.

---

## ⚙️ Configuración y Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto basándote en el siguiente ejemplo:

```env
# Google Gemini API
GEMINI_API_KEY=tu_api_key_de_gemini
GEMINI_API_VERSION=v1

# Configuración de Base de Datos
DATABASE_URL=sqlite:///./data/escuela.db
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# Pydantic Logfire (Opcional)
LOGFIRE_TOKEN=tu_token_de_logfire
LOGFIRE_ENVIRONMENT=development

# Telegram & n8n
TELEGRAM_BOT_TOKEN=tu_bot_token_telegram
N8N_WEBHOOK_URL=https://tu-dominio.ngrok-free.dev

# ngrok
NGROK_AUTHTOKEN=tu_authtoken_de_ngrok
```

---

## 🐳 Despliegue con Docker

Para levantar toda la infraestructura (FastAPI Backend, n8n y el contenedor de túnel ngrok):

```powershell
# Clonar el repositorio
git clone https://github.com/r4cun4/escuela-ia-bot.git
cd escuela-ia-bot

# Iniciar los servicios con Docker Compose
docker compose up -d --build
```

Los servicios estarán disponibles en:
* **FastAPI Backend**: `http://localhost:8000`
* **Documentación Swagger UI**: `http://localhost:8000/docs`
* **n8n Workflow**: `http://localhost:5678`

### Configuración del Túnel ngrok
El servicio `ngrok` en `docker-compose.yaml` expone n8n hacia Internet usando una URL estática gratuita (`--url=https://tu-dominio.ngrok-free.dev`). Esto garantiza que el webhook de Telegram configurado en n8n permanezca persistente sin necesidad de scripts de actualización dinámica.

---

## 📡 Uso y API Endpoints

### 1. Estado del Servicio
```http
GET /
```
**Respuesta:** `{"status": "ok", "message": "Backend corriendo dentro de Docker"}`

### 2. Procesar Reporte Diario
```http
POST /reporte/procesar
Content-Type: multipart/form-data
```

| Parámetro | Tipo | Requerido | Descripción |
| :--- | :--- | :--- | :--- |
| `file` | File (`.zip` o `.txt`) | **Sí** | Archivo con la exportación del chat de WhatsApp |
| `target_date_str` | String (`YYYY-MM-DD`)| No | Fecha objetivo (por defecto toma el día actual) |

**Ejemplo de respuesta (`200 OK`):**
```json
{
  "status": "success",
  "group": "4to A",
  "data": "## 📅 Resumen Escolar - 31/08/2026\n\n### 📝 Tareas Pendientes:\n- **Matemáticas**: Ejercicios de la pág. 45 para el viernes.\n\n### 📢 Avisos Importantes:\n- Mañana no olvidar traer el cuaderno de comunicaciones firmado.\n- Fotos de la feria de ciencias adjuntas al informe."
}
```

---

## 🧪 Ejecución de Tests

Para ejecutar la suite de pruebas unitarias e integración:

```bash
# Crear entorno virtual e instalar dependencias
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # En Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# Ejecutar pytest
pytest
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más información.
