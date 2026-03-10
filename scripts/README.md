# Scripts

Strumenti per sviluppo e manutenzione.

## Bash

| Script | Descrizione |
|---|---|
| `setup.sh` | Crea venv, installa dipendenze, genera `.env` iniziale |
| `start.sh` / `stop.sh` | Avvio e arresto dei servizi in locale (eservice + mock worker) |
| `rotate_callback_secret.sh` | Rotazione della chiave HMAC per le callback |
| `test_validation.sh` | Test funzionale: invia un file OAS e attende il report |

## Python

| Script | Descrizione |
|---|---|
| `generate_openapi.py` | Genera gli schemi OpenAPI 3.1.0 e 3.0.3 (`openapi.yaml`, `openapi_v3.yaml`) |
| `clear_db.py` | Svuota le tabelle validazioni e rate limit |
