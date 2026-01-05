import pytest
import csv
from pathlib import Path
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.managers.player_manager import PlayerManager


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database."""
    db_path = str(tmp_path / "test.db")
    manager = ConnectionManager(db_path)
    yield manager
    manager.close()


@pytest.fixture
def test_csv(tmp_path):
    """Create temporary ADP CSV file for testing."""
    csv_path = tmp_path / "test_adp.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Player", "ADP (31-)"])
        writer.writerow(["Michael Jordan", "1.41"])
        writer.writerow(["LeBron James", "1.90"])
        writer.writerow(["Stephen Curry", "4.54"])
        writer.writerow(["Luka Doncic", "30.31"])
        writer.writerow(["Dirk Nowitzki", "32.06"])
        writer.writerow(["Pau Gasol", "60.50"])
        writer.writerow(["Bill Walton", "120.00"])
        writer.writerow(["Random Player", "250.00"])
        writer.writerow(["Bench Warmer", "260.00"])
    return str(csv_path)


@pytest.fixture
def player_manager(temp_db, test_csv):
    """Create PlayerManager with test database."""
    repo = PlayerRepository(temp_db)
    return PlayerManager(repo, test_csv)


def test_calculate_rarity_tier_goat(player_manager):
    """Test rarity calculation for GOAT tier (ADP < 2)."""
    assert player_manager._calculate_rarity_tier(1.41) == "GOAT"
    assert player_manager._calculate_rarity_tier(1.90) == "GOAT"
    assert player_manager._calculate_rarity_tier(1.99) == "GOAT"


def test_calculate_rarity_tier_mythic(player_manager):
    """Test rarity calculation for Mythic tier (2 <= ADP < 32)."""
    assert player_manager._calculate_rarity_tier(2.0) == "Mythic"
    assert player_manager._calculate_rarity_tier(4.54) == "Mythic"
    assert player_manager._calculate_rarity_tier(30.31) == "Mythic"
    assert player_manager._calculate_rarity_tier(31.99) == "Mythic"


def test_calculate_rarity_tier_legendary(player_manager):
    """Test rarity calculation for Legendary tier (32 <= ADP < 64)."""
    assert player_manager._calculate_rarity_tier(32.0) == "Legendary"
    assert player_manager._calculate_rarity_tier(32.06) == "Legendary"
    assert player_manager._calculate_rarity_tier(63.99) == "Legendary"


def test_calculate_rarity_tier_epic(player_manager):
    """Test rarity calculation for Epic tier (64 <= ADP < 128)."""
    assert player_manager._calculate_rarity_tier(64.0) == "Epic"
    assert player_manager._calculate_rarity_tier(120.0) == "Epic"
    assert player_manager._calculate_rarity_tier(127.99) == "Epic"


def test_calculate_rarity_tier_rare(player_manager):
    """Test rarity calculation for Rare tier (128 <= ADP < 256)."""
    assert player_manager._calculate_rarity_tier(128.0) == "Rare"
    assert player_manager._calculate_rarity_tier(250.0) == "Rare"
    assert player_manager._calculate_rarity_tier(255.99) == "Rare"


def test_calculate_rarity_tier_common(player_manager):
    """Test rarity calculation for Common tier (ADP >= 256 or None)."""
    assert player_manager._calculate_rarity_tier(256.0) == "Common"
    assert player_manager._calculate_rarity_tier(1000.0) == "Common"
    assert player_manager._calculate_rarity_tier(None) == "Common"


def test_load_adp_board(player_manager):
    """Test loading ADP board from CSV."""
    player_manager.load_adp_board()

    # Check that players were loaded
    all_players = player_manager.repository.get_all_players()
    assert len(all_players) == 9

    # Check specific players and rarity tiers
    mj = player_manager.repository.get_player_by_name("Michael Jordan")
    assert mj["rarity_tier"] == "GOAT"
    assert mj["adp_value"] == 1.41

    curry = player_manager.repository.get_player_by_name("Stephen Curry")
    assert curry["rarity_tier"] == "Mythic"

    dirk = player_manager.repository.get_player_by_name("Dirk Nowitzki")
    assert dirk["rarity_tier"] == "Legendary"

    walton = player_manager.repository.get_player_by_name("Bill Walton")
    assert walton["rarity_tier"] == "Epic"

    random = player_manager.repository.get_player_by_name("Random Player")
    assert random["rarity_tier"] == "Rare"

    bench = player_manager.repository.get_player_by_name("Bench Warmer")
    assert bench["rarity_tier"] == "Common"
