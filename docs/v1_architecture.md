# Arquitectura y Documentación Técnica - V1 (Escuela IA Bot)

## 📌 1. Visión General del Sistema
**Escuela IA Bot (V1)** es un servicio backend construido con **FastAPI** y **Arquitectura Hexagonal (Clean Architecture)**. Su objetivo principal es procesar exportaciones de historiales de grupos escolares (chats de WhatsApp y correos electrónicos), filtrar los mensajes correspondientes a una fecha específica, procesar imágenes adjuntas (como circulares o fotos de pizarrones) y utilizar **Google Gemini AI** para generar un resumen ejecutivo diario, estructurado y priorizado para los padres.

---

## 🛠️ 2. Stack Tecnológico

| Componente | Tecnología | Versión / Detalle |
| :--- | :--- | :--- |
| **Lenguaje** | Python | `3.11+` |
| **Framework Web** | FastAPI | `>=0.110.0` |
| **Servidor ASGI** | Uvicorn | `>=0.28.0` |
| **ORM / Persistencia** | SQLAlchemy | `>=2.0.0` |
| **Base de Datos** | SQLite | `data/escuela.db` |
| **IA / LLM** | Google GenAI SDK | `google-genai>=1.0.0` (Modelo `gemini-2.5-flash`) |
| **Orquestación** | Docker & Docker Compose | Contenedores para `fastapi-backend` y `n8n` |
| **Testing** | Pytest | `pytest>=8.0.0`, `pytest-asyncio` |

---

## 🏗️ 3. Arquitectura del Sistema (Clean / Hexagonal)

El sistema está dividido estrictamente en capas para desacoplar las reglas de negocio de los detalles de infraestructura:

```mermaid
graph TD
    Client[Cliente HTTP / n8n / API Client] -->|POST /reporte/procesar| Router[report_router.py]
    Router -->|Inyecta dependencias| UseCase[ProcessDailyReportUseCase]
    
    subgraph Aplicación / Dominio
        UseCase -->|Operaciones inmutables| Entity[DailySummary Entity]
        UseCase -->|Puerto Repo| RepoPort[DailySummaryRepository]
        UseCase -->|Puerto LLM| LLMPort[LLMService]
    end
    
    subgraph Infraestructura
        RepoPort <|.. SqliteRepo[SqliteDailySummaryRepository]
        LLMPort <|.. GeminiClient[GeminiLLMService]
        SqliteRepo -->|SQLAlchemy| DB[(SQLite DB)]
        GeminiClient -->|API Google| GeminiAPI[Google Gemini API]
    end
```

---

## 📂 4. Estructura de Directorios

```text
escuela-ia-bot/
├── docker-compose.yaml
├── pytest.ini
├── docs/
│   └── v1_architecture.md
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── app/
    │   ├── main.py                     # Entrypoint de FastAPI e inicialización de DB
    │   ├── domain/
    │   │   └── entities/
    │   │       └── daily_summary.py    # Entidad de Dominio y Máquina de Estados
    │   ├── ports/
    │   │   ├── repositories.py         # Interfaz abstracta de Repositorio
    │   │   └── llm_service.py          # Interfaz abstracta de Servicio LLM
    │   ├── application/
    │   │   └── services/
    │   │       └── orquestrator.py     # Caso de Uso ProcessDailyReportUseCase
    │   └── infrastructure/
    │       ├── api/
    │       │   └── report_router.py    # Endpoint HTTP POST /reporte/procesar y extractor ZIP
    │       ├── clients/
    │       │   └── gemini_client.py    # Implementación cliente Gemini con google-genai SDK
    │       ├── database/
    │       │   ├── models.py           # Modelos SQLAlchemy (DailySummaryModel)
    │       ├── repositories.py     # Implementación concreta SQLite
    │       ├── session.py          # Motor y sesión de base de datos
    │       └── dependencies.py     # Inyector de dependencias FastAPI
    │       └── settings/
    │           └── config.py           # Configuración Pydantic de entorno
    └── tests/
        ├── domain/
        │   └── test_orchestrator.py    # Test unitario del orquestador con Fakes
        └── infrastructure/
            └── test_sqlite_repository.py # Test de integración del repo SQLite
```

---

## ⚙️ 5. Detalles de Capas y Entidades (V1)

