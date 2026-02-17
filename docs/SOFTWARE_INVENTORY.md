# Inventario Software - OAS Checker e-service

Documentazione completa di tutti i componenti software, dipendenze, versioni e licenze del progetto.

---

## Componenti Principali

### 1. e-service (FastAPI Application)

| Componente | Versione | Linguaggio | Purpose |
|------------|----------|------------|---------|
| **OAS Checker e-service** | 1.0.0 | Python 3.11+ | Microservizio FastAPI per l'orchestrazione della validazione OpenAPI. |

**Caratteristiche:**
- Architettura **Storage-less**: file e report salvati direttamente su PostgreSQL.
- **Loki Logging**: Log strutturati in JSON per integrazione nativa con Grafana/Loki.
- **Sicurezza**: Autenticazione JWT e protezione callback via HMAC-SHA256.

---

### 2. Azure Function (Validation Function)

| Componente | Versione | Linguaggio | Purpose |
|------------|----------|------------|---------|
| **Spectral Validation Function** | 1.0.0 | Python 3.11+ | Worker asincrono che esegue la Spectral CLI. |

**Caratteristiche:**
- Ricezione contenuti via payload HTTP (no storage round-trip).
- Esecuzione Spectral CLI.
- Logging JSON coerente con l'e-service.

---

## Dipendenze Python Principali

### Core Frameworks
- **FastAPI**: Web framework asincrono.
- **Uvicorn**: ASGI server production-ready.
- **Pydantic v2**: Validazione dati e schemi OpenAPI.

### Data & Database
- **asyncpg**: Driver PostgreSQL asincrono ad alte prestazioni.
- **aiosqlite**: Supporto SQLite per unit testing isolato.
- **PyYAML**: Parsing di file OpenAPI in formato YAML.

### Security & Utils
- **python-jose**: Gestione e decodifica dei token JWT.
- **httpx**: Client HTTP asincrono per chiamate alla validation function.
- **python-json-logger**: Formattazione dei log in JSON per Loki.
- **pytest-cov**: Generazione dei report di copertura del codice.