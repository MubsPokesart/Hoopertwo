import pytest
import sqlite3
from datetime import datetime, timezone
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
        ("LeBron James", 1.5, "GOAT"),
    )
    conn.commit()

    yield conn
    manager.close()


def test_add_player_to_collection_success(db_connection):
    """Test adding a player to a user's collection."""
    repo = CollectionRepository(db_connection)

    # Add player to collection
    result = repo.add_player_to_collection(user_id=123456789, player_id=1, server_id=987654321)

    assert result is True

    # Verify it was added
    cursor = db_connection.execute(
        "SELECT user_id, player_id, server_id FROM user_collections WHERE user_id = ?", (123456789,)
    )
    row = cursor.fetchone()
    assert row == (123456789, 1, 987654321)


def test_add_player_to_collection_duplicate(db_connection):
    """Test that adding the same player twice returns False."""
    repo = CollectionRepository(db_connection)

    # Add player first time
    result1 = repo.add_player_to_collection(user_id=123456789, player_id=1, server_id=987654321)
    assert result1 is True

    # Try to add same player again
    result2 = repo.add_player_to_collection(user_id=123456789, player_id=1, server_id=987654321)
    assert result2 is False

    # Verify only one entry exists
    cursor = db_connection.execute(
        "SELECT COUNT(*) FROM user_collections WHERE user_id = ? AND player_id = ?", (123456789, 1)
    )
    count = cursor.fetchone()[0]
    assert count == 1


def test_add_player_to_collection_allows_standard_and_phantom(db_connection):
    """A user can own one copy of each edition of the same player."""
    repo = CollectionRepository(db_connection)

    assert repo.add_player_to_collection(123456789, 1, 987654321) is True
    assert (
        repo.add_player_to_collection(
            123456789,
            1,
            987654321,
            edition="Phantom",
        )
        is True
    )
    assert (
        repo.add_player_to_collection(
            123456789,
            1,
            987654321,
            edition="Phantom",
        )
        is False
    )


def test_add_player_to_collection_allows_same_player_in_different_server(db_connection):
    """Test that ownership remains scoped to each Discord server."""
    repo = CollectionRepository(db_connection)

    first_result = repo.add_player_to_collection(
        user_id=123456789, player_id=1, server_id=987654321
    )
    second_result = repo.add_player_to_collection(
        user_id=123456789, player_id=1, server_id=111222333
    )

    assert first_result is True
    assert second_result is True

    cursor = db_connection.execute(
        "SELECT COUNT(*) FROM user_collections WHERE user_id = ? AND player_id = ?", (123456789, 1)
    )
    assert cursor.fetchone()[0] == 2


def test_add_player_to_collection_raises_for_invalid_player(db_connection):
    """Test that unrelated integrity failures are not reported as duplicates."""
    repo = CollectionRepository(db_connection)

    with pytest.raises(sqlite3.IntegrityError):
        repo.add_player_to_collection(user_id=123456789, player_id=999, server_id=987654321)


def test_get_user_collection(db_connection):
    """Test retrieving a user's collection with player details."""
    # Add more test players
    db_connection.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Michael Jordan", 1.0, "GOAT"),
    )
    db_connection.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Steph Curry", 15.5, "Mythic"),
    )
    db_connection.commit()

    repo = CollectionRepository(db_connection)

    # Add players to collection
    repo.add_player_to_collection(123456789, 1, 987654321)
    repo.add_player_to_collection(123456789, 2, 987654321)

    # Get collection
    collection = repo.get_user_collection(user_id=123456789, server_id=987654321)

    assert len(collection) == 2
    assert collection[0]["name"] == "LeBron James"
    assert collection[0]["rarity_tier"] == "GOAT"
    assert collection[1]["name"] == "Michael Jordan"
    assert "caught_at" in collection[0]


def test_get_collection_stats(db_connection):
    """Test getting collection statistics."""
    # Add test player with Mythic tier
    db_connection.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Steph Curry", 15.5, "Mythic"),
    )
    db_connection.commit()

    repo = CollectionRepository(db_connection)

    # Add players to collection
    repo.add_player_to_collection(123456789, 1, 987654321)  # GOAT
    repo.add_player_to_collection(123456789, 2, 987654321)  # Mythic

    # Get stats
    stats = repo.get_collection_stats(user_id=123456789, server_id=987654321)

    assert stats["total_players"] == 2
    assert stats["total_points"] > 0
    assert "GOAT" in stats["rarity_counts"]
    assert stats["rarity_counts"]["GOAT"] == 1
    assert stats["rarity_counts"]["Mythic"] == 1
    assert stats["phantom_count"] == 0


