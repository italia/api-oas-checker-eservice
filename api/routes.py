"""
FastAPI routes for OAS validation API
"""
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse

from api.dependencies import get_validation_service
from api.auth import verify_jwt_token
from api.hmac import verify_hmac_signature
from models.schemas import (
    ValidationResponse,
    ReportResponse,
    CallbackRequest,
    CallbackResponse,
    Problem,
    StatusResponse
)
from services.validation_service import ValidationService

router = APIRouter()


# OpenAPI responses for error cases (RFC 9457 Problem Details)
# We define them manually to ensure ONLY application/problem+json is used
PROBLEM_RESPONSES = {
    400: {
        "model": Problem,
        "description": "Bad Request - Invalid input",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/Problem"},
                "example": {
                    "type": "https://api-oas-checker.example.com/problems/bad-request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": "File must be YAML or JSON format",
                    "instance": "/oas/validate"
                }
            }
        }
    },
    404: {
        "model": Problem,
        "description": "Not Found - Resource does not exist",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/Problem"},
                "example": {
                    "type": "https://api-oas-checker.example.com/problems/not-found",
                    "title": "Not Found",
                    "status": 404,
                    "detail": "Validation abc123 not found",
                    "instance": "/oas/report/abc123"
                }
            }
        }
    },
    422: {
        "model": Problem,
        "description": "Validation Error - Request validation failed",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/Problem"},
                "example": {
                    "type": "https://api-oas-checker.example.com/problems/validation-error",
                    "title": "Validation Error",
                    "status": 422,
                    "detail": "Request validation failed: file -> field required",
                    "instance": "/oas/validate"
                }
            }
        }
    },
    429: {
        "model": Problem,
        "description": "Too Many Requests - Rate limit exceeded",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/Problem"},
                "example": {
                    "type": "https://api-oas-checker.example.com/problems/rate-limit-exceeded",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Rate limit exceeded. Maximum 10 requests per 60s.",
                    "instance": "/oas/validate"
                }
            }
        },
        "headers": {
            "X-RateLimit-Limit": {
                "description": "Maximum number of requests allowed in the window",
                "schema": {"type": "integer", "format": "int32"}
            },
            "X-RateLimit-Remaining": {
                "description": "Number of requests remaining in the current window",
                "schema": {"type": "integer", "format": "int32"}
            },
            "X-RateLimit-Reset": {
                "description": "Seconds until the rate limit window resets",
                "schema": {"type": "integer", "format": "int32"}
            },
            "Retry-After": {
                "description": "Minimum seconds before retrying",
                "schema": {"type": "integer", "format": "int32"}
            }
        }
    },
    500: {
        "model": Problem,
        "description": "Internal Server Error",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/Problem"},
                "example": {
                    "type": "https://api-oas-checker.example.com/problems/internal-error",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "Validation failed: unexpected error",
                    "instance": "/oas/report/abc123"
                }
            }
        }
    }
}


@router.post(
    "/oas/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start OpenAPI validation",
    description="Upload an OpenAPI file to validate with Spectral",
    tags=["Validation"],
    operation_id="validateOpenAPI",
    responses={
        400: PROBLEM_RESPONSES[400],
        422: PROBLEM_RESPONSES[422],
        429: PROBLEM_RESPONSES[429],
        500: PROBLEM_RESPONSES[500]
    }
)
async def validate_oas(
    file: Annotated[UploadFile, File(description="OpenAPI file (YAML or JSON)")],
    ruleset: Annotated[str, Form()] = "default",
    errors_only: Annotated[bool, Form()] = False,
    service: ValidationService = Depends(get_validation_service)
) -> ValidationResponse:
    """
    Start a new OpenAPI validation.

    - **file**: OpenAPI file (YAML or JSON format)
    - **ruleset**: Spectral ruleset to use (default: "default")
    - **errors_only**: Return only errors, skip warnings/info (default: False)

    Returns a validation ID and PENDING status.
    The validation report will always be in JSON format.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )

    # Validate file extension
    if not file.filename.endswith(('.yaml', '.yml', '.json')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be YAML or JSON format"
        )

    return await service.start_validation(
        file=file,
        ruleset=ruleset,
        errors_only=errors_only,
        file_format="json"  # Always use JSON format
    )


@router.get(
    "/oas/report/{validation_id}",
    summary="Get validation report",
    description="Retrieve validation status and report",
    tags=["Validation"],
    operation_id="validationReport",
    responses={
        200: {
            "model": ReportResponse,
            "description": "Validation report"
        },
        404: PROBLEM_RESPONSES[404],
        422: PROBLEM_RESPONSES[422],
        429: PROBLEM_RESPONSES[429],
        500: PROBLEM_RESPONSES[500]
    }
)
async def get_report(
    validation_id: str,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get validation report by ID.

    - **validation_id**: Validation ID returned by /oas/validate

    Returns:
    - **200**: Validation completed, report included
    - **202**: Validation in progress
    - **404**: Validation not found
    - **500**: Validation failed
    """
    report = await service.get_report(validation_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation {validation_id} not found"
        )

    # Return report (all fields included for all statuses)
    # For FAILED status, return 500 with the report data
    status_code_value = 500 if report.status.value == "FAILED" else 200

    # Serialize with mode='json' to properly serialize datetime objects
    try:
        content = report.model_dump(mode='json', exclude_none=True)
        return JSONResponse(
            content=content,
            status_code=status_code_value
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_report: {type(e).__name__}: {e}", exc_info=True)
        raise


@router.post(
    "/oas/callback",
    response_model=CallbackResponse,
    summary="Callback from validation function",
    description="Internal endpoint for validation function to report completion",
    include_in_schema=False,  # Hide from OpenAPI docs
    responses={
        404: PROBLEM_RESPONSES[404],
        422: PROBLEM_RESPONSES[422]
    },
    dependencies=[Depends(verify_hmac_signature)]
)
async def callback(
    request: CallbackRequest,
    service: ValidationService = Depends(get_validation_service)
) -> CallbackResponse:
    """
    Callback endpoint for validation function.

    The function calls this endpoint to report validation completion.

    Security:
        Protected by HMAC-SHA256 signature verification.
        Azure Function must sign requests with X-Signature and X-Timestamp headers.
        Can be disabled with HMAC_ENABLED=false for local/dev.
    """
    success = await service.handle_callback(request)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation {request.validation_id} not found"
        )

    return CallbackResponse(message="Status updated")


