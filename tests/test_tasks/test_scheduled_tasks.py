from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from src.tasks.scheduled_tasks import ScheduledTasks


def create_scheduled_tasks(bot, leaderboard_manager):
    """Create the cog without starting discord.py task loops."""
    scheduled_tasks = ScheduledTasks.__new__(ScheduledTasks)
    scheduled_tasks.bot = bot
    scheduled_tasks.leaderboard_manager = leaderboard_manager
    return scheduled_tasks


@pytest.mark.asyncio
async def test_refresh_leaderboard_snapshots_updates_every_guild():
    """Test one refresh atomically calculates all periods for each guild."""
    bot = Mock()
    bot.guilds = [SimpleNamespace(id=111), SimpleNamespace(id=222)]
    leaderboard_manager = Mock()
    leaderboard_manager.refresh_snapshots_for_server.return_value = {
        "weekly": 1,
        "monthly": 2,
        "yearly": 3,
        "alltime": 4,
    }
    scheduled_tasks = create_scheduled_tasks(bot, leaderboard_manager)
    snapshot_at = datetime(2026, 7, 11, 23, 45, tzinfo=timezone.utc)

    await scheduled_tasks.refresh_leaderboard_snapshots(snapshot_at)

    assert leaderboard_manager.refresh_snapshots_for_server.call_args_list == [
        call(server_id=111, snapshot_at=snapshot_at),
        call(server_id=222, snapshot_at=snapshot_at),
    ]


@pytest.mark.asyncio
async def test_before_snapshot_task_refreshes_immediately_after_bot_is_ready():
    """Test startup creates corrected snapshots without waiting for midnight."""
    bot = Mock()
    bot.guilds = [SimpleNamespace(id=111)]
    bot.wait_until_ready = AsyncMock()
    leaderboard_manager = Mock()
    leaderboard_manager.refresh_snapshots_for_server.return_value = {
        period: 0 for period in ("weekly", "monthly", "yearly", "alltime")
    }
    scheduled_tasks = create_scheduled_tasks(bot, leaderboard_manager)
    snapshot_at = datetime(2026, 7, 11, 16, 0, tzinfo=timezone.utc)

    with patch("src.tasks.scheduled_tasks.datetime") as mock_datetime:
        mock_datetime.now.return_value = snapshot_at
        await scheduled_tasks.before_snapshot_task()

    bot.wait_until_ready.assert_awaited_once_with()
    leaderboard_manager.refresh_snapshots_for_server.assert_called_once_with(
        server_id=111,
        snapshot_at=snapshot_at,
    )
