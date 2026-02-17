#!/bin/bash
#
# Stop script for OAS Checker E-Service
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   Stopping OAS Checker E-Service                  ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Check for tmux session
if command -v tmux &> /dev/null; then
    if tmux has-session -t oas-checker 2>/dev/null; then
        log_info "Stopping tmux session..."
        tmux kill-session -t oas-checker
        log_success "Tmux session stopped"
    fi
fi

# Check for screen session
if command -v screen &> /dev/null; then
    if screen -list | grep -q oas-checker; then
        log_info "Stopping screen session..."
        screen -S oas-checker -X quit
        log_success "Screen session stopped"
    fi
fi

# Check for PID files
if [ -f ".eservice.pid" ]; then
    ESERVICE_PID=$(cat .eservice.pid)
    log_info "Stopping e-service (PID: $ESERVICE_PID)..."
    kill $ESERVICE_PID 2>/dev/null || true
    rm .eservice.pid
    log_success "E-Service stopped"
fi

if [ -f ".function.pid" ]; then
    FUNCTION_PID=$(cat .function.pid)
    log_info "Stopping function mock (PID: $FUNCTION_PID)..."
    kill $FUNCTION_PID 2>/dev/null || true
    rm .function.pid
    log_success "Function mock stopped"
fi

# Kill any remaining Python processes running main.py or function_mock/app.py
log_info "Checking for remaining processes..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*function_mock/app.py" 2>/dev/null || true

# Kill any processes on ports 8000 and 8001
if command -v lsof &> /dev/null; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
fi

log_success "All services stopped"
echo ""
