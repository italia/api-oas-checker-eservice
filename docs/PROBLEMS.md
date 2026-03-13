# Problem Details for OAS Checker e-service

This document describes the problem types (RFC 9457) returned by the OAS Checker e-service.

## Error Types

### `bad-request`
The request was invalid or could not be understood by the server. This often happens if the uploaded file is not a valid YAML/JSON or if required parameters are missing.
- **HTTP Status:** 400 Bad Request

### `validation-error`
The request parameters failed validation (e.g., invalid ruleset name, errors_only is not a boolean).
- **HTTP Status:** 422 Unprocessable Entity

### `rate-limit-exceeded`
Too many requests have been sent in a given amount of time.
- **HTTP Status:** 429 Too Many Requests

### `internal-error`
An unexpected error occurred on the server side while processing the request.
- **HTTP Status:** 500 Internal Server Error

### `not-found`
The requested resource (e.g., a specific validation ID) was not found.
- **HTTP Status:** 404 Not Found

### `validation-not-found`
The specific validation report requested does not exist or has expired.
- **HTTP Status:** 404 Not Found
