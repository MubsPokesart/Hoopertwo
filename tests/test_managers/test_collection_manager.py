from unittest.mock import Mock
from src.managers.collection_manager import CollectionManager


def test_catch_player_success():
    """Test catching a player successfully."""
    mock_repo = Mock()
    mock_repo.add_player_to_collection.return_value = True

    manager = CollectionManager(mock_repo)

    result = manager.catch_player(user_id=123456789, player_id=1, server_id=987654321)

    assert result["success"] is True
    assert "already_owned" in result
    assert result["already_owned"] is False
    mock_repo.add_player_to_collection.assert_called_once_with(123456789, 1, 987654321, "Standard")


def test_catch_player_already_owned():
    """Test recognizing a player already in the user's server collection."""
    mock_repo = Mock()
    mock_repo.add_player_to_collection.return_value = False

    manager = CollectionManager(mock_repo)

    result = manager.catch_player(user_id=123456789, player_id=1, server_id=987654321)

    assert result == {"success": True, "already_owned": True}
    mock_repo.add_player_to_collection.assert_called_once_with(123456789, 1, 987654321, "Standard")


def test_catch_phantom_player_tracks_edition():
    mock_repo = Mock()
    mock_repo.add_player_to_collection.return_value = True
    manager = CollectionManager(mock_repo)

    result = manager.catch_player(
        user_id=123456789,
        player_id=1,
        server_id=987654321,
        edition="Phantom",
    )

    assert result == {"success": True, "already_owned": False}
    mock_repo.add_player_to_collection.assert_called_once_with(123456789, 1, 987654321, "Phantom")


def test_get_collection_formatted():
    """Test getting formatted collection data."""
    mock_repo = Mock()
    mock_repo.get_user_collection.return_value = [
        {
            "id": 1,
            "name": "LeBron James",
            "rarity_tier": "GOAT",
            "adp_value": 1.5,
            "image_url": "https://example.com/lebron.jpg",
            "caught_at": "2026-01-18 10:00:00",
            "edition": "Standard",
            "effective_points": 1000,
        }
    ]
    mock_repo.get_collection_stats.return_value = {
        "total_players": 1,
        "total_points": 1000,
        "rarity_counts": {"GOAT": 1},
        "phantom_count": 0,
    }

    manager = CollectionManager(mock_repo)

    result = manager.get_collection(user_id=123456789, server_id=987654321, page=0, page_size=10)

    assert "players" in result
    assert "stats" in result
    assert "total_pages" in result
    assert len(result["players"]) == 1
    assert result["total_pages"] == 1
