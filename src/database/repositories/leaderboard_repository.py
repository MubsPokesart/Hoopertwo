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
