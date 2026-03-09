"""
Pytest configuration and fixtures for OAS Checker tests.
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# Set environment variables for testing
os.environ["ESERVICE_HOST"] = "localhost"
os.environ["ESERVICE_PORT"] = "8000"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["JWT_ENABLED"] = "false"
os.environ["HMAC_ENABLED"] = "false"
os.environ["RULESET_AUTO_UPDATE"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "DEBUG"

from database.db import Database
from database.repository import ValidationRepository
from services.validation_service import ValidationService

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if os.path.exists("test.db"):
        os.remove("test.db")
    yield
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture
async def db():
    db_inst = Database("sqlite:///test.db")
    await db_inst.create_pool()
    await db_inst.init_db()
    yield db_inst
    await db_inst.close_pool()

@pytest.fixture
def repo(db):
    return ValidationRepository(db)

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.invoke_validation = AsyncMock(return_value=True)
    return client

@pytest.fixture
def mock_ruleset_manager():
    manager = AsyncMock()
    manager.get_metadata.return_value = {"tag": "1.0"}
    manager.get_ruleset_path.return_value = "/tmp/ruleset.yml"
    return manager

@pytest.fixture
def service(repo, mock_client, mock_ruleset_manager):
    return ValidationService(
        repository=repo,
        function_client=mock_client,
        callback_base_url="http://localhost:8000",
        ruleset_manager=mock_ruleset_manager
    )

@pytest.fixture
async def client(db, repo, service):
    """
    Client fixture that overrides dependencies
    """
    from main import app
    from api.dependencies import get_database, get_repository, get_validation_service
    
    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_validation_service] = lambda: service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides = {}