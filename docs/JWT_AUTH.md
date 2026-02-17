# Autenticazione JWT

L'OAS Checker e-service è progettato per operare dietro un API Gateway (GovWay) che si occupa della validazione dei token JWT della PDND.

## Middleware Globale

L'autenticazione è gestita centralmente dal `JWTAuthenticationMiddleware`. Questo middleware intercetta ogni richiesta e verifica la presenza di un token JWT valido negli header, a meno che l'endpoint non sia esplicitamente escluso.

### Endpoint Esclusi (Public)
I seguenti endpoint non richiedono autenticazione JWT:
- `/status`: Health check del servizio.
- `/oas/callback`: Ricezione esiti dalla Function (protetto da HMAC).
- `/docs`, `/openapi.json`: Documentazione API (Swagger UI).

## Configurazione

In produzione, l'autenticazione è abilitata tramite l'impostazione `JWT_ENABLED=true`.

In ambiente di sviluppo, la verifica può essere disabilitata (`false`) per facilitare i test manuali. In questo caso, il `consumerId` viene impostato di default al valore `dev`.

## Integrazione con GovWay

Per il corretto funzionamento dell'autenticazione, è necessario configurare l'API Gateway (GovWay) affinché l'header `Authorization` venga inoltrato all'e-service. Di default, GovWay rimuove tale header dopo aver effettuato la validazione del token. Si deve quindi attivare esplicitamente l'opzione di inoltro dell'header nelle impostazioni di controllo accessi della specifica interfaccia di erogazione.
