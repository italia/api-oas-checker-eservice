"""
Test suite for JWT authentication
"""
import pytest
from unittest.mock import Mock
from fastapi import HTTPException, Request
from jose import jwt
from api.auth import verify_jwt_token, JWTPayload
import config


@pytest.fixture
def mock_request():
    """Fixture for mocked FastAPI Request"""
    request = Mock(spec=Request)
    request.state = Mock()
    return request


class TestJWTPayload:
    """Tests for JWTPayload class"""

    def test_valid_payload(self):
        """Test payload with matching producerId and consumerId"""
        payload = JWTPayload(producer_id="test-123", consumer_id="test-123")
        assert payload.is_internal_authorized() is True

    def test_invalid_payload(self):
        """Test payload with mismatched producerId and consumerId"""
        payload = JWTPayload(producer_id="producer-1", consumer_id="consumer-2")
        assert payload.is_internal_authorized() is False


class TestVerifyJWTToken:
    """Tests for verify_jwt_token dependency"""

    @pytest.mark.asyncio
    async def test_jwt_disabled(self, monkeypatch, mock_request):
        """Test JWT verification bypassed when JWT_ENABLED=false"""
        monkeypatch.setattr(config, "JWT_ENABLED", False)

        # Should succeed without token
        payload = await verify_jwt_token(request=mock_request, authorization=None)
        assert payload.producer_id == "dev"
        assert payload.consumer_id == "dev"
        assert payload.is_internal_authorized() is True
        assert mock_request.state.consumer_id == "dev"

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, monkeypatch, mock_request):
        """Test missing Authorization header when JWT enabled"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(request=mock_request, authorization=None)

        assert exc_info.value.status_code == 401
        assert "Missing Authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self, monkeypatch, mock_request):
        """Test invalid Authorization header format"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(request=mock_request, authorization="InvalidFormat")

        assert exc_info.value.status_code == 401
        assert "Invalid Authorization header format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_token_matching_ids(self, monkeypatch, mock_request):
        """Test valid token with producerId == consumerId"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        # Create JWT token with matching IDs
        token_payload = {
            "producerId": "service-123",
            "consumerId": "service-123"
        }
        token = jwt.encode(token_payload, "secret", algorithm="HS256")

        payload = await verify_jwt_token(request=mock_request, authorization=f"Bearer {token}")
        assert payload.producer_id == "service-123"
        assert payload.consumer_id == "service-123"
        assert payload.is_internal_authorized() is True
        assert mock_request.state.consumer_id == "service-123"

    @pytest.mark.asyncio
    async def test_valid_token_mismatched_ids(self, monkeypatch, mock_request):
        """Test valid token with producerId != consumerId (should now succeed at token level)"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        # Create JWT token with mismatched IDs
        token_payload = {
            "producerId": "producer-456",
            "consumerId": "consumer-789"
        }
        token = jwt.encode(token_payload, "secret", algorithm="HS256")

        payload = await verify_jwt_token(request=mock_request, authorization=f"Bearer {token}")
        assert payload.producer_id == "producer-456"
        assert payload.consumer_id == "consumer-789"
        assert payload.is_internal_authorized() is False
        assert mock_request.state.consumer_id == "consumer-789"

    @pytest.mark.asyncio
    async def test_missing_producer_id(self, monkeypatch, mock_request):
        """Test token missing producerId claim"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        # Create JWT token without producerId
        token_payload = {
            "consumerId": "consumer-123"
        }
        token = jwt.encode(token_payload, "secret", algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(request=mock_request, authorization=f"Bearer {token}")

        assert exc_info.value.status_code == 401
        assert "missing producerId or consumerId" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_consumer_id(self, monkeypatch, mock_request):
        """Test token missing consumerId claim"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        # Create JWT token without consumerId
        token_payload = {
            "producerId": "producer-123"
        }
        token = jwt.encode(token_payload, "secret", algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(request=mock_request, authorization=f"Bearer {token}")

        assert exc_info.value.status_code == 401
        assert "missing producerId or consumerId" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_malformed_jwt(self, monkeypatch, mock_request):
        """Test malformed JWT token"""
        monkeypatch.setattr(config, "JWT_ENABLED", True)

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(request=mock_request, authorization="Bearer not-a-valid-jwt")

        assert exc_info.value.status_code == 401
        assert "Invalid JWT token" in exc_info.value.detail
