"""
Unit tests for RulesetManager
"""
import pytest
import json
import zipfile
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from services.ruleset_manager import RulesetManager, get_ruleset_manager


@pytest.fixture
def ruleset_dir(tmp_path):
    d = tmp_path / "rulesets"
    d.mkdir()
    return d


@pytest.mark.asyncio
async def test_ruleset_manager_init(ruleset_dir):
    manager = RulesetManager(repo="owner/repo", cache_dir=str(ruleset_dir))
    assert manager.repo == "owner/repo"
    assert Path(manager.rulesets_dir).exists()
    assert Path(manager.functions_dir).exists()


@pytest.mark.asyncio
async def test_download_rulesets_mock(ruleset_dir):
    manager = RulesetManager(repo="owner/repo", cache_dir=str(ruleset_dir))
    
    # Mock httpx.AsyncClient
    mock_response_release = MagicMock()
    mock_response_release.json.return_value = {
        "tag_name": "v1.0",
        "published_at": "2025-01-01T00:00:00Z",
        "assets": [
            {"name": "spectral.yml", "browser_download_url": "http://example.com/spectral.yml"},
            {"name": "functions.zip", "browser_download_url": "http://example.com/functions.zip"}
        ]
    }
    mock_response_release.raise_for_status = MagicMock()
    
    mock_response_yml = MagicMock()
    mock_response_yml.content = b"extends: spectral:oas"
    mock_response_yml.raise_for_status = MagicMock()
    
    # Create a dummy zip file for functions
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("func1.js", "console.log('test')")
    
    mock_response_zip = MagicMock()
    mock_response_zip.content = zip_buffer.getvalue()
    mock_response_zip.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [mock_response_release, mock_response_yml, mock_response_zip]
        
        rulesets = await manager.download_rulesets(force=True)
        
        assert "spectral" in rulesets
        assert Path(rulesets["spectral"]).exists()
        assert (Path(manager.functions_dir) / "func1.js").exists()
        
        # Check metadata
        metadata = await manager.get_metadata()
        assert metadata["tag"] == "v1.0"


@pytest.mark.asyncio
async def test_get_available_rulesets(ruleset_dir):
    manager = RulesetManager(repo="owner/repo", cache_dir=str(ruleset_dir))
    
    # Manually create metadata
    metadata = {
        "rulesets": {
            "spectral": str(ruleset_dir / "rules" / "spectral.yml")
        }
    }
    (ruleset_dir / "rules").mkdir(parents=True, exist_ok=True)
    (ruleset_dir / "rules" / "spectral.yml").touch()
    with open(ruleset_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)
        
    rulesets = await manager.get_available_rulesets()
    assert "spectral" in rulesets


@pytest.mark.asyncio
async def test_get_ruleset_path(ruleset_dir):
    manager = RulesetManager(repo="owner/repo", cache_dir=str(ruleset_dir))
    (ruleset_dir / "rules").mkdir(parents=True, exist_ok=True)
    p = ruleset_dir / "rules" / "test.yml"
    p.touch()
    
    metadata = {"rulesets": {"test": str(p)}}
    with open(ruleset_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)
        
    path = await manager.get_ruleset_path("test")
    assert path == str(p)
    
    assert await manager.get_ruleset_path("nonexistent") is None
