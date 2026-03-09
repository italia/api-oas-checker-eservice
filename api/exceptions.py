"""
Custom exceptions and exception handlers
"""
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import config
from models.schemas import Problem


def create_problem_details(
    status: int,
    title: str,
    detail: str = None,
    type_suffix: str = None,
    instance: str = None
) -> Problem:
    """
    Create a Problem Details object

    Args:
        status: HTTP status code
        title: Short summary
        detail: Detailed explanation
        type_suffix: Suffix for problem type URI (e.g., "validation-not-found")
        instance: URI of this specific occurrence

    Returns:
        ProblemDetails object
    """
    # Build type URI
    if type_suffix:
        problem_type = f"{config.OPENAPI_SERVER_URL}/problems/{type_suffix}"
    else:
        problem_type = "about:blank"

    return Problem(
        type=problem_type,
        title=title,
        status=status,
        detail=detail,
        instance=instance
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException and return RFC 9457 Problem Details

    Args:
        request: FastAPI request
        exc: HTTPException

    Returns:
        JSONResponse with Problem Details
    """
    # Map status codes to problem types
    status_to_type = {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        409: "conflict",
        422: "unprocessable-entity",
        500: "internal-server-error",
        502: "bad-gateway",
        503: "service-unavailable"
    }

    # Map status codes to titles
    status_to_title = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable"
    }

    problem = create_problem_details(
        status=exc.status_code,
        title=status_to_title.get(exc.status_code, "Error"),
        detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        type_suffix=status_to_type.get(exc.status_code),
        instance=str(request.url.path)
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors and return RFC 9457 Problem Details

    Args:
        request: FastAPI request
        exc: RequestValidationError

    Returns:
        JSONResponse with Problem Details
    """
    # Extract validation error details
    errors = exc.errors()
    error_messages = []
    for error in errors:
        loc = " -> ".join(str(l) for l in error["loc"])
        error_messages.append(f"{loc}: {error['msg']}")

    detail = "Request validation failed: " + "; ".join(error_messages)

    problem = create_problem_details(
        status=422,
        title="Validation Error",
        detail=detail,
        type_suffix="validation-error",
        instance=str(request.url.path)
    )

    return JSONResponse(
        status_code=422,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic exceptions and return RFC 9457 Problem Details

    Args:
        request: FastAPI request
        exc: Exception

    Returns:
        JSONResponse with Problem Details
    """
    import traceback
    import logging

    logger = logging.getLogger(__name__)

    # Log the full traceback for debugging
    logger.error(f"Exception caught by generic_exception_handler: {type(exc).__name__}: {str(exc)}", exc_info=True)

    problem = create_problem_details(
        status=500,
        title="Internal Server Error",
        detail=str(exc),
        type_suffix="internal-error",
        instance=str(request.url.path)
    )

    return JSONResponse(
        status_code=500,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )
