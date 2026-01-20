"""Repository for leaderboard database operations."""
import sqlite3
from datetime import date
from typing import List, Dict, Any, Optional


class LeaderboardRepository:
    """Handles database operations for leaderboards.

    Responsibilities:
    - Create and update snapshots
    - Query rankings by period
    - Get user rank and stats
    - All operations use parameterized queries for security
    """

    def __init__(self, connection: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            connection: SQLite database connection
        """
        self.connection = connection

    def create_snapshot(
        self,
        user_id: int,
        server_id: int,
        period: str,
        points: int,
        player_count: int,
        snapshot_date: date
    ) -> bool:
        """Create a leaderboard snapshot for a user.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            period: Time period (weekly, monthly, yearly, alltime)
            points: Total points
            player_count: Total number of players
            snapshot_date: Date of snapshot

        Returns:
            True if created/updated successfully
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO leaderboard_snapshots
                    (user_id, server_id, period, points, player_count, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, server_id, period, snapshot_date)
                DO UPDATE SET
                    points = excluded.points,
                    player_count = excluded.player_count
                """,
                (user_id, server_id, period, points, player_count, snapshot_date)
            )
            self.connection.commit()
            return True
        except sqlite3.Error:
            return False

    def get_rankings(
        self,
        server_id: int,
        period: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get leaderboard rankings for a period.

        Args:
            server_id: Discord server ID
            period: Time period to query
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of dictionaries with rank, user_id, points, and player_count
        """
        cursor = self.connection.cursor()

        # Get latest snapshot date for this period
        cursor.execute(
            """
            SELECT MAX(snapshot_date) FROM leaderboard_snapshots
            WHERE server_id = ? AND period = ?
            """,
            (server_id, period)
        )
        latest_date = cursor.fetchone()[0]

        if not latest_date:
            return []

        # Get rankings for latest snapshot
        cursor.execute(
            """
            SELECT
                user_id,
                points,
                player_count,
                ROW_NUMBER() OVER (ORDER BY points DESC) as rank
            FROM leaderboard_snapshots
            WHERE server_id = ? AND period = ? AND snapshot_date = ?
            ORDER BY points DESC
            LIMIT ? OFFSET ?
            """,
            (server_id, period, latest_date, limit, offset)
        )

        columns = ["user_id", "points", "player_count", "rank"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_user_rank(
        self,
        user_id: int,
        server_id: int,
        period: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific user's rank and stats.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            period: Time period to query

        Returns:
            Dictionary with rank, points, and player_count, or None if not found
        """
        cursor = self.connection.cursor()

        # Get latest snapshot date
        cursor.execute(
            """
            SELECT MAX(snapshot_date) FROM leaderboard_snapshots
            WHERE server_id = ? AND period = ?
            """,
            (server_id, period)
        )
        latest_date = cursor.fetchone()[0]

        if not latest_date:
            return None

        # Get user's rank using subquery
        cursor.execute(
            """
            WITH ranked_users AS (
                SELECT
                    user_id,
                    points,
                    player_count,
                    ROW_NUMBER() OVER (ORDER BY points DESC) as rank
                FROM leaderboard_snapshots
                WHERE server_id = ? AND period = ? AND snapshot_date = ?
            )
            SELECT rank, points, player_count
            FROM ranked_users
            WHERE user_id = ?
            """,
            (server_id, period, latest_date, user_id)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "rank": row[0],
            "points": row[1],
            "player_count": row[2]
        }
