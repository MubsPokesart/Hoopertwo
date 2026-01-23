"""Tests for Basketball Reference client."""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
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


@pytest.mark.asyncio
async def test_find_player_id_verified(br_client):
    """Test finding verified player ID."""
    player_id = await br_client.find_player_id("Michael Jordan")
    assert player_id == "jordami01"

    player_id = await br_client.find_player_id("LeBron James")
    assert player_id == "jamesle01"


@pytest.mark.asyncio
async def test_find_player_id_estimated(br_client):
    """Test finding estimated player ID."""
    player_id = await br_client.find_player_id("Test Player")
    assert player_id == "playette01"


@pytest.mark.asyncio
async def test_find_player_id_not_found(br_client):
    """Test handling of player not in database - returns generated ID."""
    # Two-word names will generate an ID using Basketball Reference convention
    player_id = await br_client.find_player_id("Nonexistent Player")
    assert player_id == "playeno01"  # Generated: playe(5) + no(2) + 01

@pytest.mark.asyncio
async def test_find_player_id_single_name(br_client):
    """Test that single-word names can't generate an ID."""
    player_id = await br_client.find_player_id("Madonna")
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


@pytest.mark.asyncio
async def test_get_player_image_url_verified(br_client):
    """Test getting image URL for verified player (no verification)."""
    url = await br_client.get_player_image_url("Michael Jordan")
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/jordami01.jpg"


@pytest.mark.asyncio
async def test_get_player_image_url_not_found(br_client):
    """Test getting image URL for player not in database.

    Since the client now auto-generates IDs using Basketball Reference
    naming convention, it should return an estimated URL even for unknown players.
    """
    url = await br_client.get_player_image_url("Unknown Player")

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


# Collision Detection Tests

@pytest.fixture
def temp_player_db_with_collision(tmp_path):
    """Create temporary player ID database with collision case."""
    db_path = tmp_path / "test_player_ids_collision.json"

    test_db = {
        "verified": {
            "Mikal Bridges": {
                "player_id": "bridgmi01",
                "adp": 45.0,
                "url": "https://www.basketball-reference.com/players/b/bridgmi01.html"
            }
        },
        "estimated": {},
        "needs_verification": []
    }

    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(test_db, f, indent=2)

    return str(db_path)


def test_has_collision_detects_conflict(temp_player_db_with_collision):
    """Test collision detection when generated ID conflicts with existing player."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # Miles Bridges generates 'bridgmi01', which conflicts with Mikal Bridges
    has_collision = client._has_collision("Miles Bridges", "bridgmi01")
    assert has_collision is True


def test_has_collision_no_conflict(temp_player_db_with_collision):
    """Test collision detection when no conflict exists."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # LeBron James generates 'jamesle01', no conflict
    has_collision = client._has_collision("LeBron James", "jamesle01")
    assert has_collision is False


def test_has_collision_same_player_no_conflict(temp_player_db_with_collision):
    """Test collision detection doesn't flag same player."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # Mikal Bridges with his own ID should not be a collision
    has_collision = client._has_collision("Mikal Bridges", "bridgmi01")
    assert has_collision is False


@pytest.mark.asyncio
async def test_find_player_id_without_collision(br_client):
    """Test finding player ID when no collision detected."""
    player_id = await br_client.find_player_id("Michael Jordan")
    assert player_id == "jordami01"


@pytest.mark.asyncio
async def test_find_player_id_with_collision_no_searcher(temp_player_db_with_collision):
    """Test finding player ID with collision but no searcher provided (fallback to generated)."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # Miles Bridges generates 'bridgmi01' which collides with Mikal, but no searcher
    player_id = await client.find_player_id("Miles Bridges")

    # Should return generated ID with warning (fallback behavior)
    assert player_id == "bridgmi01"


@pytest.mark.asyncio
async def test_find_player_id_with_collision_and_searcher(temp_player_db_with_collision):
    """Test collision resolution with searcher."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # Mock searcher that returns correct ID for Miles Bridges
    mock_searcher = AsyncMock()
    mock_searcher.search_player_by_name_and_years = AsyncMock(return_value="bridgmi02")

    # Miles Bridges with year range and searcher
    player_id = await client.find_player_id(
        "Miles Bridges",
        year_range=(2019, 2025),
        searcher=mock_searcher
    )

    # Should return searched ID (bridgmi02) instead of generated (bridgmi01)
    assert player_id == "bridgmi02"
    mock_searcher.search_player_by_name_and_years.assert_called_once_with(
        "Miles Bridges", 2019, 2025
    )


@pytest.mark.asyncio
async def test_find_player_id_collision_search_fails(temp_player_db_with_collision):
    """Test collision resolution when search fails (fallback to generated)."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # Mock searcher that returns None (search failed)
    mock_searcher = AsyncMock()
    mock_searcher.search_player_by_name_and_years = AsyncMock(return_value=None)

    player_id = await client.find_player_id(
        "Miles Bridges",
        year_range=(2019, 2025),
        searcher=mock_searcher
    )

    # Should fallback to generated ID with warning
    assert player_id == "bridgmi01"


@pytest.mark.asyncio
async def test_get_player_image_url_with_year_range(br_client):
    """Test getting image URL with year range parameter."""
    url = await br_client.get_player_image_url(
        "Michael Jordan",
        year_range=(1984, 2003)
    )
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/jordami01.jpg"


@pytest.mark.asyncio
async def test_get_player_image_url_collision_resolution(temp_player_db_with_collision):
    """Test getting image URL with collision resolution."""
    client = BasketballReferenceClient(player_id_db_path=temp_player_db_with_collision)

    # Mock searcher
    mock_searcher = AsyncMock()
    mock_searcher.search_player_by_name_and_years = AsyncMock(return_value="bridgmi02")

    url = await client.get_player_image_url(
        "Miles Bridges",
        year_range=(2019, 2025),
        searcher=mock_searcher
    )

    # Should use searched ID (bridgmi02)
    assert url == "https://www.basketball-reference.com/req/202106291/images/headshots/bridgmi02.jpg"


