#!/bin/bash
#
# Setup script for OAS Checker E-Service
# Installs all dependencies and configures the environment
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   OAS Checker E-Service - Setup Script           ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    log_error "Unsupported OS: $OSTYPE"
    exit 1
fi
log_info "Detected OS: $OS"

# Check Python version
log_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 not found. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    log_error "Python $REQUIRED_VERSION or higher required. Found: $PYTHON_VERSION"
    exit 1
fi
log_success "Python $PYTHON_VERSION detected"

# Check Node.js (for Azurite and Azure Functions Core Tools)
log_info "Checking Node.js..."
if ! command -v node &> /dev/null; then
    log_warning "Node.js not found. Installing Node.js..."
    if [ "$OS" == "macos" ]; then
        if command -v brew &> /dev/null; then
            brew install node
        else
            log_error "Homebrew not found. Install Node.js manually: https://nodejs.org"
            exit 1
        fi
    elif [ "$OS" == "linux" ]; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
fi
NODE_VERSION=$(node --version)
log_success "Node.js $NODE_VERSION detected"

# Create virtual environment
log_info "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip --quiet

# Install Python dependencies
log_info "Installing Python dependencies..."
pip install -r requirements.txt --quiet
log_success "Python dependencies installed"

# Install Azurite (Azure Storage Emulator)
log_info "Installing Azurite..."
if command -v azurite &> /dev/null; then
    log_info "Azurite already installed"
else
    npm install -g azurite
    log_success "Azurite installed"
fi

# Install Azure Functions Core Tools
log_info "Installing Azure Functions Core Tools..."
if command -v func &> /dev/null; then
    log_info "Azure Functions Core Tools already installed"
else
    if [ "$OS" == "macos" ]; then
        if command -v brew &> /dev/null; then
            brew tap azure/functions
            brew install azure-functions-core-tools@4
            log_success "Azure Functions Core Tools installed"
        else
            log_warning "Homebrew not found. Install manually: https://docs.microsoft.com/azure/azure-functions/functions-run-local"
        fi
    elif [ "$OS" == "linux" ]; then
        wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb
        sudo dpkg -i packages-microsoft-prod.deb
        sudo apt-get update
        sudo apt-get install -y azure-functions-core-tools-4
        rm packages-microsoft-prod.deb
        log_success "Azure Functions Core Tools installed"
    fi
fi

# Create necessary directories
log_info "Creating project directories..."
mkdir -p data/db
mkdir -p data/storage/oas
mkdir -p data/storage/reports
mkdir -p data/azurite
log_success "Directories created"

# Create .env file if not exists
log_info "Creating .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
fi
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# E-Service Configuration
ESERVICE_HOST=0.0.0.0
ESERVICE_PORT=8000

# Storage Configuration
STORAGE_TYPE=local
STORAGE_PATH=./data/storage

# Azure Storage (for Azurite or production)
# STORAGE_TYPE=azure
# AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;
# AZURE_STORAGE_CONTAINER=oas-files

# Database Configuration
DATABASE_PATH=./data/db/validations.db

# Function Configuration
FUNCTION_TYPE=mock
FUNCTION_URL=http://localhost:8001

# Azure Function (for production)
# FUNCTION_TYPE=azure
# AZURE_FUNCTION_URL=https://your-function-app.azurewebsites.net/api
# AZURE_FUNCTION_KEY=your-function-key

# Callback URL
CALLBACK_BASE_URL=http://localhost:8000

# Logging
LOG_LEVEL=INFO
EOF
    log_success ".env file created"
else
    log_info ".env file already exists (skipped)"
fi

# Create Azure Function local.settings.json if not exists
log_info "Creating Azure Function local.settings.json..."
if [ ! -f "azure_function/local.settings.json" ]; then
    cp azure_function/local.settings.json.example azure_function/local.settings.json
    log_success "Azure Function local.settings.json created"
else
    log_info "Azure Function local.settings.json already exists (skipped)"
fi

# Initialize database
log_info "Initializing database..."
python -m database.db init
log_success "Database initialized"

# Generate OpenAPI schema
log_info "Generating OpenAPI schema..."
python generate_openapi.py
log_success "OpenAPI schema generated"

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   Setup Complete!                                 ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
log_success "All dependencies installed"
log_success "Environment configured"
log_success "Database initialized"
echo ""
log_info "Next steps:"
echo ""
echo "  1. Activate virtual environment:"
echo "     ${GREEN}source venv/bin/activate${NC}"
echo ""
echo "  2. Start the e-service:"
echo "     ${GREEN}./scripts/start.sh${NC}"
echo ""
echo "  3. Or start services manually:"
echo "     Terminal 1: ${GREEN}python main.py${NC}"
echo "     Terminal 2: ${GREEN}python function_mock/app.py${NC}"
echo ""
echo "  4. Access Swagger UI:"
echo "     ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "  5. For Azure local environment (Azurite):"
echo "     ${GREEN}./scripts/start-azure-local.sh${NC}"
echo ""
