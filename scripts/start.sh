#!/bin/bash
#
# Start script for OAS Checker E-Service
# Starts e-service and function mock in separate terminals
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   Starting OAS Checker E-Service                  ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    log_warning "Virtual environment not activated. Activating..."
    source venv/bin/activate
fi

# Check if database exists
if [ ! -f "data/db/validations.db" ]; then
    log_info "Database not found. Initializing..."
    python -m database.db init
fi

# Detect terminal multiplexer
if command -v tmux &> /dev/null; then
    log_info "Using tmux to start services..."

    # Create tmux session
    SESSION_NAME="oas-checker"

    # Kill existing session if exists
    tmux kill-session -t $SESSION_NAME 2>/dev/null || true

    # Create new session with e-service
    tmux new-session -d -s $SESSION_NAME -n "e-service" "source venv/bin/activate && python main.py"

    # Create new window for function mock
    tmux new-window -t $SESSION_NAME -n "function-mock" "source venv/bin/activate && python function_mock/app.py"

    # Create new window for logs
    tmux new-window -t $SESSION_NAME -n "logs" "echo 'Logs window - use Ctrl+B followed by 0/1 to switch windows'; bash"

    # Attach to session
    log_success "Services started in tmux session"
    echo ""
    log_info "To view services:"
    echo "  ${GREEN}tmux attach -t $SESSION_NAME${NC}"
    echo ""
    log_info "Tmux commands:"
    echo "  Ctrl+B then 0 - Switch to e-service window"
    echo "  Ctrl+B then 1 - Switch to function-mock window"
    echo "  Ctrl+B then 2 - Switch to logs window"
    echo "  Ctrl+B then d - Detach from session"
    echo "  ${GREEN}tmux kill-session -t $SESSION_NAME${NC} - Stop all services"
    echo ""

    sleep 2
    tmux attach -t $SESSION_NAME

elif command -v screen &> /dev/null; then
    log_info "Using screen to start services..."

    SESSION_NAME="oas-checker"

    # Kill existing session if exists
    screen -S $SESSION_NAME -X quit 2>/dev/null || true

    # Create new session with e-service
    screen -dmS $SESSION_NAME bash -c "source venv/bin/activate && python main.py"

    # Create new window for function mock
    screen -S $SESSION_NAME -X screen bash -c "source venv/bin/activate && python function_mock/app.py"

    log_success "Services started in screen session"
    echo ""
    log_info "To view services:"
    echo "  ${GREEN}screen -r $SESSION_NAME${NC}"
    echo ""
    log_info "Screen commands:"
    echo "  Ctrl+A then n - Next window"
    echo "  Ctrl+A then p - Previous window"
    echo "  Ctrl+A then d - Detach from session"
    echo "  ${GREEN}screen -S $SESSION_NAME -X quit${NC} - Stop all services"
    echo ""

else
    log_warning "tmux/screen not found. Starting services in background..."

    # Start e-service in background
    log_info "Starting e-service on port 8000..."
    python main.py > logs/eservice.log 2>&1 &
    ESERVICE_PID=$!
    echo $ESERVICE_PID > .eservice.pid

    # Wait for e-service to start
    sleep 3

    # Start function mock in background
    log_info "Starting function mock on port 8001..."
    python function_mock/app.py > logs/function-mock.log 2>&1 &
    FUNCTION_PID=$!
    echo $FUNCTION_PID > .function.pid

    # Wait for function mock to start
    sleep 3

    log_success "Services started in background"
    echo ""
    echo "  E-Service PID: $ESERVICE_PID"
    echo "  Function Mock PID: $FUNCTION_PID"
    echo ""
    log_info "Logs:"
    echo "  E-Service:     ${GREEN}tail -f logs/eservice.log${NC}"
    echo "  Function Mock: ${GREEN}tail -f logs/function-mock.log${NC}"
    echo ""
    log_info "To stop services:"
    echo "  ${GREEN}./scripts/stop.sh${NC}"
    echo ""
fi

# Display access URLs
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   Services Running                                ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
echo "  E-Service:      ${GREEN}http://localhost:8000${NC}"
echo "  Swagger UI:     ${GREEN}http://localhost:8000/docs${NC}"
echo "  ReDoc:          ${GREEN}http://localhost:8000/redoc${NC}"
echo "  Function Mock:  ${GREEN}http://localhost:8001${NC}"
echo ""
