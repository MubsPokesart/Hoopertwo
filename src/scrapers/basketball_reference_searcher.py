"""Basketball Reference search for player ID collision resolution using nodriver.

This module provides automated searching of Basketball Reference to resolve player ID
collisions. When multiple players share the same name pattern (e.g., Mikal Bridges and
Miles Bridges both generate 'bridgmi01'), this searcher uses year ranges to find the
correct player ID from Basketball Reference's search results.

Key Features:
- Automated Cloudflare bypass via nodriver
- Year range matching to disambiguate players
- Rate limiting (2.5-3s between requests)
- Browser instance reuse for efficiency
- Retry logic with exponential backoff
- Async/await pattern for concurrent operations

Performance:
- Only used for collision cases (~1-2% of players)
- ~3-5s per search
- Results cached in player_ids.json for subsequent runs
"""

import asyncio
import logging
import time
import re
from typing import Optional, Tuple
from bs4 import BeautifulSoup

try:
    import nodriver as uc
except ImportError:
    raise ImportError(
        "nodriver is required for Basketball Reference searching. "
        "Install with: poetry add nodriver"
    )


logger = logging.getLogger(__name__)


class BasketballReferenceSearcher:
    """Search Basketball Reference to resolve player ID collisions.

    This class uses nodriver to search Basketball Reference and parse search results
    to find the correct player ID when multiple players have similar names. Uses
    year ranges to disambiguate players.

    Usage:
        searcher = BasketballReferenceSearcher(rate_limit_delay=2.5)
        player_id = await searcher.search_player_by_name_and_years(
            "Jim Paxson", 1980, 1990
        )
        await searcher.close()

    Attributes:
        _browser: Nodriver browser instance (lazy-initialized)
        _rate_limit_delay: Seconds to wait between search requests
        _last_request_time: Timestamp of last search request
        _search_base_url: Basketball Reference search endpoint
        _logger: Logger instance for debugging
    """

    def __init__(
        self,
        rate_limit_delay: float = 2.5,
        search_base_url: str = "https://www.basketball-reference.com/search/search.fcgi"
    ):
        """Initialize searcher with rate limiting.

        Args:
            rate_limit_delay: Seconds to wait between search requests.
                             Default 2.5s balances speed and Cloudflare safety.
            search_base_url: Basketball Reference search endpoint URL
        """
        self._browser: Optional[uc.Browser] = None
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0
        self._search_base_url = search_base_url
        self._logger = logging.getLogger(__name__)

    async def search_player_by_name_and_years(
        self,
        player_name: str,
        year_start: int,
        year_end: int,
        max_retries: int = 3
    ) -> Optional[str]:
        """Search Basketball Reference for correct player ID using year range.

        Searches Basketball Reference by player name and filters results by year range
        to find the correct player ID. This resolves collisions where multiple players
        share the same ID pattern.

        Args:
            player_name: Full player name (e.g., "Jim Paxson")
            year_start: First year of player's career
            year_end: Last year of player's career
            max_retries: Number of retry attempts for transient failures

        Returns:
            Player ID (e.g., "paxsoji02") or None if not found

        Raises:
            Exception: Only after max_retries exhausted (logged and returns None)
        """
        # Enforce rate limiting
        await self._enforce_rate_limit_async()

        # Lazy-initialize browser on first use
        if self._browser is None:
            self._browser = await uc.start()
            self._logger.info("Nodriver browser initialized for Basketball Reference search")

        # Try with exponential backoff
        for attempt in range(max_retries):
            try:
                result = await self._search_and_parse(
                    player_name, year_start, year_end
                )
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    self._logger.warning(
                        f"Search failed (attempt {attempt+1}/{max_retries}), "
                        f"retrying in {backoff}s: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    self._logger.error(
                        f"Search failed after {max_retries} attempts for {player_name}: {e}"
                    )
                    return None

        return None

    async def _search_and_parse(
        self,
        player_name: str,
        year_start: int,
        year_end: int
    ) -> Optional[str]:
        """Execute search and parse results for matching player ID.

        Args:
            player_name: Full player name
            year_start: First year of player's career
            year_end: Last year of player's career

        Returns:
            Player ID if found and year range matches, None otherwise

        Raises:
            Exception: Network errors, navigation failures, parsing errors
        """
        if self._browser is None:
            raise RuntimeError("Browser not initialized")

        tab = await self._browser.get()

        try:
            # Construct search URL with player name query
            search_url = f"{self._search_base_url}?search={player_name.replace(' ', '+')}"
            self._logger.debug(f"Searching: {search_url}")

            # Navigate to search results
            await tab.get(search_url)

            # Wait for page to load (Basketball Reference search is dynamic)
            await asyncio.sleep(1.0)

            # Get page HTML content
            page_content = await tab.get_content()

            # Parse HTML to find matching player
            player_id = self._parse_search_results(
                page_content, player_name, year_start, year_end
            )

            if player_id:
                self._logger.info(
                    f"Found player ID for {player_name} ({year_start}-{year_end}): {player_id}"
                )
            else:
                self._logger.warning(
                    f"No matching player ID found for {player_name} ({year_start}-{year_end})"
                )

            return player_id

        except Exception as e:
            self._logger.error(f"Error searching for {player_name}: {e}")
            raise

    def _parse_search_results(
        self,
        html: str,
        target_name: str,
        year_start: int,
        year_end: int
    ) -> Optional[str]:
        """Parse Basketball Reference search results HTML to extract player ID.

        Basketball Reference search returns results in a specific format:
        - Player links: /players/[first_letter]/[player_id].html
        - Year ranges shown as: "YYYY-YYYY" in the result text

        This method:
        1. Finds all player result links matching the name pattern
        2. Extracts year ranges from result text
        3. Matches year ranges with target player's career span
        4. Returns the player ID for the best match

        Args:
            html: Raw HTML content from Basketball Reference search page
            target_name: Player name being searched for
            year_start: Target player's first year
            year_end: Target player's last year

        Returns:
            Player ID (e.g., "paxsoji02") or None if no match found
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find player search results
            # Basketball Reference uses a search_item class for results
            search_items = soup.find_all('div', class_='search-item')

            if not search_items:
                # Try alternative structure - direct redirect to player page
                # If there's only one perfect match, BR redirects directly to player page
                if '/players/' in html:
                    # Check if we're on a player page (redirected from search)
                    player_id_match = re.search(r'/players/[a-z]/([a-z]+\d+)\.html', html)
                    if player_id_match:
                        player_id = player_id_match.group(1)
                        self._logger.debug(f"Found player ID from redirect: {player_id}")
                        return player_id

                self._logger.warning(f"No search results found for {target_name}")
                return None

            # Parse each search result
            for item in search_items:
                # Extract player link
                link = item.find('a', href=re.compile(r'/players/[a-z]/[a-z]+\d+\.html'))
                if not link:
                    continue

                # Extract player ID from URL
                player_id_match = re.search(r'/players/[a-z]/([a-z]+\d+)\.html', link['href'])
                if not player_id_match:
                    continue

                player_id = player_id_match.group(1)

                # Extract year range from result text
                # Format: "Player Name (YYYY-YYYY)" or similar
                item_text = item.get_text()
                year_match = re.search(r'(\d{4})-(\d{4})', item_text)

                if year_match:
                    result_year_start = int(year_match.group(1))
                    result_year_end = int(year_match.group(2))

                    # Check if year ranges overlap or match
                    # Allow for slight mismatches due to data source differences
                    overlap = (
                        (year_start <= result_year_end + 1) and
                        (year_end >= result_year_start - 1)
                    )

                    if overlap:
                        self._logger.debug(
                            f"Matched {target_name}: {player_id} "
                            f"(target: {year_start}-{year_end}, "
                            f"found: {result_year_start}-{result_year_end})"
                        )
                        return player_id

            # No match found
            self._logger.debug(
                f"No year range match for {target_name} ({year_start}-{year_end}) "
                f"in {len(search_items)} results"
            )
            return None

        except Exception as e:
            self._logger.error(f"Error parsing search results for {target_name}: {e}")
            return None

    async def _enforce_rate_limit_async(self):
        """Ensure minimum delay between search requests.

        Enforces rate limiting by sleeping if needed to maintain the
        configured delay between search requests. This prevents
        triggering Basketball Reference's Cloudflare rate limits.
        """
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - elapsed
            await asyncio.sleep(sleep_time)
        self._last_request_time = time.time()

    async def close(self):
        """Cleanup browser resources.

        Must be called when done with searching to properly close
        the browser instance and free resources.

        Usage:
            searcher = BasketballReferenceSearcher()
            try:
                player_id = await searcher.search_player_by_name_and_years(name, start, end)
            finally:
                await searcher.close()
        """
        if self._browser:
            try:
                # Check if browser has stop method (may be None if never initialized)
                if hasattr(self._browser, 'stop') and callable(self._browser.stop):
                    await self._browser.stop()
                    self._logger.info("Basketball Reference searcher browser closed")
                else:
                    self._logger.debug("Browser object exists but has no stop method")
            except Exception as e:
                self._logger.error(f"Error closing searcher browser: {e}")
            finally:
                self._browser = None
