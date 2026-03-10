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

## Autoscaling (HPA)

L'eservice supporta l'Horizontal Pod Autoscaler per scalare automaticamente in base al carico:

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

Quando `autoscaling.enabled: true`, il campo `eservice.replicaCount` viene ignorato e l'HPA gestisce il numero di repliche. Il worker Knative ha il proprio autoscaling gestito da Knative (`worker.knative.minScale` / `maxScale`).

## Sicurezza

Il chart applica le best practice di sicurezza Kubernetes per tutti i container.

### Security Context

| Impostazione | eservice | worker (Knative) | worker (Deployment) | govway |
|---|---|---|---|---|
| `runAsNonRoot` | true (UID 1000) | true (UID 1000) | true (UID 1000) | false (upstream) |
| `readOnlyRootFilesystem` | true | false * | true | false (upstream) |
| `allowPrivilegeEscalation` | false | false | false | false |
| `capabilities.drop` | ALL | N/A ** | ALL | ALL |
| `seccompProfile` | RuntimeDefault | N/A ** | RuntimeDefault | RuntimeDefault |

\* Il runtime Azure Functions scrive in directory interne (`/home/site/wwwroot`, `/tmp`). Il container ascolta sulla porta 8080 (non privilegiata) e gira come `funcuser` (UID 1000).

\*\* Knative Serving non permette `capabilities.add` ne' `capabilities.drop` nel `securityContext` dei container.

Le directory scrivibili sono montate come `emptyDir`:

