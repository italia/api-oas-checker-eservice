"""
Ruleset Manager - Download and manage Spectral rulesets from GitHub
"""
import httpx
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import logging
import zipfile
import io
import json

logger = logging.getLogger(__name__)


class RulesetManager:
    """
    Manages downloading and caching of Spectral rulesets from GitHub releases.
    No longer uses external storage, only local cache for the service.
    """

    def __init__(
        self,
        repo: str,
        version: str = "latest",
        cache_dir: str = "./data/rulesets"
    ):
        """
        Initialize RulesetManager

        Args:
            repo: GitHub repository in format "owner/repo"
            version: Release version ("latest" or specific tag like "1.2")
            cache_dir: Local directory to cache downloaded rulesets
        """
        self.repo = repo
        self.version = version
        self.cache_dir = Path(cache_dir).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Paths
        self.rulesets_dir = self.cache_dir / "rules"
        self.functions_dir = self.cache_dir / "functions"
        self.metadata_file = self.cache_dir / "metadata.json"

        self.rulesets_dir.mkdir(parents=True, exist_ok=True)
        self.functions_dir.mkdir(parents=True, exist_ok=True)

    async def download_rulesets(self, force: bool = False) -> Dict[str, str]:
        """
        Download rulesets from GitHub release

        Args:
            force: Force re-download even if cached

        Returns:
            Dictionary mapping ruleset names to file paths
        """
        # Check if already downloaded and up-to-date
        if not force and await self._is_cache_valid():
            logger.info("Using cached rulesets")
            return await self._get_cached_rulesets()

        logger.info(f"Downloading rulesets from {self.repo} (version: {self.version})")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Get release info
                if self.version == "latest":
                    url = f"https://api.github.com/repos/{self.repo}/releases/latest"
                else:
                    url = f"https://api.github.com/repos/{self.repo}/releases/tags/{self.version}"

                logger.debug(f"Fetching release from: {url}")
                response = await client.get(url)
                response.raise_for_status()
                release_data = response.json()

                tag_name = release_data["tag_name"]
                published_at = release_data["published_at"]
                assets = release_data.get("assets", [])

                logger.info(f"Found release: {tag_name} (published: {published_at})")
                logger.info(f"Assets: {len(assets)} files")

                # Download ruleset YAML files
                rulesets = {}
                for asset in assets:
                    name = asset["name"]
                    download_url = asset["browser_download_url"]

                    # Download .yml ruleset files (skip .html documentation)
                    if name.endswith(".yml") or name.endswith(".yaml"):
                        logger.info(f"Downloading ruleset: {name}")
                        ruleset_response = await client.get(download_url)
                        ruleset_response.raise_for_status()

                        # Save to cache
                        ruleset_path = self.rulesets_dir / name
                        ruleset_path.write_bytes(ruleset_response.content)

                        # Use filename without extension as ruleset name
                        ruleset_name = name.rsplit(".", 1)[0]
                        rulesets[ruleset_name] = str(ruleset_path)
                        logger.debug(f"Saved {name} -> {ruleset_path}")

                    # Download functions.zip
                    elif name == "functions.zip":
                        logger.info(f"Downloading functions: {name}")
                        functions_response = await client.get(download_url)
                        functions_response.raise_for_status()

                        # Extract to functions directory, stripping prefixes if present
                        with zipfile.ZipFile(io.BytesIO(functions_response.content)) as zip_file:
                            for member in zip_file.infolist():
                                if member.is_dir():
                                    continue
                                
                                # Strip prefixes like 'rulesets/functions/'
                                filename = Path(member.filename).name
                                target_path = self.functions_dir / filename
                                target_path.write_bytes(zip_file.read(member.filename))
                                
                        logger.info(f"Extracted functions to {self.functions_dir}")

                # Save metadata
                metadata = {
                    "repo": self.repo,
                    "tag": tag_name,
                    "published_at": published_at,
                    "downloaded_at": None,  # Will be set by _save_metadata
                    "rulesets": rulesets
                }
                await self._save_metadata(metadata)

                logger.info(f"Successfully downloaded {len(rulesets)} rulesets")

                return rulesets

        except httpx.HTTPError as e:
            logger.error(f"Failed to download rulesets: {e}")
            # Fall back to cached version if available
            if await self._is_cache_valid():
                logger.warning("Using cached rulesets due to download failure")
                return await self._get_cached_rulesets()
            raise

    async def get_available_rulesets(self) -> List[str]:
        """
        Get list of available ruleset names

        Returns:
            List of ruleset names
        """
        rulesets = await self._get_cached_rulesets()
        return list(rulesets.keys())

    async def get_ruleset_path(self, ruleset_name: str) -> Optional[str]:
        """
        Get path to a specific ruleset file

        Args:
            ruleset_name: Name of the ruleset (without .yml extension)

        Returns:
            Path to ruleset file, or None if not found
        """
        rulesets = await self._get_cached_rulesets()
        return rulesets.get(ruleset_name)

    async def get_functions_dir(self) -> str:
        """
        Get path to functions directory

        Returns:
            Path to functions directory
        """
        return str(self.functions_dir)

    async def _is_cache_valid(self) -> bool:
        """Check if cached rulesets are valid"""
        if not self.metadata_file.exists():
            return False

        # Check if ruleset files exist
        metadata = await self._load_metadata()
        if not metadata or "rulesets" not in metadata:
            return False

        for ruleset_path in metadata["rulesets"].values():
            if not Path(ruleset_path).exists():
                return False

        return True

    async def _get_cached_rulesets(self) -> Dict[str, str]:
        """Get cached rulesets from metadata"""
        metadata = await self._load_metadata()
        if metadata and "rulesets" in metadata:
            return metadata["rulesets"]
        return {}

    async def _load_metadata(self) -> Optional[Dict]:
        """Load metadata from file"""
        if not self.metadata_file.exists():
            return None

        try:
            return json.loads(self.metadata_file.read_text())
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

    async def _save_metadata(self, metadata: Dict):
        """Save metadata to file"""
        try:
            from datetime import datetime, timezone
            metadata["downloaded_at"] = datetime.now(timezone.utc).isoformat()
            self.metadata_file.write_text(json.dumps(metadata, indent=2))
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    async def get_metadata(self) -> Optional[Dict]:
        """
        Get current ruleset metadata

        Returns:
            Metadata dictionary with repo, tag, published_at, etc.
        """
        return await self._load_metadata()


# Singleton instance
_ruleset_manager: Optional[RulesetManager] = None


def get_ruleset_manager(
    repo: str,
    version: str = "latest",
    cache_dir: str = "./data/rulesets"
) -> RulesetManager:
    """
    Get or create RulesetManager singleton

    Args:
        repo: GitHub repository
        version: Release version
        cache_dir: Cache directory

    Returns:
        RulesetManager instance
    """
    global _ruleset_manager
    if _ruleset_manager is None:
        _ruleset_manager = RulesetManager(repo, version, cache_dir)
    return _ruleset_manager