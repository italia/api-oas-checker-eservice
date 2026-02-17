"""
Mock validator - simulates Spectral validation
"""
import json
import yaml
import random
from typing import Dict, Any, List


from typing import Dict, Any, List, Union

def validate_openapi(content: Union[str, bytes], ruleset: str, errors_only: bool) -> Dict[str, Any]:
    """
    Mock validation function that simulates Spectral.

    In production, this would be replaced by actual Spectral execution.
    For now, it returns a mock report with random issues.

    Args:
        content: OpenAPI file content
        ruleset: Ruleset name (not used in mock)
        errors_only: Return only errors

    Returns:
        Validation report dictionary
    """

    # Try to parse as YAML/JSON to check if valid
    try:
        # Try YAML first (supports both YAML and JSON)
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        data = yaml.safe_load(content)

        # Basic validation
        if not isinstance(data, dict):
            return {
                "valid": False,
                "errors": [
                    {
                        "code": "invalid-openapi",
                        "message": "OpenAPI document must be a JSON object",
                        "path": [],
                        "severity": "error"
                    }
                ],
                "warnings": [],
                "info": []
            }

        # Check for openapi or swagger version
        has_version = "openapi" in data or "swagger" in data

        if not has_version:
            return {
                "valid": False,
                "errors": [
                    {
                        "code": "missing-version",
                        "message": "OpenAPI document must have 'openapi' or 'swagger' field",
                        "path": [],
                        "severity": "error"
                    }
                ],
                "warnings": [],
                "info": []
            }

        # Generate mock validation report
        # In reality, Spectral would run here
        errors = []
        warnings = []
        info_items = []

        # Add some mock issues based on random chance
        if random.random() > 0.5:
            warnings.append({
                "code": "operation-description",
                "message": "Operation should have a description",
                "path": ["paths", "/users", "get"],
                "severity": "warning"
            })

        if random.random() > 0.7:
            warnings.append({
                "code": "operation-tag-defined",
                "message": "Operation tags should be defined in global tags",
                "path": ["paths", "/users", "get", "tags", "0"],
                "severity": "warning"
            })

        if not errors_only:
            if random.random() > 0.6:
                info_items.append({
                    "code": "info-contact",
                    "message": "Info object should contain contact information",
                    "path": ["info"],
                    "severity": "info"
                })

        # Build report
        report = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings if not errors_only else [],
            "info": info_items if not errors_only else [],
            "summary": {
                "total_issues": len(errors) + len(warnings) + len(info_items),
                "errors": len(errors),
                "warnings": len(warnings),
                "info": len(info_items)
            }
        }

        return report

    except yaml.YAMLError as e:
        return {
            "valid": False,
            "errors": [
                {
                    "code": "invalid-yaml",
                    "message": f"Failed to parse YAML: {str(e)}",
                    "path": [],
                    "severity": "error"
                }
            ],
            "warnings": [],
            "info": []
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [
                {
                    "code": "validation-error",
                    "message": f"Validation error: {str(e)}",
                    "path": [],
                    "severity": "error"
                }
            ],
            "warnings": [],
            "info": []
        }
