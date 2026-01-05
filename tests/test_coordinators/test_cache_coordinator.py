import pytest
from src.coordinators.cache_coordinator import CacheCoordinator


def test_cache_initialization():
    """Test cache coordinator initializes empty."""
    cache = CacheCoordinator()

    assert cache.get_message_count(123456) == 0
    assert cache.get_active_spawn(123456) is None


def test_increment_message_count():
    """Test incrementing message count for a channel."""
    cache = CacheCoordinator()

    cache.increment_message_count(123456)
    assert cache.get_message_count(123456) == 1

    cache.increment_message_count(123456)
    assert cache.get_message_count(123456) == 2


def test_reset_message_count():
    """Test resetting message count."""
    cache = CacheCoordinator()

    cache.increment_message_count(123456)
    cache.increment_message_count(123456)
    cache.reset_message_count(123456)

    assert cache.get_message_count(123456) == 0


def test_set_active_spawn():
    """Test setting and getting active spawn."""
    cache = CacheCoordinator()

    player_data = {"id": 1, "name": "Michael Jordan", "rarity": "GOAT"}
    cache.set_active_spawn(123456, player_data)

    active = cache.get_active_spawn(123456)
    assert active == player_data
    assert active["name"] == "Michael Jordan"


def test_clear_active_spawn():
    """Test clearing active spawn."""
    cache = CacheCoordinator()

    cache.set_active_spawn(123456, {"id": 1, "name": "Test"})
    cache.clear_active_spawn(123456)

    assert cache.get_active_spawn(123456) is None


def test_multiple_channels_independent():
    """Test that different channels have independent state."""
    cache = CacheCoordinator()

    cache.increment_message_count(111111)
    cache.increment_message_count(111111)
    cache.increment_message_count(222222)

    assert cache.get_message_count(111111) == 2
    assert cache.get_message_count(222222) == 1

    cache.set_active_spawn(111111, {"id": 1, "name": "Player 1"})
    cache.set_active_spawn(222222, {"id": 2, "name": "Player 2"})

    assert cache.get_active_spawn(111111)["name"] == "Player 1"
    assert cache.get_active_spawn(222222)["name"] == "Player 2"
