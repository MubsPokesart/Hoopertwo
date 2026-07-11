"""Repository for user collection database operations."""
import sqlite3
from typing import Optional, List, Dict, Any

# Rarity point values
RARITY_POINTS = {
    "GOAT": 1000,
    "Mythic": 500,
    "Legendary": 250,
    "Epic": 100,
    "Rare": 50,
    "Uncommon": 25,
    "Common": 10
}


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
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO user_collections (user_id, player_id, server_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, player_id, server_id) DO NOTHING
            """,
            (user_id, player_id, server_id)
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def get_user_collection(
        self,
        user_id: int,
        server_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = "time_new"
    ) -> List[Dict[str, Any]]:
        """Get a user's collection with player details.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            limit: Maximum number of players to return (None for all)
            offset: Number of players to skip for pagination
            sort_by: Sort order - "time_new", "time_old", "rarity_best", "rarity_common"

        Returns:
            List of dictionaries containing player data
        """
        cursor = self.connection.cursor()

        # Define sort orders (validated to prevent SQL injection)
        # For rarity sorting, use CASE to order by tier, then by ADP within tier
        sort_orders = {
            "time_new": "uc.caught_at DESC",
            "time_old": "uc.caught_at ASC",
            "rarity_best": """CASE p.rarity_tier
                WHEN 'GOAT' THEN 1
                WHEN 'Mythic' THEN 2
                WHEN 'Legendary' THEN 3
                WHEN 'Epic' THEN 4
                WHEN 'Rare' THEN 5
                WHEN 'Uncommon' THEN 6
                WHEN 'Common' THEN 7
                ELSE 8
            END ASC, p.adp_value ASC""",
            "rarity_common": """CASE p.rarity_tier
                WHEN 'GOAT' THEN 1
                WHEN 'Mythic' THEN 2
                WHEN 'Legendary' THEN 3
                WHEN 'Epic' THEN 4
                WHEN 'Rare' THEN 5
                WHEN 'Uncommon' THEN 6
                WHEN 'Common' THEN 7
                ELSE 8
            END DESC, p.adp_value DESC"""
        }

        # Default to time_new if invalid sort_by provided
        order_clause = sort_orders.get(sort_by, sort_orders["time_new"])

        query = f"""
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
            ORDER BY {order_clause}
        """

        params: tuple = (user_id, server_id)

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = (user_id, server_id, limit, offset)

        cursor.execute(query, params)

        columns = ["id", "name", "rarity_tier", "adp_value", "image_url", "caught_at"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_collection_stats(
        self,
        user_id: int,
        server_id: int
    ) -> Dict[str, Any]:
        """Get statistics about a user's collection.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID

        Returns:
            Dictionary with total_players, total_points, and rarity_counts
        """
        cursor = self.connection.cursor()

        # Get total count and rarity breakdown
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                p.rarity_tier,
                COUNT(*) as tier_count
            FROM user_collections uc
            JOIN players p ON uc.player_id = p.id
            WHERE uc.user_id = ? AND uc.server_id = ?
            GROUP BY p.rarity_tier
            """,
            (user_id, server_id)
        )

        rarity_counts = {}
        total_players = 0
        total_points = 0

        for row in cursor.fetchall():
            tier_count = row[2]
            rarity_tier = row[1]
            rarity_counts[rarity_tier] = tier_count
            total_players += tier_count
            total_points += tier_count * RARITY_POINTS.get(rarity_tier, 0)

        return {
            "total_players": total_players,
            "total_points": total_points,
            "rarity_counts": rarity_counts
        }

    def get_all_server_users(self, server_id: int) -> List[Dict[str, Any]]:
        """Get stats for all users in a server.

        Args:
            server_id: Discord server ID

        Returns:
            List of dictionaries with user_id, total_points, and player_count
        """
        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                uc.user_id,
                COUNT(*) as player_count,
                SUM(
                    CASE p.rarity_tier
                        WHEN 'GOAT' THEN 1000
                        WHEN 'Mythic' THEN 500
                        WHEN 'Legendary' THEN 250
                        WHEN 'Epic' THEN 100
                        WHEN 'Rare' THEN 50
                        WHEN 'Uncommon' THEN 25
                        WHEN 'Common' THEN 10
                        ELSE 0
                    END
                ) as total_points
            FROM user_collections uc
            JOIN players p ON uc.player_id = p.id
            WHERE uc.server_id = ?
            GROUP BY uc.user_id
            """,
            (server_id,)
        )

        columns = ["user_id", "player_count", "total_points"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
