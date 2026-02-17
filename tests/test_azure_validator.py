"""
Unit tests for Spectral validator
"""
import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
from shared.validator import validate_openapi


def test_validate_openapi_invalid_yaml():
    content = "invalid: yaml: : content"
    report = validate_openapi(content, "default", "", False)
    assert report["valid"] is False
    assert any("Failed to parse content" in err["message"] for err in report["errors"])


def test_validate_openapi_missing_version():
    content = "info: {title: test, version: 1.0.0}\npaths: {}"
    report = validate_openapi(content, "default", "", False)
    assert report["valid"] is False
    assert any("openapi" in err["message"].lower() for err in report["errors"])


@patch("subprocess.run")
def test_validate_openapi_spectral_success(mock_run):
    content = "openapi: 3.0.0\ninfo: {title: test, version: 1.0.0}\npaths: {}"
    
    # Mock successful spectral run with no issues
    mock_run.return_value = MagicMock(
        stdout="[]",
        returncode=0
    )
    
    report = validate_openapi(content, "default", "ruleset content", False)
    assert report["valid"] is True
    assert report["summary"]["total_issues"] == 0


@patch("subprocess.run")
def test_validate_openapi_spectral_with_issues(mock_run):
    content = "openapi: 3.0.0\ninfo: {title: test, version: 1.0.0}\npaths: {}"
    
    # Mock spectral output with an error
    spectral_output = [
        {
            "code": "test-rule",
            "message": "test message",
            "path": ["info", "title"],
            "severity": 0, # Error
            "range": {"start": {"line": 1, "character": 1}, "end": {"line": 1, "character": 5}}
        }
    ]
    
    mock_run.return_value = MagicMock(
        stdout=json.dumps(spectral_output),
        returncode=0
    )
    
    report = validate_openapi(content, "default", "ruleset content", False)
    assert report["valid"] is False
    assert len(report["errors"]) == 1
    assert report["errors"][0]["code"] == "test-rule"