# Azure Function - ProcessValidation

Questa Azure Function funge da worker asincrono per la validazione di documenti OpenAPI (Swagger) utilizzando la CLI ufficiale di [Spectral](https://rules.stoplight.io/).

## Architettura

La funzione è implementata in Python ed è progettata per essere eseguita in un ambiente containerizzato (Azure Functions on Container) o come funzione standard. 

### Caratteristiche principali:
- **Stateless**: Non richiede storage persistente per l'elaborazione.
- **Asincrona**: Risponde immediatamente al chiamante e invia i risultati tramite una callback HTTP.
- **Sicura**: Implementa la firma HMAC-SHA256 per le notifiche di callback.
- **Estensibile**: Supporta ruleset Spectral personalizzati e funzioni custom.

## Requisiti

- **Python 3.11**
- **Node.js 20+** (per Spectral CLI)
- **Spectral CLI** (`@stoplight/spectral-cli`)

## Configurazione

Le seguenti variabili d'ambiente devono essere configurate:

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `CALLBACK_SECRET` | Chiave segreta per la generazione della firma HMAC nelle callback. | (obbligatoria in prod) |
| `RULESET_FUNCTIONS_PATH` | Percorso locale alle funzioni Spectral personalizzate. | `/home/site/wwwroot/data/rulesets/functions` |
| `FUNCTIONS_WORKER_RUNTIME` | Runtime della funzione. | `python` |

## API Interface

### POST `/api/ProcessValidation`

Avvia un processo di validazione.

#### Payload (JSON):
```json
{
  "validation_id": "uuid-string",
  "file_content": "contenuto del file openapi (YAML o JSON)",
  "callback_url": "https://your-service.com/callback",
  "ruleset_name": "default",
  "ruleset_content": "estensione del ruleset spectral (opzionale)",
  "errors_only": false
}
```

#### Risposta (200 OK):
```json
{
  "validation_id": "uuid-string",
  "status": "success",
  "message": "Validation completed and callback initiated"
}
```

### Callback

I risultati vengono inviati all'URL specificato in `callback_url`. La richiesta include gli header:
- `X-Signature`: Firma HMAC-SHA256 del payload.
- `X-Timestamp`: Timestamp utilizzato per la firma.

## Sviluppo Locale

1. Installa le dipendenze Python:
   ```bash
   pip install -r requirements.txt
   ```
2. Installa Spectral CLI:
   ```bash
   npm install -g @stoplight/spectral-cli
   ```
3. Avvia la funzione:
   ```bash
   func start
   ```

## Docker

È disponibile un `Dockerfile` ottimizzato per il deployment su Azure Container Apps o Azure Functions on Container.

```bash
docker build -t oas-checker-function .
docker run -p 7071:80 -e CALLBACK_SECRET=tuasegreta oas-checker-function
```

## Struttura del Progetto

- `ProcessValidation/`: Entry point della Azure Function.
- `shared/`: Logica condivisa (validazione, sicurezza, utility).
- `Dockerfile`: Configurazione per la containerizzazione.
- `host.json`: Configurazione globale dell'host Azure Functions.