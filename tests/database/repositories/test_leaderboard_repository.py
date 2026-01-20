import pytest
import sqlite3
from datetime import date
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.connection_manager import ConnectionManager


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()

    # Insert test player
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("LeBron James", 1.5, "GOAT")
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
        snapshot_date=date(2026, 1, 18)
    )

    assert result is True

    # Verify snapshot was created
    cursor = db_connection.execute(
        "SELECT user_id, points, player_count, period FROM leaderboard_snapshots WHERE user_id = ?",
        (123456789,)
    )
    row = cursor.fetchone()
    assert row == (123456789, 1500, 3, "weekly")


def test_get_rankings(db_connection):
    """Test retrieving rankings for a period."""
    repo = LeaderboardRepository(db_connection)

    # Create multiple snapshots
    snapshot_date = date(2026, 1, 18)
    repo.create_snapshot(123, 987, "weekly", 1500, 3, snapshot_date)
    repo.create_snapshot(456, 987, "weekly", 2000, 4, snapshot_date)
    repo.create_snapshot(789, 987, "weekly", 1000, 2, snapshot_date)

    # Get rankings
    rankings = repo.get_rankings(
        server_id=987,
        period="weekly",
        limit=10
    )

    assert len(rankings) == 3
    # Should be sorted by points descending
    assert rankings[0]["user_id"] == 456
    assert rankings[0]["points"] == 2000
    assert rankings[0]["rank"] == 1
    assert rankings[1]["user_id"] == 123
    assert rankings[1]["rank"] == 2


def test_get_user_rank(db_connection):
    """Test getting a specific user's rank."""
    repo = LeaderboardRepository(db_connection)

    snapshot_date = date(2026, 1, 18)
    repo.create_snapshot(123, 987, "weekly", 1500, 3, snapshot_date)
    repo.create_snapshot(456, 987, "weekly", 2000, 4, snapshot_date)
    repo.create_snapshot(789, 987, "weekly", 1000, 2, snapshot_date)

    # Get rank for middle user
    user_rank = repo.get_user_rank(
        user_id=123,
        server_id=987,
        period="weekly"
    )

    assert user_rank is not None
    assert user_rank["rank"] == 2
    assert user_rank["points"] == 1500
    assert user_rank["player_count"] == 3
