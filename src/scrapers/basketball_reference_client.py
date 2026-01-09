"""Basketball Reference scraper client with rate limiting.

Fetches player headshot images from Basketball Reference using a database
of verified player IDs. Provides fallback when NBA CDN images are unavailable.
"""
import time
import logging
import json
from pathlib import Path
from typing import Optional, Dict
from collections import deque
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BasketballReferenceClient:
    """Client for Basketball Reference player image scraping.

    Responsibilities:
    - Look up player IDs from verified database
    - Construct Basketball Reference URLs
    - Parse player headshot images from HTML
    - Enforce rate limiting to avoid blocks
    - Handle errors gracefully

    Image URL format: https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg
    """

    def __init__(
        self,
        player_id_db_path: str = "data/player_ids.json",
        rate_limit_per_minute: int = 10,
        base_url: str = "https://www.basketball-reference.com"
    ):
        """Initialize Basketball Reference client with rate limiting.

        Args:
            player_id_db_path: Path to player ID database JSON file
            rate_limit_per_minute: Maximum requests per minute (conservative for BR)
            base_url: Base URL for Basketball Reference
        """
        self.player_id_db_path = player_id_db_path
        self.rate_limit_per_minute = rate_limit_per_minute
        self.base_url = base_url
        self.request_times: deque = deque()
        self._player_id_cache: Optional[Dict] = None

    def _load_player_id_database(self) -> Dict:
        """Load player ID database from JSON file.

        Returns:
            Dictionary with verified and estimated player IDs

        Raises:
            FileNotFoundError: If database file doesn't exist
        """
        if self._player_id_cache is not None:
            return self._player_id_cache

        db_path = Path(self.player_id_db_path)
        if not db_path.exists():
            logger.warning(f"Player ID database not found at {self.player_id_db_path}")
            return {"verified": {}, "estimated": {}, "needs_verification": []}

        with open(db_path, 'r', encoding='utf-8') as f:
            self._player_id_cache = json.load(f)

        logger.info(
            f"Loaded player ID database: "
            f"{len(self._player_id_cache['verified'])} verified, "
            f"{len(self._player_id_cache['estimated'])} estimated"
        )
        return self._player_id_cache

    def find_player_id(self, player_name: str) -> Optional[str]:
        """Find Basketball Reference player ID by name.

        Searches verified IDs first, then estimated IDs.

        Args:
            player_name: Full player name (e.g., "LeBron James")

        Returns:
            Player ID (e.g., "jamesle01") or None if not found
        """
        db = self._load_player_id_database()

        # Check verified IDs first
        if player_name in db["verified"]:
            return db["verified"][player_name]["player_id"]

        # Check estimated IDs
        if player_name in db["estimated"]:
            logger.debug(f"Using estimated ID for {player_name}")
            return db["estimated"][player_name]["player_id"]

        logger.warning(f"No player ID found for {player_name}")
        return None

    def construct_player_url(self, player_id: str) -> str:
        """Construct Basketball Reference player page URL.

        Args:
            player_id: Basketball Reference player ID (e.g., "jamesle01")

        Returns:
            Full URL to player page
        """
        first_letter = player_id[0]
        return f"{self.base_url}/players/{first_letter}/{player_id}.html"

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting by waiting if necessary.

        More conservative than NBA API to avoid 403 blocks.
        """
        current_time = time.time()

        # Remove requests older than 60 seconds
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()

        # If at rate limit, wait until we can make another request
        if len(self.request_times) >= self.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self._enforce_rate_limit()  # Recheck after sleeping

        # Record this request time
        self.request_times.append(time.time())

    def _parse_image_from_html(self, html_content: str) -> Optional[str]:
        """Parse player image URL from Basketball Reference HTML.

        Looks for: div#meta > div.media-item > img

        Args:
            html_content: HTML content of player page

        Returns:
            Image URL if found, None otherwise
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find div with id="meta"
            meta_div = soup.find('div', id='meta')
            if not meta_div:
                logger.debug("No meta div found in HTML")
                return None

            # Find div with class="media-item" inside meta
            media_item = meta_div.find('div', class_='media-item')
            if not media_item:
                logger.debug("No media-item div found")
                return None

            # Find img tag inside media-item
            img = media_item.find('img')
            if not img:
                logger.debug("No img tag found in media-item")
                return None

            # Extract src attribute
            img_url = img.get('src')
            if img_url:
                # Convert to absolute URL if relative
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = self.base_url + img_url

            return img_url

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None

    def scrape_player_image_url(self, player_id: str) -> Optional[str]:
        """Scrape player image URL from Basketball Reference.

        Args:
            player_id: Basketball Reference player ID

        Returns:
            Image URL if found, None otherwise
        """
        self._enforce_rate_limit()

        url = self.construct_player_url(player_id)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.basketball-reference.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            image_url = self._parse_image_from_html(response.text)

            if image_url:
                logger.info(f"Successfully scraped image for player ID {player_id}")
            else:
                logger.warning(f"No image found for player ID {player_id}")

            return image_url

        except requests.RequestException as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None

    def get_player_image_url(self, player_name: str) -> Optional[str]:
        """Get player image URL by name (convenience method).

        Combines player ID lookup and image scraping.

        Args:
            player_name: Full player name

        Returns:
            Image URL or None if not found
        """
        player_id = self.find_player_id(player_name)
        if player_id is None:
            return None

        return self.scrape_player_image_url(player_id)

    def parse_image_from_html_file(self, html_file_path: str) -> Optional[str]:
        """Parse image URL from a saved HTML file (for offline testing).

        Args:
            html_file_path: Path to HTML file

        Returns:
            Image URL if found, None otherwise
        """
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return self._parse_image_from_html(html_content)
        except Exception as e:
            logger.error(f"Failed to read HTML file: {e}")
            return None
