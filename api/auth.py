"""
JWT Authentication for OAS Checker e-service

This module provides JWT token verification for protected endpoints.
The JWT token is validated by an external API Gateway (GovWay), so this module
only needs to decode the token and verify the producerId == consumerId claim.
"""
from typing import Optional, List
from fastapi import Header, HTTPException, status, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
import config
import logging
from api.exceptions import create_problem_details

logger = logging.getLogger(__name__)


class JWTPayload:
    """JWT payload with producerId and consumerId"""

    def __init__(self, producer_id: str, consumer_id: str):
        self.producer_id = producer_id
        self.consumer_id = consumer_id

    def is_internal_authorized(self) -> bool:
        """Check if producerId equals consumerId (authorized for internal operations)"""
        return self.producer_id == self.consumer_id


def decode_jwt_token(token: str) -> JWTPayload:
    """
    Decode JWT token without signature verification and extract payload.
    """
    try:
        # Decode token WITHOUT signature verification
        # API Gateway (GovWay) already validated signature and expiry
        payload = jwt.decode(
            token,
            key="",  # Empty key since we're not verifying signature
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False
            }
        )

        producer_id = payload.get("producerId")
        consumer_id = payload.get("consumerId")

        if not producer_id or not consumer_id:
            logger.warning(f"Missing producerId or consumerId in JWT payload: {payload.keys()}")
            raise ValueError("JWT payload missing producerId or consumerId")

        jwt_payload = JWTPayload(producer_id=producer_id, consumer_id=consumer_id)

        return jwt_payload

    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise ValueError(f"Invalid JWT token: {str(e)}")


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global JWT authentication.
    """

    def __init__(self, app):
        super().__init__(app)
        self.excluded_paths = {
            "/status",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/openapi.yaml",
            "/oas/callback"
        }

    async def dispatch(self, request: Request, call_next):
        # Log incoming request details
        logger.info(f"Incoming Request: {request.method} {request.url}")
        logger.info("Request Headers:")
        for name, value in request.headers.items():
            logger.info(f"  {name}: {value}")
        # Bypass if JWT is disabled
        if not config.JWT_ENABLED:
            request.state.consumer_id = "dev"
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Missing Authorization header for {request.url.path}")
            problem = create_problem_details(
                status=401,
                title="Unauthorized",
                detail="Missing Authorization header",
                type_suffix="unauthorized",
                instance=str(request.url.path)
            )
            return JSONResponse(
                status_code=401,
                content=problem.model_dump(exclude_none=True),
                headers={"WWW-Authenticate": "Bearer", "Content-Type": "application/problem+json"}
            )

        # Extract Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"Invalid Authorization header format: {auth_header}")
            problem = create_problem_details(
                status=401,
                title="Unauthorized",
                detail="Invalid Authorization header format. Expected: Bearer <token>",
                type_suffix="unauthorized",
                instance=str(request.url.path)
            )
            return JSONResponse(
                status_code=401,
                content=problem.model_dump(exclude_none=True),
                headers={"WWW-Authenticate": "Bearer", "Content-Type": "application/problem+json"}
            )

        token = parts[1]

        try:
            jwt_payload = decode_jwt_token(token)
            request.state.consumer_id = jwt_payload.consumer_id
            request.state.jwt_payload = jwt_payload
            return await call_next(request)
        except ValueError as e:
            problem = create_problem_details(
                status=401,
                title="Unauthorized",
                detail=str(e),
                type_suffix="unauthorized",
                instance=str(request.url.path)
            )
            return JSONResponse(
                status_code=401,
                content=problem.model_dump(exclude_none=True),
                headers={"WWW-Authenticate": "Bearer", "Content-Type": "application/problem+json"}
            )


async def verify_jwt_token(
    request: Request,
    authorization: Optional[str] = Header(None, description="Bearer JWT token")
) -> JWTPayload:
    """
    FastAPI dependency to verify JWT token.
    Can be used to get the payload in route handlers.
    """
    # If middleware already set the payload, use it
    jwt_payload = getattr(request.state, "jwt_payload", None)
    if isinstance(jwt_payload, JWTPayload):
        return jwt_payload

    # Fallback for when middleware is skipped or not yet executed
    if not config.JWT_ENABLED:
        payload = JWTPayload(producer_id="dev", consumer_id="dev")
        request.state.consumer_id = payload.consumer_id
        return payload

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        jwt_payload = decode_jwt_token(parts[1])
        request.state.consumer_id = jwt_payload.consumer_id
        return jwt_payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

