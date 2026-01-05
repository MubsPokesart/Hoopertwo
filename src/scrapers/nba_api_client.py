"""NBA API client with rate limiting.

Fetches player data from NBA.com official API and constructs
CDN image URLs. Uses nba_api library for API access.
"""
import time
import logging
from typing import Optional, Dict, List
from collections import deque
from nba_api.stats.static import players

logger = logging.getLogger(__name__)


class NBAApiClient:
    """Client for NBA API with image URL construction.

    Responsibilities:
    - Find player IDs by name using nba_api
    - Construct NBA CDN image URLs from player IDs
    - Enforce rate limiting (default: 20 requests/minute)
    - Handle errors gracefully

    Image URL format: https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png
    """

    def __init__(
        self,
        rate_limit_per_minute: int = 20,
        cdn_base_url: str = "https://cdn.nba.com/headshots/nba/latest/1040x760"
    ):
        """Initialize NBA API client with rate limiting.

        Args:
            rate_limit_per_minute: Maximum API requests per minute
            cdn_base_url: Base URL for NBA CDN images
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self.cdn_base_url = cdn_base_url
        self.request_times: deque = deque()

    def construct_image_url(self, player_id: int) -> str:
        """Construct NBA CDN image URL from player ID.

        Args:
            player_id: NBA player ID (e.g., 2544 for LeBron James)

        Returns:
            Full CDN URL to player headshot image
        """
        return f"{self.cdn_base_url}/{player_id}.png"

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting by waiting if necessary."""
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

    def _get_all_players(self) -> List[Dict]:
        """Get all NBA players from nba_api static data.

        Returns:
            List of player dictionaries with id and full_name
        """
        return players.get_players()

    def _api_find_player(self, player_name: str) -> Optional[int]:
        """Internal method to find player ID (for testing/mocking).

        Args:
            player_name: Full player name

        Returns:
            Player ID or None if not found
        """
        player_dict = players.find_players_by_full_name(player_name)
        if player_dict:
            return player_dict[0]['id']
        return None

    def find_player_id(self, player_name: str) -> Optional[int]:
        """Find NBA player ID by name with rate limiting.

        Args:
            player_name: Full player name (e.g., "LeBron James")

        Returns:
            Player ID or None if not found
        """
        self._enforce_rate_limit()

        try:
            return self._api_find_player(player_name)
        except Exception as e:
            logger.error(f"Failed to find player {player_name}: {e}")
            return None

    def get_player_image_url(self, player_name: str) -> Optional[str]:
        """Get player image URL by finding player ID and constructing CDN URL.

        Args:
            player_name: Full player name

        Returns:
            CDN image URL or None if player not found
        """
        player_id = self.find_player_id(player_name)
        if player_id is None:
            return None

        return self.construct_image_url(player_id)
