"""
Client for invoking validation function (mock or Azure)
"""
import httpx
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional
from models.schemas import FunctionValidationRequest

logger = logging.getLogger(__name__)


class FunctionClient(ABC):
    """
    Abstract client for invoking validation function
    """

    @abstractmethod
    async def invoke_validation(self, request: FunctionValidationRequest) -> bool:
        """
        Invoke validation function

        Args:
            request: Validation request

        Returns:
            True if invocation succeeded, False otherwise
        """
        pass


class MockFunctionClient(FunctionClient):
    """
    Mock function client for development.
    Invokes a local HTTP endpoint (function_mock).
    """

    def __init__(self, function_url: str):
        """
        Initialize mock function client

        Args:
            function_url: Base URL of mock function (e.g., 'http://localhost:8001')
        """
        self.function_url = function_url.rstrip('/')

    async def invoke_validation(self, request: FunctionValidationRequest) -> bool:
        """
        Invoke mock validation function via HTTP POST
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.function_url}/api/validate",
                    json=request.model_dump()
                )
                if response.status_code not in [200, 202]:
                    logger.error(f"Mock function returned error: {response.status_code} - {response.text}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Error invoking mock function: {e}", exc_info=True)
            return False


class AzureFunctionClient(FunctionClient):
    """
    Azure Function client for production and local environments.
    Invokes Azure Function via HTTP with optional authentication.
    """

    def __init__(self, function_url: str, function_key: Optional[str] = None):
        """
        Initialize Azure Function client

        Args:
            function_url: Azure Function URL (complete URL including /api/validate)
            function_key: Function key for authentication (optional for local)
        """
        self.function_url = function_url.rstrip('/')
        self.function_key = function_key

    async def _invoke_async(self, request: FunctionValidationRequest):
        """Background task to invoke Azure Function without blocking"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.function_key:
                headers["x-functions-key"] = self.function_key

            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Invoking Azure Function for validation {request.validation_id}")
                response = await client.post(
                    self.function_url,
                    json=request.model_dump(),
                    headers=headers
                )
                
                if response.status_code not in [200, 202]:
                    logger.error(
                        f"Azure Function returned error: {response.status_code} "
                        f"for validation {request.validation_id}"
                    )
                else:
                    logger.info(f"Azure Function accepted validation {request.validation_id}")
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout invoking Azure Function for validation {request.validation_id}")
        except Exception as e:
            logger.error(f"Unexpected error in background Azure Function invocation: {e}", exc_info=True)

    async def invoke_validation(self, request: FunctionValidationRequest) -> bool:
        """
        Invoke Azure Function via HTTP POST.
        Starts a background task and returns immediately (fire-and-forget).
        """
        try:
            # We use create_task to run the HTTP call in the background
            # This allows the API to return 202 immediately to the user
            asyncio.create_task(self._invoke_async(request))
            return True
        except Exception as e:
            logger.error(f"Error creating Azure Function background task: {e}")
            return False