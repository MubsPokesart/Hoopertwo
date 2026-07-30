"""Repository for user collection database operations."""
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Rarity point values
RARITY_POINTS = {
    "GOAT": 1000,
    "Cosmic": 750,
    "Mythic": 500,
    "Legendary": 250,
    "Epic": 100,
    "Rare": 50,
    "Uncommon": 25,
    "Common": 10,
}
PHANTOM_BONUS = 150


def _effective_points_sql() -> str:
    """Build SQL scoring from the same constants used by collection stats."""
    cases = "\n".join(f"WHEN '{rarity}' THEN {points}" for rarity, points in RARITY_POINTS.items())
    return f"""
    (
        CASE p.rarity_tier
            {cases}
            ELSE 0
        END
        + CASE uc.edition WHEN 'Phantom' THEN {PHANTOM_BONUS} ELSE 0 END
    )
    """


def _format_utc_timestamp(timestamp: datetime) -> str:
    """Convert an aware datetime to SQLite's UTC timestamp format."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Leaderboard boundaries must be timezone-aware")
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _build_capture_window(
    server_id: int,
    caught_after: Optional[datetime],
    caught_before: Optional[datetime],
) -> tuple[str, List[Any]]:
    """Build the fixed leaderboard filter and its bound parameters."""
    clauses = ["uc.server_id = ?"]
    params: List[Any] = [server_id]
    if caught_after is not None:
        clauses.append("uc.caught_at >= ?")
        params.append(_format_utc_timestamp(caught_after))
    if caught_before is not None:
        clauses.append("uc.caught_at < ?")
        params.append(_format_utc_timestamp(caught_before))
    return " AND ".join(clauses), params


def _get_server_collection_totals(
    connection: sqlite3.Connection,
    server_id: int,
    caught_after: Optional[datetime],
    caught_before: Optional[datetime],
) -> List[Dict[str, Any]]:
    """Aggregate leaderboard points for captures inside a UTC window."""
    where_clause, params = _build_capture_window(
        server_id,
        caught_after,
        caught_before,
    )
    effective_points_sql = _effective_points_sql()
    cursor = connection.execute(
        f"""
        SELECT
            uc.user_id,
            COUNT(*) as player_count,
            SUM({effective_points_sql}) as total_points
        FROM user_collections uc
        JOIN players p ON uc.player_id = p.id
        WHERE {where_clause}
        GROUP BY uc.user_id
        ORDER BY uc.user_id
        """,
        params,
    )
    columns = ["user_id", "player_count", "total_points"]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


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
        server_id: int,
        edition: str = "Standard",
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
            INSERT INTO user_collections (user_id, player_id, server_id, edition)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, player_id, server_id, edition) DO NOTHING
            """,
            (user_id, player_id, server_id, edition),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def get_user_collection(
        self,
        user_id: int,
        server_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = "time_new",
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
        effective_points_sql = _effective_points_sql()
        sort_orders = {
            "time_new": "uc.caught_at DESC",
            "time_old": "uc.caught_at ASC",
            "rarity_best": (f"{effective_points_sql} DESC, p.adp_value ASC, p.name ASC"),
            "rarity_common": (f"{effective_points_sql} ASC, p.adp_value DESC, p.name ASC"),
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
                uc.caught_at,
                uc.edition,
                {effective_points_sql} AS effective_points
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

        columns = [
            "id",
            "name",
            "rarity_tier",
            "adp_value",
            "image_url",
            "caught_at",
            "edition",
            "effective_points",
        ]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_collection_stats(self, user_id: int, server_id: int) -> Dict[str, Any]:
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
                p.rarity_tier,
                uc.edition,
                COUNT(*) as tier_count
            FROM user_collections uc
            JOIN players p ON uc.player_id = p.id
            WHERE uc.user_id = ? AND uc.server_id = ?
            GROUP BY p.rarity_tier, uc.edition
            """,
            (user_id, server_id),
        )

        rarity_counts = {}
        total_players = 0
        total_points = 0
        phantom_count = 0

        for row in cursor.fetchall():
            rarity_tier, edition, tier_count = row
            rarity_counts[rarity_tier] = rarity_counts.get(rarity_tier, 0) + tier_count
            total_players += tier_count
            total_points += tier_count * RARITY_POINTS.get(rarity_tier, 0)
            if edition == "Phantom":
                phantom_count += tier_count
                total_points += tier_count * PHANTOM_BONUS

        return {
            "total_players": total_players,
            "total_points": total_points,
            "rarity_counts": rarity_counts,
            "phantom_count": phantom_count,
        }

    def get_all_server_users(
        self,
        server_id: int,
        caught_after: Optional[datetime] = None,
        caught_before: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get stats for users with captures inside an optional UTC window.

        Args:
            server_id: Discord server ID
            caught_after: Inclusive UTC capture boundary
            caught_before: Exclusive UTC capture boundary

        Returns:
            List of dictionaries with user_id, total_points, and player_count
        """
        return _get_server_collection_totals(
            self.connection,
            server_id,
            caught_after,
            caught_before,
        )
