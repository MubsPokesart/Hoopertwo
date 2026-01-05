"""Image manager for downloading and caching player images."""
import logging
from pathlib import Path
from typing import Optional
import aiohttp
from src.scrapers.nba_api_client import NBAApiClient

logger = logging.getLogger(__name__)


class ImageManager:
    """Manager for player image downloading and caching.

    Responsibilities:
    - Download player images from NBA CDN
    - Cache images locally to avoid re-downloads
    - Handle download failures gracefully
    """

    def __init__(self, nba_client: NBAApiClient, cache_dir: str):
        """Initialize image manager.

        Args:
            nba_client: NBA API client instance
            cache_dir: Directory to cache downloaded images
        """
        self.nba_client = nba_client
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

    def download_player_image(self, player_name: str, image_url: str) -> bool:
        """Download and cache a player's image.

        Args:
            player_name: Full player name
            image_url: URL to download image from

        Returns:
            True if download successful, False otherwise
        """
        if self.is_cached(player_name):
            logger.debug(f"Image already cached for {player_name}")
            return True

        try:
            save_path = self.get_cached_image_path(player_name)
            self._download_from_url(image_url, save_path)
            logger.info(f"Downloaded image for {player_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to download image for {player_name}: {e}")
            return False
