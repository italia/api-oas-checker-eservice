"""
Test suite for Rate Limiting functionality
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.rate_limit import RateLimiter, RateLimitInfo, RateLimitMiddleware
import config


class MockDatabase:
    """Mock database for testing"""

    def __init__(self):
        self.records = {}
        self.connection = AsyncMock()

    def get_connection(self):
        """Return mock connection context manager"""
        class AsyncContextManager:
            def __init__(self, conn):
                self.conn = conn

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        return AsyncContextManager(self.connection)


class TestRateLimitInfo:
    """Tests for RateLimitInfo class"""

    def test_rate_limit_info_creation(self):
        """Test RateLimitInfo object creation"""
        info = RateLimitInfo(limit=10, remaining=7, reset_seconds=45)
        assert info.limit == 10
        assert info.remaining == 7
        assert info.reset_seconds == 45


class TestRateLimiter:
    """Tests for RateLimiter class"""

    def test_get_rate_limit_config_validate(self):
        """Test rate limit config for /oas/validate endpoint"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        max_requests, window = limiter._get_rate_limit_config("/oas/validate")
        assert max_requests == config.RATE_LIMIT_VALIDATE_REQUESTS
        assert window == config.RATE_LIMIT_VALIDATE_WINDOW

    def test_get_rate_limit_config_report(self):
        """Test rate limit config for /oas/report endpoint"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        max_requests, window = limiter._get_rate_limit_config("/oas/report/abc123")
        assert max_requests == config.RATE_LIMIT_REPORT_REQUESTS
        assert window == config.RATE_LIMIT_REPORT_WINDOW

    def test_get_rate_limit_config_default(self):
        """Test rate limit config for other endpoints"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        max_requests, window = limiter._get_rate_limit_config("/status")
        assert max_requests == config.RATE_LIMIT_DEFAULT_REQUESTS
        assert window == config.RATE_LIMIT_DEFAULT_WINDOW

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self):
        """Test rate limiting for first request (no existing record)"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        # Mock database response - no existing record
        db.connection.fetchrow.return_value = None

        allowed, rate_info = await limiter.check_rate_limit(
            consumer_id="test-consumer",
            endpoint="/oas/validate"
        )

        assert allowed is True
        assert rate_info.limit == config.RATE_LIMIT_VALIDATE_REQUESTS
        assert rate_info.remaining == config.RATE_LIMIT_VALIDATE_REQUESTS - 1
        assert rate_info.reset_seconds > 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self):
        """Test rate limiting when within limit"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        # Mock database response - existing record with count = 5
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(seconds=30)

        db.connection.fetchrow.return_value = {
            "request_count": 5,
            "window_end": window_end
        }

        allowed, rate_info = await limiter.check_rate_limit(
            consumer_id="test-consumer",
            endpoint="/oas/validate"
        )

        assert allowed is True
        assert rate_info.limit == config.RATE_LIMIT_VALIDATE_REQUESTS
        # Should be limit - (current_count + 1)
        assert rate_info.remaining == config.RATE_LIMIT_VALIDATE_REQUESTS - 6

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test rate limiting when limit is exceeded"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        # Mock database response - existing record at limit
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(seconds=30)

        db.connection.fetchrow.return_value = {
            "request_count": config.RATE_LIMIT_VALIDATE_REQUESTS,
            "window_end": window_end
        }

        allowed, rate_info = await limiter.check_rate_limit(
            consumer_id="test-consumer",
            endpoint="/oas/validate"
        )

        assert allowed is False
        assert rate_info.limit == config.RATE_LIMIT_VALIDATE_REQUESTS
        assert rate_info.remaining == 0
        assert rate_info.reset_seconds > 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_window_expired(self):
        """Test rate limiting when window has expired"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        # Mock database response - window expired
        now = datetime.now(timezone.utc)
        window_end = now - timedelta(seconds=10)  # Expired

        db.connection.fetchrow.return_value = {
            "request_count": config.RATE_LIMIT_VALIDATE_REQUESTS,
            "window_end": window_end
        }

        allowed, rate_info = await limiter.check_rate_limit(
            consumer_id="test-consumer",
            endpoint="/oas/validate"
        )

        # Should be allowed because window expired and resets
        assert allowed is True
        assert rate_info.remaining == config.RATE_LIMIT_VALIDATE_REQUESTS - 1

    @pytest.mark.asyncio
    async def test_cleanup_old_records(self):
        """Test cleanup of old rate limit records"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        db.connection.execute.return_value = "DELETE 42"

        await limiter.cleanup_old_records()

        # Verify delete was called
        db.connection.execute.assert_called_once()
        call_args = db.connection.execute.call_args
        assert "DELETE FROM rate_limit_tracking" in call_args[0][0]


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware"""

    @pytest.mark.asyncio
    async def test_middleware_disabled(self, monkeypatch):
        """Test middleware bypassed when RATE_LIMIT_ENABLED=false"""
        monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)

        db = MockDatabase()
        middleware = RateLimitMiddleware(app=None, database=db)

        request = Mock(spec=Request)
        request.url.path = "/oas/validate"

        async def call_next(req):
            return JSONResponse(content={"status": "ok"})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        # Database should not be called
        db.connection.fetchrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_excluded_path(self, monkeypatch):
        """Test middleware bypassed for excluded paths"""
        monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

        db = MockDatabase()
        middleware = RateLimitMiddleware(app=None, database=db)

        request = Mock(spec=Request)
        request.url.path = "/docs"  # Excluded path

        async def call_next(req):
            return JSONResponse(content={"status": "ok"})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        # Database should not be called
        db.connection.fetchrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_no_consumer_id(self, monkeypatch):
        """Test middleware bypassed when no consumer_id in request state"""
        monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

        db = MockDatabase()
        middleware = RateLimitMiddleware(app=None, database=db)

        # Create request state without consumer_id attribute
        class RequestState:
            pass

        request = Mock(spec=Request)
        request.url.path = "/oas/validate"
        request.state = RequestState()
        # No consumer_id attribute

        async def call_next(req):
            return JSONResponse(content={"status": "ok"})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        # Database should not be called
        db.connection.fetchrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_within_limit(self, monkeypatch):
        """Test middleware allows request within rate limit"""
        monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

        db = MockDatabase()
        middleware = RateLimitMiddleware(app=None, database=db)

        request = Mock(spec=Request)
        request.url.path = "/oas/validate"
        request.state = Mock()
        request.state.consumer_id = "test-consumer"

        # Mock rate limiter to allow request
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(seconds=30)
        db.connection.fetchrow.return_value = {
            "request_count": 5,
            "window_end": window_end
        }

        async def call_next(req):
            return JSONResponse(content={"status": "ok"})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_middleware_rate_limit_exceeded(self, monkeypatch):
        """Test middleware returns 429 when rate limit exceeded"""
        monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

        db = MockDatabase()
        middleware = RateLimitMiddleware(app=None, database=db)

        request = Mock(spec=Request)
        request.url.path = "/oas/validate"
        request.state = Mock()
        request.state.consumer_id = "test-consumer"

        # Mock rate limiter to reject request
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(seconds=30)
        db.connection.fetchrow.return_value = {
            "request_count": config.RATE_LIMIT_VALIDATE_REQUESTS,
            "window_end": window_end
        }

        async def call_next(req):
            return JSONResponse(content={"status": "ok"})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 429
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers
        assert response.headers["Content-Type"] == "application/problem+json"


class TestRateLimitingIntegration:
    """Integration tests for rate limiting with different endpoints"""

    @pytest.mark.asyncio
    async def test_different_consumers_independent_limits(self):
        """Test that different consumers have independent rate limits"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        # Consumer 1 makes request
        db.connection.fetchrow.return_value = None
        allowed1, info1 = await limiter.check_rate_limit(
            consumer_id="consumer-1",
            endpoint="/oas/validate"
        )
        assert allowed1 is True

        # Consumer 2 makes request - should have independent limit
        db.connection.fetchrow.return_value = None
        allowed2, info2 = await limiter.check_rate_limit(
            consumer_id="consumer-2",
            endpoint="/oas/validate"
        )
        assert allowed2 is True
        assert info2.remaining == config.RATE_LIMIT_VALIDATE_REQUESTS - 1

    @pytest.mark.asyncio
    async def test_different_endpoints_independent_limits(self):
        """Test that different endpoints have independent rate limits"""
        db = MockDatabase()
        limiter = RateLimiter(db)

        # Request to /oas/validate
        db.connection.fetchrow.return_value = None
        allowed1, info1 = await limiter.check_rate_limit(
            consumer_id="consumer-1",
            endpoint="/oas/validate"
        )
        assert allowed1 is True
        assert info1.limit == config.RATE_LIMIT_VALIDATE_REQUESTS

        # Request to /oas/report - should have different limit
        db.connection.fetchrow.return_value = None
        allowed2, info2 = await limiter.check_rate_limit(
            consumer_id="consumer-1",
            endpoint="/oas/report/abc123"
        )
        assert allowed2 is True
        assert info2.limit == config.RATE_LIMIT_REPORT_REQUESTS
