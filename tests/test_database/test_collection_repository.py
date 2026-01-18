import pytest
import sqlite3
from src.database.repositories.collection_repository import CollectionRepository
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


def test_add_player_to_collection_success(db_connection):
    """Test adding a player to a user's collection."""
    repo = CollectionRepository(db_connection)

    # Add player to collection
    result = repo.add_player_to_collection(
        user_id=123456789,
        player_id=1,
        server_id=987654321
    )

    assert result is True

    # Verify it was added
    cursor = db_connection.execute(
        "SELECT user_id, player_id, server_id FROM user_collections WHERE user_id = ?",
        (123456789,)
    )
    row = cursor.fetchone()
    assert row == (123456789, 1, 987654321)


def test_add_player_to_collection_duplicate(db_connection):
    """Test that adding the same player twice returns False."""
    repo = CollectionRepository(db_connection)

    # Add player first time
    result1 = repo.add_player_to_collection(
        user_id=123456789,
        player_id=1,
        server_id=987654321
    )
    assert result1 is True

    # Try to add same player again
    result2 = repo.add_player_to_collection(
        user_id=123456789,
        player_id=1,
        server_id=987654321
    )
    assert result2 is False

    # Verify only one entry exists
    cursor = db_connection.execute(
        "SELECT COUNT(*) FROM user_collections WHERE user_id = ? AND player_id = ?",
        (123456789, 1)
    )
    count = cursor.fetchone()[0]
    assert count == 1
