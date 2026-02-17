# OAS Checker E-Service

Microservizio per la validazione di file OpenAPI tramite Spectral, progettato per essere scalabile, sicuro e conforme alle linee guida ModI della Pubblica Amministrazione.

## Caratteristiche Principali

- **Architettura Storage-less**: Tutti i file e i report sono persistiti direttamente in PostgreSQL (campi TEXT e JSONB), garantendo semplicità e velocità di accesso.
- **Asincronia Nativa**: Gestione delle richieste tramite worker asincroni (Azure Function o Mock locale) con risposta immediata `202 Accepted`.
- **OpenAPI Compliance**: Generazione automatica di schemi OpenAPI 3.1.0 e 3.0.3 per garantire massima compatibilità con gli strumenti della PA (es. validatore ModI).
- **Monitoring & Logging**: Integrazione con Loki via structured JSON logging.
- **Sicurezza Enterprise**: Autenticazione JWT e protezione delle callback tramite firma HMAC-SHA256.
- **High Performance**: Connection pooling nativo per PostgreSQL via asyncpg.

## Flusso Operativo

1.  **Invio**: Caricamento di un file OpenAPI tramite `POST /oas/validate`.
2.  **Persistenza**: Salvataggio del contenuto del file nel database e generazione di un `validation_id`.
3.  **Validazione**: Invocazione asincrona della Validation Function con invio del contenuto via HTTP.
4.  **Esito**: Esecuzione di Spectral da parte della Function e invio del report JSON all'E-Service via callback.
5.  **Recupero**: Consultazione del report finale tramite `GET /oas/report/{id}`.

## Documentazione

Tutta la documentazione tecnica è disponibile nella cartella `docs/`:

### 🚀 Guide Rapide
- [Guida Rapida](docs/QUICKSTART.md) - Per l'avvio rapido con Docker.
- [Configurazione](docs/CONFIGURATION.md) - Lista variabili d'ambiente e ordine di precedenza.
- [Infrastruttura GovWay](docs/GOVWAY_README.md) - Dettagli sull'integrazione con il gateway.

### 🛠️ Architettura e Dati
- [Modello Dati](docs/DATA_MODEL.md) - Schema PostgreSQL e performance.
- [Ciclo di Vita dei Dati](docs/FILE_LIFECYCLE.md) - Come vengono gestiti file e report.
- [Gestione Ruleset](docs/RULESETS.md) - Download automatico e aggiornamento dei ruleset.
- [Utilizzo OpenAPI](docs/OPENAPI_USAGE.md) - Dettagli sulla generazione degli schemi 3.1.0 e 3.0.3.

### 🔐 Sicurezza e Qualità
- [Autenticazione JWT](docs/JWT_AUTH.md) - Integrazione con PDND/GovWay.
- [Sicurezza Callback (HMAC)](docs/HMAC_CALLBACK.md) - Protezione dell'integrità dei dati.
- [Rate Limiting](docs/RATE_LIMITING.md) - Controllo della frequenza delle richieste.
- [Suite di Test](tests/README.md) - Strategia di test, E2E e coverage.
- [Piano di Test](docs/TEST_PLAN.md) - Casi di test e criteri di accettazione.
- [Inventario Software](docs/SOFTWARE_INVENTORY.md) - Componenti e licenze.

## Requisiti

- **Python 3.11+**
- **PostgreSQL**
- **Docker & Docker Compose**

## Deployment



Il sistema può essere avviato in due modalità tramite lo script `run-oas.sh`:



- **Modalità Bridge (Default)**: Utilizza la rete isolata di Docker. Ideale per ambienti di produzione o test standard.

- **Modalità Host**: Condivide lo stack di rete dell'host. Utile per risolvere problemi di binding su sistemi dove le porte sono già parzialmente occupate o per integrazioni di rete particolari.



### Avvio rapido con script



```bash

# Avvio standard (Bridge)

./run-oas.sh



# Avvio in modalità Host con porte personalizzate

./run-oas.sh --mode host --port-api 8080 --port-func 9090 --port-db 15432

```



| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `-m, --mode` | Modalità di rete (`bridge` o `host`) | `bridge` |
| `-p, --port-api` | Porta per le API dell'e-service | `8000` |
| `-f, --port-func` | Porta per la Azure Function | `7071` |
| `-db, --port-db` | Porta per PostgreSQL | `15432` |



## Sviluppo e Test



```bash

# Esecuzione dei test (Unit + Logic)

pytest -v -m "not integration"



# Esecuzione test End-to-End

pytest -v tests/test_e2e.py

```
