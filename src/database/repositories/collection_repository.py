"""Repository for user collection database operations."""
import sqlite3
from typing import Optional, List, Dict, Any


class CollectionRepository:
    """Handles database operations for user collections.

    Responsibilities:
    - Add players to user collections
    - Query user collections
    - Get collection statistics
    - All operations use parameterized queries for security
    """

    def __init__(self, connection: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            connection: SQLite database connection
        """
        self.connection = connection

    def add_player_to_collection(
        self,
        user_id: int,
        player_id: int,
        server_id: int
    ) -> bool:
        """Add a player to a user's collection.

        Args:
            user_id: Discord user ID
            player_id: Player database ID
            server_id: Discord server ID

        Returns:
            True if added successfully, False if already owned
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO user_collections (user_id, player_id, server_id)
                VALUES (?, ?, ?)
                """,
                (user_id, player_id, server_id)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            # Unique constraint violation - already owned
            return False

    def get_user_collection(
        self,
        user_id: int,
        server_id: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get a user's collection with player details.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            limit: Maximum number of players to return (None for all)
            offset: Number of players to skip for pagination

        Returns:
            List of dictionaries containing player data
        """
        cursor = self.connection.cursor()

        query = """
            SELECT
                p.id,
                p.name,
                p.rarity_tier,
                p.adp_value,
                p.image_url,
                uc.caught_at
            FROM user_collections uc
            JOIN players p ON uc.player_id = p.id
            WHERE uc.user_id = ? AND uc.server_id = ?
            ORDER BY uc.caught_at DESC
        """

        params: tuple = (user_id, server_id)

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = (user_id, server_id, limit, offset)

        cursor.execute(query, params)

        columns = ["id", "name", "rarity_tier", "adp_value", "image_url", "caught_at"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
