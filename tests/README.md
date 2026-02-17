# Test Suite - OAS Checker e-service

Suite di test completa per la validazione della logica di business, della sicurezza e delle API del servizio.

## Strategia di Test

Il progetto utilizza un approccio a più livelli per garantire la massima affidabilità:
1.  **Unit Tests (Isolati)**: Verifica della logica pura, del database (tramite SQLite) e dei componenti interni senza dipendenze esterne.
2.  **Integration Tests (PostgreSQL)**: Verifica dell'integrazione reale con il database di produzione.
3.  **End-to-End (E2E)**: Verifica dell'intero flusso operativo, dall'upload alla ricezione del report finale, inclusa la validazione delle firme HMAC.

## Prerequisiti

Le dipendenze per l'esecuzione dei test sono incluse nel file `requirements.txt` principale.

```bash
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite
```

## Esecuzione Test

### 1. Test Unitari e E2E (SQLite)
Questi test coprono la logica del database, la business logic e il flusso completo utilizzando **SQLite**, garantendo la correttezza del codice senza necessità di infrastruttura esterna.

```bash
# Esecuzione dei test (esclusi quelli di integrazione PostgreSQL)
pytest -v -m "not integration"
```

### 2. Test di Integrazione (PostgreSQL)
Questi test verificano che la connessione e le query specifiche per PostgreSQL vengano eseguite correttamente.

```bash
# Avvio di PostgreSQL tramite Docker
docker-compose up -d postgres

# Esecuzione dei test di integrazione
pytest -v -m integration
```

### 3. Report di Copertura (Coverage)
La suite è progettata per mantenere una copertura del codice superiore all'80%.

```bash
# Generazione del report di copertura
pytest --cov=. --cov-report=term-missing
```

## Struttura della Suite

| File | Descrizione |
|------|-------------|
| `test_api.py` | Endpoint API, conformità ModI e RFC 9457. |
| `test_validation_service.py` | Orchestrazione della validazione (flusso storage-less). |
| `test_ruleset_manager.py` | Download da GitHub e gestione della cache dei ruleset. |
| `test_azure_validator.py` | Logica di validazione Spectral (shared component). |
| `test_e2e.py` | Test End-to-End del ciclo di vita completo (con HMAC). |
| `test_down_converter.py` | Conversione OpenAPI 3.1.0 -> 3.0.3. |
| `test_jwt_auth.py` | Autenticazione e autorizzazione JWT. |
| `test_hmac.py` | Sicurezza delle callback tramite firma HMAC. |
| `test_rate_limit.py` | Algoritmo di limitazione delle richieste. |

## Note Tecniche
*   **HMAC**: I test utilizzano i moduli condivisi in `shared/` per generare firme valide, garantendo la coerenza con la logica di produzione.
*   **Fixtures**: `tests/conftest.py` gestisce l'inizializzazione automatica del database temporaneo e la configurazione dei mock.