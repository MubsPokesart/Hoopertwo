"""Fixtures for integration tests."""
import pytest
import tempfile
from pathlib import Path
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.database.repositories.collection_repository import CollectionRepository
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.repositories.server_config_repository import ServerConfigRepository
from src.managers.player_manager import PlayerManager
from src.managers.collection_manager import CollectionManager
from src.managers.leaderboard_manager import LeaderboardManager
from src.managers.config_manager import ConfigManager
from src.managers.spawn_manager import SpawnManager


@pytest.fixture
def temp_db():
    """Create temporary database with all tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        manager = ConnectionManager(str(db_path))
        conn = manager.get_connection()

        yield {
            "connection": conn,
            "manager": manager,
            "path": str(db_path)
        }

        manager.close()


@pytest.fixture
def all_repositories(temp_db):
    """Create all repository instances."""
    conn = temp_db["connection"]

    return {
        "player": PlayerRepository(temp_db["manager"]),
        "collection": CollectionRepository(conn),
        "leaderboard": LeaderboardRepository(conn),
        "config": ServerConfigRepository(conn)
    }


@pytest.fixture
def all_managers(all_repositories):
    """Create all manager instances."""
    repos = all_repositories

    return {
        "player": PlayerManager(repos["player"], "data/adp_board.csv"),
        "collection": CollectionManager(repos["collection"]),
        "leaderboard": LeaderboardManager(repos["leaderboard"], repos["collection"]),
        "config": ConfigManager(repos["config"]),
        "spawn": SpawnManager(repos["player"])
    }