| Container | Path | Scopo |
|---|---|---|
| eservice | `/tmp` | File temporanei (Spectral validation) |
| eservice | `/app/data/rulesets` | Cache rulesets (scaricati da GitHub all'avvio) |
| worker | `/tmp` | File temporanei (Spectral validation) |

Per sovrascrivere i security context:

```yaml
eservice:
  podSecurityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    runAsNonRoot: true
  containerSecurityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: [ALL]
    seccompProfile:
      type: RuntimeDefault
```

### Network Policy

Il chart include NetworkPolicy che limitano il traffico in ingresso e uscita per ogni componente:

```mermaid
graph LR
    internet((Internet))
    ingress["Ingress NGINX"]
    eservice["eservice :8000"]
    worker["worker :80"]
    db["PostgreSQL :5432"]
    github["GitHub API :443"]
    dns["DNS :53"]

    internet --> ingress
    ingress -->|"ingress"| eservice
    eservice -->|"egress"| worker
    eservice -->|"egress"| db
    eservice -->|"egress"| github
    eservice -->|"egress"| dns
    worker -->|"callback"| eservice
    worker -->|"egress"| dns
```

**eservice:**
- Ingress: da ingress-nginx (porta 8000), da worker (callback porta 8000)
- Egress: verso worker (porta 80), verso DB (porta 5432), verso GitHub API (porta 443), DNS

**worker:**
- Ingress: da eservice (porta 80), da Knative system (se mode=knative)
- Egress: verso eservice (callback porta 8000), DNS

**govway** (se abilitato):
- Ingress: da ingress-nginx (porte 8080/8081)
- Egress: verso eservice (porta 8000), DNS

```yaml
networkPolicy:
  enabled: true
  ingressNamespaceSelector:
    kubernetes.io/metadata.name: ingress-nginx
  allowExternalHttps: true
  externalDatabaseCidr: ""  # es. "10.0.0.5/32" per restringere
```

### Ruleset Cache (PVC vs emptyDir)

Il chart supporta due modalita' per la cache dei rulesets:

| Modalita' | `rulesetCache.persistence` | Comportamento |
|---|---|---|
| **emptyDir** (default) | `false` | Ogni pod scarica i rulesets all'avvio da GitHub. Nessun PVC creato. Compatibile con multi-replica. |
| **PVC** | `true` | Crea un PersistentVolumeClaim. Richiede `ReadWriteMany` per multi-replica. |

```yaml
rulesetCache:
  enabled: true
  persistence: false  # emptyDir (consigliato)
  size: 1Gi
```

## Monitoraggio

### Prometheus (ServiceMonitor + PrometheusRule)

Il chart include template per Prometheus Operator. Richiedono che il Prometheus Operator sia installato nel cluster.

```yaml
metrics:
  serviceMonitor:
    enabled: true
    interval: 30s
    labels:
      release: kube-prometheus-stack

  prometheusRule:
    enabled: true
    labels:
      release: kube-prometheus-stack
```

**Alert inclusi:**

| Alert | Severita' | Condizione |
|---|---|---|
| `OasCheckerDown` | critical | Tutte le repliche non disponibili per 5 minuti |
| `OasCheckerPodRestarting` | warning | Piu' di 3 restart in 1 ora |
| `OasCheckerReplicasMismatch` | warning | Repliche desiderate != repliche pronte per 10 minuti |

> **Nota:** Il ServiceMonitor richiede che l'applicazione esponga un endpoint `/metrics` (da aggiungere con `prometheus_client` in Python). Gli alert usano metriche di kube-state-metrics gia' disponibili.

### AlertmanagerConfig (notifiche email)

Il chart puo' creare un `AlertmanagerConfig` per instradare gli alert via email tramite Alertmanager:

```yaml
metrics:
  alertmanagerConfig:
    enabled: true
    namespace: monitoring
    labels:
      alertmanagerConfig: main
    smtp:
      from: "oas-checker@innovazione.gov.it"
      smarthost: "smtp.eu.mailgun.org:587"
      authUsername: "oas-checker@innovazione.gov.it"
      authPasswordSecret:
        name: alertmanager-smtp-secret
        key: password
      requireTLS: true
    recipients:
      - "admin1@example.com"
      - "admin2@example.com"
```

L'`AlertmanagerConfig` viene creato nel namespace di Alertmanager (default: `monitoring`) e richiede un Secret SMTP preesistente nel cluster. Gli alert con pattern `OasChecker.*` vengono instradati ai destinatari configurati, con ripetizione ogni 4h (1h per alert critical).

### Health Check

L'eservice espone `GET /status` che ritorna `application/problem+json` (RFC 9457):

```json
{
  "status": 200,
  "title": "Service Operational",
  "detail": "OAS Checker e-service is running and healthy"
}
```

Il chart configura tre tipi di probe:

| Probe | Scopo | Default |
|---|---|---|
| `startupProbe` | Protegge lo startup lento (download rulesets da GitHub). Evita che il liveness probe uccida il pod durante l'avvio. | 60s max (12 x 5s) |
| `livenessProbe` | Riavvia il pod se non risponde | ogni 30s, 3 fallimenti |
| `readinessProbe` | Rimuove il pod dal Service se non e' pronto | ogni 10s, 3 fallimenti |

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

### sicurezza e rete

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `eservice.containerSecurityContext.readOnlyRootFilesystem` | `true` | Filesystem in sola lettura |
| `eservice.containerSecurityContext.runAsNonRoot` | `true` | Esecuzione non-root |
| `worker.containerSecurityContext.readOnlyRootFilesystem` | `true` | Filesystem in sola lettura |
| `networkPolicy.enabled` | `true` | Abilita NetworkPolicy |
| `networkPolicy.ingressNamespaceSelector` | `{kubernetes.io/metadata.name: ingress-nginx}` | Label del namespace ingress |
| `networkPolicy.allowExternalHttps` | `true` | Permetti egress HTTPS (GitHub API) |
| `networkPolicy.externalDatabaseCidr` | `""` | CIDR per restringere egress DB |

### autoscaling

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `autoscaling.enabled` | `false` | Abilita HPA per eservice |
| `autoscaling.minReplicas` | `2` | Minimo repliche |
| `autoscaling.maxReplicas` | `6` | Massimo repliche |
| `autoscaling.targetCPUUtilizationPercentage` | `70` | Target CPU |
| `autoscaling.targetMemoryUtilizationPercentage` | `80` | Target memoria |

### monitoraggio

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `metrics.serviceMonitor.enabled` | `false` | Crea ServiceMonitor |
| `metrics.serviceMonitor.interval` | `30s` | Intervallo di scraping |
| `metrics.prometheusRule.enabled` | `false` | Crea PrometheusRule con alert |
| `metrics.alertmanagerConfig.enabled` | `false` | Crea AlertmanagerConfig per notifiche email |
| `metrics.alertmanagerConfig.namespace` | `monitoring` | Namespace di Alertmanager |
| `metrics.alertmanagerConfig.recipients` | `[]` | Lista email destinatari alert |

### altri

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `ingress.enabled` | `false` | Abilita Ingress |
| `ingress.className` | `nginx` | Ingress class |
| `govway.enabled` | `false` | Deploya GovWay |
| `rulesetCache.enabled` | `true` | Cache rulesets |
| `rulesetCache.persistence` | `false` | Usa PVC (true) o emptyDir (false) |
| `rulesetCache.size` | `1Gi` | Dimensione cache |
| `secrets.existingSecret` | `""` | Nome di un Secret esistente |
| `eservice.config.openApiGenerateOnStartup` | `false` | Genera schema OpenAPI all'avvio |

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
