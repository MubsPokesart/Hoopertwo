import pytest
from unittest.mock import Mock
from src.managers.config_manager import ConfigManager, ConfigValidationError


def test_set_spawn_threshold_valid():
    """Test setting spawn threshold with valid value."""
    mock_repo = Mock()
    mock_repo.update_spawn_threshold.return_value = True

    manager = ConfigManager(mock_repo)

    result = manager.set_spawn_threshold(
        server_id=987654321,
        threshold=300
    )

    assert result["success"] is True
    mock_repo.update_spawn_threshold.assert_called_once_with(987654321, 300)


def test_set_spawn_threshold_invalid():
    """Test that invalid threshold raises error."""
    mock_repo = Mock()
    manager = ConfigManager(mock_repo)

    # Too low
    with pytest.raises(ConfigValidationError, match="between 10 and 10000"):
        manager.set_spawn_threshold(987654321, 5)

    # Too high
    with pytest.raises(ConfigValidationError, match="between 10 and 10000"):
        manager.set_spawn_threshold(987654321, 15000)


def test_set_spawn_channels_valid():
    """Test setting spawn channels with valid IDs."""
    mock_repo = Mock()
    mock_repo.update_spawn_channels.return_value = True

    manager = ConfigManager(mock_repo)

    result = manager.set_spawn_channels(
        server_id=987654321,
        channel_ids=[111111, 222222]
    )

    assert result["success"] is True
    assert result["channel_count"] == 2


def test_set_spawn_channels_too_many():
    """Test that too many channels raises error."""
    mock_repo = Mock()
    manager = ConfigManager(mock_repo)

    # Create list exceeding limit
    too_many_channels = list(range(51))

    with pytest.raises(ConfigValidationError, match="more than 50"):
        manager.set_spawn_channels(987654321, too_many_channels)