def test_get_collection_stats_uncommon(db_connection):
    """Test collection stats with Uncommon tier players."""
    db_connection.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Vlade Divac", 258.36, "Uncommon"),
    )
    db_connection.commit()

    repo = CollectionRepository(db_connection)
    repo.add_player_to_collection(123456789, 2, 987654321)

    stats = repo.get_collection_stats(123456789, 987654321)
    assert stats["rarity_counts"]["Uncommon"] == 1
    assert stats["total_points"] == 25  # Verify 25 points for Uncommon


def test_phantom_bonus_and_cosmic_points(db_connection):
    db_connection.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Kevin Garnett", 4.05, "Cosmic"),
    )
    db_connection.commit()
    repo = CollectionRepository(db_connection)
    repo.add_player_to_collection(
        123456789,
        2,
        987654321,
        edition="Phantom",
    )

    stats = repo.get_collection_stats(123456789, 987654321)

    assert stats["total_points"] == 900
    assert stats["rarity_counts"] == {"Cosmic": 1}
    assert stats["phantom_count"] == 1
    assert repo.get_all_server_users(987654321) == [
        {"user_id": 123456789, "player_count": 1, "total_points": 900}
    ]


def test_rarity_sort_uses_effective_points(db_connection):
    players = [
        ("Epic Player", 100.0, "Epic"),
        ("Common Player", None, "Common"),
    ]
    db_connection.executemany(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        players,
    )
    db_connection.commit()
    repo = CollectionRepository(db_connection)
    repo.add_player_to_collection(123456789, 2, 987654321)
    repo.add_player_to_collection(
        123456789,
        3,
        987654321,
        edition="Phantom",
    )

    collection = repo.get_user_collection(
        123456789,
        987654321,
        sort_by="rarity_best",
    )

    assert [player["name"] for player in collection] == [
        "Common Player",
        "Epic Player",
    ]
    assert collection[0]["effective_points"] == 160


def test_get_all_server_users_filters_by_utc_capture_window(db_connection):
    """Test leaderboard aggregation uses inclusive start and exclusive end times."""
    players = [
        ("Before Window", 2.0, "Mythic"),
        ("At Window Start", 1.0, "GOAT"),
        ("Before Window End", 15.0, "Mythic"),
        ("At Window End", 40.0, "Legendary"),
        ("Other Server", 70.0, "Epic"),
    ]
    db_connection.executemany(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        players,
    )
    db_connection.executemany(
        """
        INSERT INTO user_collections (user_id, player_id, caught_at, server_id)
        VALUES (?, ?, ?, ?)
        """,
        [
            (111, 2, "2026-07-03 23:59:59", 987),
            (111, 3, "2026-07-04 00:00:00", 987),
            (222, 4, "2026-07-10 23:59:59", 987),
            (222, 5, "2026-07-11 00:00:00", 987),
            (333, 6, "2026-07-05 00:00:00", 654),
        ],
    )
    db_connection.commit()

    repo = CollectionRepository(db_connection)
    rankings = repo.get_all_server_users(
        server_id=987,
        caught_after=datetime(2026, 7, 4, tzinfo=timezone.utc),
        caught_before=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )

    assert rankings == [
        {"user_id": 111, "player_count": 1, "total_points": 1000},
        {"user_id": 222, "player_count": 1, "total_points": 500},
    ]


def test_get_all_server_users_all_time_still_respects_snapshot_boundary(db_connection):
    """Test all-time aggregation includes history but not later captures."""
    db_connection.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("Future Player", 15.0, "Mythic"),
    )
    db_connection.executemany(
        """
        INSERT INTO user_collections (user_id, player_id, caught_at, server_id)
        VALUES (?, ?, ?, ?)
        """,
        [
            (111, 1, "2020-01-01 00:00:00", 987),
            (222, 2, "2026-07-11 00:00:00", 987),
        ],
    )
    db_connection.commit()

    repo = CollectionRepository(db_connection)
    rankings = repo.get_all_server_users(
        server_id=987,
        caught_before=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )

    assert rankings == [{"user_id": 111, "player_count": 1, "total_points": 1000}]
