# Batch 8: Leaderboard System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a competitive leaderboard system that tracks user points across different time periods (weekly, monthly, yearly, all-time), creates automatic snapshots, and displays rankings with pagination.

**Architecture:** Repository for leaderboard data (LeaderboardRepository), manager for points calculation and snapshot logic (LeaderboardManager), background task for automated snapshot creation, and Discord cog for leaderboard commands. Uses discord.ui.Select for time period selection and pagination for rankings.

**Tech Stack:** Python 3.10+, discord.py 2.0+, discord.ext.tasks for background jobs, SQLite3 with parameterized queries, discord.ui.View for interactive displays

---

## Task 1: Leaderboard Repository - Create Snapshot

**Files:**
- Create: `src/database/repositories/leaderboard_repository.py`
- Test: `tests/database/repositories/test_leaderboard_repository.py`
- Reference: `src/database/models.py:42-54` (leaderboard_snapshots table schema)

**Step 1: Write the failing test**

```python
import pytest
import sqlite3
from datetime import date
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.connection_manager import ConnectionManager


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()

    # Insert test player
    conn.execute(
        "INSERT INTO players (name, adp_value, rarity_tier) VALUES (?, ?, ?)",
        ("LeBron James", 1.5, "GOAT")
    )
    conn.commit()

    yield conn
    manager.close()


def test_create_snapshot(db_connection):
    """Test creating a leaderboard snapshot."""
    repo = LeaderboardRepository(db_connection)

    result = repo.create_snapshot(
        user_id=123456789,
        server_id=987654321,
        period="weekly",
        points=1500,
        player_count=3,
        snapshot_date=date(2026, 1, 18)
    )

    assert result is True

    # Verify snapshot was created
    cursor = db_connection.execute(
        "SELECT user_id, points, player_count, period FROM leaderboard_snapshots WHERE user_id = ?",
        (123456789,)
    )
    row = cursor.fetchone()
    assert row == (123456789, 1500, 3, "weekly")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/repositories/test_leaderboard_repository.py::test_create_snapshot -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.database.repositories.leaderboard_repository'"

**Step 3: Write minimal implementation**

```python
"""Repository for leaderboard database operations."""
import sqlite3
from datetime import date
from typing import List, Dict, Any, Optional


