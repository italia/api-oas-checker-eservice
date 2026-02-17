# Dockerfile per Azure Function - ProcessValidation
FROM --platform=linux/amd64 mcr.microsoft.com/azure-functions/python:4-python3.11

# Metadata
LABEL maintainer="OAS Checker Team"
LABEL description="Azure Function per validazione OpenAPI"
LABEL version="1.1.0"

# Variabili di build
ARG DEBIAN_FRONTEND=noninteractive

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Installa Node.js (v20 LTS) per Spectral CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Installa Spectral CLI globalmente
RUN npm install -g @stoplight/spectral-cli@6.11.0

# Imposta working directory
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Copia requirements e installa dipendenze Python
# Nota: il context ora è la root del progetto
COPY azure_function/requirements.txt /home/site/wwwroot/
RUN cd /home/site/wwwroot && \
    pip install --no-cache-dir -r requirements.txt

# Copia configurazione Azure Functions
COPY azure_function/host.json /home/site/wwwroot/
COPY azure_function/local.settings.json /home/site/wwwroot/

# Copia moduli condivisi (dalla root)
COPY shared/ /home/site/wwwroot/shared/

# Copia function ProcessValidation
COPY azure_function/ProcessValidation/ /home/site/wwwroot/ProcessValidation/

# Environment variables di default
ENV FUNCTIONS_WORKER_RUNTIME=python \
    PYTHON_THREADPOOL_THREAD_COUNT=4

# Crea directory per storage/cache
RUN mkdir -p /home/site/wwwroot/data/rulesets

# Espone porta 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1