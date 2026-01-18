import pytest
from unittest.mock import Mock
from src.managers.collection_manager import CollectionManager


def test_catch_player_success():
    """Test catching a player successfully."""
    mock_repo = Mock()
    mock_repo.add_player_to_collection.return_value = True

    manager = CollectionManager(mock_repo)

    result = manager.catch_player(
        user_id=123456789,
        player_id=1,
        server_id=987654321
    )

    assert result["success"] is True
    assert "already_owned" in result
    assert result["already_owned"] is False
    mock_repo.add_player_to_collection.assert_called_once_with(123456789, 1, 987654321)
