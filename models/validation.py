"""
Validation models and enums
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


class ValidationStatus(str, Enum):
    """Status of a validation request"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileFormat(str, Enum):
    """Supported file formats for validation"""
    JSON = "json"
    YAML = "yaml"
    YML = "yml"


@dataclass
class Validation:
    """
    Validation record stored in database
    """
    id: str  # validation ID (SHA256 hash of content + params)
    status: ValidationStatus
    ruleset: str
    ruleset_version: str  # version of ruleset used (e.g., "1.2.3" or "latest")
    errors_only: bool
    format: FileFormat
    file_sha256: str  # SHA256 hash of file content only
    file_content: str  # Content of the OpenAPI file
    created_at: datetime
    completed_at: Optional[datetime] = None
    report_content: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def is_completed(self) -> bool:
        """Check if validation is completed"""
        return self.status in [ValidationStatus.COMPLETED, ValidationStatus.FAILED]

    def is_in_progress(self) -> bool:
        """Check if validation is in progress"""
        return self.status == ValidationStatus.IN_PROGRESS

    def is_pending(self) -> bool:
        """Check if validation is pending"""
        return self.status == ValidationStatus.PENDING