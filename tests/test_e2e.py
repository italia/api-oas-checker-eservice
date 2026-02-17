"""
End-to-End tests for OAS Checker e-service
"""
import pytest
import config
from httpx import AsyncClient
from unittest.mock import patch

from shared.utils import json_dumps
from shared.security import generate_hmac_headers

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_validation_flow(client: AsyncClient, monkeypatch):
    """
    E2E Test: Full flow from upload to completion via callback.
    Verifies that the system correctly orchestrates validation and updates status.
    """
    # 1. Setup
    monkeypatch.setattr(config, "JWT_ENABLED", False)
    monkeypatch.setattr(config, "HMAC_ENABLED", True)
    secret = "e2e-test-secret"
    monkeypatch.setattr(config, "CALLBACK_SECRET", secret)
    monkeypatch.setenv("CALLBACK_SECRET", secret)
    
    # Mock Path.read_text to avoid FileNotFoundError for ruleset
    with patch("pathlib.Path.read_text", return_value="ruleset content"):
        # 2. Upload OAS file
        yaml_content = b"openapi: 3.0.0\ninfo:\n  title: E2E Test\n  version: 1.0.0\npaths: {}"
        files = {"file": ("e2e.yaml", yaml_content, "application/x-yaml")}
        
        response = await client.post("/oas/validate", files=files, data={"ruleset": "default"})
        assert response.status_code == 202
        validation_id = response.json()["validation_id"]
        
        # 3. Check status (should be PENDING)
        response = await client.get(f"/oas/report/{validation_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING"
        
        # 4. Simulate Function Callback with HMAC
        callback_data = {
            "validation_id": validation_id,
            "status": "COMPLETED",
            "report_content": {
                "valid": True,
                "errors": [],
                "warnings": [],
                "info": [],
                "summary": {"total_issues": 0, "errors": 0, "warnings": 0, "info": 0}
            }
        }
        
        payload_str = json_dumps(callback_data)
        headers = generate_hmac_headers(payload_str)
        
        response = await client.post(
            "/oas/callback", 
            content=payload_str,
            headers={**headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        # 5. Verify final report
        response = await client.get(f"/oas/report/{validation_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["report"]["valid"] is True
        assert data["validation_id"] == validation_id