from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, call

import pytest

from src.managers.leaderboard_manager import LeaderboardManager


def test_refresh_snapshots_for_server():
    """Test one refresh calculates and publishes every period."""
    mock_leaderboard_repo = Mock()
    mock_collection_repo = Mock()
    period_results = [
        [{"user_id": 123, "total_points": 1000, "player_count": 1}],
        [{"user_id": 123, "total_points": 1500, "player_count": 2}],
        [{"user_id": 123, "total_points": 1750, "player_count": 3}],
        [{"user_id": 123, "total_points": 1850, "player_count": 4}],
    ]
    expected_counts = {
        "weekly": 1,
        "monthly": 1,
        "yearly": 1,
        "alltime": 1,
    }
    mock_collection_repo.get_all_server_users.side_effect = period_results
    mock_leaderboard_repo.replace_server_snapshots.return_value = expected_counts
    manager = LeaderboardManager(mock_leaderboard_repo, mock_collection_repo)
    snapshot_at = datetime(2026, 1, 18, 12, 30, tzinfo=timezone.utc)

    counts = manager.refresh_snapshots_for_server(
        server_id=987,
        snapshot_at=snapshot_at,
    )

    assert counts == expected_counts
    assert mock_collection_repo.get_all_server_users.call_args_list == [
        call(
            server_id=987,
            caught_after=snapshot_at - timedelta(days=7),
            caught_before=snapshot_at,
        ),
        call(
            server_id=987,
            caught_after=snapshot_at - timedelta(days=30),
            caught_before=snapshot_at,
        ),
        call(
            server_id=987,
            caught_after=snapshot_at - timedelta(days=365),
            caught_before=snapshot_at,
        ),
        call(server_id=987, caught_after=None, caught_before=snapshot_at),
    ]
    mock_leaderboard_repo.replace_server_snapshots.assert_called_once_with(
        server_id=987,
        snapshot_date=snapshot_at.date(),
        period_rankings={
            period: rankings for period, rankings in zip(manager.PERIOD_DURATIONS, period_results)
        },
    )


def test_get_rankings_rejects_unsupported_period():
    """Test invalid periods cannot silently behave like all-time."""
    mock_leaderboard_repo = Mock()
    manager = LeaderboardManager(mock_leaderboard_repo, Mock())

    with pytest.raises(ValueError, match="Unsupported leaderboard period"):
        manager.get_rankings(server_id=987, period="daily")

    mock_leaderboard_repo.get_rankings.assert_not_called()


def test_refresh_snapshots_requires_timezone_aware_boundary():
    """Test snapshot boundaries must identify UTC unambiguously."""
    manager = LeaderboardManager(Mock(), Mock())

    with pytest.raises(ValueError, match="timezone-aware"):
        manager.refresh_snapshots_for_server(
            server_id=987,
            snapshot_at=datetime(2026, 7, 11),
        )


def test_get_rankings():
    """Test getting formatted rankings."""
    mock_leaderboard_repo = Mock()
    mock_leaderboard_repo.get_rankings.return_value = [
        {"user_id": 456, "points": 2000, "player_count": 4, "rank": 1},
        {"user_id": 123, "points": 1500, "player_count": 3, "rank": 2},
    ]
    manager = LeaderboardManager(mock_leaderboard_repo, Mock())

    rankings = manager.get_rankings(
        server_id=987,
        period="weekly",
        page=0,
        page_size=10,
    )

    assert len(rankings["rankings"]) == 2
    assert rankings["rankings"][0]["rank"] == 1
    assert rankings["period"] == "weekly"
    assert rankings["total_pages"] >= 1
