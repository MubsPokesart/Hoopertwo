import pytest
import sqlite3
from src.database.repositories.server_config_repository import ServerConfigRepository
from src.database.connection_manager import ConnectionManager


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()
    yield conn
    manager.close()


def test_get_or_create_config_new_server(db_connection):
    """Test getting config for a new server creates defaults."""
    repo = ServerConfigRepository(db_connection)

    config = repo.get_or_create_config(server_id=987654321)

    assert config is not None
    assert config["server_id"] == 987654321
    assert config["spawn_threshold"] == 500  # Default
    assert config["spawn_channels"] == []  # Default empty list


def test_update_spawn_threshold(db_connection):
    """Test updating spawn threshold."""
    repo = ServerConfigRepository(db_connection)

    # Create config
    repo.get_or_create_config(987654321)

    # Update threshold
    result = repo.update_spawn_threshold(
        server_id=987654321,
        threshold=300
    )

    assert result is True

    # Verify update
    config = repo.get_or_create_config(987654321)
    assert config["spawn_threshold"] == 300


def test_update_spawn_channels(db_connection):
    """Test updating spawn channels list."""
    repo = ServerConfigRepository(db_connection)

    # Create config
    repo.get_or_create_config(987654321)

    # Update channels
    channel_ids = [111111, 222222, 333333]
    result = repo.update_spawn_channels(
        server_id=987654321,
        channel_ids=channel_ids
    )

    assert result is True

    # Verify update
    config = repo.get_or_create_config(987654321)
    assert config["spawn_channels"] == channel_ids
    assert len(config["spawn_channels"]) == 3
