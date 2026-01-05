import pytest
from pathlib import Path
from src.managers.image_manager import ImageManager
from src.scrapers.nba_api_client import NBAApiClient


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "images"
    cache_dir.mkdir()
    return str(cache_dir)


@pytest.fixture
def image_manager(temp_cache_dir):
    """Create ImageManager with temp cache."""
    client = NBAApiClient(rate_limit_per_minute=60)  # Fast for testing
    return ImageManager(client, temp_cache_dir)


def test_get_cached_image_path(image_manager):
    """Test getting cached image path for a player."""
    path = image_manager.get_cached_image_path("Michael Jordan")

    assert "michael_jordan" in path.lower()
    assert path.endswith(".png")  # NBA CDN uses PNG format


def test_image_is_cached(image_manager, temp_cache_dir):
    """Test checking if image is already cached."""
    # Initially not cached
    assert not image_manager.is_cached("Michael Jordan")

    # Create a fake cached file with data
    cached_path = image_manager.get_cached_image_path("Michael Jordan")
    Path(cached_path).write_text("fake image data")

    # Now should be cached
    assert image_manager.is_cached("Michael Jordan")


def test_download_image_creates_file(image_manager, monkeypatch):
    """Test that downloading image creates file in cache."""
    # Mock the actual download to avoid network calls
    def mock_download(url, save_path):
        Path(save_path).write_text("fake image data")

    monkeypatch.setattr(image_manager, "_download_from_url", mock_download)

    result = image_manager.download_player_image("Test Player", "http://example.com/test.jpg")

    assert result is True
    assert image_manager.is_cached("Test Player")


def test_download_image_handles_errors_gracefully(image_manager, monkeypatch):
    """Test that download errors are handled without crashing."""
    def mock_download_error(url, save_path):
        raise Exception("Network error")

    monkeypatch.setattr(image_manager, "_download_from_url", mock_download_error)

    result = image_manager.download_player_image("Test Player", "http://example.com/test.jpg")

    assert result is False  # Should return False on error, not crash
