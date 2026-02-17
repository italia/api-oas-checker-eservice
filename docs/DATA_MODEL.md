# Modello Dati - OAS Checker e-service

Documentazione completa dello schema PostgreSQL e delle logiche di persistenza dell'e-service.

## Schema Database

Lo schema SQL completo è definito nel file `database/schema.sql`. L'inizializzazione avviene automaticamente all'avvio dell'applicazione.

---

## Tabelle

### 1. `validations`

Tabella principale per il tracciamento delle richieste di validazione, memorizzazione dei contenuti dei file e dei report finali.

| Campo | Tipo | Vincoli | Descrizione |
|-------|------|---------|-------------|
| `id` | TEXT | PRIMARY KEY | Validation ID (SHA256 del file + parametri) |
| `status` | TEXT | NOT NULL | Stato: PENDING, IN_PROGRESS, COMPLETED, FAILED |
| `ruleset` | TEXT | NOT NULL | Nome del ruleset utilizzato |
| `ruleset_version` | TEXT | NOT NULL | Versione del ruleset (es. "1.2") |
| `errors_only` | BOOLEAN | NOT NULL | Flag per richiedere solo gli errori nel report |
| `format` | TEXT | NOT NULL | Formato del report (default: 'json') |
| `file_sha256` | TEXT | NOT NULL | Hash SHA256 del contenuto del file |
| `file_content` | TEXT | NOT NULL | **Contenuto completo del file OpenAPI originale** |
| `report_content` | JSONB | NULL | **Esito completo della validazione in formato JSON** |
| `created_at` | TIMESTAMP | NOT NULL | Timestamp di creazione della richiesta |
| `completed_at` | TIMESTAMP | NULL | Timestamp di completamento della validazione |
| `error_message` | TEXT | NULL | Eventuale messaggio di errore in caso di stato FAILED |

#### Razionale Architetturale
Il modello **Storage-less** prevede che il database PostgreSQL funga da unica fonte di verità.
- `file_content`: Memorizza il file originale per permettere alla validation function di accedervi direttamente senza ricorrere a storage condivisi.
- `report_content`: Memorizza l'esito come oggetto JSON nativo (JSONB), consentendo ricerche efficienti e analisi sui risultati.

### 2. `rate_limit_tracking`

Tabella utilizzata per la gestione del rate limiting per singolo consumer, basata su un algoritmo a finestra fissa.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `id` | SERIAL | ID incrementale interno |
| `consumer_id` | TEXT | Identificativo del fruitore (da JWT) |
| `endpoint` | TEXT | Endpoint chiamato |
| `request_count` | INTEGER | Conteggio delle richieste nella finestra attuale |
| `window_start` | TIMESTAMP | Inizio della finestra temporale |
| `window_end` | TIMESTAMP | Fine della finestra temporale |

---

## Performance e Dimensionamento

### Stima Occupazione Storage
Sulla base di un utilizzo tipico del servizio, si prevedono le seguenti metriche:
- **Volume giornaliero**: ~100 validazioni.
- **Peso medio per riga**: ~250 KB (include file originale e report JSONB).
- **Crescita mensile**: ~750 MB.
- **Crescita annuale**: ~9 GB.

L'utilizzo del tipo **JSONB** e dei campi **TEXT** in PostgreSQL è ottimizzato tramite il meccanismo **TOAST**, che comprime i dati voluminosi e li memorizza efficientemente fuori riga.

### Connection Pooling
L'e-service implementa un sistema di connection pooling nativo tramite la libreria `asyncpg`.
- **Efficienza**: Il pool mantiene connessioni "calde" verso il database, eliminando la latenza dovuta all'handshake TCP e alla negoziazione TLS per ogni singola richiesta.
- **Configurazione**: I parametri di default (`min_size=2`, `max_size=10`) permettono al sistema di scalare dinamicamente in base al carico, garantendo tempi di risposta inferiori ai 50ms per le operazioni di persistenza.