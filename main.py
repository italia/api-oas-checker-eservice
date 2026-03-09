"""
OAS Checker e-service - Main entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import logging
import uvicorn

from api.routes import router
from api.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from api.logging_config import setup_logging
import config

logger = logging.getLogger(__name__)

# Setup structured logging
setup_logging()

# Create FastAPI app
# Configure multiple servers for Swagger UI dropdown
servers = []

# Add localhost server if running locally
if config.ESERVICE_HOST in ["0.0.0.0", "localhost", "127.0.0.1"]:
    servers.append({
        "url": f"http://localhost:{config.ESERVICE_PORT}",
        "description": "Local Development Server"
    })

# Add configured production/staging server if different from localhost
if config.OPENAPI_SERVER_URL not in [f"http://localhost:{config.ESERVICE_PORT}", "http://localhost:8000"]:
    servers.append({
        "url": config.OPENAPI_SERVER_URL,
        "description": "Production Server"
    })

# Fallback if no servers configured
if not servers:
    servers.append({
        "url": config.OPENAPI_SERVER_URL,
        "description": "API Server"
    })

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting OAS Checker e-service...")
    config.print_config()

    # Initialize database connection pool
    try:
        from api.dependencies import get_database
        db = get_database()
        logger.info("Initializing database connection pool...")
        await db.create_pool()
        await db.init_db()
        logger.info("Database ready!")
    except Exception as e:
        logger.error(f"Error: Failed to initialize database: {e}")
        raise

    # Download rulesets from GitHub
    if config.RULESET_AUTO_UPDATE:
        try:
            from services.ruleset_manager import get_ruleset_manager

            logger.info(f"Downloading rulesets from {config.RULESET_REPO} ({config.RULESET_VERSION})...")

            manager = get_ruleset_manager(
                repo=config.RULESET_REPO,
                version=config.RULESET_VERSION,
                cache_dir=config.RULESET_PATH
            )

            rulesets = await manager.download_rulesets(force=False)
            logger.info(f"Rulesets ready! Available: {', '.join(rulesets.keys())}")

        except Exception as e:
            logger.warning(f"Warning: Failed to download rulesets: {e}")
            logger.info("Service will continue with cached rulesets if available")
    else:
        logger.info("Ruleset auto-update disabled (RULESET_AUTO_UPDATE=false)")

    # Generate OpenAPI schema on startup (requires writable CWD, disable in prod)
    if config.OPENAPI_GENERATE_ON_STARTUP:
        try:
            from scripts.generate_openapi import generate_openapi_schema
            logger.info("Generating OpenAPI schema...")
            generate_openapi_schema(output_format="both", output_dir=".")
        except Exception as e:
            logger.warning(f"Warning: Failed to generate OpenAPI schema: {e}")
    else:
        logger.info("OpenAPI schema generation disabled (OPENAPI_GENERATE_ON_STARTUP=false)")

    # Start rate limit cleanup task
    if config.RATE_LIMIT_ENABLED:
        import asyncio
        from api.rate_limit import RateLimiter
        from api.dependencies import get_database

        async def rate_limit_cleanup_task():
            """Background task to cleanup old rate limit records"""
            rate_limiter = RateLimiter(get_database())
            while True:
                try:
                    await asyncio.sleep(3600)  # Run every hour
                    await rate_limiter.cleanup_old_records()
                except Exception as e:
                    logger.error(f"Error in rate limit cleanup task: {e}")

        asyncio.create_task(rate_limit_cleanup_task())
        logger.info(f"Rate limit cleanup task started (runs every hour)")

    yield

    # Shutdown
    logger.info("Shutting down OAS Checker e-service...")

    # Close database connection pool
    try:
        from api.dependencies import get_database
        db = get_database()
        await db.close_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.warning(f"Warning: Failed to close database pool: {e}")

app = FastAPI(
    title="OAS Checker e-service",
    description="OpenAPI validation service using Spectral",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=servers,
    lifespan=lifespan
)


# Register exception handlers (RFC 9457 Problem Details)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS middleware (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
if config.RATE_LIMIT_ENABLED:
    from api.rate_limit import RateLimitMiddleware
    from api.dependencies import get_database

    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware, database=get_database())

# JWT Authentication middleware
from api.auth import JWTAuthenticationMiddleware
app.add_middleware(JWTAuthenticationMiddleware)

# Include API routes
app.include_router(router)





if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=config.ESERVICE_HOST,
        port=config.ESERVICE_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )
