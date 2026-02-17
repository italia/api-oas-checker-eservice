import hmac
import hashlib
import time
import os
import logging

logger = logging.getLogger(__name__)

def generate_hmac_headers(payload_str: str) -> dict:
    """
    Generate HMAC-SHA256 signature headers for callback request.
    """
    secret = os.getenv('CALLBACK_SECRET')
    if not secret:
        # In a public repo for "Italia", we should probably fail if not set in production,
        # but for now we keep the fallback with a clear warning.
        logger.warning("CALLBACK_SECRET is not set. Using fallback for development.")
        secret = 'dev-secret-change-in-production'

    timestamp = str(int(time.time()))
    message = f"{timestamp}{payload_str}"
    
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return {
        'X-Signature': signature,
        'X-Timestamp': timestamp
    }
