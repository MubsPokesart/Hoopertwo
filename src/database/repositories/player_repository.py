"""Player repository for database operations.

All queries use parameterized statements to prevent SQL injection.
"""
from typing import Optional, List, Dict, Any
from src.database.connection_manager import ConnectionManager
from src.utils.text_normalizer import TextNormalizer


class PlayerRepository:
    """Repository for player data operations.

    Responsibilities:
    - CRUD operations for players table
    - Parameterized queries only (SQL injection prevention)
    - Name normalization for lookups
    """

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize repository with database connection.

        Args:
            connection_manager: Database connection manager
        """
        self.conn = connection_manager.get_connection()

    def create_player(
        self,
        name: str,
        adp_value: Optional[float],
        rarity_tier: str,
        image_url: Optional[str],
        career_minutes: Optional[int] = None
    ) -> int:
        """Create a new player record.

        Args:
            name: Player's full name
            adp_value: Average draft position value (if on ADP board)
            rarity_tier: One of: GOAT, Mythic, Legendary, Epic, Rare, Common
            image_url: Basketball Reference image URL
            career_minutes: Total career minutes played

        Returns:
            ID of created player
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO players (name, adp_value, rarity_tier, image_url, career_minutes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, adp_value, rarity_tier, image_url, career_minutes)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_player_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get player by name with normalization.

        Args:
            name: Player name (case/accent/punctuation insensitive)

        Returns:
            Player dict or None if not found
        """
        normalized_search = TextNormalizer.normalize(name)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players")

        # Search with normalized comparison
        for row in cursor.fetchall():
            row_dict = self._row_to_dict(cursor, row)
            if TextNormalizer.normalize(row_dict["name"]) == normalized_search:
                return row_dict

        return None

    def get_all_players(self) -> List[Dict[str, Any]]:
        """Get all players.

        Returns:
            List of player dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players ORDER BY name")
        return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def get_players_by_rarity(self, rarity_tier: str) -> List[Dict[str, Any]]:
        """Get all players of a specific rarity tier.

        Args:
            rarity_tier: Rarity tier to filter by

        Returns:
            List of player dicts
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM players WHERE rarity_tier = ? ORDER BY name",
            (rarity_tier,)
        )
        return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        """Convert database row to dictionary.

        Args:
            cursor: Database cursor (for column names)
            row: Database row tuple

        Returns:
            Dictionary with column names as keys
        """
        return {
            col[0]: row[idx]
            for idx, col in enumerate(cursor.description)
        }
