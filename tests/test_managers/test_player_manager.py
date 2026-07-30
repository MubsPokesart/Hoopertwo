import pytest
import csv
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
    with open(csv_path, "w", newline="") as f:
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
    assert player_manager.calculate_rarity_tier(1.41) == "GOAT"
    assert player_manager.calculate_rarity_tier(1.90) == "GOAT"
    assert player_manager.calculate_rarity_tier(1.99) == "GOAT"


def test_calculate_rarity_tier_cosmic(player_manager):
    """Test Cosmic boundaries (2 <= ADP < 10)."""
    assert player_manager.calculate_rarity_tier(2.0) == "Cosmic"
    assert player_manager.calculate_rarity_tier(4.54) == "Cosmic"
    assert player_manager.calculate_rarity_tier(9.99) == "Cosmic"


def test_calculate_rarity_tier_mythic(player_manager):
    """Test rarity calculation for Mythic tier (10 <= ADP < 33)."""
    assert player_manager.calculate_rarity_tier(10.0) == "Mythic"
    assert player_manager.calculate_rarity_tier(30.31) == "Mythic"
    assert player_manager.calculate_rarity_tier(32.99) == "Mythic"


def test_calculate_rarity_tier_legendary(player_manager):
    """Test rarity calculation for Legendary tier (33 <= ADP < 75)."""
    assert player_manager.calculate_rarity_tier(33.0) == "Legendary"
    assert player_manager.calculate_rarity_tier(74.99) == "Legendary"


def test_calculate_rarity_tier_epic(player_manager):
    """Test rarity calculation for Epic tier (75 <= ADP < 155.25)."""
    assert player_manager.calculate_rarity_tier(75.0) == "Epic"
    assert player_manager.calculate_rarity_tier(120.0) == "Epic"
    assert player_manager.calculate_rarity_tier(155.24) == "Epic"


def test_calculate_rarity_tier_rare(player_manager):
    """Test rarity calculation for Rare tier (155.25 <= ADP < 260.1)."""
    assert player_manager.calculate_rarity_tier(155.25) == "Rare"
    assert player_manager.calculate_rarity_tier(250.0) == "Rare"
    assert player_manager.calculate_rarity_tier(260.09) == "Rare"


def test_calculate_rarity_tier_uncommon(player_manager):
    """Test rarity calculation for Uncommon tier (ADP >= 260.1)."""
    assert player_manager.calculate_rarity_tier(260.1) == "Uncommon"
    assert player_manager.calculate_rarity_tier(1000.0) == "Uncommon"


def test_calculate_rarity_tier_common(player_manager):
    """Test rarity calculation for Common tier (no ADP value)."""
    # Only None should return Common now
    assert player_manager.calculate_rarity_tier(None) == "Common"


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
    assert curry["rarity_tier"] == "Cosmic"

    dirk = player_manager.repository.get_player_by_name("Dirk Nowitzki")
    assert dirk["rarity_tier"] == "Mythic"

    walton = player_manager.repository.get_player_by_name("Bill Walton")
    assert walton["rarity_tier"] == "Epic"

    random = player_manager.repository.get_player_by_name("Random Player")
    assert random["rarity_tier"] == "Rare"

    bench = player_manager.repository.get_player_by_name("Bench Warmer")
    assert bench["rarity_tier"] == "Rare"
