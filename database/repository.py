"""
Repository for validation CRUD operations
"""
import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone

from database.db import Database
from models.validation import Validation, ValidationStatus, FileFormat

logger = logging.getLogger(__name__)


class ValidationRepository:
    """
    Repository for managing validation records in database.
    Supports both PostgreSQL and SQLite.
    """

    def __init__(self, database: Database):
        """
        Initialize repository

        Args:
            database: Database instance
        """
        self.db = database

    async def create(
        self,
        validation_id: str,
        ruleset: str,
        ruleset_version: str,
        errors_only: bool,
        file_format: FileFormat,
        file_sha256: str,
        file_content: str
    ) -> Validation:
        """
        Create a new validation record
        """
        created_at = datetime.now(timezone.utc)

        async with self.db.get_connection() as conn:
            if self.db.is_sqlite:
                await conn.execute(
                    """
                    INSERT INTO validations
                    (id, status, ruleset, ruleset_version, errors_only, format, file_sha256, file_content, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (validation_id, ValidationStatus.PENDING.value, ruleset, ruleset_version, 
                     int(errors_only), file_format.value, file_sha256, file_content, created_at.isoformat())
                )
                await conn.commit()
            else:
                await conn.execute(
                    """
                    INSERT INTO validations
                    (id, status, ruleset, ruleset_version, errors_only, format, file_sha256, file_content, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    validation_id,
                    ValidationStatus.PENDING.value,
                    ruleset,
                    ruleset_version,
                    errors_only,
                    file_format.value,
                    file_sha256,
                    file_content,
                    created_at
                )

        return Validation(
            id=validation_id,
            status=ValidationStatus.PENDING,
            ruleset=ruleset,
            ruleset_version=ruleset_version,
            errors_only=errors_only,
            format=file_format,
            file_sha256=file_sha256,
            file_content=file_content,
            created_at=created_at
        )

    async def get_by_id(self, validation_id: str) -> Optional[Validation]:
        """
        Get validation by ID
        """
        async with self.db.get_connection() as conn:
            if self.db.is_sqlite:
                cursor = await conn.execute("SELECT * FROM validations WHERE id = ?", (validation_id,))
                row = await cursor.fetchone()
            else:
                row = await conn.fetchrow("SELECT * FROM validations WHERE id = $1", validation_id)

        if not row:
            return None

        return self._map_row_to_validation(row)

    async def update_status(
        self,
        validation_id: str,
        status: ValidationStatus,
        report_content: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update validation status and result
        """
        completed_at = datetime.now(timezone.utc) if status in [
            ValidationStatus.COMPLETED,
            ValidationStatus.FAILED
        ] else None

        report_json = json.dumps(report_content) if report_content else None

        async with self.db.get_connection() as conn:
            if self.db.is_sqlite:
                result = await conn.execute(
                    """
                    UPDATE validations
                    SET status = ?,
                        completed_at = ?,
                        report_content = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
                    (status.value, completed_at.isoformat() if completed_at else None, 
                     report_json, error_message, validation_id)
                )
                await conn.commit()
                return result.rowcount > 0
            else:
                # asyncpg returns 'UPDATE 1' or similar
                result = await conn.execute(
                    """
                    UPDATE validations
                    SET status = $1,
                        completed_at = $2,
                        report_content = $3,
                        error_message = $4
                    WHERE id = $5
                    """,
                    status.value, completed_at, report_json, error_message, validation_id
                )
                return result != 'UPDATE 0'

    async def exists(self, validation_id: str) -> bool:
        """
        Check if validation exists
        """
        async with self.db.get_connection() as conn:
            if self.db.is_sqlite:
                cursor = await conn.execute("SELECT 1 FROM validations WHERE id = ?", (validation_id,))
                row = await cursor.fetchone()
            else:
                row = await conn.fetchrow("SELECT 1 FROM validations WHERE id = $1", validation_id)
        return row is not None

    def _map_row_to_validation(self, row: Any) -> Validation:
        """Helper to map a database row to a Validation object"""
        
        # Handle report_content (PostgreSQL JSONB vs SQLite TEXT)
        report_content = row['report_content']
        if isinstance(report_content, str) and report_content:
            try:
                report_content = json.loads(report_content)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse report_content JSON for {row['id']}")
                report_content = None

        # Handle datetimes (PostgreSQL datetime vs SQLite ISO string)
        created_at = row['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        completed_at = row['completed_at']
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        return Validation(
            id=row['id'],
            status=ValidationStatus(row['status']),
            ruleset=row['ruleset'],
            ruleset_version=row['ruleset_version'],
            errors_only=bool(row['errors_only']),
            format=FileFormat(row['format']),
            file_sha256=row['file_sha256'],
            file_content=row['file_content'],
            created_at=created_at,
            completed_at=completed_at,
            report_content=report_content,
            error_message=row['error_message']
        )