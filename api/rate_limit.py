"""
Rate Limiting middleware for OAS Checker e-service

Implements per-consumer rate limiting using PostgreSQL database.
Tracks requests per consumerId (from JWT) per endpoint.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import logging
import config
from api.exceptions import create_problem_details

logger = logging.getLogger(__name__)


class RateLimitInfo:
    """Rate limit information for response headers"""

    def __init__(self, limit: int, remaining: int, reset_seconds: int):
        self.limit = limit
        self.remaining = remaining
        self.reset_seconds = reset_seconds


class RateLimiter:
    """
    Rate limiter using PostgreSQL database for tracking
    """

    def __init__(self, database):
        """
        Initialize rate limiter

        Args:
            database: Database instance for tracking
        """
        self.database = database

    def _get_rate_limit_config(self, endpoint: str) -> Tuple[int, int]:
        """
        Get rate limit configuration for endpoint

        Args:
            endpoint: Endpoint path (e.g., "/oas/validate")

        Returns:
            Tuple of (max_requests, window_seconds)
        """
        # Normalize endpoint for matching
        endpoint_normalized = endpoint.rstrip("/")

        # Map endpoints to configuration
        if endpoint_normalized.startswith("/oas/validate"):
            return (config.RATE_LIMIT_VALIDATE_REQUESTS, config.RATE_LIMIT_VALIDATE_WINDOW)
        elif endpoint_normalized.startswith("/oas/report"):
            return (config.RATE_LIMIT_REPORT_REQUESTS, config.RATE_LIMIT_REPORT_WINDOW)
        else:
            return (config.RATE_LIMIT_DEFAULT_REQUESTS, config.RATE_LIMIT_DEFAULT_WINDOW)

    async def check_rate_limit(
        self,
        consumer_id: str,
        endpoint: str
    ) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is within rate limit

        Uses fixed window algorithm:
        - Each time window starts at a specific timestamp
        - Requests are counted within that window
        - Window resets when window_end is reached

        Args:
            consumer_id: Consumer ID from JWT
            endpoint: Endpoint path

        Returns:
            Tuple of (allowed: bool, rate_limit_info: RateLimitInfo)
        """
        max_requests, window_seconds = self._get_rate_limit_config(endpoint)

        now = datetime.now(timezone.utc)

        # Calculate current window boundaries
        # Windows start at :00 seconds of each minute (or custom intervals)
        window_start = now.replace(second=0, microsecond=0)
        window_end = window_start + timedelta(seconds=window_seconds)

        async with self.database.get_connection() as conn:
            # Try to get existing window record
            record = await conn.fetchrow(
                """
                SELECT request_count, window_end
                FROM rate_limit_tracking
                WHERE consumer_id = $1 AND endpoint = $2 AND window_start = $3
                """,
                consumer_id,
                endpoint,
                window_start
            )

            if record:
                current_count = record["request_count"]
                record_window_end = record["window_end"]

                # Check if window has expired
                if now >= record_window_end:
                    # Window expired, start new window
                    await conn.execute(
                        """
                        UPDATE rate_limit_tracking
                        SET request_count = 1, window_end = $1
                        WHERE consumer_id = $2 AND endpoint = $3 AND window_start = $4
                        """,
                        window_end,
                        consumer_id,
                        endpoint,
                        window_start
                    )
                    current_count = 1
                else:
                    # Window still active
                    if current_count >= max_requests:
                        # Rate limit exceeded
                        reset_seconds = int((record_window_end - now).total_seconds())
                        rate_info = RateLimitInfo(
                            limit=max_requests,
                            remaining=0,
                            reset_seconds=reset_seconds
                        )
                        return (False, rate_info)
                    else:
                        # Increment counter
                        await conn.execute(
                            """
                            UPDATE rate_limit_tracking
                            SET request_count = request_count + 1
                            WHERE consumer_id = $1 AND endpoint = $2 AND window_start = $3
                            """,
                            consumer_id,
                            endpoint,
                            window_start
                        )
                        current_count += 1
            else:
                # No record exists, create new window
                await conn.execute(
                    """
                    INSERT INTO rate_limit_tracking (consumer_id, endpoint, request_count, window_start, window_end)
                    VALUES ($1, $2, 1, $3, $4)
                    ON CONFLICT (consumer_id, endpoint, window_start) DO UPDATE
                    SET request_count = rate_limit_tracking.request_count + 1
                    """,
                    consumer_id,
                    endpoint,
                    window_start,
                    window_end
                )
                current_count = 1

            # Calculate rate limit info
            remaining = max(0, max_requests - current_count)
            reset_seconds = int((window_end - now).total_seconds())

            rate_info = RateLimitInfo(
                limit=max_requests,
                remaining=remaining,
                reset_seconds=reset_seconds
            )

            return (True, rate_info)

    async def cleanup_old_records(self):
        """
        Cleanup rate limit records older than configured hours
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=config.RATE_LIMIT_CLEANUP_HOURS)

        async with self.database.get_connection() as conn:
            result = await conn.execute(
                """
                DELETE FROM rate_limit_tracking
                WHERE created_at < $1
                """,
                cutoff_time
            )
            logger.info(f"Cleaned up old rate limit records: {result}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    """

    def __init__(self, app, database):
        super().__init__(app)
        self.rate_limiter = RateLimiter(database)
        self.excluded_paths = {"/docs", "/redoc", "/openapi.json", "/openapi.yaml", "/status"}

        # Warn if rate limiting enabled but JWT disabled
        if config.RATE_LIMIT_ENABLED and not config.JWT_ENABLED:
            logger.warning(
                "Rate limiting is enabled but JWT is disabled. "
                "All clients will share consumer_id='dev' and the same rate limit. "
                "Consider setting RATE_LIMIT_ENABLED=false for local development."
            )

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting if disabled
        if not config.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip excluded paths (docs, status, etc.)
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Extract consumer_id from request state (set by JWT middleware)
        consumer_id = getattr(request.state, "consumer_id", None)

        if not consumer_id:
            # No consumer_id available (JWT middleware not executed), skip rate limiting
            logger.debug(f"No consumer_id for rate limiting on {request.url.path}")
            return await call_next(request)

        # Check rate limit
        try:
            allowed, rate_info = await self.rate_limiter.check_rate_limit(
                consumer_id=consumer_id,
                endpoint=request.url.path
            )

            if not allowed:
                # Rate limit exceeded - return 429
                logger.warning(
                    f"Rate limit exceeded for consumer={consumer_id} endpoint={request.url.path}"
                )

                problem = create_problem_details(
                    status=429,
                    title="Too Many Requests",
                    detail=f"Rate limit exceeded. Maximum {rate_info.limit} requests per {config.RATE_LIMIT_VALIDATE_WINDOW}s.",
                    type_suffix="rate-limit-exceeded",
                    instance=str(request.url.path)
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=problem.model_dump(exclude_none=True),
                    headers={
                        "X-RateLimit-Limit": str(rate_info.limit),
                        "X-RateLimit-Remaining": str(rate_info.remaining),
                        "X-RateLimit-Reset": str(rate_info.reset_seconds),
                        "Retry-After": str(rate_info.reset_seconds),
                        "Content-Type": "application/problem+json"
                    }
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to successful response
            response.headers["X-RateLimit-Limit"] = str(rate_info.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_info.remaining)
            response.headers["X-RateLimit-Reset"] = str(rate_info.reset_seconds)

            return response

        except Exception as e:
            # Log error but don't block request
            logger.error(f"Rate limiting error: {e}", exc_info=True)
            return await call_next(request)
