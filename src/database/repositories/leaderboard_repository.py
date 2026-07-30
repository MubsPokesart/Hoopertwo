"""Repository for leaderboard database operations."""
import sqlite3
from datetime import date
from typing import List, Dict, Any, Optional


def _upsert_snapshot(
    connection: sqlite3.Connection,
    user_id: int,
    server_id: int,
    period: str,
    points: int,
    player_count: int,
    snapshot_date: date,
) -> None:
    """Write one snapshot row while preserving database errors."""
    try:
        connection.execute(
            """
            INSERT INTO leaderboard_snapshots
                (user_id, server_id, period, points, player_count, snapshot_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, server_id, period, snapshot_date)
            DO UPDATE SET
                points = excluded.points,
                player_count = excluded.player_count
            """,
            (user_id, server_id, period, points, player_count, snapshot_date),
        )
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise


class LeaderboardRepository:
    """Handles database operations for leaderboards.

    Responsibilities:
    - Create and update snapshots
    - Query rankings by period
    - Get user rank and stats
    - All operations use parameterized queries for security
    """

    PERIODS = ("weekly", "monthly", "yearly", "alltime")

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
        snapshot_date: date,
    ) -> bool:
        """Create or update one snapshot row."""
        _upsert_snapshot(
            self.connection,
            user_id,
            server_id,
            period,
            points,
            player_count,
            snapshot_date,
        )
        return True

    def replace_server_snapshots(
        self,
        server_id: int,
        snapshot_date: date,
        period_rankings: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, int]:
        """Atomically replace and publish every period for one server and date."""
        if set(period_rankings) != set(self.PERIODS):
            raise ValueError("Snapshot refresh must include every leaderboard period")

        rows = [
            (
                ranking["user_id"],
                server_id,
                period,
                ranking["total_points"],
                ranking["player_count"],
                snapshot_date,
            )
            for period in self.PERIODS
            for ranking in period_rankings[period]
        ]
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute(
                """
                DELETE FROM leaderboard_snapshots
                WHERE server_id = ? AND snapshot_date = ?
                """,
                (server_id, snapshot_date),
            )
            cursor.executemany(
                """
                INSERT INTO leaderboard_snapshots
                    (user_id, server_id, period, points, player_count, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            cursor.execute(
                """
                INSERT INTO leaderboard_snapshot_runs (server_id, snapshot_date)
                VALUES (?, ?)
                ON CONFLICT(server_id, snapshot_date)
                DO UPDATE SET published_at = CURRENT_TIMESTAMP
                """,
                (server_id, snapshot_date),
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            raise

        return {period: len(period_rankings[period]) for period in self.PERIODS}

    def get_rankings(
        self, server_id: int, period: str, limit: int = 100, offset: int = 0
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

        latest_date = self._get_latest_published_date(server_id)

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
            (server_id, period, latest_date, limit, offset),
        )

        columns = ["user_id", "points", "player_count", "rank"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_user_rank(self, user_id: int, server_id: int, period: str) -> Optional[Dict[str, Any]]:
        """Get a specific user's rank and stats.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            period: Time period to query

        Returns:
            Dictionary with rank, points, and player_count, or None if not found
        """
        cursor = self.connection.cursor()

        latest_date = self._get_latest_published_date(server_id)

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
            (server_id, period, latest_date, user_id),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {"rank": row[0], "points": row[1], "player_count": row[2]}

    def _get_latest_published_date(self, server_id: int) -> Optional[str]:
        """Get the latest date whose all-time cohort completed publication."""
        cursor = self.connection.execute(
            """
            SELECT MAX(snapshot_date)
            FROM leaderboard_snapshot_runs
            WHERE server_id = ?
            """,
            (server_id,),
        )
        return cursor.fetchone()[0]
