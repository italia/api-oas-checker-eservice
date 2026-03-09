# Helm Chart - OAS Checker e-service

Chart Helm per il deploy su Kubernetes dell'OAS Checker e-service, il servizio di validazione OpenAPI con Spectral per la PA italiana.

## Architettura

```mermaid
graph TB
    internet((Internet))
    
    subgraph cluster [Kubernetes Cluster]
        ingress[Ingress NGINX]
        
        subgraph ns [Namespace]
            direction TB
            
            eservice["<b>eservice</b><br/>FastAPI :8000<br/>Deployment"]
            worker["<b>worker</b><br/>Spectral Validator<br/>Knative / Deployment / Esterno"]
            govway["<b>govway</b><br/>API Gateway :8080<br/>Deployment<br/><i>(opzionale)</i>"]
            
            configmap[ConfigMap]
            secret[Secret]
            pvc["PVC<br/>Ruleset Cache"]
        end
        
        subgraph dbChoice ["Database (1 di 2)"]
            bitnami["PostgreSQL Bitnami<br/>Subchart<br/><i>(dev/test)</i>"]
            externalDb["DB Esterno Condiviso<br/><i>(produzione)</i>"]
        end
    end
    
    internet --> ingress
    ingress --> eservice
    ingress -.->|opzionale| govway
    govway -.-> eservice
    eservice -->|"FUNCTION_URL"| worker
    worker -->|"callback"| eservice
    eservice --> dbChoice
    configmap -.-> eservice
    secret -.-> eservice
    secret -.-> worker
    pvc -.-> eservice
    pvc -.-> worker
```

## Flusso di validazione

```mermaid
sequenceDiagram
    participant C as Client
    participant E as eservice (FastAPI)
    participant W as Worker (Knative/Deploy)
    participant DB as PostgreSQL
    
    C->>E: POST /oas/validate
    E->>DB: Salva richiesta (status=PENDING)
    E->>W: POST /api/validate (async)
    E-->>C: 202 Accepted + validation_id
    
    W->>W: Esegue Spectral CLI
    W->>E: POST /callback (HMAC signed)
    E->>DB: Aggiorna report (status=COMPLETED)
    
    C->>E: GET /oas/report/{id}
    E->>DB: Leggi report
    E-->>C: 200 Report completo
```

## Prerequisiti

