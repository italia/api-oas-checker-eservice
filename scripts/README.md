# Script di Gestione

Directory contenente strumenti per l'automazione delle attività di sviluppo e manutenzione.

## Script Bash (.sh)

### 📦 setup.sh
Configura l'ambiente di sviluppo locale:
- Creazione del virtual environment (`venv`).
- Installazione delle dipendenze Python.
- Creazione delle directory per la cache dei ruleset.
- Generazione del file `.env` iniziale.

### 🚀 start.sh / stop.sh
Avvio e arresto dei servizi in modalità sviluppo locale (e-service + Mock Function).

### 🔑 rotate_callback_secret.sh
Utility per la rotazione della chiave segreta HMAC utilizzata per la sicurezza delle callback tra la Function e l'e-service.

### 🧪 test_validation.sh
Script per l'esecuzione di un test funzionale completo: invio di un file OAS e attesa dell'esito della validazione.

## Script Python (.py)

### 🛠️ generate_openapi.py
Genera gli schemi OpenAPI del progetto in due versioni:
- `openapi.yaml/json`: Versione **3.1.0** (moderna).
- `openapi_v3.yaml/json`: Versione **3.0.3** (legacy per compatibilità Spectral).

### 🧹 clear_db.py
Utility per la pulizia delle tabelle del database (rimozione di tutte le validazioni e record di rate limit).
