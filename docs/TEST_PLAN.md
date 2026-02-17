# Piano di Test - OAS Checker e-service

Questo documento definisce la strategia di test per garantire la qualità, la sicurezza e la conformità del servizio OAS Checker.

## 1. Strategia di Test

### 1.1 Architettura dei Test
*   **Layer 1: Unit & Logic (SQLite)**: Copertura della business logic e del repository utilizzando un backend SQLite isolato.
*   **Layer 2: Integration (PostgreSQL)**: Verifica delle specificità di PostgreSQL (JSONB, indici, pooling) in ambiente containerizzato.
*   **Layer 3: End-to-End (E2E)**: Validazione dei flussi completi: Upload -> Background Validation -> Callback -> Report Retrieval.

### 1.2 Tooling
*   **Pytest**: Framework principale per l'esecuzione dei test.
*   **pytest-cov**: Strumento per la misurazione della copertura del codice.
*   **aiosqlite**: Utilizzato per test database isolati.
*   **httpx (AsyncClient)**: Utilizzato per simulare chiamate API reali.
*   **Mock/AsyncMock**: Utilizzati per isolare servizi esterni (GitHub, Azure Functions).

---

## 2. Casi di Test Chiave

### 2.1 API & Conformità
*   **TC-01**: Verifica conformità ModI (`/status` ritorna `application/problem+json`).
*   **TC-02**: Verifica RFC 9457 (Problem Details) su tutti gli errori (400, 404, 422, 429, 500).
*   **TC-03**: Verifica generazione automatica schema OpenAPI (v3.1.0 e v3.0.3).

### 2.2 Ciclo di Vita Validazione
*   **TC-10**: Upload file OpenAPI -> Salvataggio contenuto su DB -> Stato `PENDING`.
*   **TC-11**: Invio payload completo alla Function (file + ruleset content).
*   **TC-12**: Ricezione callback -> Update report JSONB su DB -> Stato `COMPLETED`.
*   **TC-13**: Deduplicazione (stesso contenuto + parametri = stesso ID).

### 2.3 Gestione Ruleset
*   **TC-20**: Download automatico release da GitHub.
*   **TC-21**: Validità della cache locale e meccanismo di refresh.
*   **TC-22**: Down-conversion dei ruleset per compatibilità OpenAPI 3.0.3.

### 2.4 Sicurezza
*   **TC-30**: Autenticazione JWT (estrazione `producerId` e `consumerId`).
*   **TC-31**: Autorizzazione interna (verifica matching `producerId` == `consumerId` per endpoint `/internal/*`).
*   **TC-32**: Validazione firma HMAC nelle callback (integrità payload).
*   **TC-33**: Protezione da Replay Attack (controllo timestamp).

---

## 3. Criteri di Accettazione (Stato Attuale)
*   **Pass Rate**: 100% (65 test eseguiti con successo).
*   **Coverage**: 80% (media su tutti i moduli core).
*   **Tempo di risposta `/oas/validate`**: < 50ms (invocazione asincrona).
