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
        career_minutes: Optional[int] = None,
    ) -> int:
        """Create a new player record.

        Args:
            name: Player's full name
            adp_value: Average draft position value (if on ADP board)
            rarity_tier: One of: GOAT, Cosmic, Mythic, Legendary, Epic, Rare,
                Uncommon, Common
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
            (name, adp_value, rarity_tier, image_url, career_minutes),
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
        cursor.execute("SELECT * FROM players WHERE rarity_tier = ? ORDER BY name", (rarity_tier,))
        return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def update_player_image(self, name: str, image_url: str) -> bool:
        """Update a player's image URL.

        Args:
            name: Player's full name
            image_url: New image URL

        Returns:
            True if player was found and updated, False otherwise
        """
        player = self.get_player_by_name(name)
        if not player:
            return False

        cursor = self.conn.cursor()
        cursor.execute("UPDATE players SET image_url = ? WHERE id = ?", (image_url, player["id"]))
        self.conn.commit()
        return True

    def update_player_rarity(self, player_id: int, rarity_tier: str) -> bool:
        """Update a player's rarity tier.

        Args:
            player_id: Player's database ID
            rarity_tier: New rarity tier

        Returns:
            True if update successful
        """
        cursor = self.conn.cursor()
        cursor.execute("UPDATE players SET rarity_tier = ? WHERE id = ?", (rarity_tier, player_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_players_with_adp(self) -> List[Dict[str, Any]]:
        """Get all players that have an ADP value.

        Returns:
            List of player dicts with non-null ADP values
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players WHERE adp_value IS NOT NULL ORDER BY adp_value")
        return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        """Convert database row to dictionary.

        Args:
            cursor: Database cursor (for column names)
            row: Database row tuple

        Returns:
            Dictionary with column names as keys
        """
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
