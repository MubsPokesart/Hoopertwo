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
