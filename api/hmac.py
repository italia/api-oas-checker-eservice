"""
HMAC-SHA256 signature verification for callback endpoint

This module provides request signature verification using HMAC-SHA256 to ensure
that callback requests originate from the Azure Function and haven't been tampered with.

Security features:
- HMAC-SHA256 signature verification
- Timestamp validation with configurable window (default: ±5 minutes)
- Constant-time signature comparison (prevents timing attacks)
- Optional bypass for local/dev (HMAC_ENABLED=false)
"""
import hmac
import hashlib
import time
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
import config

logger = logging.getLogger(__name__)


async def verify_hmac_signature(request: Request) -> None:
    """
    FastAPI dependency to verify HMAC-SHA256 signature from callback requests.

    This function:
    1. Extracts signature and timestamp from request headers
    2. Validates timestamp is within acceptable window (prevents replay attacks)
    3. Recomputes HMAC signature from request body + timestamp
    4. Compares signatures using constant-time comparison (prevents timing attacks)

    If HMAC_ENABLED=false in config, this check is bypassed (local/dev mode).

    Headers required:
        X-Signature: HMAC-SHA256 hex digest
        X-Timestamp: Unix timestamp (seconds since epoch)

    Args:
        request: FastAPI Request object (injected automatically)

    Raises:
        HTTPException 401: If signature is missing, invalid, or timestamp expired
    """
    # If HMAC is disabled (local/dev), bypass check
    if not config.HMAC_ENABLED:
        logger.debug("HMAC verification disabled (HMAC_ENABLED=false)")
        return

    # Extract headers
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")

    # Validate headers presence
    if not signature:
        logger.warning("Missing X-Signature header in callback request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature header"
        )

    if not timestamp:
        logger.warning("Missing X-Timestamp header in callback request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Timestamp header"
        )

    # Validate timestamp format
    try:
        request_time = int(timestamp)
    except ValueError:
        logger.warning(f"Invalid X-Timestamp format: {timestamp}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Timestamp format. Expected Unix timestamp"
        )

    # Validate timestamp freshness (prevent replay attacks)
    current_time = int(time.time())
    time_diff = abs(current_time - request_time)

    if time_diff > config.HMAC_TIMESTAMP_WINDOW:
        logger.warning(
            f"Timestamp expired: request={request_time}, current={current_time}, "
            f"diff={time_diff}s, window={config.HMAC_TIMESTAMP_WINDOW}s"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Request timestamp expired. Window: ±{config.HMAC_TIMESTAMP_WINDOW}s"
        )

    # Read request body
    body = await request.body()
    body_str = body.decode("utf-8")

    # Compute expected signature
    # Format: HMAC-SHA256(secret, timestamp + body)
    message = f"{timestamp}{body_str}"
    expected_signature = hmac.new(
        config.CALLBACK_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison (prevents timing attacks)
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning(
            f"HMAC signature mismatch. Expected signature for validation_id from body"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    logger.info(f"HMAC signature verified successfully for callback at {timestamp}")


def generate_hmac_signature(payload: str, timestamp: Optional[int] = None) -> tuple[str, int]:
    """
    Generate HMAC-SHA256 signature for a payload.

    This is a utility function used by the Azure Function to sign callback requests.

    Args:
        payload: JSON payload as string
        timestamp: Unix timestamp (if None, uses current time)

    Returns:
        Tuple of (signature_hex, timestamp)

    Example:
        >>> payload = json.dumps({"validation_id": "abc123", "status": "COMPLETED"})
        >>> signature, ts = generate_hmac_signature(payload)
        >>> headers = {"X-Signature": signature, "X-Timestamp": str(ts)}
    """
    if timestamp is None:
        timestamp = int(time.time())

    message = f"{timestamp}{payload}"
    signature = hmac.new(
        config.CALLBACK_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return signature, timestamp
