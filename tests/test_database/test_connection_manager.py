import pytest
import sqlite3
from pathlib import Path
from src.database.connection_manager import ConnectionManager
from src.database.migrations import migrate_schema


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
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]

    assert "players" in table_names
    assert "user_collections" in table_names
    assert "server_configs" in table_names
    assert "leaderboard_snapshots" in table_names
    assert "leaderboard_snapshot_runs" in table_names

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
        ("Test Player", 10.0, "Mythic", "http://example.com/image.jpg"),
    )
    conn.commit()

    # Fetch with parameterized query
    result = cursor.execute("SELECT name FROM players WHERE name = ?", ("Test Player",)).fetchone()

    assert result[0] == "Test Player"
    manager.close()


def test_connection_manager_migrates_existing_database_with_verified_backup(temp_db_path, tmp_path):
    """Explicit offline migration preserves catches and creates a verified backup."""
    connection = sqlite3.connect(temp_db_path)
    connection.executescript(
        """
        CREATE TABLE players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            adp_value REAL,
            rarity_tier TEXT NOT NULL CHECK(
                rarity_tier IN (
                    'GOAT', 'Mythic', 'Legendary', 'Epic',
                    'Rare', 'Uncommon', 'Common'
                )
            ),
            image_url TEXT,
            career_minutes INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE user_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            server_id INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
            UNIQUE(user_id, player_id, server_id)
        );
        CREATE TABLE server_configs (
            server_id INTEGER PRIMARY KEY,
            spawn_channels TEXT NOT NULL DEFAULT '[]',
            spawn_threshold INTEGER NOT NULL DEFAULT 500,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE leaderboard_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            period TEXT NOT NULL CHECK(period IN ('weekly', 'monthly', 'yearly', 'alltime')),
            points INTEGER NOT NULL DEFAULT 0,
            player_count INTEGER NOT NULL DEFAULT 0,
            snapshot_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, server_id, period, snapshot_date)
        );
        INSERT INTO players
            (id, name, adp_value, rarity_tier, image_url, career_minutes, created_at)
        VALUES
            (7, 'Kevin Garnett', 4.05, 'Mythic', 'https://example.com/kg.jpg', 51370,
             '2026-01-25 02:22:54');
        INSERT INTO user_collections
            (id, user_id, player_id, caught_at, server_id)
        VALUES (9, 123, 7, '2026-07-01 12:34:56', 456);
        """
    )
    connection.close()

    with pytest.raises(RuntimeError, match="offline migration"):
        ConnectionManager(temp_db_path, str(tmp_path / "automatic-backups"))

    backup_directory = tmp_path / "migration-backups"
    migrated = sqlite3.connect(temp_db_path, isolation_level=None)
    migrated.execute("PRAGMA foreign_keys = ON")
    migrate_schema(
        migrated,
        temp_db_path,
        str(backup_directory),
        allow_upgrade=True,
    )

    assert migrated.execute("PRAGMA user_version").fetchone() == (1,)
    assert migrated.execute("SELECT id, rarity_tier FROM players WHERE id = 7").fetchone() == (
        7,
        "Cosmic",
    )
    assert (
        migrated.execute(
            """
        SELECT id, user_id, player_id, caught_at, server_id, edition
        FROM user_collections
        """
        ).fetchone()
        == (9, 123, 7, "2026-07-01 12:34:56", 456, "Standard")
    )

    migrated.execute(
        """
        INSERT INTO user_collections (user_id, player_id, server_id, edition)
        VALUES (?, ?, ?, ?)
        """,
        (123, 7, 456, "Phantom"),
    )
    migrated.commit()
    assert migrated.execute("SELECT COUNT(*) FROM user_collections").fetchone() == (2,)
    assert migrated.execute("PRAGMA foreign_key_check").fetchall() == []

    backups = list(backup_directory.glob("test_pre_v1_*.db"))
    assert len(backups) == 1
    backup = sqlite3.connect(backups[0])
    assert backup.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert backup.execute("SELECT rarity_tier FROM players WHERE id = 7").fetchone() == ("Mythic",)
    backup.close()
    migrated.close()
