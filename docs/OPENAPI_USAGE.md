# Utilizzo Schemi OpenAPI

Il servizio OAS Checker genera automaticamente la propria documentazione API in diversi formati per garantire la massima compatibilità con validatori e client diversi.

## Versioni Disponibili

Ad ogni avvio del servizio, vengono generati o aggiornati i seguenti file nella root del progetto:

| File | Versione OAS | Destinazione d'uso |
|------|--------------|--------------------|
| `openapi.yaml` | **3.1.0** | Versione moderna per Swagger UI, Redoc e client di ultima generazione. |
| `openapi_v3.yaml` | **3.0.3** | **Versione Legacy** per validatori ModI, API Gateway datati e tool che non supportano OAS 3.1. |

## Caratteristiche della Versione Legacy (3.0.3)

La versione `openapi_v3.yaml` viene prodotta tramite un processo di down-conversion automatico che risolve le incompatibilità comuni:
- **Nullability**: Converte i blocchi moderni `anyOf: [..., {type: 'null'}]` nel formato `type: ..., nullable: true`.
- **Metadata**: Sposta il campo `info.summary` in `info.x-summary` per evitare errori di validazione.
- **Sandbox**: Marca il server localhost come `x-sandbox: true`.

## Accesso via API

È possibile recuperare gli schemi JSON direttamente dal servizio in esecuzione:

- **OAS 3.1.0 (JSON)**: `GET /openapi.json`
- **OAS 3.0.3 (JSON)**: `openapi_v3.json` (disponibile sul filesystem del container o via server statico se configurato)

## Documentazione Interattiva

Il servizio offre due interfacce per testare le API:
- **Swagger UI**: `http://localhost:8000/docs` (Usa OAS 3.1.0)
- **ReDoc**: `http://localhost:8000/redoc` (Usa OAS 3.1.0)