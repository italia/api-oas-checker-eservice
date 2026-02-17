"""
Tests for HMAC-SHA256 callback signature verification.
"""
import pytest
import time
import json
import os
from fastapi import Request, HTTPException
from api.hmac import verify_hmac_signature
import config

from shared.utils import json_dumps
from shared.security import generate_hmac_headers


@pytest.fixture
def mock_request():
    def _create_request(payload_bytes, headers):
        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        }

        async def receive():
            return {
                "type": "http.request",
                "body": payload_bytes,
                "more_body": False,
            }

        return Request(scope, receive)

    return _create_request


class TestHMACVerification:
    """Unit tests for verify_hmac_signature function"""

    @pytest.mark.asyncio
    async def test_verify_hmac_disabled(self, mock_request, monkeypatch):
        """Test verification passes when disabled in config"""
        monkeypatch.setattr(config, "HMAC_ENABLED", False)
        request = mock_request(b"{}", {})
        # Should not raise exception
        await verify_hmac_signature(request)

    @pytest.mark.asyncio
    async def test_verify_hmac_missing_signature(self, mock_request, monkeypatch):
        """Test verification fails when signature is missing"""
        monkeypatch.setattr(config, "HMAC_ENABLED", True)
        request = mock_request(b"{}", {"X-Timestamp": "12345"})
        with pytest.raises(HTTPException) as exc_info:
            await verify_hmac_signature(request)
        assert exc_info.value.status_code == 401
        assert "Missing X-Signature header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_hmac_invalid_timestamp(self, mock_request, monkeypatch):
        """Test verification fails when timestamp is too old"""
        monkeypatch.setattr(config, "HMAC_ENABLED", True)
        monkeypatch.setattr(config, "HMAC_TIMESTAMP_WINDOW", 300)
        
        old_timestamp = str(int(time.time()) - 600)
        headers = {
            "X-Timestamp": old_timestamp,
            "X-Signature": "some-sig"
        }
        request = mock_request(b"{}", headers)
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_hmac_signature(request)
        assert exc_info.value.status_code == 401
        assert "Request timestamp expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_hmac_valid_signature(self, mock_request, monkeypatch):
        """Test verification passes with valid signature using shared logic"""
        monkeypatch.setattr(config, "HMAC_ENABLED", True)
        secret = "test-secret"
        monkeypatch.setattr(config, "CALLBACK_SECRET", secret)
        monkeypatch.setenv("CALLBACK_SECRET", secret) # For shared.security
        
        payload = {"validation_id": "test123", "status": "COMPLETED"}
        payload_str = json_dumps(payload)
        
        # Generate headers using shared logic
        headers = generate_hmac_headers(payload_str)
        
        request = mock_request(payload_str.encode(), headers)
        
        # Should not raise exception
        await verify_hmac_signature(request)

    @pytest.mark.asyncio
    async def test_verify_hmac_invalid_signature(self, mock_request, monkeypatch):
        """Test verification fails with invalid signature"""
        monkeypatch.setattr(config, "HMAC_ENABLED", True)
        monkeypatch.setattr(config, "CALLBACK_SECRET", "secret")
        
        headers = {
            "X-Timestamp": str(int(time.time())),
            "X-Signature": "wrong-signature"
        }
        request = mock_request(b'{"id":"1"}', headers)
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_hmac_signature(request)
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail


class TestHMACIntegration:
    """Integration tests with AsyncClient"""

    @pytest.mark.asyncio
    async def test_callback_without_hmac_headers(self, client, monkeypatch):
        """Test callback endpoint rejects request without HMAC headers"""
        monkeypatch.setattr(config, "HMAC_ENABLED", True)
        
        response = await client.post(
            "/oas/callback",
            json={
                "validation_id": "test123",
                "status": "COMPLETED"
            }
        )

        # Should be rejected
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_callback_with_valid_hmac(self, client, monkeypatch, repo):
        """Test callback endpoint accepts request with valid HMAC signature"""
        monkeypatch.setattr(config, "HMAC_ENABLED", True)
        secret = "test-callback-secret"
        monkeypatch.setattr(config, "CALLBACK_SECRET", secret)
        monkeypatch.setenv("CALLBACK_SECRET", secret)
        
        # Create validation first
        val_id = "test-hmac-123"
        from models.validation import FileFormat
        await repo.create(
            val_id, "default", "1.0", False, 
            file_format=FileFormat.JSON, file_sha256="abc", file_content="{}"
        )
        
        callback_data = {
            "validation_id": val_id,
            "status": "COMPLETED",
            "report_content": {"valid": True}
        }
        
        payload_str = json_dumps(callback_data)
        headers = generate_hmac_headers(payload_str)
        
        response = await client.post(
            "/oas/callback",
            content=payload_str,
            headers={**headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Status updated"
