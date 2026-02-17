# Guida Rapida - OAS Checker e-service

Questa guida permette di avviare il sistema completo in pochi minuti utilizzando Docker.

## Prerequisiti

- **Docker** e **Docker Compose** installati.
- Porte **8000** (API), **5432** (PostgreSQL) e **7071** (Function) libere.

## Architettura

Il sistema è **completamente Storage-less**: non richiede Azure Blob Storage o volumi condivisi. Tutto lo scambio di dati avviene via HTTP e PostgreSQL.

1.  **e-service**: Gestisce le API e persiste i dati su DB.
2.  **PostgreSQL**: Memorizza metadati, file OpenAPI e report JSON.
3.  **Validation Function**: Esegue Spectral sui contenuti ricevuti via payload.

## 1. Avvio Rapido

Dalla root del progetto, è possibile eseguire:

```bash
docker-compose up -d
```

Verifica dello stato:
```bash
docker-compose ps
```

## 2. Test di Validazione

Invio di un file di esempio (richiede l'header `Authorization` con un Voucher PDND valido o JWT di test):
```bash
curl -X POST http://localhost:8000/oas/validate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@examples/example_api.yml" \
  -F "ruleset=spectral-modi"
```

A seguito della richiesta verrà restituito un `validation_id`. È possibile utilizzarlo per recuperare il report (si raccomanda di attendere circa 3-5 secondi):
```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/oas/report/{validation_id}
```

## 3. Note sulla Sicurezza (Local Dev)

Di default nel `docker-compose.yml`, la sicurezza potrebbe essere abilitata. In caso di ricezione di un errore `401 Unauthorized`:

- **JWT**: Per test rapidi, è possibile disabilitare la verifica impostando `JWT_ENABLED=false` nel file `.env` o passare un header `Authorization: Bearer <token>` se GovWay è attivo.
- **HMAC**: La comunicazione tra Function ed e-service è protetta. È necessario assicurarsi che `CALLBACK_SECRET` sia identico in entrambi i servizi.

## 4. Comandi Utili


| Azione | Comando |
|--------|---------|
| Visualizzazione Log (JSON) | `docker-compose logs -f` |
| Esecuzione Test | `pytest -v -m "not integration"` |
| Esecuzione Test E2E | `pytest -v tests/test_e2e.py` |
| Rigenerazione OpenAPI | `python scripts/generate_openapi.py` |
| Verifica Status | `curl http://localhost:8000/status` |

## 4. Documentazione API

- **Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI Legacy (3.0.3)**: `openapi_v3.yaml` (nella root)