### A. Capa de Dominio (`app/domain/entities/daily_summary.py`)
- **`DailySummary`**: Dataclass inmutable (`frozen=True`).
- **Estados (`SummaryState`)**:
  - `RECIBIDO`: Estado inicial al registrar el archivo.
  - `PROCESANDO`: Durante la comunicación con la IA.
  - `COMPLETADO`: Cuando la IA responde exitosamente con el resumen final.
  - `FALLIDO`: Ante errores de dominio o comunicación.
- **Transiciones Inmutables**: `transition_to_processing()`, `transition_to_completed()`, `transition_to_failed()`.

### B. Capa de Puertos (`app/ports/`)
- **`DailySummaryRepository`**: Métodos `save(summary: DailySummary)` y `get_by_date(target_date: date)`.
- **`LLMService`**: Método `generate_summary(raw_content: str, group_name: str, images: Dict[str, bytes]) -> str`.

### C. Capa de Aplicación (`app/application/services/orquestrator.py`)
- **`ProcessDailyReportUseCase`**:
  1. Recibe `target_date`, `raw_content`, `group_name` e `images`.
  2. Ejecuta `_filtrar_chat_por_fecha()`: limpia el historial con expresiones regulares compatibles con formatos de fecha de Android e iOS (`DD/MM/YYYY`, `D/M/YY`), conservando únicamente líneas a partir de `target_date`.
  3. Asocia e incluye solo las imágenes que fueron mencionadas/adjuntas en el fragmento de chat de la fecha.
  4. Gestiona las transiciones de estado de la entidad y las persiste en la base de datos.

### D. Capa de Infraestructura (`app/infrastructure/`)
- **`report_router.py`**:
  - Parsea archivos subidos `.zip` (extrae `.txt` de chat y fotos `.jpg`/`.png`) o `.txt` en texto plano con autodetección de codificaciones (`utf-8`, `cp1252`, `latin-1`).
  - Extrae automáticamente el nombre del grupo eliminando prefijos habituales de WhatsApp (ej. `"Chat de WhatsApp con 4to A.zip"` ➔ `"4to A"`).
- **`gemini_client.py`**:
  - Instancia el cliente oficial `google.genai.Client`.
  - Construye un prompt especializado para rol de asistente escolar.
  - Adjunta las imágenes filtradas como partes multimodales (`types.Part.from_bytes`).
- **`database/`**:
  - Contiene el modelo ORM `DailySummaryModel`.
  - Incluye la restricción compuesta `UniqueConstraint("target_date", "group_name", name="uq_target_date_group")` para evitar resúmenes duplicados del mismo grupo el mismo día.

---

## 📡 6. Especificación de Endpoints HTTP

### `GET /`
- **Respuesta**: `{"status": "ok", "message": "Backend corriendo dentro de Docker"}`

### `POST /reporte/procesar`
- **Content-Type**: `multipart/form-data`
- **Parámetros**:
  - `file`: Archivo subido (`.zip` o `.txt`).
  - `target_date_str`: (Opcional) Fecha objetivo en formato `YYYY-MM-DD`. Si se omite, toma la fecha actual del sistema.
- **Respuesta exitosa**:
```json
{
  "status": "success",
  "group": "4to A",
  "data": "## Resumen del día 16/08/2026...\n- Tarea de Matemáticas para el viernes.\n- Recordatorio: Llevar uniforme de educación física."
}
```

---

## 🐳 7. Entorno y Despliegue Docker

El archivo `docker-compose.yaml` define dos servicios:
1. `fastapi-backend`:
   - Construido desde `./backend/Dockerfile`.
   - Expuesto en puerto `8000:8000`.
   - Volumen montado en `./data:/app/data` para persistencia del archivo SQLite `escuela.db`.
   - Requiere variable `GEMINI_API_KEY`.
2. `n8n`:
   - Imagen `docker.n8n.io/n8nio/n8n:latest`.
   - Expuesto en puerto `5678:5678`.
   - Configurado con tiempos de timeout de ejecuciones y guardado selectivo de logs en error.

---

## 🧪 8. Cobertura de Tests Unitarios e Integración

- `backend/tests/domain/test_orchestrator.py`: Valida todo el ciclo de vida del caso de uso usando `FakeDailySummaryRepository` y `FakeLLMService`.
- `backend/tests/infrastructure/test_sqlite_repository.py`: Valida el guardado, recuperación y actualización de transiciones de estado sobre una base SQLite en memoria (`sqlite:///:memory:`).
