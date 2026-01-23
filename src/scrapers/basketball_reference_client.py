
"""Basketball Reference client for player image URLs.

Provides direct Basketball Reference image URLs using a database of verified
player IDs. Primary source for all player images in HooperTwo.
"""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class BasketballReferenceClient:
    """Client for Basketball Reference player images (primary source).

    Responsibilities:
    - Look up player IDs from verified database or generate using BR naming convention
    - Construct direct Basketball Reference image URLs
    - NO verification (Cloudflare blocks automated requests)

    Image URL format: https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg

    Note: Returns direct image URLs without verification. Cloudflare protection prevents
    automated HEAD/GET requests. Invalid URLs will 404 when Discord bot displays them.
    """

    def __init__(
        self,
        player_id_db_path: str = "data/player_ids.json",
        base_url: str = "https://www.basketball-reference.com"
    ):
        """Initialize Basketball Reference client.

        Args:
            player_id_db_path: Path to player ID database JSON file
            base_url: Base URL for Basketball Reference
        """
        self.player_id_db_path = player_id_db_path
        self.base_url = base_url
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

    async def find_player_id(
        self,
        player_name: str,
        year_range: Optional[Tuple[int, int]] = None,
        searcher: Optional['BasketballReferenceSearcher'] = None
    ) -> Optional[str]:
        """Find Basketball Reference player ID by name.

        4-tier lookup system:
        1. Verified database (highest confidence)
        2. Estimated database
        3. Generated ID with collision check
        4. Basketball Reference search (if collision detected and searcher provided)

        Args:
            player_name: Full player name (e.g., "LeBron James")
            year_range: Optional tuple of (year_start, year_end) for collision resolution
            searcher: Optional BasketballReferenceSearcher instance for collision resolution

        Returns:
            Player ID (e.g., "jamesle01") or None if not found
        """
        db = self._load_player_id_database()

        # Tier 1: Check verified IDs first
        if player_name in db["verified"]:
            return db["verified"][player_name]["player_id"]

        # Tier 2: Check estimated IDs
        if player_name in db["estimated"]:
            logger.debug(f"Using estimated ID for {player_name}")
            return db["estimated"][player_name]["player_id"]

        # Tier 3: Generate ID and check for collisions
        generated_player_id = self.generate_player_id(player_name)
        if generated_player_id:
            # Check if this generated ID might collide with another player
            has_collision = self._has_collision(player_name, generated_player_id)

            if has_collision:
                logger.warning(
                    f"Collision detected for {player_name} -> {generated_player_id}"
                )

                # Tier 4: Use searcher to resolve collision if available
                if searcher and year_range:
                    logger.info(
                        f"Searching Basketball Reference to resolve collision for {player_name}"
                    )
                    try:
                        searched_id = await searcher.search_player_by_name_and_years(
                            player_name, year_range[0], year_range[1]
                        )
                        if searched_id:
                            logger.info(
                                f"Resolved collision via search: {player_name} -> {searched_id}"
                            )
                            return searched_id
                        else:
                            logger.warning(
                                f"Search failed to resolve collision for {player_name}, "
                                f"using generated ID: {generated_player_id}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error during collision resolution search for {player_name}: {e}"
                        )
                        # Fallback to generated ID
                else:
                    logger.warning(
                        f"Collision detected but no searcher/year_range provided, "
                        f"using generated ID: {generated_player_id}"
                    )

            logger.debug(
                f"Using Basketball Reference naming convention for {player_name}: "
                f"{generated_player_id}"
            )
            return generated_player_id

        logger.warning(f"No player ID found for {player_name}")
        return None
    
    def _has_collision(self, player_name: str, generated_id: str) -> bool:
        """Check if generated ID might collide with another player.

        A collision occurs when the same ID is already associated with a different
        player name in the verified or estimated databases.

        Args:
            player_name: Player name being checked
            generated_id: Generated Basketball Reference ID

        Returns:
            True if collision detected, False otherwise
        """
        db = self._load_player_id_database()

        # Check both verified and estimated categories
        for category in ['verified', 'estimated']:
            if category not in db:
                continue

            for name, data in db[category].items():
                # Skip if it's the same player
                if name == player_name:
                    continue

                # Check if same ID is used for different player
                if data.get('player_id') == generated_id:
                    logger.debug(
                        f"Collision detected: {player_name} -> {generated_id} "
                        f"conflicts with {name}"
                    )
                    return True

        return False

    def generate_player_id(self, player_name: str) -> str:
        """
        Generate Basketball Reference player ID using their naming convention.
        Format: {last_name_5chars}{first_name_2chars}01

        Note: This is best-effort. Some players have suffixes (02, 03) or
        different patterns (Jr., Sr., III, etc.)
        """

        # Handle special cases
        name_parts = player_name.replace("'", "").replace(".", "").lower().split()

        # Remove common suffixes
        suffixes = ["jr", "sr", "ii", "iii", "iv"]
        name_parts = [p for p in name_parts if p not in suffixes]

        if len(name_parts) < 2:
            return None

        first_name = name_parts[0]
        last_name = name_parts[-1]

        # Generate ID
        last_5 = last_name[:5]
        first_2 = first_name[:2]
        player_id = f"{last_5}{first_2}01"

        return player_id

    def construct_player_url(self, player_id: str) -> str:
        """Construct Basketball Reference player page URL.

        Args:
            player_id: Basketball Reference player ID (e.g., "jamesle01")

        Returns:
            Full URL to player page
        """
        first_letter = player_id[0]
        return f"{self.base_url}/players/{first_letter}/{player_id}.html"

    def construct_image_url(self, player_id: str) -> str:
        """Construct direct Basketball Reference image URL.

        Format: https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg

        Args:
            player_id: Basketball Reference player ID (e.g., "jordami01")

        Returns:
            Direct image URL
        """
        return f"https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg"

    async def get_player_image_url(
        self,
        player_name: str,
        year_range: Optional[Tuple[int, int]] = None,
        searcher: Optional['BasketballReferenceSearcher'] = None
    ) -> Optional[str]:
        """Get player image URL by name.

        NOTE: Returns constructed URL without verification due to Cloudflare protection.
        Invalid URLs will return 404 when accessed by Discord bot.

        Args:
            player_name: Full player name
            year_range: Optional tuple of (year_start, year_end) for collision resolution
            searcher: Optional BasketballReferenceSearcher instance for collision resolution

        Returns:
            Image URL if player ID found, None otherwise
        """
        # Look up player ID from database
        player_id = await self.find_player_id(player_name, year_range, searcher)
        if not player_id:
            logger.warning(f"No player ID found for {player_name}")
            return None

        # Construct direct image URL (no verification due to Cloudflare)
        image_url = self.construct_image_url(player_id)
        logger.info(f"Constructed image URL for {player_name}: {image_url}")
        return image_url
