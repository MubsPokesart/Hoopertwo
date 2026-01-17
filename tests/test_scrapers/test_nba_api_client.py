"""Tests for NBA API client.

DEPRECATED: These tests are skipped as NBA API is no longer used for seeding.
Preserved as documentation of the original implementation.
"""
import pytest
import time
from src.scrapers.nba_api_client import NBAApiClient

# Skip all tests in this module - NBA API no longer used for seeding
pytestmark = pytest.mark.skip(reason="Deprecated - NBA API no longer used for seeding")


def test_client_initialization():
    """Test client initializes with rate limit."""
    client = NBAApiClient(rate_limit_per_minute=20)
    assert client.rate_limit_per_minute == 20


def test_find_player_by_name(monkeypatch):
    """Test finding player ID by name using nba_api."""
    client = NBAApiClient()

    # Mock the nba_api call to avoid real API requests
    def mock_get_players():
        return [
            {"id": 2544, "full_name": "LeBron James"},
            {"id": 203076, "full_name": "Anthony Davis"},
        ]

    monkeypatch.setattr(client, "_get_all_players", mock_get_players)

    player_id = client.find_player_id("LeBron James")
    assert player_id == 2544


def test_rate_limiting(monkeypatch):
    """Test that rate limiting is enforced."""
    client = NBAApiClient(rate_limit_per_minute=2)  # 2 per minute for testing

    # Mock the actual API call to avoid real HTTP requests
    fetch_times = []

    def mock_api_call(name):
        fetch_times.append(time.time())
        return 12345

    monkeypatch.setattr(client, "_api_find_player", mock_api_call)

    # Make 3 requests
    client.find_player_id("Player 1")
    client.find_player_id("Player 2")
    client.find_player_id("Player 3")

    # Check that there's a delay between 2nd and 3rd request
    if len(fetch_times) >= 3:
        time_diff = fetch_times[2] - fetch_times[1]
        assert time_diff >= 29  # Should wait ~30 seconds (60s / 2 per minute)
