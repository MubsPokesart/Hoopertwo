import pytest
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = str(tmp_path / "test.db")
    manager = ConnectionManager(db_path)
    yield manager
    manager.close()


@pytest.fixture
def player_repo(temp_db):
    """Create PlayerRepository with temp database."""
    return PlayerRepository(temp_db)


def test_create_player(player_repo):
    """Test creating a player with parameterized query."""
    player_id = player_repo.create_player(
        name="Michael Jordan",
        adp_value=1.41,
        rarity_tier="GOAT",
        image_url="http://example.com/mj.jpg",
        career_minutes=41011
    )

    assert player_id is not None
    assert player_id > 0


def test_get_player_by_name(player_repo):
    """Test retrieving player by normalized name."""
    player_repo.create_player(
        name="LeBron James",
        adp_value=1.90,
        rarity_tier="GOAT",
        image_url="http://example.com/lbj.jpg"
    )

    # Test case-insensitive lookup
    player = player_repo.get_player_by_name("lebron james")
    assert player is not None
    assert player["name"] == "LeBron James"
    assert player["rarity_tier"] == "GOAT"


def test_get_player_by_name_with_accents(player_repo):
    """Test retrieving player with accent normalization."""
    player_repo.create_player(
        name="Nikola Jokić",
        adp_value=15.39,
        rarity_tier="Mythic",
        image_url="http://example.com/jokic.jpg"
    )

    # Should find with or without accent
    player1 = player_repo.get_player_by_name("Nikola Jokić")
    player2 = player_repo.get_player_by_name("Nikola Jokic")

    assert player1 is not None
    assert player2 is not None
    assert player1["id"] == player2["id"]


def test_get_all_players(player_repo):
    """Test retrieving all players."""
    player_repo.create_player("Player 1", None, "Common", None)
    player_repo.create_player("Player 2", None, "Common", None)
    player_repo.create_player("Player 3", None, "Rare", None)

    players = player_repo.get_all_players()

    assert len(players) == 3


def test_get_players_by_rarity(player_repo):
    """Test filtering players by rarity tier."""
    player_repo.create_player("MJ", 1.41, "GOAT", None)
    player_repo.create_player("LBJ", 1.90, "GOAT", None)
    player_repo.create_player("Curry", 4.54, "Mythic", None)

    goat_players = player_repo.get_players_by_rarity("GOAT")

    assert len(goat_players) == 2


def test_sql_injection_prevention(player_repo):
    """Test that SQL injection attempts are safely handled."""
    # Attempt SQL injection via player name
    malicious_name = "Robert'; DROP TABLE players; --"

    player_repo.create_player(malicious_name, None, "Common", None)

    # Table should still exist and contain the literal string
    players = player_repo.get_all_players()
    assert len(players) == 1
    assert players[0]["name"] == malicious_name
