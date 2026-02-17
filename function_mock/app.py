"""
Mock Azure Function - FastAPI implementation

This simulates an Azure Function that validates OpenAPI files.
In production, this would be replaced by a real Azure Function.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path to import shared modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, BackgroundTasks
import uvicorn
from pydantic import BaseModel

# Import from shared package (copied from azure_function/shared during setup or symlinked)
try:
    from azure_function.shared.utils import json_dumps
    from azure_function.shared.security import generate_hmac_headers
    from azure_function.shared.http_client import get_http_client
except ImportError:
    # If not found (e.g. running outside of docker without proper paths), 
    # we might need to adjust based on how the project is structured.
    # For the mock, we can try to find it in the current project
    from shared.utils import json_dumps
    from shared.security import generate_hmac_headers
    from shared.http_client import get_http_client

# Import mock validator
from function_mock.validator import validate_openapi

# Configuration
FUNCTION_PORT = int(os.getenv("FUNCTION_PORT", "8001"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("function-mock")

# Create FastAPI app
app = FastAPI(
    title="OAS Validation Function (Mock)",
    description="Mock Azure Function for OpenAPI validation",
    version="1.1.0"
)


class ValidationRequest(BaseModel):
    """Request from e-service to start validation"""
    validation_id: str
    file_content: str
    file_extension: Optional[str] = ".yaml"
    ruleset_name: str = "default"
    ruleset_content: str = ""
    errors_only: bool = False
    callback_url: str


class ValidationStatus(BaseModel):
    """Status response"""
    status: str
    message: str


async def process_validation(request: ValidationRequest):
    """
    Process validation in background with HMAC signature
    """
    try:
        logger.info(f"Processing validation {request.validation_id}")

        # Simulate some processing time
        await asyncio.sleep(1)

        # Run mock validation
        report = validate_openapi(request.file_content, request.ruleset_name, request.errors_only)

        # Prepare callback payload
        callback_data = {
            "validation_id": request.validation_id,
            "status": "COMPLETED",
            "report_content": report
        }

        # Use shared utilities for consistency
        payload_str = json_dumps(callback_data)
        headers = generate_hmac_headers(payload_str)
        headers["Content-Type"] = "application/json"

        logger.info(f"Calling callback: {request.callback_url}")
        client = get_http_client()
        response = await client.post(
            request.callback_url,
            content=payload_str,
            headers=headers
        )
        logger.info(f"Callback response: {response.status_code}")

    except Exception as e:
        logger.error(f"Error processing validation: {e}", exc_info=True)
        # Call callback with FAILED status
        try:
            callback_data = {
                "validation_id": request.validation_id,
                "status": "FAILED",
                "error_message": str(e)
            }
            payload_str = json_dumps(callback_data)
            headers = generate_hmac_headers(payload_str)
            headers["Content-Type"] = "application/json"
            
            client = get_http_client()
            await client.post(request.callback_url, content=payload_str, headers=headers)
        except Exception as cb_err:
            logger.error(f"Failed to send error callback: {cb_err}")


@app.post("/api/validate", response_model=ValidationStatus)
async def validate(
    request: ValidationRequest,
    background_tasks: BackgroundTasks
):
    """
    Start validation (mimics Azure Function HTTP trigger)
    """
    logger.info(f"Received validation request: {request.validation_id}")

    # Add validation to background tasks
    background_tasks.add_task(process_validation, request)

    return ValidationStatus(
        status="accepted",
        message=f"Validation {request.validation_id} started"
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "oas-validation-function-mock"}


if __name__ == "__main__":
    logger.info(f"Starting Mock Validation Function on port {FUNCTION_PORT}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=FUNCTION_PORT
    )