- Kubernetes >= 1.25
- Helm >= 3.10
- **Knative Serving** (solo se `worker.mode=knative`) - vedi [sezione dedicata](#knative-su-aks)
- **Ingress NGINX Controller** (solo se `ingress.enabled=true`)

## Quick Start

```bash
# 1. Aggiorna le dipendenze
cd helm/oas-checker
helm dependency update

# 2. Deploy con DB esterno + Knative (produzione)
helm install oas-checker . \
  --namespace oas-checker --create-namespace \
  --set externalDatabase.host=db.prod.internal \
  --set externalDatabase.password=my-db-password \
  --set secrets.callbackSecret=my-secure-secret \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=oas-checker.miodominio.it

# 3. Deploy con PostgreSQL in-cluster + Deployment classico (dev)
helm install oas-checker . \
  --namespace oas-checker --create-namespace \
  --set postgresql.enabled=true \
  --set worker.mode=deployment \
  --set eservice.config.jwtEnabled=false \
  --set eservice.config.hmacEnabled=false \
  --set eservice.config.rateLimitEnabled=false
```

## Modalita' Worker Spectral

Il worker esegue la validazione OpenAPI con Spectral CLI. Tre modalita' disponibili, selezionabili con `worker.mode`:

```mermaid
graph LR
    subgraph knativeMode ["worker.mode = knative (default)"]
        ksvc["Knative Service"]
        ksvc --> p0["(scale to zero)"]
        ksvc --> p1[Pod 1]
        ksvc --> pN[Pod N]
    end
    
    subgraph deployMode ["worker.mode = deployment"]
        dep[Deployment]
        svc[Service :80]
        dep --> dp1[Pod 1]
        dep --> dpN["Pod N (fisso)"]
        svc --> dep
    end
    
    subgraph extMode ["worker.mode = external"]
        url["URL Esterno<br/>Azure Function / altro"]
    end
```

### `knative` (default)

Crea un [Knative Service](https://knative.dev/docs/serving/) con autoscaling e scale-to-zero.

```yaml
worker:
  mode: knative
  knative:
    minScale: 0        # scale-to-zero abilitato
    maxScale: 5        # massimo 5 pod
    concurrencyTarget: 10  # target richieste concorrenti per pod
    scaleDownDelay: "60s"  # attesa prima di scalare a zero
```

Ideale per produzione: risparmia risorse quando non ci sono validazioni in corso, scala automaticamente sotto carico.

### `deployment`

Crea un Deployment + Service Kubernetes classico. Utile se Knative non e' disponibile nel cluster.

```yaml
worker:
  mode: deployment
  replicaCount: 2  # numero fisso di repliche
```

### `external`

Non crea risorse per il worker. L'eservice punta a un URL esterno (es. Azure Function vera su Azure, o qualsiasi altro endpoint HTTP).

```yaml
worker:
  mode: external
  externalUrl: "https://my-func.azurewebsites.net/api/validate"
  # Se la function richiede una chiave:
secrets:
  azureFunctionKey: "my-azure-function-key"
```

## Modalita' Database

```mermaid
graph LR
    subgraph inCluster ["postgresql.enabled = true"]
        bitnami["PostgreSQL Bitnami<br/>StatefulSet + PVC<br/>User/pass da values"]
    end
    
    subgraph external ["postgresql.enabled = false (default)"]
        extDb["DB Esterno"]
        url["externalDatabase.url<br/>oppure<br/>host + port + user + password"]
    end
```

### PostgreSQL in-cluster (dev/test)

Deploya PostgreSQL tramite il [subchart Bitnami](https://github.com/bitnami/charts/tree/main/bitnami/postgresql):

```yaml
postgresql:
  enabled: true
  auth:
    username: oaschecker
    password: oaschecker
    database: oaschecker
```

Il `DATABASE_URL` viene costruito automaticamente. Tutti i parametri Bitnami sono disponibili sotto la chiave `postgresql.*` (vedi [documentazione Bitnami](https://github.com/bitnami/charts/tree/main/bitnami/postgresql#parameters)).

### Database esterno condiviso (produzione)

```yaml
postgresql:
  enabled: false  # default

# Opzione 1: URL completo
externalDatabase:
  url: "postgresql://user:pass@db.prod.internal:5432/oaschecker"

# Opzione 2: campi separati
externalDatabase:
  host: db.prod.internal
  port: 5432
  user: oaschecker
  password: my-password
  database: oaschecker
```

## Gestione Secrets

Il chart crea un Secret Kubernetes con:
- `DATABASE_URL` - connection string PostgreSQL
- `CALLBACK_SECRET` - chiave HMAC per i callback worker -> eservice
- `AZURE_FUNCTION_KEY` - chiave per Azure Function (opzionale)

### Secret gestito dal chart

```yaml
secrets:
  callbackSecret: "my-secure-callback-secret"
  azureFunctionKey: ""  # opzionale
```

### Secret esterno (Vault, Sealed Secrets, ecc.)

```yaml
secrets:
  existingSecret: "my-precreated-secret"
  # Il secret deve contenere le chiavi: DATABASE_URL, CALLBACK_SECRET
  # e opzionalmente AZURE_FUNCTION_KEY
```

## Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: oas-checker.miodominio.it
      paths:
        - path: /
          pathType: Prefix
          service: eservice  # oppure "govway" per passare dal gateway
  tls:
    - secretName: oas-checker-tls
      hosts:
        - oas-checker.miodominio.it
```

## GovWay (opzionale)

API Gateway per integrazione ModI/PDND:

```yaml
govway:
  enabled: true
  entityName: mio-ente
```

## Knative su AKS

Il container del worker usa come base image il runtime Azure Functions (`mcr.microsoft.com/azure-functions/python:4-python3.11`), ma funziona perfettamente su Knative perche':

1. E' un container HTTP standard che ascolta sulla porta 80
2. Espone `POST /api/validate` e risponde a health check su `/`
3. Non dipende da infrastruttura Azure (come dimostrato dal docker-compose)

```mermaid
graph TB
    subgraph aks [AKS Cluster]
        subgraph knativeServing [Knative Serving]
            ksvc["Knative Service<br/>oas-checker-worker"]
            activator[Activator]
            autoscaler[Autoscaler]
        end
        
        eservice["eservice (FastAPI)"]
        
        eservice -->|"POST /api/validate"| ksvc
        activator -->|"cold start"| pod1["Pod (Azure Functions Runtime)"]
        autoscaler -->|"scale 0..N"| ksvc
        ksvc --> pod1
        ksvc --> pod2[Pod 2]
        pod1 -->|callback| eservice
    end
```

### Installare Knative su AKS

```bash
# Installa Knative Serving CRDs e core
kubectl apply -f https://github.com/knative/serving/releases/latest/download/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/latest/download/serving-core.yaml

# Installa il networking layer (Kourier o Istio)
# Kourier (piu' leggero):
kubectl apply -f https://github.com/knative/net-kourier/releases/latest/download/kourier.yaml
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

# Verifica
kubectl get pods -n knative-serving
```

### Considerazioni per AKS

| Aspetto | Dettaglio |
|---------|-----------|
| **Cold start** | L'immagine Azure Functions e' ~1GB. Con `minScale: 0` il primo avvio puo' richiedere 10-30s. Impostare `minScale: 1` per eliminare il cold start. |
| **Concurrency** | Spectral CLI e' CPU-intensive. Consigliato `concurrencyTarget: 5-10` per evitare sovraccarico. |
| **Scale down** | `scaleDownDelay: 60s` evita flapping. Aumentare se le richieste arrivano a burst. |
| **Alternativa** | Se il cold start e' un problema, usare `worker.mode=deployment` con `replicaCount: 1`. |

### Ottimizzazione cold start

Per ridurre il cold start su Knative, si puo' considerare in futuro di creare un Dockerfile "leggero" basato su Python puro (senza il runtime Azure Functions), dato che il container viene invocato via HTTP standard. Questo ridurrebbe l'immagine da ~1GB a ~300MB.

## Parametri di riferimento

### eservice

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `eservice.replicaCount` | `1` | Numero di repliche |
| `eservice.image.repository` | `ghcr.io/italia/oas-checker-eservice` | Repository immagine |
| `eservice.image.tag` | `appVersion` | Tag immagine |
| `eservice.service.port` | `8000` | Porta del servizio |
| `eservice.resources.requests.cpu` | `100m` | CPU request |
| `eservice.resources.requests.memory` | `256Mi` | Memory request |
| `eservice.resources.limits.cpu` | `500m` | CPU limit |
| `eservice.resources.limits.memory` | `512Mi` | Memory limit |
| `eservice.config.logLevel` | `INFO` | Livello di log |
| `eservice.config.jwtEnabled` | `true` | Abilita autenticazione JWT |
| `eservice.config.hmacEnabled` | `true` | Abilita verifica HMAC callback |
| `eservice.config.rateLimitEnabled` | `true` | Abilita rate limiting |

### worker

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `worker.mode` | `knative` | Modalita': `knative`, `deployment`, `external` |
| `worker.image.repository` | `ghcr.io/italia/oas-checker-function` | Repository immagine |
| `worker.replicaCount` | `1` | Repliche (solo mode=deployment) |
| `worker.externalUrl` | `""` | URL esterno (solo mode=external) |
| `worker.knative.minScale` | `0` | Min pod Knative |
| `worker.knative.maxScale` | `5` | Max pod Knative |
| `worker.knative.concurrencyTarget` | `10` | Target concurrency per pod |
| `worker.knative.scaleDownDelay` | `60s` | Delay prima di scale-down |

### database

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `postgresql.enabled` | `false` | Deploya PostgreSQL in-cluster |
| `postgresql.auth.username` | `oaschecker` | Username DB |
| `postgresql.auth.password` | `oaschecker` | Password DB |
| `postgresql.auth.database` | `oaschecker` | Nome database |
| `externalDatabase.url` | `""` | URL completo DB esterno |
| `externalDatabase.host` | `""` | Host DB esterno |
| `externalDatabase.port` | `5432` | Porta DB esterno |

### altri

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `ingress.enabled` | `false` | Abilita Ingress |
| `ingress.className` | `nginx` | Ingress class |
| `govway.enabled` | `false` | Deploya GovWay |
| `rulesetCache.enabled` | `true` | PVC per cache rulesets |
| `rulesetCache.size` | `1Gi` | Dimensione PVC |
| `secrets.existingSecret` | `""` | Nome di un Secret esistente |

## Esempi di configurazione

### Produzione completa (AKS + Knative + DB esterno + Ingress + TLS)

```yaml
# values-production.yaml
eservice:
  replicaCount: 2
  config:
    jwtEnabled: "true"
    hmacEnabled: "true"
    rateLimitEnabled: "true"

worker:
  mode: knative
  knative:
    minScale: 1  # niente cold start
    maxScale: 10
    concurrencyTarget: 5

postgresql:
  enabled: false

externalDatabase:
  host: db.prod.internal
  port: 5432
  user: oaschecker_prod
  password: ""  # meglio via existingSecret

secrets:
  existingSecret: "oas-checker-prod-secrets"

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: oas-checker.miodominio.it
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: oas-checker-tls
      hosts:
        - oas-checker.miodominio.it
```

```bash
helm install oas-checker ./helm/oas-checker \
  --namespace oas-checker --create-namespace \
  -f values-production.yaml
```

### Sviluppo locale (tutto in-cluster)

```yaml
# values-dev.yaml
eservice:
  config:
    jwtEnabled: "false"
    hmacEnabled: "false"
    rateLimitEnabled: "false"
    logLevel: DEBUG

worker:
  mode: deployment
  replicaCount: 1

postgresql:
  enabled: true

secrets:
  callbackSecret: "dev-secret"

rulesetCache:
  enabled: true
```

### Worker su Azure Function esterna

```yaml
# values-azure.yaml
worker:
  mode: external
  externalUrl: "https://my-func.azurewebsites.net/api/validate"

secrets:
  azureFunctionKey: "my-azure-key"

eservice:
  config:
    functionType: azure

rulesetCache:
  enabled: false  # i rulesets sono gestiti dalla Function su Azure
```

## Upgrade e Rollback

```bash
# Upgrade
helm upgrade oas-checker ./helm/oas-checker -f values-production.yaml

# Rollback
helm rollback oas-checker 1

# Visualizza la storia dei rilasci
helm history oas-checker
```

## Disinstallazione

```bash
helm uninstall oas-checker --namespace oas-checker

# Se vuoi rimuovere anche il PVC dei rulesets:
kubectl delete pvc -l app.kubernetes.io/part-of=oas-checker -n oas-checker
```
