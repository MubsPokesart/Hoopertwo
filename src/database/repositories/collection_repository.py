"""Repository for user collection database operations."""
import sqlite3
from typing import Optional


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
