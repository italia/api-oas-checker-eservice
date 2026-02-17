# Dockerfile per OAS Checker e-service
# Build: docker build -t oas-checker-eservice .
# Run: docker run -p 8000:8000 -v $(pwd)/data:/app/data oas-checker-eservice

FROM python:3.11-slim

# Metadata
LABEL maintainer="OAS Checker Team"
LABEL description="e-service per validazione OpenAPI con Spectral"
LABEL version="1.0.0"

# Variabili di build
ARG DEBIAN_FRONTEND=noninteractive

# Imposta working directory
WORKDIR /app

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia codice sorgente
COPY config.py .
COPY main.py .
COPY models/ models/
COPY database/ database/
COPY shared/ shared/
COPY services/ services/
COPY api/ api/
COPY scripts/ scripts/

# Crea directory per dati runtime
RUN mkdir -p /app/data/rulesets

# Note: Database initialization will happen at startup, not at build time
# This is required for PostgreSQL as it needs a live connection

# Espone porta 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/status || exit 1

# User non-root per sicurezza
RUN useradd -m -u 1000 oasuser && \
    chown -R oasuser:oasuser /app
USER oasuser

# Environment variables di default
ENV ESERVICE_HOST=0.0.0.0
ENV ESERVICE_PORT=8000
ENV DATABASE_URL=postgresql://oaschecker:oaschecker@localhost:5432/oaschecker
ENV FUNCTION_TYPE=azure-local
ENV FUNCTION_URL=http://azure-function:80/api/validate
ENV RULESET_REPO=italia/api-oas-checker-rules
ENV RULESET_VERSION=latest
ENV RULESET_PATH=/app/data/rulesets
ENV RULESET_AUTO_UPDATE=true

# Comando di avvio
CMD ["python", "main.py"]