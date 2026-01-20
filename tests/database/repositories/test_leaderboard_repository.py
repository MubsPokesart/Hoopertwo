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
