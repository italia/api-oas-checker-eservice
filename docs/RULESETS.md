# Gestione Ruleset Spectral

Il servizio OAS Checker scarica automaticamente i ruleset Spectral dal repository ufficiale [italia/api-oas-checker-rules](https://github.com/italia/api-oas-checker-rules).

## Panoramica

All'avvio, il microservizio:
1. Effettua il download dell'ultima release dal repository GitHub.
2. Estrae tutti i file `.yml` dei ruleset e le funzioni JavaScript.
3. Memorizza i file in una cache locale (`data/rulesets`).

Nel modello **Storage-less**, l'e-service legge il contenuto del ruleset richiesto dalla cache locale e lo invia direttamente alla Validation Function nel payload della richiesta.

## Uso dei Ruleset

Quando viene inviata una richiesta di validazione, si deve specificare il nome del ruleset (senza estensione `.yml`). 

**Nota Speciale:** Il ruleset `default` viene mappato automaticamente al file `spectral.yml` (il ruleset base di Spectral).

```bash
curl -X POST http://localhost:8000/oas/validate \
  -F "file=@openapi.yaml" \
  -F "ruleset=spectral-modi"
```


### Ruleset Disponibili

È possibile utilizzare l'endpoint API per ottenere la lista aggiornata:

```bash
curl http://localhost:8000/oas/rulesets
```

## Flusso di Validazione (Storage-less)

1. **e-service**: Riceve la richiesta, legge il ruleset dalla cache locale.
2. **Invocazione Function**: L'e-service invia alla function un payload JSON contenente sia il `file_content` che il `ruleset_content`.
3. **Function**: Riceve i contenuti, li salva in file temporanei ed esegue Spectral CLI tramite il wrapper `shared.validator.py`. Infine, restituisce il report JSON.

Questo approccio garantisce che la function non debba mai scaricare file da storage esterni o GitHub, rendendo il sistema più veloce e robusto.

## Forzare l'aggiornamento

Per forzare il re-download dei ruleset da GitHub è possibile utilizzare l'endpoint interno:

```bash
curl -X POST http://localhost:8000/internal/rulesets/refresh
```

> **Sicurezza**: Se l'e-service è pubblicato, questo endpoint è protetto. L'operazione può essere invocata esclusivamente dall'**erogatore** stesso. Il sistema verifica la corrispondenza tra `producerId` e `consumerId` all'interno del token JWT (Voucher PDND). In caso di mancata corrispondenza, verrà restituito un errore `403 Forbidden`.
