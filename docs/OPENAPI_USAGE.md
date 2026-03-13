# Utilizzo Schemi OpenAPI

Il servizio OAS Checker genera automaticamente la propria documentazione API in diversi formati e per diversi ambienti per garantire la massima compatibilità con validatori e client.

## Generazione Automatica

Tutti gli schemi sono generati dallo script `scripts/generate_openapi.py`. Lo script esegue l'introspezione del codice FastAPI, applica i metadati (licenza EUPL, link GitHub), configura i server per i vari ambienti e gestisce la conversione automatica tra le versioni.

Per rigenerare tutti gli schemi:
```bash
python3 scripts/generate_openapi.py
```

## Struttura delle Cartelle

I file generati sono organizzati nella cartella `openapi/` con una struttura gerarchica per ambiente e versione dello standard:

```text
openapi/
├── full/           # Tutti i server inclusi (Produzione, Collaudo, Attestazione, Local)
├── produzione/     # Solo server di produzione
├── collaudo/       # Solo server di collaudo
└── attestazione/   # Solo server di attestazione
    ├── v3.0/       # Versione Legacy (OAS 3.0.3)
    │   ├── openapi.json
    │   └── openapi.yaml
    └── v3.1/       # Versione Moderna (OAS 3.1.0)
        ├── openapi.json
        └── openapi.yaml
```

## Versioni dello Standard

### OAS 3.1.0 (v3.1)
È la versione moderna e predefinita, utilizzata da Swagger UI e ReDoc. Supporta le ultime estensioni di JSON Schema.

### OAS 3.0.3 (v3.0 - Legacy)
Questa versione è generata tramite un processo di **down-conversion automatico** per garantire la compatibilità con tool datati (es. alcuni API Gateway o validatori ModI rigorosi).

Lo script gestisce automaticamente le seguenti trasformazioni:
- **Nullability**: Converte `type: [string, null]` o `anyOf: [..., {type: null}]` nel formato legacy `type: string, nullable: true`.
- **Media Types**: Converte `contentMediaType` (introdotto in 3.1) nel formato legacy `format: binary` per gli upload di file.
- **Metadata**: Rimuove o sposta campi non supportati (es. `info.summary` viene rimosso in 3.0.x).
- **Cleanup RFC 9457**: Assicura che le risposte di errore utilizzino esclusivamente `application/problem+json`.

## Link ai Problem Details (RFC 9457)

Tutti gli schemi includono link diretti alla documentazione degli errori (`type` field nelle risposte). Questi link puntano al file `docs/PROBLEMS.md` nel repository GitHub, fornendo agli integratori una guida immediata su come gestire le eccezioni restituite dall'API.

## Integrazione con Gateway (es. GovWay)

Per l'integrazione con gateway specifici per ambiente, si consiglia di utilizzare i file YAML presenti nelle rispettive sottocartelle (es. `openapi/produzione/v3.0/openapi.yaml`), che contengono esclusivamente l'URL del server pertinente all'ambiente di destinazione.
