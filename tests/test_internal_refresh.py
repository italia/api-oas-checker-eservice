"""
Test suite for internal refresh endpoint
"""
import pytest
from unittest.mock import patch
from jose import jwt
import config

@pytest.mark.asyncio
class TestInternalRefresh:
    """Tests for /internal/rulesets/refresh endpoint"""

    async def test_refresh_no_auth(self, client, monkeypatch):
        """Test refresh without Authorization header (should be 401 via middleware)"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)
        response = await client.post("/internal/rulesets/refresh")
        assert response.status_code == 401

    async def test_refresh_mismatched_ids(self, client, monkeypatch):
        """Test refresh with mismatched producerId and consumerId (should be 403 Forbidden)"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)
        
        # Create token with mismatched IDs
        token_payload = {
            "producerId": "producer-1",
            "consumerId": "consumer-2"
        }
        token = jwt.encode(token_payload, "secret", algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post("/internal/rulesets/refresh", headers=headers)
        
        assert response.status_code == 403
        data = response.json()
        assert "Forbidden" in data["title"]
        assert "producerId must equal consumerId" in data["detail"]

    async def test_refresh_matching_ids_success(self, client, monkeypatch):
        """Test refresh with matching producerId and consumerId (should be 200 OK)"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)
        
        # Create token with matching IDs
        token_payload = {
            "producerId": "admin-123",
            "consumerId": "admin-123"
        }
        token = jwt.encode(token_payload, "secret", algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock download_rulesets to avoid actual GitHub call
        with patch("services.ruleset_manager.RulesetManager.download_rulesets") as mock_download:
            mock_download.return_value = {"default": "path/to/ruleset"}
            with patch("services.ruleset_manager.RulesetManager.get_metadata") as mock_metadata:
                mock_metadata.return_value = {"repo": "test/repo", "tag": "v1.0"}
                
                response = await client.post("/internal/rulesets/refresh", headers=headers)
                
                assert response.status_code == 200
                assert response.json()["success"] is True

    async def test_refresh_jwt_disabled(self, client, monkeypatch):
        """Test refresh when JWT is disabled (should be 200 OK)"""
        monkeypatch.setattr(config, "JWT_ENABLED", False)
        
        # Mock download_rulesets
        with patch("services.ruleset_manager.RulesetManager.download_rulesets") as mock_download:
            mock_download.return_value = {"default": "path/to/ruleset"}
            with patch("services.ruleset_manager.RulesetManager.get_metadata") as mock_metadata:
                mock_metadata.return_value = {"repo": "test/repo", "tag": "v1.0"}
                
                response = await client.post("/internal/rulesets/refresh")
                
                assert response.status_code == 200
                assert response.json()["success"] is True