class LeaderboardRepository:
    """Handles database operations for leaderboards.

    Responsibilities:
    - Create and update snapshots
    - Query rankings by period
    - Get user rank and stats
    - All operations use parameterized queries for security
    """

    def __init__(self, connection: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            connection: SQLite database connection
        """
        self.connection = connection

    def create_snapshot(
        self,
        user_id: int,
        server_id: int,
        period: str,
        points: int,
        player_count: int,
        snapshot_date: date
    ) -> bool:
        """Create a leaderboard snapshot for a user.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            period: Time period (weekly, monthly, yearly, alltime)
            points: Total points
            player_count: Total number of players
            snapshot_date: Date of snapshot

        Returns:
            True if created/updated successfully
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO leaderboard_snapshots
                    (user_id, server_id, period, points, player_count, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, server_id, period, snapshot_date)
                DO UPDATE SET
                    points = excluded.points,
                    player_count = excluded.player_count
                """,
                (user_id, server_id, period, points, player_count, snapshot_date)
            )
            self.connection.commit()
            return True
        except sqlite3.Error:
            return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/repositories/test_leaderboard_repository.py::test_create_snapshot -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/database/repositories/leaderboard_repository.py tests/database/repositories/test_leaderboard_repository.py
git commit -m "feat: add leaderboard repository with snapshot creation"
```

---

## Task 2: Leaderboard Repository - Get Rankings

**Files:**
- Modify: `src/database/repositories/leaderboard_repository.py`
- Modify: `tests/database/repositories/test_leaderboard_repository.py`

**Step 1: Write the failing test**

```python
def test_get_rankings(db_connection):
    """Test retrieving rankings for a period."""
    repo = LeaderboardRepository(db_connection)

    # Create multiple snapshots
    snapshot_date = date(2026, 1, 18)
    repo.create_snapshot(123, 987, "weekly", 1500, 3, snapshot_date)
    repo.create_snapshot(456, 987, "weekly", 2000, 4, snapshot_date)
    repo.create_snapshot(789, 987, "weekly", 1000, 2, snapshot_date)

    # Get rankings
    rankings = repo.get_rankings(
        server_id=987,
        period="weekly",
        limit=10
    )

    assert len(rankings) == 3
    # Should be sorted by points descending
    assert rankings[0]["user_id"] == 456
    assert rankings[0]["points"] == 2000
    assert rankings[0]["rank"] == 1
    assert rankings[1]["user_id"] == 123
    assert rankings[1]["rank"] == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/repositories/test_leaderboard_repository.py::test_get_rankings -v`

Expected: FAIL with "AttributeError: 'LeaderboardRepository' object has no attribute 'get_rankings'"

**Step 3: Write minimal implementation**

Add to `leaderboard_repository.py`:

```python
def get_rankings(
    self,
    server_id: int,
    period: str,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get leaderboard rankings for a period.

    Args:
        server_id: Discord server ID
        period: Time period to query
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of dictionaries with rank, user_id, points, and player_count
    """
    cursor = self.connection.cursor()

    # Get latest snapshot date for this period
    cursor.execute(
        """
        SELECT MAX(snapshot_date) FROM leaderboard_snapshots
        WHERE server_id = ? AND period = ?
        """,
        (server_id, period)
    )
    latest_date = cursor.fetchone()[0]

    if not latest_date:
        return []

    # Get rankings for latest snapshot
    cursor.execute(
        """
        SELECT
            user_id,
            points,
            player_count,
            ROW_NUMBER() OVER (ORDER BY points DESC) as rank
        FROM leaderboard_snapshots
        WHERE server_id = ? AND period = ? AND snapshot_date = ?
        ORDER BY points DESC
        LIMIT ? OFFSET ?
        """,
        (server_id, period, latest_date, limit, offset)
    )

    columns = ["user_id", "points", "player_count", "rank"]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/repositories/test_leaderboard_repository.py::test_get_rankings -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/database/repositories/leaderboard_repository.py tests/database/repositories/test_leaderboard_repository.py
git commit -m "feat: add get rankings query with pagination"
```

---

## Task 3: Leaderboard Repository - Get User Rank

**Files:**
- Modify: `src/database/repositories/leaderboard_repository.py`
- Modify: `tests/database/repositories/test_leaderboard_repository.py`

**Step 1: Write the failing test**

```python
def test_get_user_rank(db_connection):
    """Test getting a specific user's rank."""
    repo = LeaderboardRepository(db_connection)

    snapshot_date = date(2026, 1, 18)
    repo.create_snapshot(123, 987, "weekly", 1500, 3, snapshot_date)
    repo.create_snapshot(456, 987, "weekly", 2000, 4, snapshot_date)
    repo.create_snapshot(789, 987, "weekly", 1000, 2, snapshot_date)

    # Get rank for middle user
    user_rank = repo.get_user_rank(
        user_id=123,
        server_id=987,
        period="weekly"
    )

    assert user_rank is not None
    assert user_rank["rank"] == 2
    assert user_rank["points"] == 1500
    assert user_rank["player_count"] == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/repositories/test_leaderboard_repository.py::test_get_user_rank -v`

Expected: FAIL with "AttributeError: 'LeaderboardRepository' object has no attribute 'get_user_rank'"

**Step 3: Write minimal implementation**

Add to `leaderboard_repository.py`:

```python
def get_user_rank(
    self,
    user_id: int,
    server_id: int,
    period: str
) -> Optional[Dict[str, Any]]:
    """Get a specific user's rank and stats.

    Args:
        user_id: Discord user ID
        server_id: Discord server ID
        period: Time period to query

    Returns:
        Dictionary with rank, points, and player_count, or None if not found
    """
    cursor = self.connection.cursor()

    # Get latest snapshot date
    cursor.execute(
        """
        SELECT MAX(snapshot_date) FROM leaderboard_snapshots
        WHERE server_id = ? AND period = ?
        """,
        (server_id, period)
    )
    latest_date = cursor.fetchone()[0]

    if not latest_date:
        return None

    # Get user's rank using subquery
    cursor.execute(
        """
        WITH ranked_users AS (
            SELECT
                user_id,
                points,
                player_count,
                ROW_NUMBER() OVER (ORDER BY points DESC) as rank
            FROM leaderboard_snapshots
            WHERE server_id = ? AND period = ? AND snapshot_date = ?
        )
        SELECT rank, points, player_count
        FROM ranked_users
        WHERE user_id = ?
        """,
        (server_id, period, latest_date, user_id)
    )

    row = cursor.fetchone()
    if not row:
        return None

    return {
        "rank": row[0],
        "points": row[1],
        "player_count": row[2]
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/repositories/test_leaderboard_repository.py::test_get_user_rank -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/database/repositories/leaderboard_repository.py tests/database/repositories/test_leaderboard_repository.py
git commit -m "feat: add get user rank functionality"
```

---

## Task 4: Leaderboard Manager - Calculate Points

**Files:**
- Create: `src/managers/leaderboard_manager.py`
- Test: `tests/managers/test_leaderboard_manager.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_leaderboard_manager.py::test_update_snapshots_for_server -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.managers.leaderboard_manager'"

**Step 3: Write minimal implementation**

```python
"""Manager for leaderboard business logic."""
from datetime import date
from typing import Dict, Any, List
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.repositories.collection_repository import CollectionRepository


class LeaderboardManager:
    """Manages leaderboard business logic.

    Responsibilities:
    - Update snapshots for all users
    - Get formatted rankings
    - Calculate points from collections
    """

    def __init__(
        self,
        leaderboard_repository: LeaderboardRepository,
        collection_repository: CollectionRepository
    ):
        """Initialize manager with repositories.

        Args:
            leaderboard_repository: Leaderboard repository instance
            collection_repository: Collection repository instance
        """
        self.leaderboard_repo = leaderboard_repository
        self.collection_repo = collection_repository

    def update_snapshots_for_server(
        self,
        server_id: int,
        period: str,
        snapshot_date: date
    ) -> int:
        """Create/update snapshots for all users in a server.

        Args:
            server_id: Discord server ID
            period: Time period for snapshot
            snapshot_date: Date of snapshot

        Returns:
            Number of snapshots created
        """
        # Get all users with collections in this server
        users = self.collection_repo.get_all_server_users(server_id)

        count = 0
        for user_data in users:
            self.leaderboard_repo.create_snapshot(
                user_id=user_data["user_id"],
                server_id=server_id,
                period=period,
                points=user_data["total_points"],
                player_count=user_data["player_count"],
                snapshot_date=snapshot_date
            )
            count += 1

        return count
```

**Step 4: Add get_all_server_users to CollectionRepository**

Before test can pass, we need to add this method to CollectionRepository:

Modify `src/database/repositories/collection_repository.py`:

```python
def get_all_server_users(self, server_id: int) -> List[Dict[str, Any]]:
    """Get stats for all users in a server.

    Args:
        server_id: Discord server ID

    Returns:
        List of dictionaries with user_id, total_points, and player_count
    """
    cursor = self.connection.cursor()

    cursor.execute(
        """
        SELECT
            uc.user_id,
            COUNT(*) as player_count,
            SUM(
                CASE p.rarity_tier
                    WHEN 'GOAT' THEN 1000
                    WHEN 'Mythic' THEN 500
                    WHEN 'Legendary' THEN 250
                    WHEN 'Epic' THEN 100
                    WHEN 'Rare' THEN 50
                    WHEN 'Common' THEN 10
                    ELSE 0
                END
            ) as total_points
        FROM user_collections uc
        JOIN players p ON uc.player_id = p.id
        WHERE uc.server_id = ?
        GROUP BY uc.user_id
        """,
        (server_id,)
    )

    columns = ["user_id", "player_count", "total_points"]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/managers/test_leaderboard_manager.py::test_update_snapshots_for_server -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/managers/leaderboard_manager.py tests/managers/test_leaderboard_manager.py src/database/repositories/collection_repository.py
git commit -m "feat: add leaderboard manager with snapshot update logic"
```

---

## Task 5: Leaderboard Manager - Get Formatted Rankings

**Files:**
- Modify: `src/managers/leaderboard_manager.py`
- Modify: `tests/managers/test_leaderboard_manager.py`

**Step 1: Write the failing test**

```python
def test_get_rankings():
    """Test getting formatted rankings."""
    mock_leaderboard_repo = Mock()
    mock_collection_repo = Mock()

    mock_leaderboard_repo.get_rankings.return_value = [
        {"user_id": 456, "points": 2000, "player_count": 4, "rank": 1},
        {"user_id": 123, "points": 1500, "player_count": 3, "rank": 2}
    ]

    manager = LeaderboardManager(mock_leaderboard_repo, mock_collection_repo)

    rankings = manager.get_rankings(
        server_id=987,
        period="weekly",
        page=0,
        page_size=10
    )

    assert len(rankings["rankings"]) == 2
    assert rankings["rankings"][0]["rank"] == 1
    assert rankings["period"] == "weekly"
    assert rankings["total_pages"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_leaderboard_manager.py::test_get_rankings -v`

Expected: FAIL with "AttributeError: 'LeaderboardManager' object has no attribute 'get_rankings'"

**Step 3: Write minimal implementation**

Add to `leaderboard_manager.py`:

```python
import math

def get_rankings(
    self,
    server_id: int,
    period: str,
    page: int = 0,
    page_size: int = 10
) -> Dict[str, Any]:
    """Get formatted leaderboard rankings.

    Args:
        server_id: Discord server ID
        period: Time period to query
        page: Page number (0-indexed)
        page_size: Number of results per page

    Returns:
        Dictionary with rankings, period, and pagination info
    """
    # Get total count first (query without limit)
    all_rankings = self.leaderboard_repo.get_rankings(
        server_id=server_id,
        period=period,
        limit=1000  # Get all for count
    )
    total_count = len(all_rankings)
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    # Get paginated results
    offset = page * page_size
    rankings = self.leaderboard_repo.get_rankings(
        server_id=server_id,
        period=period,
        limit=page_size,
        offset=offset
    )

    return {
        "rankings": rankings,
        "period": period,
        "current_page": page,
        "total_pages": total_pages
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_leaderboard_manager.py::test_get_rankings -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/leaderboard_manager.py tests/managers/test_leaderboard_manager.py
git commit -m "feat: add get formatted rankings with pagination"
```

---

## Task 6: Background Task - Automated Snapshot Creation

**Files:**
- Create: `src/tasks/leaderboard_tasks.py`
- Test: Manual testing (background tasks are hard to unit test)

**Step 1: Write background task implementation**

```python
"""Background tasks for leaderboard system."""
import logging
from datetime import date, datetime, timezone, timedelta
from discord.ext import tasks, commands
from src.managers.leaderboard_manager import LeaderboardManager

logger = logging.getLogger(__name__)


class LeaderboardTasks(commands.Cog):
    """Background tasks for leaderboard snapshots.

    Responsibilities:
    - Create daily snapshots for all periods
    - Run at midnight UTC
    - Log snapshot creation
    """

    def __init__(self, bot: commands.Bot, leaderboard_manager: LeaderboardManager):
        """Initialize background tasks.

        Args:
            bot: Discord bot instance
            leaderboard_manager: Leaderboard manager instance
        """
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager
        self.create_daily_snapshots.start()

    def cog_unload(self):
        """Stop tasks when cog is unloaded."""
        self.create_daily_snapshots.cancel()

    @tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=timezone.utc))
    async def create_daily_snapshots(self):
        """Create snapshots for all servers at midnight UTC."""
        logger.info("Starting daily snapshot creation...")
        snapshot_date = date.today()

        # Get all servers the bot is in
        for guild in self.bot.guilds:
            try:
                # Create snapshots for all periods
                for period in ["weekly", "monthly", "yearly", "alltime"]:
                    count = self.leaderboard_manager.update_snapshots_for_server(
                        server_id=guild.id,
                        period=period,
                        snapshot_date=snapshot_date
                    )
                    logger.info(f"Created {count} {period} snapshots for server {guild.id}")

            except Exception as e:
                logger.error(f"Error creating snapshots for server {guild.id}: {e}")

        logger.info("Daily snapshot creation complete")

    @create_daily_snapshots.before_loop
    async def before_snapshot_task(self):
        """Wait for bot to be ready before starting task."""
        logger.info("Waiting for bot to be ready before starting snapshot task...")
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize in bot.py with proper dependencies
    # from src.managers.leaderboard_manager import LeaderboardManager
    # await bot.add_cog(LeaderboardTasks(bot, leaderboard_manager))
    pass
```

**Step 2: Manual testing**

Test by running bot and observing logs at midnight UTC, or modify time for testing.

**Step 3: Commit**

```bash
git add src/tasks/leaderboard_tasks.py
git commit -m "feat: add daily snapshot background task"
```

---

## Task 7: Leaderboard Cog - Base View with Period Selector

**Files:**
- Create: `src/cogs/leaderboard_cog.py`

**Step 1: Write LeaderboardView class**

```python
"""Leaderboard system Discord cog."""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from src.managers.leaderboard_manager import LeaderboardManager


class LeaderboardView(discord.ui.View):
    """Interactive view for displaying leaderboards.

    Features:
    - Period selection dropdown (weekly, monthly, yearly, all-time)
    - Page navigation buttons
    - Auto-disable on timeout
    """

    PERIOD_LABELS = {
        "weekly": "📅 Weekly",
        "monthly": "📆 Monthly",
        "yearly": "🗓️ Yearly",
        "alltime": "♾️ All Time"
    }

    def __init__(
        self,
        interaction: discord.Interaction,
        leaderboard_manager: LeaderboardManager,
        server_id: int,
        initial_period: str = "weekly",
        timeout: float = 180.0
    ):
        """Initialize leaderboard view.

        Args:
            interaction: Original interaction
            leaderboard_manager: Leaderboard manager instance
            server_id: Discord server ID
            initial_period: Starting time period
            timeout: Seconds before timeout
        """
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.manager = leaderboard_manager
        self.server_id = server_id
        self.current_period = initial_period
        self.current_page = 0
        self.rankings_data = None
        self.message: Optional[discord.Message] = None

        # Load initial data
        self._load_rankings()
        self._update_buttons()

    def _load_rankings(self):
        """Load rankings data for current period and page."""
        self.rankings_data = self.manager.get_rankings(
            server_id=self.server_id,
            period=self.current_period,
            page=self.current_page,
            page_size=10
        )

    def _create_embed(self) -> discord.Embed:
        """Create embed for current rankings."""
        period_label = self.PERIOD_LABELS.get(self.current_period, self.current_period)

        embed = discord.Embed(
            title=f"🏆 Leaderboard - {period_label}",
            description="Top players ranked by collection points",
            color=discord.Color.gold()
        )

        # Add rankings
        if self.rankings_data["rankings"]:
            ranking_text = []
            for entry in self.rankings_data["rankings"]:
                rank = entry["rank"]
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"**#{rank}**"
                ranking_text.append(
                    f"{medal} <@{entry['user_id']}> - {entry['points']:,} pts ({entry['player_count']} players)"
                )

            embed.add_field(
                name="Rankings",
                value="\n".join(ranking_text),
                inline=False
            )
        else:
            embed.add_field(
                name="No Rankings Yet",
                value="Start collecting players to appear on the leaderboard!",
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.rankings_data['total_pages']}")

        return embed

    def _update_buttons(self):
        """Update button states based on current page."""
        # Will implement after adding buttons
        pass

    async def on_timeout(self):
        """Disable all components on timeout."""
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(view=self)
```

**Step 2: Commit**

```bash
git add src/cogs/leaderboard_cog.py
git commit -m "feat: add leaderboard view base class"
```

---

## Task 8: Leaderboard Cog - Add Period Selector and Navigation

**Files:**
- Modify: `src/cogs/leaderboard_cog.py`

**Step 1: Add period selector and buttons**

```python
# Add after _update_buttons method

@discord.ui.select(
    placeholder="Select Time Period",
    options=[
        discord.SelectOption(label="Weekly", value="weekly", emoji="📅", default=True),
        discord.SelectOption(label="Monthly", value="monthly", emoji="📆"),
        discord.SelectOption(label="Yearly", value="yearly", emoji="🗓️"),
        discord.SelectOption(label="All Time", value="alltime", emoji="♾️")
    ]
)
async def period_selector(self, interaction: discord.Interaction, select: discord.ui.Select):
    """Handle period selection."""
    self.current_period = select.values[0]
    self.current_page = 0  # Reset to first page

    # Update dropdown default
    for option in select.options:
        option.default = (option.value == self.current_period)

    self._load_rankings()
    self._update_buttons()

    await interaction.response.edit_message(embed=self._create_embed(), view=self)

@discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.gray, custom_id="lb_first")
async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
    """Jump to first page."""
    self.current_page = 0
    self._load_rankings()
    self._update_buttons()
    await interaction.response.edit_message(embed=self._create_embed(), view=self)

@discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.blurple, custom_id="lb_prev")
async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
    """Go to previous page."""
    self.current_page = max(0, self.current_page - 1)
    self._load_rankings()
    self._update_buttons()
    await interaction.response.edit_message(embed=self._create_embed(), view=self)

@discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.green, custom_id="lb_page", disabled=True)
async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
    """Page indicator (disabled button)."""
    pass

@discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.blurple, custom_id="lb_next")
async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
    """Go to next page."""
    self.current_page = min(self.rankings_data["total_pages"] - 1, self.current_page + 1)
    self._load_rankings()
    self._update_buttons()
    await interaction.response.edit_message(embed=self._create_embed(), view=self)

@discord.ui.button(label="Last ⏭️", style=discord.ButtonStyle.gray, custom_id="lb_last")
async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
    """Jump to last page."""
    self.current_page = self.rankings_data["total_pages"] - 1
    self._load_rankings()
    self._update_buttons()
    await interaction.response.edit_message(embed=self._create_embed(), view=self)
```

**Step 2: Update _update_buttons implementation**

```python
def _update_buttons(self):
    """Update button states based on current page."""
    # Get buttons (skip select menu at index 0)
    first_button = self.children[1]
    prev_button = self.children[2]
    page_button = self.children[3]
    next_button = self.children[4]
    last_button = self.children[5]

    # Disable first/prev if on first page
    first_button.disabled = self.current_page == 0
    prev_button.disabled = self.current_page == 0

    # Disable next/last if on last page
    total_pages = self.rankings_data["total_pages"]
    next_button.disabled = self.current_page >= total_pages - 1
    last_button.disabled = self.current_page >= total_pages - 1

    # Update page indicator
    page_button.label = f"Page {self.current_page + 1}/{total_pages}"
```

**Step 3: Commit**

```bash
git add src/cogs/leaderboard_cog.py
git commit -m "feat: add period selector and pagination buttons"
```

---

## Task 9: Leaderboard Cog - Commands

**Files:**
- Modify: `src/cogs/leaderboard_cog.py`

**Step 1: Add cog class and commands**

```python
# Add after LeaderboardView class

class LeaderboardCog(commands.Cog):
    """Commands for viewing leaderboards and rankings."""

    def __init__(self, bot: commands.Bot, leaderboard_manager: LeaderboardManager):
        """Initialize cog.

        Args:
            bot: Discord bot instance
            leaderboard_manager: Leaderboard manager instance
        """
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager

    @app_commands.command(name="leaderboard", description="View server leaderboard")
    @app_commands.describe(period="Time period to view (defaults to weekly)")
    @app_commands.choices(period=[
        app_commands.Choice(name="Weekly", value="weekly"),
        app_commands.Choice(name="Monthly", value="monthly"),
        app_commands.Choice(name="Yearly", value="yearly"),
        app_commands.Choice(name="All Time", value="alltime")
    ])
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str] = None
    ):
        """Display server leaderboard with rankings.

        Args:
            interaction: Discord interaction
            period: Time period to display
        """
        selected_period = period.value if period else "weekly"

        # Create view
        view = LeaderboardView(
            interaction=interaction,
            leaderboard_manager=self.leaderboard_manager,
            server_id=interaction.guild_id,
            initial_period=selected_period
        )

        # Send initial message
        embed = view._create_embed()
        await interaction.response.send_message(embed=embed, view=view)

        # Store message reference
        callback = await interaction.original_response()
        view.message = callback

    @app_commands.command(name="rank", description="Check your current rank")
    @app_commands.describe(
        period="Time period to check (defaults to all-time)",
        user="User to check rank for (defaults to yourself)"
    )
    @app_commands.choices(period=[
        app_commands.Choice(name="Weekly", value="weekly"),
        app_commands.Choice(name="Monthly", value="monthly"),
        app_commands.Choice(name="Yearly", value="yearly"),
        app_commands.Choice(name="All Time", value="alltime")
    ])
    async def rank(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str] = None,
        user: Optional[discord.Member] = None
    ):
        """Check your or another user's rank.

        Args:
            interaction: Discord interaction
            period: Time period to check
            user: User to check (defaults to command user)
        """
        target_user = user or interaction.user
        selected_period = period.value if period else "alltime"

        # Get user's rank
        rank_data = self.leaderboard_manager.leaderboard_repo.get_user_rank(
            user_id=target_user.id,
            server_id=interaction.guild_id,
            period=selected_period
        )

        period_label = LeaderboardView.PERIOD_LABELS.get(selected_period, selected_period)

        if rank_data:
            embed = discord.Embed(
                title=f"📊 Rank - {period_label}",
                description=f"**{target_user.display_name}'s Stats**",
                color=discord.Color.blue()
            )
            embed.add_field(name="Rank", value=f"#{rank_data['rank']}", inline=True)
            embed.add_field(name="Points", value=f"{rank_data['points']:,}", inline=True)
            embed.add_field(name="Players", value=str(rank_data['player_count']), inline=True)
        else:
            embed = discord.Embed(
                title=f"📊 Rank - {period_label}",
                description=f"{target_user.display_name} has no ranking yet!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Get Started",
                value="Catch players using `/recognize` to start building your collection!",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize in bot.py with proper dependencies
    pass
```

**Step 2: Commit**

```bash
git add src/cogs/leaderboard_cog.py
git commit -m "feat: add leaderboard and rank commands"
```

---

## Testing & Validation

**Run repository tests:**
```bash
poetry run pytest tests/database/repositories/test_leaderboard_repository.py -v
```

**Run manager tests:**
```bash
poetry run pytest tests/managers/test_leaderboard_manager.py -v
```

**Manual testing:**
1. Run bot
2. Test `/leaderboard` with period selection
3. Test `/rank` for yourself and others
4. Verify pagination works
5. Test background task (modify time or manually trigger)

**Coverage check:**
```bash
poetry run pytest --cov=src/database/repositories --cov=src/managers tests/
```

---

## References

**Discord.py Documentation:**
- [Background Tasks](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html)
- [Select Menus](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [App Commands Choices](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.app_commands.Choice)

**SQLite Window Functions:**
- [ROW_NUMBER for Rankings](https://www.sqlite.org/windowfunctions.html)

**Bot Best Practices:**
- [Background Task Patterns](https://guide.pycord.dev/getting-started/rules-and-common-practices)

---

**Plan saved to:** `docs/plans/2026-01-18-batch-08-leaderboard-system.md`
