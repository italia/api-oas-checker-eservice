#!/bin/bash

# Default values
MODE="bridge"
ESERVICE_PORT=8000
FUNCTION_PORT=7071
POSTGRES_PORT=15432

# Detect docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Error: Neither 'docker compose' nor 'docker-compose' found."
    exit 1
fi

show_help() {
    echo "Usage: ./run-oas.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --mode [bridge|host]    Deployment mode (default: bridge)"
    echo "  -p, --port-api PORT         e-service API port (default: 8000)"
    echo "  -f, --port-func PORT        Azure Function port (default: 7071)"
    echo "  -db, --port-db PORT         PostgreSQL port (default: 15432)"
    echo "  -h, --help                  Show this help"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode) MODE="$2"; shift 2 ;;
        -p|--port-api) ESERVICE_PORT="$2"; shift 2 ;;
        -f|--port-func) FUNCTION_PORT="$2"; shift 2 ;;
        -db|--port-db) POSTGRES_PORT="$2"; shift 2 ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown option: $1"; show_help; exit 1 ;;
    esac
done

echo "🚀 Starting OAS Checker in '$MODE' mode using '$DOCKER_COMPOSE'..."

if [ "$MODE" == "host" ]; then
    export ESERVICE_PORT_HOST=$ESERVICE_PORT
    export FUNCTION_PORT_HOST=$FUNCTION_PORT
    export POSTGRES_PORT_HOST=$POSTGRES_PORT
    $DOCKER_COMPOSE -f docker-compose-host.yml up -d
else
    # BRIDGE MODE
    # Mapping custom ports both as host port and container port for consistency
    export ESERVICE_PORT=$ESERVICE_PORT
    export FUNCTION_PORT=$FUNCTION_PORT
    export POSTGRES_PORT=$POSTGRES_PORT
    
    # Sync internal ports with the chosen ports so eservice logs show the correct values
    export POSTGRES_PORT_INTERNAL=$POSTGRES_PORT
    export FUNCTION_PORT_INTERNAL=$FUNCTION_PORT
    
    $DOCKER_COMPOSE -f docker-compose.yml up -d
fi

if [ $? -eq 0 ]; then
    echo "✅ System started!"
    echo "🔗 API: http://localhost:$ESERVICE_PORT"
    echo "🔗 DB:  localhost:$POSTGRES_PORT"
else
    echo "❌ Failed to start."
    exit 1
fi