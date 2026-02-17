"""
Validation service - business logic orchestration
"""
import hashlib
import logging
from typing import Optional, Dict, Any
import yaml
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

from database.repository import ValidationRepository
from services.function_client import FunctionClient
from models.validation import Validation, ValidationStatus, FileFormat
from models.schemas import (
    ValidationResponse,
    ReportResponse,
    FunctionValidationRequest,
    CallbackRequest
)

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for orchestrating validation workflow without external storage.
    """

    def __init__(
        self,
        repository: ValidationRepository,
        function_client: FunctionClient,
        callback_base_url: str,
        ruleset_manager = None
    ):
        """
        Initialize validation service

        Args:
            repository: Validation repository
            function_client: Function client
            callback_base_url: Base URL for callback endpoint
            ruleset_manager: Optional RulesetManager for ruleset content resolution
        """
        self.repository = repository
        self.function_client = function_client
        self.callback_base_url = callback_base_url.rstrip('/')
        self.ruleset_manager = ruleset_manager
        self._ruleset_cache: Dict[str, str] = {}

    async def start_validation(
        self,
        file: UploadFile,
        ruleset: str,
        errors_only: bool,
        file_format: str
    ) -> ValidationResponse:
        """
        Start a new validation request.
        
        Workflow:
        1. Read and validate file content
        2. Resolve ruleset and its content
        3. Generate stable validation ID (SHA256)
        4. Create database record (if not exists)
        5. Trigger asynchronous validation via Function
        """
        # 1. Read and validate file content
        content_bytes = await file.read()
        try:
            content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be valid UTF-8 text"
            )

        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML/JSON format: {str(e)}"
            )

        file_sha256 = hashlib.sha256(content_bytes).hexdigest()

        # 2. Resolve ruleset
        ruleset_version = "unknown"
        ruleset_content = ""
        
        if self.ruleset_manager:
            metadata = await self.ruleset_manager.get_metadata()
            if metadata:
                ruleset_version = metadata.get("tag", "unknown")

            ruleset_to_load = "spectral" if ruleset == "default" else ruleset
            ruleset_content = await self._get_ruleset_content(ruleset_to_load)
            
            if not ruleset_content:
                available = await self.ruleset_manager.get_available_rulesets()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ruleset '{ruleset_to_load}' not found. Available: {', '.join(available)}"
                )

        # 3. Generate validation ID
        unique_string = f"{file_sha256}|{ruleset}|{errors_only}|{ruleset_version}"
        validation_id = hashlib.sha256(unique_string.encode()).hexdigest()

        # 4. Check existence or create
        existing = await self.repository.get_by_id(validation_id)
        if existing:
            return ValidationResponse(
                validation_id=validation_id,
                status=existing.status,
                message=f"Validation already exists with status {existing.status.value}"
            )

        await self.repository.create(
            validation_id=validation_id,
            ruleset=ruleset,
            ruleset_version=ruleset_version,
            errors_only=errors_only,
            file_format=FileFormat(file_format),
            file_sha256=file_sha256,
            file_content=content
        )
        
        # 5. Invoke validation function
        file_extension = ".json" if file.filename and file.filename.endswith(".json") else ".yaml"
        
        function_request = FunctionValidationRequest(
            validation_id=validation_id,
            file_content=content,
            file_extension=file_extension,
            ruleset_name=ruleset,
            ruleset_content=ruleset_content,
            errors_only=errors_only,
            callback_url=f"{self.callback_base_url}/oas/callback"
        )

        success = await self.function_client.invoke_validation(function_request)

        if not success:
            await self.repository.update_status(
                validation_id=validation_id,
                status=ValidationStatus.FAILED,
                error_message="Failed to invoke validation function"
            )
            return ValidationResponse(
                validation_id=validation_id,
                status=ValidationStatus.FAILED,
                message="Failed to start validation"
            )

        return ValidationResponse(
            validation_id=validation_id,
            status=ValidationStatus.PENDING,
            message="Validation started"
        )

    async def get_report(self, validation_id: str) -> Optional[ReportResponse]:
        """Get validation report by ID"""
        validation = await self.repository.get_by_id(validation_id)
        if not validation:
            return None

        return ReportResponse(
            validation_id=validation.id,
            status=validation.status,
            ruleset=validation.ruleset,
            ruleset_version=validation.ruleset_version,
            errors_only=validation.errors_only,
            file_sha256=validation.file_sha256,
            created_at=validation.created_at,
            completed_at=validation.completed_at,
            report=validation.report_content,
            error=validation.error_message
        )

    async def handle_callback(self, callback: CallbackRequest) -> bool:
        """Handle callback from validation function"""
        logger.info(f"Received callback for validation {callback.validation_id} (Status: {callback.status})")
        return await self.repository.update_status(
            validation_id=callback.validation_id,
            status=callback.status,
            report_content=callback.report_content,
            error_message=callback.error_message
        )

    async def _get_ruleset_content(self, ruleset_name: str) -> Optional[str]:
        """Helper to get ruleset content with basic caching"""
        if ruleset_name in self._ruleset_cache:
            return self._ruleset_cache[ruleset_name]

        ruleset_path = await self.ruleset_manager.get_ruleset_path(ruleset_name)
        if not ruleset_path:
            return None

        try:
            content = Path(ruleset_path).read_text(encoding="utf-8")
            self._ruleset_cache[ruleset_name] = content
            return content
        except Exception as e:
            logger.error(f"Error reading ruleset file {ruleset_path}: {e}")
            return None
            
    def clear_cache(self):
        """Clear the ruleset content cache"""
        self._ruleset_cache.clear()
