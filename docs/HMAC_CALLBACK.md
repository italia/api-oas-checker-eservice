# Sicurezza Callback (HMAC)

Per garantire che l'esito della validazione provenga esclusivamente dalla Validation Function autorizzata, l'endpoint `/oas/callback` è protetto da un meccanismo di firma **HMAC-SHA256**.

## Flusso di Verifica

1.  **Generazione**: La Validation Function calcola una firma usando una `CALLBACK_SECRET` condivisa, basata sul corpo della richiesta JSON e su un timestamp.
2.  **Trasmissione**: La firma e il timestamp vengono inviati negli header `X-Signature` e `X-Timestamp`.
3.  **Verifica**: L'e-service ricalcola la firma e la confronta in tempo costante. Verifica inoltre che il timestamp rientri in una finestra di 5 minuti per prevenire Replay Attack.

## Implementazione e Moduli Condivisi

Per garantire la massima affidabilità e sincronia tra i componenti, la logica di sicurezza è centralizzata nel modulo `shared/` (utilizzato sia dall'e-service che dalla Validation Function):

- **`shared/security.py`**: Contiene la logica di generazione degli header di firma.
- **`shared/utils.py`**: Fornisce una serializzazione JSON canonica (chiavi ordinate, nessun spazio superfluo) tramite la funzione `json_dumps`.

### Requisito: Serializzazione Canonica

È **fondamentale** che il corpo della richiesta JSON sia serializzato in modo identico sia durante la generazione della firma che durante l'invio della richiesta HTTP. Differenze anche minime (come uno spazio dopo la virgola) causeranno un fallimento della verifica (`401 Unauthorized`).

L'uso di `shared.utils.json_dumps` garantisce automaticamente:
- Nessuno spazio tra i separatori: `separators=(',', ':')`
- Chiavi ordinate alfabeticamente: `sort_keys=True`
- Gestione corretta di oggetti `datetime` e `date`.
- Codifica caratteri: `UTF-8`

Esempio di utilizzo (Validation Function):
```python
from shared.utils import json_dumps
from shared.security import generate_hmac_headers

payload_str = json_dumps(callback_data)
headers = generate_hmac_headers(payload_str)
# Invio...
```

## Configurazione

Le seguenti variabili devono coincidere tra e-service e Function:
- `CALLBACK_SECRET`: La chiave segreta condivisa.
- `HMAC_ENABLED`: Impostare a `true` in produzione.

## Header Richiesti

- `X-Signature`: La firma HMAC-SHA256 in formato esadecimale.
- `X-Timestamp`: Unix timestamp (secondi).