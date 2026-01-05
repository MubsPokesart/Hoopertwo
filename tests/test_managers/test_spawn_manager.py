import pytest
import csv
from pathlib import Path
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.managers.spawn_manager import SpawnManager


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database with test players."""
    db_path = str(tmp_path / "test.db")
    manager = ConnectionManager(db_path)
    repo = PlayerRepository(manager)

    # Add test players with different rarities
    repo.create_player("MJ", 1.0, "GOAT", None)
    repo.create_player("LBJ", 1.5, "GOAT", None)
    repo.create_player("Curry", 5.0, "Mythic", None)
    repo.create_player("Durant", 10.0, "Mythic", None)
    repo.create_player("Common1", None, "Common", None)
    repo.create_player("Common2", None, "Common", None)
    repo.create_player("Common3", None, "Common", None)

    yield manager
    manager.close()


@pytest.fixture
def spawn_manager(temp_db):
    """Create SpawnManager with test database."""
    repo = PlayerRepository(temp_db)
    return SpawnManager(repo)


def test_select_random_player_returns_player(spawn_manager):
    """Test that random player selection returns a valid player."""
    player = spawn_manager.select_random_player()

    assert player is not None
    assert "name" in player
    assert "rarity_tier" in player


def test_select_random_player_distribution(spawn_manager):
    """Test that rarity weighting affects spawn distribution."""
    # Select 1000 players and check distribution
    selections = [spawn_manager.select_random_player() for _ in range(1000)]

    goat_count = sum(1 for p in selections if p["rarity_tier"] == "GOAT")
    common_count = sum(1 for p in selections if p["rarity_tier"] == "Common")

    # GOAT should be rarer than Common (but not necessarily 0 GOATs)
    # With proper weighting, Common should appear more often
    assert common_count > goat_count


def test_calculate_spawn_weight_goat(spawn_manager):
    """Test spawn weight for GOAT tier."""
    weight = spawn_manager._calculate_spawn_weight("GOAT")
    assert weight == 1  # Lowest weight = rarest


def test_calculate_spawn_weight_common(spawn_manager):
    """Test spawn weight for Common tier."""
    weight = spawn_manager._calculate_spawn_weight("Common")
    assert weight == 100  # Highest weight = most common


def test_calculate_spawn_weight_tiers(spawn_manager):
    """Test relative spawn weights across tiers."""
    goat = spawn_manager._calculate_spawn_weight("GOAT")
    mythic = spawn_manager._calculate_spawn_weight("Mythic")
    legendary = spawn_manager._calculate_spawn_weight("Legendary")
    epic = spawn_manager._calculate_spawn_weight("Epic")
    rare = spawn_manager._calculate_spawn_weight("Rare")
    common = spawn_manager._calculate_spawn_weight("Common")

    # Weights should increase (more common = higher weight)
    assert goat < mythic < legendary < epic < rare < common
