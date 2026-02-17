import httpx
import logging

logger = logging.getLogger(__name__)

# Global client instance for connection pooling
_client = None

def get_http_client() -> httpx.AsyncClient:
    """
    Get or create a global httpx.AsyncClient instance for connection pooling.
    """
    global _client
    if _client is None or _client.is_closed:
        logger.info("Initializing global httpx.AsyncClient")
        _client = httpx.AsyncClient(
            timeout=60.0, 
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    return _client

async def close_http_client():
    """
    Close the global httpx.AsyncClient instance.
    """
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None
