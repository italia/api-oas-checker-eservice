# Data Lifecycle - OAS Checker e-service

Questo documento descrive come vengono gestiti i dati nel sistema. Il sistema è **Storage-less**, ovvero utilizza il database PostgreSQL come unica fonte di persistenza per lo scambio dei file e dei risultati.

## Overview

Il sistema gestisce 3 tipi di dati:
1. **Contenuto OpenAPI caricato dall'utente** (persistente su DB fino a validazione)
2. **Report di validazione** (persistenti su DB)
3. **Rulesets Spectral** (cache locale all'e-service)

---

## 1. Contenuto OpenAPI Caricato dall'Utente

### ➡️ CREAZIONE

**Quando**: POST `/oas/validate`
**Dove**: Tabella `validations`, campo `file_content` (TEXT)
**Codice**: `services/validation_service.py`

Il contenuto del file viene letto, validato come YAML/JSON sintatticamente, e salvato direttamente nel record della validazione nel database PostgreSQL.

### ❌ RIMOZIONE

**Attualmente**: Il contenuto del file rimane nel database come riferimento storico della validazione effettuata.
**Futuro**: Se necessario per privacy, si può implementare un cleanup del campo `file_content` dopo il completamento.

---

## 2. Report di Validazione

### ➡️ CREAZIONE

**Quando**: La Validation Function completa la validazione.
**Dove**: Tabella `validations`, campo `report_content` (JSONB).
**Codice**: `api/routes.py` (callback endpoint)

La function invia il report JSON completo nel corpo della callback. L'e-service riceve il JSON e lo salva nativamente nel campo JSONB del database.

### ❌ RIMOZIONE

**Mai rimossi automaticamente**. I report sono persistenti e rimangono indefinitamente per consultazione.

---

## 3. Rulesets Spectral

### ➡️ CREAZIONE/UPDATE

**Quando**:
- Startup dell'e-service (se `RULESET_AUTO_UPDATE=true`)
- Manualmente via POST `/internal/rulesets/refresh`

**Dove**: Cache locale sul filesystem del container dell'e-service: `data/rulesets/`

**Source**: GitHub `italia/api-oas-checker-rules`

---

## Workflow Completo: Esempio

### 1. Upload File
- Il client invia un file via `POST /oas/validate`.
- L'e-service calcola l'hash, salva il contenuto nel DB e risponde con l'ID.

### 2. Validazione
- L'e-service invia una richiesta HTTP alla Validation Function.
- Il payload contiene: `file_content`, `ruleset_content`, `validation_id`, ecc.
- La function esegue Spectral CLI tramite il modulo `shared.validator`.
- La function non deve scaricare nulla: ha tutto nel corpo della richiesta.

### 3. Callback
- La function esegue Spectral e ottiene il report JSON.
- Invia il report via `POST /oas/callback` all'e-service.
- L'e-service aggiorna il record nel DB inserendo il report nel campo `report_content` e impostando lo stato a `COMPLETED`.

### 4. Consultazione
- Il client chiama `GET /oas/report/{id}`.
- L'e-service legge il report dal DB e lo restituisce.