"""
FastAPI dependency injection
"""
from functools import lru_cache

import config
from database.db import Database
from database.repository import ValidationRepository
from services.function_client import FunctionClient, MockFunctionClient, AzureFunctionClient
from services.validation_service import ValidationService


@lru_cache()
def get_database() -> Database:
    """
    Get database instance with connection pool
    """
    db = Database(config.DATABASE_URL)
    return db


@lru_cache()
def get_repository() -> ValidationRepository:
    """
    Get validation repository
    """
    return ValidationRepository(get_database())


@lru_cache()
def get_function_client() -> FunctionClient:
    """
    Get function client based on configuration
    """
    if config.FUNCTION_TYPE == "mock":
        return MockFunctionClient(config.FUNCTION_URL)
    elif config.FUNCTION_TYPE == "azure":
        return AzureFunctionClient(
            function_url=config.FUNCTION_URL,
            function_key=config.AZURE_FUNCTION_KEY
        )
    elif config.FUNCTION_TYPE == "azure-local":
        # Azure Function locale (no authentication key needed)
        return AzureFunctionClient(
            function_url=config.FUNCTION_URL,
            function_key=None
        )
    else:
        raise ValueError(f"Unknown function type: {config.FUNCTION_TYPE}")


@lru_cache()
def get_validation_service() -> ValidationService:
    """
    Get validation service with all dependencies
    """
    # Get ruleset manager if configured
    ruleset_manager = None
    try:
        from services.ruleset_manager import get_ruleset_manager
        ruleset_manager = get_ruleset_manager(
            repo=config.RULESET_REPO,
            version=config.RULESET_VERSION,
            cache_dir=config.RULESET_PATH
        )
    except Exception:
        pass  # Ruleset manager is optional

    return ValidationService(
        repository=get_repository(),
        function_client=get_function_client(),
        callback_base_url=config.CALLBACK_BASE_URL,
        ruleset_manager=ruleset_manager
    )