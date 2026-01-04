import sqlite3
import pytest
from pathlib import Path
from src.database.connection_manager import ConnectionManager


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    return str(tmp_path / "test.db")


def test_connection_manager_creates_database(temp_db_path):
    """Test that ConnectionManager creates database file."""
    manager = ConnectionManager(temp_db_path)

    assert Path(temp_db_path).exists()
    manager.close()


def test_connection_manager_initializes_schema(temp_db_path):
    """Test that ConnectionManager creates all required tables."""
    manager = ConnectionManager(temp_db_path)

    cursor = manager.get_connection().cursor()

    # Check that tables exist
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t[0] for t in tables]

    assert "players" in table_names
    assert "user_collections" in table_names
    assert "server_configs" in table_names
    assert "leaderboard_snapshots" in table_names

    manager.close()


def test_connection_manager_enables_foreign_keys(temp_db_path):
    """Test that foreign key constraints are enabled."""
    manager = ConnectionManager(temp_db_path)

    cursor = manager.get_connection().cursor()
    result = cursor.execute("PRAGMA foreign_keys").fetchone()

    assert result[0] == 1  # Foreign keys enabled
    manager.close()


def test_connection_manager_uses_parameterized_queries(temp_db_path):
    """Test that parameterized queries work (SQL injection prevention)."""
    manager = ConnectionManager(temp_db_path)
    conn = manager.get_connection()
    cursor = conn.cursor()

    # Insert with parameterized query
    cursor.execute(
        "INSERT INTO players (name, adp_value, rarity_tier, image_url) VALUES (?, ?, ?, ?)",
        ("Test Player", 10.0, "Mythic", "http://example.com/image.jpg")
    )
    conn.commit()

    # Fetch with parameterized query
    result = cursor.execute(
        "SELECT name FROM players WHERE name = ?",
        ("Test Player",)
    ).fetchone()

    assert result[0] == "Test Player"
    manager.close()
