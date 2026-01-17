"""NBA API client for player statistics and filtering.

DEPRECATED: This client is no longer used for player seeding.
Player data now comes from CSV (data/scoring.csv) via PlayerStatsCSVParser.

Preserved for potential future use:
- Real-time stats integration
- Career stats API access
- Player lookup by name

For player seeding, see: src/scrapers/player_stats_csv_parser.py
"""
import time
import logging
from typing import Optional, Dict, List
from collections import deque
from nba_api.stats.static import players

logger = logging.getLogger(__name__)


class NBAApiClient:
    """Client for NBA API player statistics and filtering.

    Responsibilities:
    - Find player IDs by name using nba_api
    - Access player career statistics
    - Filter players by games played, career minutes, etc.
    - Enforce rate limiting (default: 20 requests/minute)
    - Handle errors gracefully

    Note: Image handling is done by BasketballReferenceClient.
    """

    def __init__(
        self,
        rate_limit_per_minute: int = 20
    ):
        """Initialize NBA API client with rate limiting.

        Args:
            rate_limit_per_minute: Maximum API requests per minute
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_times: deque = deque()

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
