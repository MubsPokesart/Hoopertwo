import pytest
from unittest.mock import Mock
from datetime import date
from src.managers.leaderboard_manager import LeaderboardManager


def test_update_snapshots_for_server():
    """Test creating snapshots for all users in a server."""
    mock_leaderboard_repo = Mock()
    mock_collection_repo = Mock()

    # Mock collection stats for two users
    mock_collection_repo.get_all_server_users.return_value = [
        {"user_id": 123, "total_points": 1500, "player_count": 3},
        {"user_id": 456, "total_points": 2000, "player_count": 4}
    ]

    manager = LeaderboardManager(mock_leaderboard_repo, mock_collection_repo)

    # Update snapshots
    manager.update_snapshots_for_server(
        server_id=987,
        period="weekly",
        snapshot_date=date(2026, 1, 18)
    )

    # Should create snapshot for each user
    assert mock_leaderboard_repo.create_snapshot.call_count == 2
