import pytest
from unittest.mock import patch
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
    repo.create_player("Curry", 5.0, "Cosmic", None)
    repo.create_player("Durant", 10.0, "Mythic", None)
    repo.create_player("Legendary1", 40.0, "Legendary", None)
    repo.create_player("Epic1", 100.0, "Epic", None)
    repo.create_player("Rare1", 200.0, "Rare", None)
    repo.create_player("Uncommon1", 260.0, "Uncommon", None)
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
    assert player["edition"] in ("Standard", "Phantom")


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
    assert weight == 25


def test_calculate_spawn_weight_uncommon(spawn_manager):
    """Test spawn weight for Uncommon tier."""
    weight = spawn_manager._calculate_spawn_weight("Uncommon")
    assert weight == 12500


def test_calculate_spawn_weight_common(spawn_manager):
    """Test spawn weight for Common tier."""
    weight = spawn_manager._calculate_spawn_weight("Common")
    assert weight == 65000


def test_calculate_spawn_weight_tiers(spawn_manager):
    """Test relative spawn weights across tiers."""
    goat = spawn_manager._calculate_spawn_weight("GOAT")
    cosmic = spawn_manager._calculate_spawn_weight("Cosmic")
    mythic = spawn_manager._calculate_spawn_weight("Mythic")
    legendary = spawn_manager._calculate_spawn_weight("Legendary")
    epic = spawn_manager._calculate_spawn_weight("Epic")
    rare = spawn_manager._calculate_spawn_weight("Rare")
    uncommon = spawn_manager._calculate_spawn_weight("Uncommon")
    common = spawn_manager._calculate_spawn_weight("Common")

    # Weights should increase (more common = higher weight)
    assert goat < cosmic < mythic < legendary < epic < rare < uncommon < common


def test_spawn_weights_are_exact_percentages(spawn_manager):
    assert spawn_manager.SPAWN_WEIGHTS == {
        "GOAT": 25,
        "Cosmic": 100,
        "Mythic": 375,
        "Legendary": 2000,
        "Epic": 7500,
        "Rare": 9500,
        "Uncommon": 12500,
        "Common": 65000,
        "Phantom": 3000,
    }
    assert sum(spawn_manager.SPAWN_WEIGHTS.values()) == 100000


def test_phantom_selects_uniformly_from_entire_player_bank(spawn_manager):
    all_players = spawn_manager.repository.get_all_players()

    with patch("src.managers.spawn_manager.random.choices", return_value=["Phantom"]):
        with patch(
            "src.managers.spawn_manager.random.choice",
            return_value=all_players[0],
        ) as choose_player:
            selected = spawn_manager.select_random_player()

    choose_player.assert_called_once_with(all_players)
    assert selected["edition"] == "Phantom"


def test_runtime_spawn_weights_keep_exact_denominator(spawn_manager):
    with patch(
        "src.managers.spawn_manager.random.choices",
        return_value=["Common"],
    ) as choose_bucket:
        spawn_manager.select_random_player()

    buckets = choose_bucket.call_args.args[0]
    weights = choose_bucket.call_args.kwargs["weights"]
    assert buckets == list(spawn_manager.SPAWN_WEIGHTS)
    assert sum(weights) == 100000


def test_missing_base_tier_fails_instead_of_distorting_probabilities(temp_db):
    temp_db.get_connection().execute(
        "DELETE FROM players WHERE rarity_tier = ?",
        ("Legendary",),
    )
    manager = SpawnManager(PlayerRepository(temp_db))

    with pytest.raises(
        ValueError,
        match="Player bank is missing spawn tiers: Legendary",
    ):
        manager.select_random_player()
