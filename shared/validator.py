"""
Spectral validator wrapper for OpenAPI files.
"""
import json
import yaml
import subprocess
import tempfile
import os
import shutil
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def validate_openapi(content: str, ruleset_name: str, ruleset_content: str, errors_only: bool) -> Dict[str, Any]:
    """
    Validate OpenAPI content using Spectral CLI.
    
    Args:
        content: The OpenAPI document content (YAML/JSON).
        ruleset_name: Name of the ruleset to use.
        ruleset_content: Content of the Spectral ruleset.
        errors_only: Whether to include only errors in the report.
        
    Returns:
        A dictionary containing validation results.
    """

    # Initial syntax check
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return _error_result("invalid-openapi", "OpenAPI document must be a JSON/YAML object")
        if "openapi" not in data and "swagger" not in data:
            return _error_result("missing-version", "OpenAPI document must have 'openapi' or 'swagger' field")
    except Exception as e:
        return _error_result("invalid-syntax", f"Failed to parse content: {str(e)}")

    # Spectral execution
    tmp_dir = tempfile.mkdtemp()
    oas_file_path = os.path.join(tmp_dir, "openapi.yaml")
    ruleset_file_path = os.path.join(tmp_dir, "ruleset.yaml")
    
    try:
        # Prepare files
        with open(oas_file_path, 'w') as f:
            f.write(content)

        if ruleset_content:
            with open(ruleset_file_path, 'w') as f:
                f.write(ruleset_content)
            
            # Copy custom functions if available
            _copy_custom_functions(tmp_dir)

        # Execute Spectral
        cmd = ['spectral', 'lint', oas_file_path, '--format', 'json']
        if ruleset_content:
            cmd += ['--ruleset', ruleset_file_path]

        logger.info(f"Executing Spectral: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        
        spectral_output = result.stdout.strip()
        if not spectral_output:
            return _success_result()

        try:
            # Spectral might output extra text, try to find the JSON array
            start = spectral_output.find('[')
            end = spectral_output.rfind(']') + 1
            if start != -1 and end > 0:
                spectral_results = json.loads(spectral_output[start:end])
            else:
                spectral_results = json.loads(spectral_output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Spectral output: {spectral_output}")
            return _error_result("spectral-parse-error", f"Failed to parse Spectral output: {str(e)}")

        return _process_spectral_results(spectral_results, errors_only)

    except subprocess.TimeoutExpired:
        logger.error("Spectral validation timed out")
        return _error_result("timeout", "Spectral validation timed out after 45 seconds")
    except Exception as e:
        logger.error(f"Spectral validation error: {e}", exc_info=True)
        return _error_result("spectral-error", str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def _copy_custom_functions(dest_dir: str):
    """Copy custom functions to the temporary execution directory."""
    src_functions_dir = os.getenv("RULESET_FUNCTIONS_PATH", "/home/site/wwwroot/data/rulesets/functions")
    if os.path.exists(src_functions_dir):
        dest_functions_dir = os.path.join(dest_dir, "functions")
        try:
            shutil.copytree(src_functions_dir, dest_functions_dir, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to copy custom functions: {e}")

def _map_severity(spectral_severity: int) -> str:
    """Map Spectral severity levels to human-readable strings."""
    return {0: "error", 1: "warning", 2: "info", 3: "hint"}.get(spectral_severity, "unknown")

def _error_result(code: str, message: str) -> Dict[str, Any]:
    """Helper to return a standardized error result."""
    return {
        "valid": False, 
        "errors": [{"code": code, "message": message, "path": [], "severity": "error"}],
        "warnings": [], "info": [], "summary": {"total_issues": 1, "errors": 1, "warnings": 0, "info": 0}
    }

def _success_result() -> Dict[str, Any]:
    """Helper to return a standardized success result."""
    return {
        "valid": True, "errors": [], "warnings": [], "info": [],
        "summary": {"total_issues": 0, "errors": 0, "warnings": 0, "info": 0}
    }

def _process_spectral_results(results: List[Dict[str, Any]], errors_only: bool) -> Dict[str, Any]:
    """Format and filter Spectral results."""
    errors, warnings, info_items = [], [], []

    for issue in results:
        severity_num = issue.get('severity', 1)
        severity_str = _map_severity(severity_num)
        
        formatted_issue = {
            "code": issue.get('code', 'unknown'),
            "message": issue.get('message', ''),
            "path": issue.get('path', []),
            "severity": severity_str,
            "range": issue.get('range', {})
        }
        
        if severity_num == 0:
            errors.append(formatted_issue)
        elif severity_num == 1:
            if not errors_only:
                warnings.append(formatted_issue)
        elif not errors_only:
            info_items.append(formatted_issue)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "info": info_items,
        "summary": {
            "total_issues": len(errors) + len(warnings) + len(info_items),
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info_items)
        }
    }
