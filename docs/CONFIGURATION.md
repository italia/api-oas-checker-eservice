# Configurazione e Variabili d'Ambiente

Il servizio OAS Checker è configurato interamente tramite variabili d'ambiente.

## Ordine di Precedenza

L'applicazione segue questo ordine (dal più forte al più debole):

1.  **Variabili di Sistema/Shell**: Impostate nel terminale o iniettate dal runtime (Docker, K8s).
2.  **File `.env`**: Caricato all'avvio (non sovrascrive variabili già presenti nel sistema).
3.  **Default nel codice**: Valori definiti in `config.py`.

---

## Lista delle Variabili

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| **Generali** | | |
| `ESERVICE_PORT` | Porta del servizio FastAPI | `8000` |
| `LOG_LEVEL` | Livello di logging (DEBUG, INFO, etc.) | `INFO` |
| **Database** | | |
| `DATABASE_URL` | URL di connessione PostgreSQL | `postgresql://...` |
| **Validation Backend** | | |
| `FUNCTION_TYPE` | Tipo di backend (`mock`, `azure`, `azure-local`) | `mock` |
| `FUNCTION_URL` | Endpoint della Validation Function | `http://localhost:8001` |
| `AZURE_FUNCTION_KEY` | Chiave API (solo per `FUNCTION_TYPE=azure`) | `""` |
| **Ruleset Management** | | |
| `RULESET_REPO` | Repo GitHub per download ruleset | `italia/api-oas-checker-rules` |
| `RULESET_VERSION` | Tag specifico o `latest` | `latest` |
| `RULESET_PATH` | Directory cache locale | `./data/rulesets` |
| `RULESET_AUTO_UPDATE` | Abilita download all'avvio | `true` |
| **Sicurezza** | | |
| `JWT_ENABLED` | Abilita validazione JWT (PDND) | `true` |
| `CALLBACK_SECRET` | Chiave segreta per firma HMAC | `dev-secret-...` |
| `HMAC_ENABLED` | Abilita verifica firma su callback | `true` |
| `HMAC_TIMESTAMP_WINDOW` | Finestra temporale callback (secondi) | `300` |
| **Rate Limiting** | | |
| `RATE_LIMIT_ENABLED` | Abilita controllo frequenza richieste | `true` |
| `RATE_LIMIT_VALIDATE_REQUESTS` | Richieste max per finestra (/oas/validate) | `10` |
| `RATE_LIMIT_VALIDATE_WINDOW` | Finestra temporale (secondi) | `60` |
