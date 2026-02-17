"""
Unit tests for ValidationService (storage-less version)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from services.validation_service import ValidationService
from models.validation import ValidationStatus, FileFormat
from models.schemas import FunctionValidationRequest, CallbackRequest, ReportResponse
from datetime import datetime, timezone


@pytest.fixture
def mock_repo():
    return AsyncMock()


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
def service(mock_repo, mock_client, mock_ruleset_manager):
    return ValidationService(
        repository=mock_repo,
        function_client=mock_client,
        callback_base_url="http://localhost:8000",
        ruleset_manager=mock_ruleset_manager
    )


@pytest.mark.asyncio
async def test_start_validation_success(service, mock_repo, mock_client):
    # Mock UploadFile
    content = b"openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}"
    file = AsyncMock(spec=UploadFile)
    file.read.return_value = content
    file.filename = "test.yaml"
    
    mock_repo.get_by_id.return_value = None
    
    with patch("pathlib.Path.read_text", return_value="ruleset content"):
        # We need to mock Path.exists too because we check it
        with patch("pathlib.Path.exists", return_value=True):
            response = await service.start_validation(file, "default", False, "json")
            
            assert response.status == ValidationStatus.PENDING
            assert mock_repo.create.called
            assert mock_client.invoke_validation.called
            
            # Verify request sent to function
            req = mock_client.invoke_validation.call_args[0][0]
            assert isinstance(req, FunctionValidationRequest)
            assert req.file_content == content.decode()
            assert req.ruleset_content == "ruleset content"


@pytest.mark.asyncio
async def test_start_validation_existing(service, mock_repo, mock_client):
    content = b"openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}"
    file = AsyncMock(spec=UploadFile)
    file.read.return_value = content
    file.filename = "test.yaml"
    
    existing = MagicMock()
    existing.status = ValidationStatus.COMPLETED
    mock_repo.get_by_id.return_value = existing
    
    with patch("pathlib.Path.read_text", return_value="ruleset content"):
        response = await service.start_validation(file, "default", False, "json")
        
        assert response.status == ValidationStatus.COMPLETED
        assert "already exists" in response.message
        assert not mock_repo.create.called


@pytest.mark.asyncio
async def test_handle_callback(service, mock_repo):
    cb = CallbackRequest(
        validation_id="test-id",
        status=ValidationStatus.COMPLETED,
        report_content={"valid": True}
    )
    
    await service.handle_callback(cb)
    
    mock_repo.update_status.assert_called_with(
        validation_id="test-id",
        status=ValidationStatus.COMPLETED,
        report_content={"valid": True},
        error_message=None
    )


@pytest.mark.asyncio
async def test_get_report(service, mock_repo):
    now = datetime.now(timezone.utc)
    mock_val = MagicMock()
    mock_val.id = "test-id"
    mock_val.status = ValidationStatus.COMPLETED
    mock_val.ruleset = "default"
    mock_val.ruleset_version = "1.0"
    mock_val.errors_only = False
    mock_val.file_sha256 = "hash"
    mock_val.report_content = {"valid": True}
    mock_val.created_at = now
    mock_val.completed_at = now
    mock_val.error_message = None
    
    mock_repo.get_by_id.return_value = mock_val
    
    report = await service.get_report("test-id")
    
    assert isinstance(report, ReportResponse)
    assert report.status == ValidationStatus.COMPLETED
    assert report.report == {"valid": True}