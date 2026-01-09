"""Tests for Basketball Reference client."""
import pytest
import json
from pathlib import Path
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
                "player_id": "playertest01",
                "adp": 100.0,
                "url": "https://www.basketball-reference.com/players/p/playertest01.html"
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
        player_id_db_path=temp_player_db,
        rate_limit_per_minute=60  # Fast for testing
    )


def test_client_initialization(br_client):
    """Test client initializes with rate limit."""
    assert br_client.rate_limit_per_minute == 60
    assert br_client.base_url == "https://www.basketball-reference.com"


def test_find_player_id_verified(br_client):
    """Test finding verified player ID."""
    player_id = br_client.find_player_id("Michael Jordan")
    assert player_id == "jordami01"

    player_id = br_client.find_player_id("LeBron James")
    assert player_id == "jamesle01"


def test_find_player_id_estimated(br_client):
    """Test finding estimated player ID."""
    player_id = br_client.find_player_id("Test Player")
    assert player_id == "playertest01"


def test_find_player_id_not_found(br_client):
    """Test handling of player not in database."""
    player_id = br_client.find_player_id("Nonexistent Player")
    assert player_id is None


def test_construct_player_url(br_client):
    """Test constructing player page URL."""
    url = br_client.construct_player_url("jordami01")
    assert url == "https://www.basketball-reference.com/players/j/jordami01.html"

    url = br_client.construct_player_url("lopezbr01")
    assert url == "https://www.basketball-reference.com/players/l/lopezbr01.html"


def test_parse_image_from_html_valid(br_client):
    """Test parsing image URL from valid HTML."""
    html = '''
    <html>
        <div id="meta">
            <div class="media-item">
                <img src="https://www.basketball-reference.com/req/202106291/images/headshots/lopezbr01.jpg" alt="Brook Lopez">
            </div>
        </div>
    </html>
    '''

    img_url = br_client._parse_image_from_html(html)
    assert img_url == "https://www.basketball-reference.com/req/202106291/images/headshots/lopezbr01.jpg"


def test_parse_image_from_html_relative_url(br_client):
    """Test parsing image with relative URL."""
    html = '''
    <html>
        <div id="meta">
            <div class="media-item">
                <img src="/req/202106291/images/headshots/jordami01.jpg">
            </div>
        </div>
    </html>
    '''

    img_url = br_client._parse_image_from_html(html)
    assert img_url == "https://www.basketball-reference.com/req/202106291/images/headshots/jordami01.jpg"


def test_parse_image_from_html_protocol_relative(br_client):
    """Test parsing image with protocol-relative URL."""
    html = '''
    <html>
        <div id="meta">
            <div class="media-item">
                <img src="//cdn.ssref.net/req/202106291/images/headshots/jamesle01.jpg">
            </div>
        </div>
    </html>
    '''

    img_url = br_client._parse_image_from_html(html)
    assert img_url.startswith("https://")
    assert "jamesle01.jpg" in img_url


def test_parse_image_from_html_no_meta(br_client):
    """Test parsing fails gracefully when meta div missing."""
    html = '<html><div class="other">No meta here</div></html>'

    img_url = br_client._parse_image_from_html(html)
    assert img_url is None


def test_parse_image_from_html_no_media_item(br_client):
    """Test parsing fails gracefully when media-item missing."""
    html = '<html><div id="meta">No media-item here</div></html>'

    img_url = br_client._parse_image_from_html(html)
    assert img_url is None


def test_parse_image_from_html_no_img_tag(br_client):
    """Test parsing fails gracefully when img tag missing."""
    html = '<html><div id="meta"><div class="media-item">No img tag</div></div></html>'

    img_url = br_client._parse_image_from_html(html)
    assert img_url is None


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


def test_rate_limiting_basic(br_client):
    """Test that rate limiting doesn't crash (basic smoke test)."""
    # This just ensures the rate limiting mechanism doesn't error
    br_client._enforce_rate_limit()
    br_client._enforce_rate_limit()

    # Should have recorded 2 request times
    assert len(br_client.request_times) == 2
