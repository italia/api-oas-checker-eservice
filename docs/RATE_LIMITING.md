# Rate Limiting

Il servizio implementa una limitazione delle richieste per consumer per proteggere le risorse del database e della Validation Function.

## Funzionamento

Il rate limiting si basa sull'algoritmo **Fixed Window** e identifica i consumer tramite il `consumerId` estratto dal token JWT (gestito dall'API Gateway GovWay).

### Configurazione Limiti

I limiti sono configurabili tramite variabili d'ambiente:

| Endpoint | Limite Default | Finestra | Variabile ENV |
|----------|----------------|----------|---------------|
| `/oas/validate` | 10 richieste | 60s | `RATE_LIMIT_VALIDATE_REQUESTS` |
| `/oas/report/*` | 60 richieste | 60s | `RATE_LIMIT_REPORT_REQUESTS` |
| Altri endpoint | 30 richieste | 60s | `RATE_LIMIT_DEFAULT_REQUESTS` |

## Persistenza e Tracciamento

I dati di tracking vengono memorizzati nella tabella PostgreSQL `rate_limit_tracking`. 
Un task in background provvede a ripulire i record obsoleti ogni ora (configurabile via `RATE_LIMIT_CLEANUP_HOURS`).

## Header HTTP

In ogni risposta API (eccetto quelle escluse come `/status`), vengono inclusi i seguenti header:
- `X-RateLimit-Limit`: Limite massimo consentito.
- `X-RateLimit-Remaining`: Richieste rimanenti nella finestra corrente.
- `X-RateLimit-Reset`: Secondi alla fine della finestra.

In caso di superamento del limite, il servizio risponde con **429 Too Many Requests** includendo anche l'header `Retry-After`.

## Sviluppo Locale

Per facilitare lo sviluppo, il rate limiting è disabilitato se `RATE_LIMIT_ENABLED=false`. In caso di test con JWT disabilitato, tutte le richieste vengono associate al consumer fittizio `dev`.