@router.get(
    "/oas/rulesets",
    summary="List available rulesets",
    description="Get list of available Spectral rulesets",
    tags=["Rulesets"],
    operation_id="availableRulesets"
)
async def list_rulesets():
    """
    Get list of available rulesets

    Returns list of ruleset names that can be used in validation requests.
    """
    from services.ruleset_manager import get_ruleset_manager
    import config

    manager = get_ruleset_manager(
        repo=config.RULESET_REPO,
        version=config.RULESET_VERSION,
        cache_dir=config.RULESET_PATH
    )

    try:
        rulesets = await manager.get_available_rulesets()
        metadata = await manager.get_metadata()

        return {
            "rulesets": rulesets,
            "metadata": {
                "repo": metadata.get("repo") if metadata else None,
                "version": metadata.get("tag") if metadata else None,
                "published_at": metadata.get("published_at") if metadata else None,
                "downloaded_at": metadata.get("downloaded_at") if metadata else None
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rulesets: {str(e)}"
        )


@router.get(
    "/status",
    summary="Service health check",
    description="Health check endpoint as per ModI guidelines. Returns application/problem+json format.",
    tags=["Status"],
    operation_id="healthStatus",
    response_model=StatusResponse,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "Service is operational",
            "content": {
                "application/problem+json": {
                    "schema": {
                        "$ref": "#/components/schemas/StatusResponse"
                    }
                }
            }
        }
    }
)
async def get_status():
    """
    Service status endpoint (ModI compliant).

    Returns a Problem Details JSON (RFC 9457) indicating service health.
    This endpoint is required by ModI guidelines for API health monitoring.

    Returns:
        JSON response with application/problem+json media type containing:
        - status: HTTP status code (200 = healthy)
        - title: Service status title
        - detail: Detailed service status information
    """
    response_data = {
        "status": 200,
        "title": "Service Operational",
        "detail": "OAS Checker e-service is running and healthy"
    }

    return JSONResponse(
        content=response_data,
        status_code=200,
        media_type="application/problem+json"
    )


@router.post(
    "/internal/rulesets/refresh",
    include_in_schema=False,  # Exclude from OpenAPI documentation
    summary="Force refresh rulesets (Internal)",
    description="Internal endpoint to force download and update of rulesets from GitHub"
)
async def refresh_rulesets(jwt_payload=Depends(verify_jwt_token)):
    """
    Force refresh of rulesets from GitHub repository.

    This endpoint is internal and not exposed in the public API documentation.
    It forces a fresh download of all rulesets from the configured GitHub repository.

    Authentication:
        Requires JWT token with producerId == consumerId.
        Can be disabled with JWT_ENABLED=false for local/dev.
    """
    # Verify internal authorization (producerId == consumerId)
    if not jwt_payload.is_internal_authorized():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: producerId must equal consumerId for internal endpoints"
        )

    import logging
    from services.ruleset_manager import get_ruleset_manager
    import config

    logger = logging.getLogger(__name__)

    try:
        logger.info("Forcing ruleset refresh from GitHub...")

        # Get ruleset manager
        manager = get_ruleset_manager(
            repo=config.RULESET_REPO,
            version=config.RULESET_VERSION,
            cache_dir=config.RULESET_PATH
        )

        # Force download with force=True
        rulesets = await manager.download_rulesets(force=True)
        metadata = await manager.get_metadata()

        logger.info(f"✅ Rulesets refreshed successfully. Available: {', '.join(rulesets.keys())}")

        return {
            "success": True,
            "message": "Rulesets refreshed successfully",
            "rulesets": list(rulesets.keys()),
            "metadata": {
                "repo": metadata.get("repo") if metadata else None,
                "version": metadata.get("tag") if metadata else None,
                "published_at": metadata.get("published_at") if metadata else None,
                "downloaded_at": metadata.get("downloaded_at") if metadata else None
            }
        }
    except Exception as e:
        logger.error(f"❌ Failed to refresh rulesets: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh rulesets: {str(e)}"
        )
