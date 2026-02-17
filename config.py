"""
Configuration management
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# e-service configuration
ESERVICE_HOST = os.getenv("ESERVICE_HOST", "0.0.0.0")
ESERVICE_PORT = int(os.getenv("ESERVICE_PORT", "8000"))

# OpenAPI Server URL (for Swagger UI and API documentation)
OPENAPI_SERVER_URL = os.getenv("OPENAPI_SERVER_URL", f"http://localhost:{ESERVICE_PORT}")

# Database configuration
# PostgreSQL connection URL format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://oaschecker:oaschecker@localhost:5432/oaschecker"
)

# Function configuration
FUNCTION_TYPE = os.getenv("FUNCTION_TYPE", "mock")  # mock | azure
FUNCTION_URL = os.getenv("FUNCTION_URL", "http://localhost:8001")

# Azure Function (if using azure function)
AZURE_FUNCTION_KEY = os.getenv("AZURE_FUNCTION_KEY", "")

# Callback URL (for function to call back)
CALLBACK_BASE_URL = os.getenv(
    "CALLBACK_BASE_URL",
    f"http://{ESERVICE_HOST}:{ESERVICE_PORT}"
)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ruleset configuration
RULESET_REPO = os.getenv(
    "RULESET_REPO",
    "italia/api-oas-checker-rules"
)
RULESET_VERSION = os.getenv("RULESET_VERSION", "latest")  # "latest" or specific tag like "1.2"
RULESET_PATH = os.getenv("RULESET_PATH", str(DATA_DIR / "rulesets"))
RULESET_AUTO_UPDATE = os.getenv("RULESET_AUTO_UPDATE", "true").lower() == "true"

# JWT Authentication
JWT_ENABLED = os.getenv("JWT_ENABLED", "true").lower() == "true"  # Disable in local/dev

# HMAC Callback Security
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET", "dev-secret-change-in-production")  # Must match Azure Function
HMAC_ENABLED = os.getenv("HMAC_ENABLED", "true").lower() == "true"  # Disable in local/dev
HMAC_TIMESTAMP_WINDOW = int(os.getenv("HMAC_TIMESTAMP_WINDOW", "300"))  # 5 minutes default

# Rate Limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"  # Enable rate limiting
RATE_LIMIT_VALIDATE_REQUESTS = int(os.getenv("RATE_LIMIT_VALIDATE_REQUESTS", "10"))  # /oas/validate
RATE_LIMIT_VALIDATE_WINDOW = int(os.getenv("RATE_LIMIT_VALIDATE_WINDOW", "60"))  # seconds
RATE_LIMIT_REPORT_REQUESTS = int(os.getenv("RATE_LIMIT_REPORT_REQUESTS", "60"))  # /oas/report
RATE_LIMIT_REPORT_WINDOW = int(os.getenv("RATE_LIMIT_REPORT_WINDOW", "60"))  # seconds
RATE_LIMIT_DEFAULT_REQUESTS = int(os.getenv("RATE_LIMIT_DEFAULT_REQUESTS", "30"))  # other endpoints
RATE_LIMIT_DEFAULT_WINDOW = int(os.getenv("RATE_LIMIT_DEFAULT_WINDOW", "60"))  # seconds
RATE_LIMIT_CLEANUP_HOURS = int(os.getenv("RATE_LIMIT_CLEANUP_HOURS", "24"))  # cleanup records older than N hours


import logging

logger = logging.getLogger(__name__)

def print_config():
    """Log current configuration"""
    logger.info("=== OAS Checker e-service Configuration ===")
    logger.info(f"Host: {ESERVICE_HOST}:{ESERVICE_PORT}")
    logger.info(f"OpenAPI Server URL: {OPENAPI_SERVER_URL}")
    # Mask password in database URL for security
    db_url_display = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Database URL: ***@{db_url_display}")
    logger.info(f"Function Type: {FUNCTION_TYPE}")
    logger.info(f"Function URL: {FUNCTION_URL}")
    logger.info(f"Callback URL: {CALLBACK_BASE_URL}")
    logger.info(f"Ruleset Repo: {RULESET_REPO}")
    logger.info(f"Ruleset Version: {RULESET_VERSION}")
    logger.info(f"Ruleset Path: {RULESET_PATH}")
    logger.info(f"Ruleset Auto-Update: {RULESET_AUTO_UPDATE}")
    logger.info(f"JWT Authentication: {JWT_ENABLED}")
    logger.info(f"HMAC Callback Security: {HMAC_ENABLED}")
    logger.info(f"Rate Limiting: {RATE_LIMIT_ENABLED}")
    if RATE_LIMIT_ENABLED:
        logger.info(f"  /oas/validate: {RATE_LIMIT_VALIDATE_REQUESTS} req/{RATE_LIMIT_VALIDATE_WINDOW}s")
        logger.info(f"  /oas/report: {RATE_LIMIT_REPORT_REQUESTS} req/{RATE_LIMIT_REPORT_WINDOW}s")
        logger.info(f"  default: {RATE_LIMIT_DEFAULT_REQUESTS} req/{RATE_LIMIT_DEFAULT_WINDOW}s")
    logger.info("==========================================")


if __name__ == "__main__":
    print_config()