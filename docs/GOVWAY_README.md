# GovWay API Gateway

GovWay è un API Gateway open source italiano sviluppato da Link.it per la Pubblica Amministrazione, conforme alle linee guida AGID ModI e PDND.

## Architettura

```
Internet → Ingress → GovWay (JWT/PDND) → eservice (interno)
                 └→ GovWay Console (gestione/monitoraggio)
```

GovWay è il punto di contatto con l'esterno e gestisce:
- Autenticazione JWT con token rilasciati dalla PDND
- Erogazione delle API verso i fruitori
- Tracciamento delle transazioni

L'e-service non è esposto pubblicamente; riceve traffico solo da GovWay.

## Porte

| Porta | Listener | Descrizione |
|-------|----------|-------------|
| 8080  | Erogazione | Traffico API in ingresso (max 100 thread) |
| 8081  | Fruizione  | Traffico API in uscita (max 100 thread) |
| 8082  | Gestione   | Console web e API di configurazione (max 20 thread) |

## Console Web

- **Console Gestione**: `https://<host>/govwayConsole/`
- **Console Monitoraggio**: `https://<host>/govwayMonitor/`

Credenziali default (primo accesso):

| Console | Username | Password |
|---------|----------|----------|
| govwayConsole | `amministratore` | `123456` |
| govwayMonitor | `operatore` | `123456` |

**Cambiare le password al primo accesso.**

## Health Check

- Runtime: `/govway/check` (porta 8080)
- Manager: `/govwayMonitor/check` (porta 8082)

## Deploy su Kubernetes

### Prerequisiti

1. **Database PostgreSQL** dedicato per GovWay (configurazione e tracciamento)
2. Il database viene inizializzato automaticamente al primo avvio con `GOVWAY_POP_DB_SKIP=false`

### Abilitazione nel Helm Chart

```yaml
govway:
  enabled: true
  image:
    tag: "3.4.2"
  entityName: "NomeEnte"
  popDbSkip: "false"    # impostare "true" dopo il primo avvio
  database:
    type: postgresql
    server: "db-host:5432"
    name: govway_db
    user: govway
    password: "..."
  persistence:
    enabled: true
    size: 2Gi
```

### Routing Ingress

Con GovWay abilitato, l'ingress instrada il traffico così:

| Path | Service | Porta | Descrizione |
|------|---------|-------|-------------|
| `/govway` | govway | 8080 | API Gateway runtime |
| `/govwayConsole` | govway-management | 8082 | Console gestione |
| `/govwayMonitor` | govway-management | 8082 | Console monitoraggio |

```yaml
ingress:
  hosts:
    - host: api-oas-checker.innovazione.gov.it
      paths:
        - path: /govway
          pathType: Prefix
          service: govway
        - path: /govwayConsole
          pathType: Prefix
          service: govway-management
        - path: /govwayMonitor
          pathType: Prefix
          service: govway-management
```

### NetworkPolicy

Quando GovWay è abilitato:
- L'eservice accetta traffico solo da pod GovWay e dal worker (callback)
- GovWay accetta traffico dall'ingress controller
- GovWay ha egress verso eservice, database PostgreSQL e HTTPS esterno (JWKS PDND)

### Primo Avvio

1. Creare il database PostgreSQL dedicato
2. Deploy con `popDbSkip: "false"` (GovWay inizializza lo schema)
3. Verificare che GovWay sia running: `kubectl logs -f deploy/<release>-govway`
4. Accedere a `/govwayConsole/` e cambiare la password di default
5. Configurare l'erogazione API (registrare e-service, routing, policy JWT)
6. Aggiornare `popDbSkip: "true"` nei values e fare upgrade

### Configurazione API su GovWay Console

Tramite govwayConsole configurare:
1. **Soggetto**: il soggetto operativo (es. "DTD")
2. **API**: registrare l'API OAS Checker importando l'OpenAPI spec
3. **Erogazione**: creare l'erogazione puntando al backend `http://<release>-eservice:8000`
4. **Autenticazione**: configurare validazione JWT con chiavi PDND (JWKS)

## Persistenza

| Mount | Tipo | Descrizione |
|-------|------|-------------|
| `/etc/govway` | PVC | Configurazione GovWay (persiste tra restart) |
| `/var/log/govway` | emptyDir | Log applicativi (effimeri) |
| `/tmp` | emptyDir | File temporanei |

## Variabili d'Ambiente

| Variabile | Descrizione |
|-----------|-------------|
| `GOVWAY_DB_TYPE` | Tipo database: `hsql`, `postgresql`, `mysql`, `oracle` |
| `GOVWAY_DB_SERVER` | Host e porta del database (es. `host:5432`) |
| `GOVWAY_DB_NAME` | Nome database |
| `GOVWAY_DB_USER` | Utente database |
| `GOVWAY_DB_PASSWORD` | Password database (da Secret) |
| `GOVWAY_DEFAULT_ENTITY_NAME` | Nome soggetto operativo |
| `GOVWAY_POP_DB_SKIP` | `false` per inizializzare DB, `true` dopo primo avvio |
| `TZ` | Timezone (default: `Europe/Rome`) |

## Troubleshooting

```bash
# Log GovWay
kubectl logs -f deploy/oas-checker-govway -n api-oas-checker

# Accesso console via port-forward (alternativa all'ingress)
kubectl port-forward svc/oas-checker-govway 8082:8082 -n api-oas-checker
# Poi aprire http://localhost:8082/govwayConsole/

# Verifica health
kubectl exec deploy/oas-checker-govway -- curl -s http://localhost:8080/govway/check

# Restart
kubectl rollout restart deploy/oas-checker-govway -n api-oas-checker
```

## Riferimenti

- [Documentazione GovWay](https://govway.org/documentazione/)
- [govway-docker su GitHub](https://github.com/link-it/govway-docker)
- [Immagine Docker su Docker Hub](https://hub.docker.com/r/linkitaly/govway)
