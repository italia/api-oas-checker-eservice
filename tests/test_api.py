"""
Test suite for OAS Checker e-service API endpoints.
"""
import pytest
from unittest.mock import patch
from models.validation import ValidationStatus
from models.schemas import ValidationResponse, ReportResponse
from datetime import datetime, timezone

class TestStatusEndpoint:
    """Tests for /status endpoint (ModI compliance)"""

    async def test_status_returns_200(self, client):
        """Test that status endpoint returns 200 OK"""
        response = await client.get("/status")
        assert response.status_code == 200

    async def test_status_content_type(self, client):
        """Test that status returns application/problem+json"""
        response = await client.get("/status")
        assert "application/problem+json" in response.headers["content-type"]

    async def test_status_response_structure(self, client):
        """Test that status response has correct RFC 9457 structure"""
        response = await client.get("/status")
        data = response.json()
        assert "status" in data
        assert "title" in data
        assert "detail" in data
        assert data["status"] == 200


class TestRulesetsEndpoint:
    """Tests for /oas/rulesets endpoint"""

    async def test_rulesets_returns_200(self, client):
        """Test that rulesets endpoint returns 200 OK"""
        response = await client.get("/oas/rulesets")
        assert response.status_code == 200

    async def test_rulesets_response_structure(self, client):
        """Test that rulesets response has correct structure"""
        response = await client.get("/oas/rulesets")
        data = response.json()
        assert "rulesets" in data
        assert "metadata" in data
        assert isinstance(data["rulesets"], list)


class TestValidateEndpoint:
    """Tests for /oas/validate endpoint"""

    async def test_validate_requires_file(self, client):
        """Test that validate endpoint requires file parameter"""
        response = await client.post("/oas/validate")
        assert response.status_code == 422  # Validation error

    async def test_validate_success(self, client):
        """Test successful validation submission"""
        yaml_content = b"openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}"
        files = {"file": ("test.yaml", yaml_content, "application/x-yaml")}
        
        with patch("pathlib.Path.read_text", return_value="ruleset content"):
            with patch("pathlib.Path.exists", return_value=True):
                response = await client.post("/oas/validate", files=files)
                
                assert response.status_code == 202
                assert "validation_id" in response.json()


class TestReportEndpoint:
    """Tests for /oas/report/{validation_id} endpoint"""

    async def test_get_report_nonexistent(self, client):
        """Test that requesting non-existent report returns 404"""
        response = await client.get("/oas/report/nonexistent123")
        assert response.status_code == 404

    async def test_get_report_after_validation(self, client):
        """Test submitting validation and then getting report"""
        yaml_content = b"openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}"
        files = {"file": ("test.yaml", yaml_content, "application/x-yaml")}
        
        with patch("pathlib.Path.read_text", return_value="ruleset content"):
            with patch("pathlib.Path.exists", return_value=True):
                # 1. Start validation
                resp = await client.post("/oas/validate", files=files)
                val_id = resp.json()["validation_id"]
                
                # 2. Get report (should be PENDING)
                resp = await client.get(f"/oas/report/{val_id}")
                assert resp.status_code == 200
                assert resp.json()["status"] == "PENDING"


class TestOpenAPISchema:
    """Tests for OpenAPI schema endpoints"""

    async def test_openapi_json_available(self, client):
        """Test that OpenAPI JSON schema is available"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    async def test_docs_available(self, client):
        """Test that Swagger UI docs are available"""
        response = await client.get("/docs")
        assert response.status_code == 200