"""Tests for Basketball Reference client."""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock
from src.scrapers.basketball_reference_client import BasketballReferenceClient


@pytest.fixture
def temp_player_db(tmp_path):
    """Create temporary player ID database for testing."""
    db_path = tmp_path / "test_player_ids.json"

    test_db = {
        "verified": {
            "Michael Jordan": {
                "player_id": "jordami01",
                "adp": 1.41,
                "url": "https://www.basketball-reference.com/players/j/jordami01.html"
            },
            "LeBron James": {
                "player_id": "jamesle01",
                "adp": 1.90,
                "url": "https://www.basketball-reference.com/players/j/jamesle01.html"
            },
            "Brook Lopez": {
                "player_id": "lopezbr01",
                "adp": 240.0,
                "url": "https://www.basketball-reference.com/players/l/lopezbr01.html"
            }
        },
        "estimated": {
            "Test Player": {
                "player_id": "playette01",
                "adp": 100.0,
                "url": "https://www.basketball-reference.com/players/p/playette01.html"
            }
        },
        "needs_verification": []
    }

    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(test_db, f, indent=2)

    return str(db_path)


@pytest.fixture
def br_client(temp_player_db):
    """Create Basketball Reference client with test database."""
    return BasketballReferenceClient(
        player_id_db_path=temp_player_db
    )


def test_client_initialization(br_client):
    """Test client initializes correctly."""
    assert br_client.base_url == "https://www.basketball-reference.com"
    assert br_client.player_id_db_path is not None


def test_find_player_id_verified(br_client):
    """Test finding verified player ID."""
    player_id = br_client.find_player_id("Michael Jordan")
    assert player_id == "jordami01"

    player_id = br_client.find_player_id("LeBron James")
    assert player_id == "jamesle01"


def test_find_player_id_estimated(br_client):
    """Test finding estimated player ID."""
    player_id = br_client.find_player_id("Test Player")
    assert player_id == "playette01"


def test_find_player_id_not_found(br_client):
    """Test handling of player not in database - returns generated ID."""
    # Two-word names will generate an ID using Basketball Reference convention
    player_id = br_client.find_player_id("Nonexistent Player")
    assert player_id == "playeno01"  # Generated: playe(5) + no(2) + 01

def test_find_player_id_single_name(br_client):
    """Test that single-word names can't generate an ID."""
    player_id = br_client.find_player_id("Madonna")
    assert player_id is None


def test_construct_player_url(br_client):
    """Test constructing player page URL."""
    url = br_client.construct_player_url("jordami01")
    assert url == "https://www.basketball-reference.com/players/j/jordami01.html"

    url = br_client.construct_player_url("lopezbr01")
    assert url == "https://www.basketball-reference.com/players/l/lopezbr01.html"


def test_construct_image_url(br_client):
    """Test constructing direct BR image URLs."""
    url = br_client.construct_image_url("jordami01")
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/jordami01.jpg"

    url = br_client.construct_image_url("jamesle01")
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/jamesle01.jpg"


def test_get_player_image_url_verified(br_client):
    """Test getting image URL for verified player (no verification)."""
    url = br_client.get_player_image_url("Michael Jordan")
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/jordami01.jpg"


def test_get_player_image_url_not_found(br_client):
    """Test getting image URL for player not in database.

    Since the client now auto-generates IDs using Basketball Reference
    naming convention, it should return an estimated URL even for unknown players.
    """
    url = br_client.get_player_image_url("Unknown Player")

    # Should generate URL using BR naming convention: playeun01
    assert url is not None
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/playeun01.jpg"




def test_database_caching(br_client):
    """Test that player ID database is cached after first load."""
    # First load
    db1 = br_client._load_player_id_database()

    # Second load (should use cache)
    db2 = br_client._load_player_id_database()

    assert db1 is db2  # Should be same object (cached)


def test_missing_database_file():
    """Test handling of missing database file."""
    client = BasketballReferenceClient(player_id_db_path="nonexistent.json")

    db = client._load_player_id_database()

    assert db["verified"] == {}
    assert db["estimated"] == {}


