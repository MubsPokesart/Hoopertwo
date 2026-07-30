import sqlite3
from datetime import date
from unittest.mock import Mock

import pytest

from src.database.connection_manager import ConnectionManager
from src.database.repositories.leaderboard_repository import LeaderboardRepository


def complete_rankings(**period_rankings):
    """Build a complete four-period snapshot payload."""
    rankings = {
        "weekly": [],
        "monthly": [],
        "yearly": [],
        "alltime": [],
    }
    rankings.update(period_rankings)
    return rankings


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("LeBron James", 1.5, "GOAT"),
    )
    conn.commit()

    yield conn
    manager.close()


def test_create_snapshot(db_connection):
    """Test creating a leaderboard snapshot."""
    repo = LeaderboardRepository(db_connection)

    result = repo.create_snapshot(
        user_id=123456789,
        server_id=987654321,
        period="weekly",
        points=1500,
        player_count=3,
        snapshot_date=date(2026, 1, 18),
    )

    assert result is True
    row = db_connection.execute(
        """
        SELECT user_id, points, player_count, period
        FROM leaderboard_snapshots
        WHERE user_id = ?
        """,
        (123456789,),
    ).fetchone()
    assert row == (123456789, 1500, 3, "weekly")


def test_create_snapshot_propagates_database_errors(db_connection):
    """Test invalid snapshots are not reported as successful writes."""
    repo = LeaderboardRepository(db_connection)

    with pytest.raises(sqlite3.IntegrityError):
        repo.create_snapshot(
            user_id=123,
            server_id=987,
            period="daily",
            points=100,
            player_count=1,
            snapshot_date=date(2026, 1, 18),
        )


def test_get_rankings(db_connection):
    """Test retrieving rankings from the latest completed run."""
    repo = LeaderboardRepository(db_connection)
    repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=date(2026, 1, 18),
        period_rankings=complete_rankings(
            weekly=[
                {"user_id": 123, "total_points": 1500, "player_count": 3},
                {"user_id": 456, "total_points": 2000, "player_count": 4},
                {"user_id": 789, "total_points": 1000, "player_count": 2},
            ],
        ),
    )

    rankings = repo.get_rankings(server_id=987, period="weekly", limit=10)

    assert len(rankings) == 3
    assert rankings[0]["user_id"] == 456
    assert rankings[0]["points"] == 2000
    assert rankings[0]["rank"] == 1
    assert rankings[1]["user_id"] == 123
    assert rankings[1]["rank"] == 2


def test_get_user_rank(db_connection):
    """Test getting a specific user's rank."""
    repo = LeaderboardRepository(db_connection)
    repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=date(2026, 1, 18),
        period_rankings=complete_rankings(
            weekly=[
                {"user_id": 123, "total_points": 1500, "player_count": 3},
                {"user_id": 456, "total_points": 2000, "player_count": 4},
                {"user_id": 789, "total_points": 1000, "player_count": 2},
            ],
        ),
    )

    user_rank = repo.get_user_rank(user_id=123, server_id=987, period="weekly")

    assert user_rank == {"rank": 2, "points": 1500, "player_count": 3}


def test_replace_server_snapshots_removes_stale_same_day_users(db_connection):
    """Test a refresh replaces every cohort for the same date."""
    repo = LeaderboardRepository(db_connection)
    snapshot_date = date(2026, 7, 11)
    repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=snapshot_date,
        period_rankings=complete_rankings(
            weekly=[
                {"user_id": 123, "total_points": 1500, "player_count": 3},
                {"user_id": 456, "total_points": 2000, "player_count": 4},
            ],
        ),
    )

    counts = repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=snapshot_date,
        period_rankings=complete_rankings(
            weekly=[
                {"user_id": 123, "total_points": 1000, "player_count": 1},
            ],
        ),
    )

    assert counts == {"weekly": 1, "monthly": 0, "yearly": 0, "alltime": 0}
    rows = db_connection.execute(
        """
        SELECT user_id, points, player_count
        FROM leaderboard_snapshots
        WHERE server_id = ? AND period = ? AND snapshot_date = ?
        """,
        (987, "weekly", snapshot_date),
    ).fetchall()
    assert rows == [(123, 1000, 1)]


def test_failed_same_day_refresh_keeps_previous_periods(db_connection):
    """Test a failed refresh rolls every period back to its prior generation."""
    repo = LeaderboardRepository(db_connection)
    snapshot_date = date(2026, 7, 11)
    repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=snapshot_date,
        period_rankings=complete_rankings(
            weekly=[
                {"user_id": 123, "total_points": 1000, "player_count": 1},
            ],
            monthly=[
                {"user_id": 123, "total_points": 1500, "player_count": 2},
            ],
        ),
    )
    invalid_rankings = complete_rankings(
        weekly=[{"user_id": 456, "total_points": 2000, "player_count": 2}],
        monthly=[{"user_id": 456, "total_points": None, "player_count": 2}],
    )

    with pytest.raises(sqlite3.IntegrityError):
        repo.replace_server_snapshots(987, snapshot_date, invalid_rankings)

    weekly = repo.get_rankings(server_id=987, period="weekly")
    monthly = repo.get_rankings(server_id=987, period="monthly")
    assert [(entry["user_id"], entry["points"]) for entry in weekly] == [(123, 1000)]
    assert [(entry["user_id"], entry["points"]) for entry in monthly] == [(123, 1500)]


def test_commit_failure_rolls_back_shared_connection():
    """Test commit errors cannot leave the shared connection in a transaction."""
    connection = Mock()
    connection.commit.side_effect = sqlite3.OperationalError("commit failed")
    repo = LeaderboardRepository(connection)

    with pytest.raises(sqlite3.OperationalError, match="commit failed"):
        repo.replace_server_snapshots(
            server_id=987,
            snapshot_date=date(2026, 7, 11),
            period_rankings=complete_rankings(),
        )

    connection.rollback.assert_called_once_with()


def test_published_empty_run_does_not_fall_back_to_old_snapshot(db_connection):
    """Test a fully empty current run does not return stale rows."""
    repo = LeaderboardRepository(db_connection)
    repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=date(2026, 7, 10),
        period_rankings=complete_rankings(
            weekly=[
                {"user_id": 123, "total_points": 1000, "player_count": 1},
            ],
            alltime=[
                {"user_id": 123, "total_points": 1000, "player_count": 1},
            ],
        ),
    )

    repo.replace_server_snapshots(
        server_id=987,
        snapshot_date=date(2026, 7, 11),
        period_rankings=complete_rankings(),
    )

    assert repo.get_rankings(server_id=987, period="weekly") == []
    assert repo.get_user_rank(user_id=123, server_id=987, period="weekly") is None
