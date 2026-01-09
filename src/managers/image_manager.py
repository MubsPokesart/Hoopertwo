"""Image manager for downloading and caching player images.

Supports dual-source image fetching:
1. NBA CDN (primary) - Fast, reliable, official images
2. Basketball Reference (fallback) - Comprehensive coverage, historical players
"""
import logging
from pathlib import Path
from typing import Optional
import aiohttp
from src.scrapers.nba_api_client import NBAApiClient
from src.scrapers.basketball_reference_client import BasketballReferenceClient

logger = logging.getLogger(__name__)


class ImageManager:
    """Manager for player image downloading and caching.

    Responsibilities:
    - Download player images from NBA CDN (primary)
    - Fallback to Basketball Reference when NBA CDN unavailable
    - Cache images locally to avoid re-downloads
    - Handle download failures gracefully

    Strategy:
    1. Try NBA CDN first (fast, official)
    2. If fails, try Basketball Reference (comprehensive)
    3. If both fail, log error and return False
    """

    def __init__(
        self,
        nba_client: NBAApiClient,
        cache_dir: str,
        br_client: Optional[BasketballReferenceClient] = None
    ):
        """Initialize image manager with dual sources.

        Args:
            nba_client: NBA API client instance (primary)
            cache_dir: Directory to cache downloaded images
            br_client: Basketball Reference client (fallback, optional)
        """
        self.nba_client = nba_client
        self.br_client = br_client
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cached_image_path(self, player_name: str) -> str:
        """Get the file path for a cached player image.

        Args:
            player_name: Full player name

        Returns:
            Path where image is/should be cached
        """
        # Normalize player name for filename (lowercase, underscores)
        filename = player_name.lower().replace(" ", "_").replace(".", "")
        filename = filename.replace("-", "_") + ".png"  # NBA CDN uses PNG
        return str(self.cache_dir / filename)

    def is_cached(self, player_name: str) -> bool:
        """Check if player image is already cached.

        Args:
            player_name: Full player name

        Returns:
            True if image exists in cache
        """
        cached_path = Path(self.get_cached_image_path(player_name))
        return cached_path.exists() and cached_path.stat().st_size > 0

    def _download_from_url(self, url: str, save_path: str) -> None:
        """Download image from URL and save to disk.

        Args:
            url: Image URL
            save_path: Local path to save image
        """
        import requests

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)

    def download_player_image(self, player_name: str, image_url: Optional[str] = None) -> bool:
        """Download and cache a player's image using dual sources.

        Strategy:
        1. Check if already cached
        2. If image_url provided, try that first
        3. Try NBA CDN
        4. Try Basketball Reference (if client available)

        Args:
            player_name: Full player name
            image_url: Optional direct URL to download from

        Returns:
            True if download successful, False otherwise
        """
        if self.is_cached(player_name):
            logger.debug(f"Image already cached for {player_name}")
            return True

        save_path = self.get_cached_image_path(player_name)

        # Try provided URL first
        if image_url:
            try:
                self._download_from_url(image_url, save_path)
                logger.info(f"Downloaded image for {player_name} from provided URL")
                return True
            except Exception as e:
                logger.warning(f"Failed to download from provided URL: {e}")

        # Try NBA CDN
        try:
            nba_url = self.nba_client.get_player_image_url(player_name)
            if nba_url:
                self._download_from_url(nba_url, save_path)
                logger.info(f"Downloaded image for {player_name} from NBA CDN")
                return True
        except Exception as e:
            logger.warning(f"Failed to download from NBA CDN: {e}")

        # Try Basketball Reference fallback
        if self.br_client:
            try:
                br_url = self.br_client.get_player_image_url(player_name)
                if br_url:
                    self._download_from_url(br_url, save_path)
                    logger.info(f"Downloaded image for {player_name} from Basketball Reference")
                    return True
            except Exception as e:
                logger.warning(f"Failed to download from Basketball Reference: {e}")

        logger.error(f"Failed to download image for {player_name} from all sources")
        return False

    def get_player_image_url(self, player_name: str) -> Optional[str]:
        """Get player image URL from available sources without downloading.

        Tries NBA CDN first, then Basketball Reference.

        Args:
            player_name: Full player name

        Returns:
            Image URL or None if not found
        """
        # Try NBA CDN first
        try:
            nba_url = self.nba_client.get_player_image_url(player_name)
            if nba_url:
                logger.debug(f"Found NBA CDN URL for {player_name}")
                return nba_url
        except Exception as e:
            logger.debug(f"NBA CDN lookup failed: {e}")

        # Try Basketball Reference
        if self.br_client:
            try:
                br_url = self.br_client.get_player_image_url(player_name)
                if br_url:
                    logger.debug(f"Found Basketball Reference URL for {player_name}")
                    return br_url
            except Exception as e:
                logger.debug(f"Basketball Reference lookup failed: {e}")

        logger.warning(f"No image URL found for {player_name}")
        return None
