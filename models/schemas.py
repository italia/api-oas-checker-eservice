"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from models.validation import ValidationStatus


class Problem(BaseModel):
    """
    RFC 9457 Problem Details for HTTP APIs
    https://www.rfc-editor.org/rfc/rfc9457.html
    """
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "type": "https://api.example.com/problems/validation-not-found",
                "title": "Validation Not Found",
                "status": 404,
                "detail": "Validation abc123 not found",
                "instance": "/oas/report/abc123"
            }
        }
    )

    type: str = Field(
        default="about:blank",
        description="URI reference that identifies the problem type"
    )
    title: str = Field(
        description="Short, human-readable summary of the problem"
    )
    status: int = Field(
        description="HTTP status code",
        ge=100,
        le=599,
        json_schema_extra={"format": "int32"}
    )
    detail: Optional[str] = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence"
    )
    instance: Optional[str] = Field(
        default=None,
        description="URI reference that identifies the specific occurrence"
    )


class StatusResponse(BaseModel):
    """
    Status response for /status endpoint (ModI compliant)
    Returns application/problem+json format
    """
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "status": 200,
                "title": "Service Operational",
                "detail": "OAS Checker e-service is running and healthy"
            }
        }
    )

    status: int = Field(
        description="HTTP status code (200 = healthy)",
        ge=100,
        le=599,
        json_schema_extra={"format": "int32"}
    )
    title: str = Field(
        description="Service status title"
    )
    detail: str = Field(
        description="Detailed service status information"
    )


class ValidationRequest(BaseModel):
    """Request schema for POST /oas/validate"""
    ruleset: str = Field(default="default", description="Ruleset to use for validation")
    errors_only: bool = Field(default=False, description="Return only errors, skip warnings and info")


class ValidationResponse(BaseModel):
    """Response schema for POST /oas/validate"""
    validation_id: str = Field(description="Unique validation ID")
    status: ValidationStatus = Field(description="Current validation status")
    message: str = Field(description="Human-readable message")


class ReportResponse(BaseModel):
    """Response schema for GET /oas/report/{validationId}"""
    model_config = ConfigDict(exclude_none=True)

    validation_id: str = Field(description="Validation ID (SHA256 hash of file + params)")
    status: ValidationStatus
    ruleset: str = Field(description="Ruleset used for validation")
    ruleset_version: str = Field(description="Version of ruleset used")
    errors_only: bool = Field(description="Whether only errors were requested")
    file_sha256: str = Field(description="SHA256 hash of the validated file content")
    created_at: datetime
    completed_at: Optional[datetime] = None
    report: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CallbackRequest(BaseModel):
    """Request schema for POST /oas/callback (from Function)"""
    validation_id: str
    status: ValidationStatus
    report_content: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class CallbackResponse(BaseModel):
    """Response schema for POST /oas/callback"""
    message: str


class FunctionValidationRequest(BaseModel):
    """Request schema sent to the validation function"""
    validation_id: str
    file_content: str  # Full content of the OpenAPI file
    file_extension: str  # .yaml or .json
    ruleset_name: str  # Name of the ruleset (e.g., "spectral-modi")
    ruleset_content: str  # Full content of the ruleset YAML
    errors_only: bool
    callback_url: str


# Custom Validation Error schemas to satisfy RAC_REST_FORMAT_004
class ValidationErrorItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "loc": ["body", "file"],
                "msg": "field required",
                "type": "value_error.missing"
            }
        }
    )

    loc: List[Union[str, int]] = Field(
        description="Location of the error",
    )
    msg: str = Field(description="Message")
    type: str = Field(description="Error type")

    @staticmethod
    def json_schema_extra(schema: dict, _):
        # Hack to add format: int32 to anyOf integers
        for prop in schema.get("properties", {}).values():
            if "items" in prop and "anyOf" in prop["items"]:
                for item in prop["items"]["anyOf"]:
                    if item.get("type") == "integer":
                        item["format"] = "int32"

class HTTPValidationError(BaseModel):
    detail: List[ValidationErrorItem] = Field(description="Validation error details")