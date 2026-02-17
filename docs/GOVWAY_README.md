# GovWay API Gateway

GovWay è un API Gateway open source italiano sviluppato da Link.it per la Pubblica Amministrazione, conforme alle linee guida AGID ModI e PDND.

## Porte

| Porta | Servizio | Descrizione |
|-------|----------|-------------|
| 8080  | Gateway Runtime | Endpoint API Gateway per traffico API |
| 8081  | Console Gestione | Console web per configurazione (govwayConsole) |
| 8082  | Console Monitoraggio | Console web per monitoraggio traffico (govwayMonitor) |

## Accessi Web

- **Console Gestione**: http://localhost:8081/govwayConsole
- **Console Monitoraggio**: http://localhost:8082/govwayMonitor

Credenziali default (primo accesso):
- Username: `amministratore`
- Password: `123456`

**IMPORTANTE**: Cambiare la password al primo accesso!

## Storage Locale

I dati sono persistiti in cartelle locali (non volumi Docker interni):

```
govway/
├── govway_conf/    # Configurazioni GovWay
│                   # Path container: /etc/govway
│
└── govway_log/     # Log applicativi
                    # Path container: /var/log/govway
```

**Permessi**: Le directory richiedono user ID 100 e group ID 101.

## Configurazione

Modifica il file `.env` per personalizzare:

```bash
# Nome ente/entità
GOVWAY_ENTITY_NAME=ente-test

# Skip popolamento database (true dopo primo avvio)
GOVWAY_POP_DB_SKIP=false
```

## Modalità Database

Questa configurazione usa **standalone mode** con database HSQL interno (file-based).

Per produzione con PostgreSQL esterno, vedi [govway-docker](https://github.com/link-it/govway-docker).

## Troubleshooting

```bash
# Log in tempo reale
docker-compose logs -f govway

# Restart container
docker-compose restart govway

# Rebuild (se cambi immagine)
docker-compose down && docker-compose up -d
```

---

**Documentazione ufficiale**: https://github.com/link-it/govway-docker
