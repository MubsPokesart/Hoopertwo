# Batch 11: Final Integration and Testing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate all systems (collection, leaderboard, admin, backup) into bot.py, create comprehensive integration tests, update documentation, and prepare for production deployment with Docker.

**Architecture:** Wire all managers, repositories, and cogs together in bot.py setup_hook, create end-to-end integration tests, update README and deployment docs, and ensure Docker deployment works seamlessly.

**Tech Stack:** Python 3.10+, discord.py 2.0+, pytest for integration tests, Docker Compose for deployment, comprehensive logging

---

## Task 1: Integrate Collection System into Bot

**Files:**
- Modify: `bot.py`
- Reference: `src/cogs/collection_cog.py`, `src/managers/collection_manager.py`

**Step 1: Update bot.py setup_hook for collection cog**

```python
# Update the setup_hook method in bot.py
# After the SpawningCog loading section (around line 68), add:

# Load CollectionCog (Batch 7)
from src.cogs.collection_cog import CollectionCog
from src.database.repositories.collection_repository import CollectionRepository
from src.managers.collection_manager import CollectionManager

# Initialize collection dependencies
collection_repo = CollectionRepository(self.db.get_connection())
collection_manager = CollectionManager(collection_repo)

# Update SpawningCog to include collection_manager
# Remove line 67 and replace with:
await self.add_cog(SpawningCog(self, cache, spawn_manager, collection_manager))

# Add CollectionCog
await self.add_cog(CollectionCog(self, collection_manager))
logger.info("✅ CollectionCog loaded")
```

**Step 2: Test manually**

Run: `poetry run python bot.py`

Test commands:
- `/recognize <player>` - verify it adds to collection
- `/collection` - verify pagination works
- `/collection @user` - verify viewing others' collections

**Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: integrate collection system into bot"
```

---

## Task 2: Integrate Leaderboard System into Bot

**Files:**
- Modify: `bot.py`
- Reference: `src/cogs/leaderboard_cog.py`, `src/tasks/scheduled_tasks.py`

**Step 1: Update bot.py setup_hook for leaderboard**

```python
# After CollectionCog loading, add:

# Load LeaderboardCog (Batch 8)
from src.cogs.leaderboard_cog import LeaderboardCog
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.managers.leaderboard_manager import LeaderboardManager

# Initialize leaderboard dependencies
leaderboard_repo = LeaderboardRepository(self.db.get_connection())
leaderboard_manager = LeaderboardManager(leaderboard_repo, collection_repo)

# Add LeaderboardCog
await self.add_cog(LeaderboardCog(self, leaderboard_manager))
logger.info("✅ LeaderboardCog loaded")
```

**Step 2: Test manually**

Run: `poetry run python bot.py`

Test commands:
- `/leaderboard` - verify displays rankings
- `/leaderboard weekly` - verify period selection
- `/rank` - verify shows your rank
- `/rank @user` - verify shows other user's rank

**Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: integrate leaderboard system into bot"
```

---

## Task 3: Integrate Admin Configuration into Bot

**Files:**
- Modify: `bot.py`
- Modify: `src/cogs/spawning_cog.py`
- Reference: `src/cogs/admin_cog.py`, `src/managers/config_manager.py`

**Step 1: Update bot.py setup_hook for admin config**

```python
# After LeaderboardCog loading, add:

# Load AdminCog (Batch 9)
from src.cogs.admin_cog import AdminCog
from src.database.repositories.server_config_repository import ServerConfigRepository
from src.managers.config_manager import ConfigManager

# Initialize config dependencies
config_repo = ServerConfigRepository(self.db.get_connection())
config_manager = ConfigManager(config_repo)

# Update SpawningCog to include config_manager (modify earlier line)
# The SpawningCog initialization should now look like:
# await self.add_cog(SpawningCog(self, cache, spawn_manager, collection_manager, config_manager))
```

**Step 2: Update SpawningCog initialization**

Modify the SpawningCog line to pass config_manager:

```python
# Update around line 67 to include config_manager:
await self.add_cog(SpawningCog(self, cache, spawn_manager, collection_manager, config_manager))
```

Add AdminCog after config_manager initialization:

```python
# Add AdminCog
await self.add_cog(AdminCog(self, config_manager, None))  # backup_manager added in next task
logger.info("✅ AdminCog loaded")
```

**Step 3: Test manually (as admin)**

Run: `poetry run python bot.py`

Test commands:
- `/config` - verify shows current settings
- `/set-spawn-threshold 300` - verify updates threshold
- `/set-spawn-channels #general` - verify updates channels
- `/clear-spawn-channels` - verify clears restrictions

**Step 4: Commit**

```bash
git add bot.py src/cogs/spawning_cog.py
git commit -m "feat: integrate admin configuration into bot"
```

---

## Task 4: Integrate Backup System and Scheduled Tasks

**Files:**
- Modify: `bot.py`
- Reference: `src/managers/backup_manager.py`, `src/tasks/scheduled_tasks.py`

**Step 1: Update bot.py setup_hook for backup system**

```python
# After AdminCog loading, add:

# Load Backup System (Batch 10)
from src.managers.backup_manager import BackupManager
from src.tasks.scheduled_tasks import ScheduledTasks
from src.config.settings import BACKUP_DIRECTORY, BACKUP_RETENTION_DAYS

# Initialize backup manager
backup_manager = BackupManager(
    database_path=self.settings.database_path,
    backup_directory=BACKUP_DIRECTORY
)

# Update AdminCog initialization to include backup_manager
# Change the AdminCog line from before to:
await self.add_cog(AdminCog(self, config_manager, backup_manager))

# Load ScheduledTasks (background jobs)
await self.add_cog(ScheduledTasks(self, leaderboard_manager, backup_manager))
logger.info("✅ ScheduledTasks loaded (daily snapshots & backups)")
```

**Step 2: Import settings at top of bot.py**

```python
# Add near top of bot.py with other imports:
from src.config import settings
```

**Step 3: Test manually (as admin)**

Run: `poetry run python bot.py`

Test commands:
- `/backup` - verify creates backup
- `/list-backups` - verify lists backups

Check logs for scheduled task initialization.

**Step 4: Commit**

```bash
git add bot.py
git commit -m "feat: integrate backup system and scheduled tasks"
```

---

## Task 5: Create Integration Test Suite

**Files:**
- Create: `tests/integration/test_full_workflow.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/conftest.py`

**Step 1: Create integration test fixtures**

```python
# tests/integration/conftest.py
"""Fixtures for integration tests."""
import pytest
import tempfile
from pathlib import Path
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.database.repositories.collection_repository import CollectionRepository
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.repositories.server_config_repository import ServerConfigRepository
from src.managers.player_manager import PlayerManager
from src.managers.collection_manager import CollectionManager
from src.managers.leaderboard_manager import LeaderboardManager
from src.managers.config_manager import ConfigManager
from src.managers.spawn_manager import SpawnManager


@pytest.fixture
def temp_db():
    """Create temporary database with all tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        manager = ConnectionManager(str(db_path))
        conn = manager.get_connection()

        yield {
            "connection": conn,
            "manager": manager,
            "path": str(db_path)
        }

        manager.close()


@pytest.fixture
def all_repositories(temp_db):
    """Create all repository instances."""
    conn = temp_db["connection"]

    return {
        "player": PlayerRepository(conn),
        "collection": CollectionRepository(conn),
        "leaderboard": LeaderboardRepository(conn),
        "config": ServerConfigRepository(conn)
    }


@pytest.fixture
def all_managers(all_repositories):
    """Create all manager instances."""
    repos = all_repositories

    return {
        "player": PlayerManager(repos["player"]),
        "collection": CollectionManager(repos["collection"]),
        "leaderboard": LeaderboardManager(repos["leaderboard"], repos["collection"]),
        "config": ConfigManager(repos["config"]),
        "spawn": SpawnManager(repos["player"])
    }
```

**Step 2: Write integration test**

```python
# tests/integration/test_full_workflow.py
"""Integration tests for complete user workflows."""
import pytest
from datetime import date


def test_full_player_collection_workflow(all_repositories, all_managers):
    """Test complete workflow: spawn -> recognize -> collect -> leaderboard."""

    repos = all_repositories
    managers = all_managers

    # Setup: Add test player to database
    player_data = {
        "name": "LeBron James",
        "adp_value": 1.5,
        "rarity_tier": "GOAT",
        "image_url": "https://example.com/lebron.jpg",
        "career_minutes": 50000
    }

    player_id = repos["player"].add_player(**player_data)
    assert player_id is not None

    # Step 1: User "catches" the player
    user_id = 123456789
    server_id = 987654321

    result = managers["collection"].catch_player(
        user_id=user_id,
        player_id=player_id,
        server_id=server_id
    )

    assert result["success"] is True
    assert result["already_owned"] is False

    # Step 2: Verify player in collection
    collection = managers["collection"].get_collection(
        user_id=user_id,
        server_id=server_id,
        page=0,
        page_size=10
    )

    assert len(collection["players"]) == 1
    assert collection["players"][0]["name"] == "LeBron James"
    assert collection["stats"]["total_players"] == 1
    assert collection["stats"]["total_points"] == 1000  # GOAT rarity

    # Step 3: Create leaderboard snapshot
    snapshot_date = date.today()
    count = managers["leaderboard"].update_snapshots_for_server(
        server_id=server_id,
        period="alltime",
        snapshot_date=snapshot_date
    )

    assert count == 1

    # Step 4: Verify user appears in leaderboard
    rankings = managers["leaderboard"].get_rankings(
        server_id=server_id,
        period="alltime",
        page=0,
        page_size=10
    )

    assert len(rankings["rankings"]) == 1
    assert rankings["rankings"][0]["user_id"] == user_id
    assert rankings["rankings"][0]["points"] == 1000
    assert rankings["rankings"][0]["rank"] == 1

    # Step 5: Try to catch same player again
    result2 = managers["collection"].catch_player(
        user_id=user_id,
        player_id=player_id,
        server_id=server_id
    )

    assert result2["success"] is True
    assert result2["already_owned"] is True  # Should indicate duplicate


def test_server_configuration_workflow(all_managers):
    """Test server configuration changes."""

    managers = all_managers
    server_id = 987654321

    # Step 1: Get initial config
    config = managers["config"].get_config(server_id)

    assert config["spawn_threshold"] == 500  # Default
    assert config["spawn_channels"] == []

    # Step 2: Update spawn threshold
    result = managers["config"].set_spawn_threshold(
        server_id=server_id,
        threshold=300
    )

    assert result["success"] is True

    # Step 3: Verify threshold updated
    config = managers["config"].get_config(server_id)
    assert config["spawn_threshold"] == 300

    # Step 4: Set spawn channels
    channel_ids = [111111, 222222, 333333]
    result = managers["config"].set_spawn_channels(
        server_id=server_id,
        channel_ids=channel_ids
    )

    assert result["success"] is True
    assert result["channel_count"] == 3

    # Step 5: Verify channels updated
    config = managers["config"].get_config(server_id)
    assert config["spawn_channels"] == channel_ids


def test_multi_user_leaderboard_workflow(all_repositories, all_managers):
    """Test leaderboard with multiple users."""

    repos = all_repositories
    managers = all_managers
    server_id = 987654321

    # Create test players
    players = [
        {"name": "LeBron James", "adp_value": 1.5, "rarity_tier": "GOAT"},
        {"name": "Michael Jordan", "adp_value": 1.0, "rarity_tier": "GOAT"},
        {"name": "Steph Curry", "adp_value": 15.5, "rarity_tier": "Mythic"}
    ]

    player_ids = []
    for player_data in players:
        pid = repos["player"].add_player(
            **player_data,
            image_url="https://example.com/test.jpg",
            career_minutes=10000
        )
        player_ids.append(pid)

    # User 1 catches 2 GOAT players (2000 points)
    user1 = 111111
    managers["collection"].catch_player(user1, player_ids[0], server_id)
    managers["collection"].catch_player(user1, player_ids[1], server_id)

    # User 2 catches 1 Mythic player (500 points)
    user2 = 222222
    managers["collection"].catch_player(user2, player_ids[2], server_id)

    # Create snapshots
    snapshot_date = date.today()
    managers["leaderboard"].update_snapshots_for_server(
        server_id=server_id,
        period="alltime",
        snapshot_date=snapshot_date
    )

    # Verify rankings
    rankings = managers["leaderboard"].get_rankings(
        server_id=server_id,
        period="alltime",
        page=0,
        page_size=10
    )

    assert len(rankings["rankings"]) == 2

    # User 1 should be rank 1 (more points)
    assert rankings["rankings"][0]["user_id"] == user1
    assert rankings["rankings"][0]["points"] == 2000
    assert rankings["rankings"][0]["rank"] == 1

    # User 2 should be rank 2
    assert rankings["rankings"][1]["user_id"] == user2
    assert rankings["rankings"][1]["points"] == 500
    assert rankings["rankings"][1]["rank"] == 2
```

**Step 3: Run integration tests**

Run: `pytest tests/integration/ -v`

Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add comprehensive integration tests"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/DEPLOYMENT.md`
- Create: `docs/COMMANDS.md`

**Step 1: Update README.md**

```markdown
# HooperTwo - NBA Player Collection Discord Bot

Discord bot for collecting NBA players. Players spawn in chat after X messages, users recognize them to build collections. Rarity based on community ADP board, compete on leaderboards.

## Features

- 🏀 **Player Spawning**: Players appear after configurable message thresholds
- ✅ **Recognition System**: Use `/recognize` to catch spawned players
- 📦 **Collections**: View your collection with `/collection` (paginated)
- 🏆 **Leaderboards**: Compete on weekly/monthly/yearly/all-time leaderboards
- ⚙️ **Admin Controls**: Configure spawn channels and thresholds
- 💾 **Auto Backups**: Daily database backups with retention policy
- 🎯 **Rarity Tiers**: GOAT, Mythic, Legendary, Epic, Rare, Common

## Quick Start

### Prerequisites

- Python 3.10+
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Poetry (for dependency management)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/HooperTwo.git
cd HooperTwo

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env and add your Discord bot token

# Run bot
poetry run python bot.py
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Commands

See [COMMANDS.md](docs/COMMANDS.md) for complete command reference.

### User Commands

- `/recognize <player>` - Catch a spawned player
- `/collection [@user]` - View your or someone's collection
- `/leaderboard [period]` - View server leaderboard
- `/rank [@user] [period]` - Check your or someone's rank

### Admin Commands (Require Administrator Permission)

- `/config` - View server configuration
- `/set-spawn-threshold <number>` - Set messages needed for spawn
- `/set-spawn-channels <channels>` - Configure spawn channels
- `/clear-spawn-channels` - Allow spawns in all channels
- `/backup` - Create manual database backup
- `/list-backups` - List available backups

## Development

```bash
# Run tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src

# Format code
poetry run black src tests

# Lint
poetry run ruff check src tests
```

## Project Structure

```
HooperTwo/
├── src/
│   ├── cogs/           # Discord command cogs
│   ├── managers/       # Business logic
│   ├── repositories/   # Database operations
│   ├── coordinators/   # State management
│   ├── tasks/          # Background tasks
│   └── utils/          # Utilities
├── tests/              # Test suite
├── data/               # ADP board and player data
├── backups/            # Database backups
└── docs/               # Documentation
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
```

**Step 2: Create COMMANDS.md**

```markdown
# HooperTwo Commands Reference

Complete reference for all bot commands.

## User Commands

### `/recognize <player_name>`

Catch a spawned player and add them to your collection.

**Parameters:**
- `player_name` (required): Full name of the player (case-insensitive)

**Example:**
```
/recognize LeBron James
```

**Response:**
- ✅ Success: Player added to collection with rarity tier
- ⚠️ Already owned: Player added but you already have them
- ❌ Wrong player: Name doesn't match active spawn
- ❌ No spawn: No player to recognize

**Cooldown:** 5 seconds per user

---

### `/collection [@user]`

View a player collection with pagination.

**Parameters:**
- `user` (optional): User to view (defaults to yourself)

**Features:**
- Shows total players and points
- Rarity breakdown
- Paginated list (9 players per page)
- Navigation buttons: First, Prev, Next, Last

**Example:**
```
/collection
/collection @friend
```

---

### `/leaderboard [period]`

View server leaderboard rankings.

**Parameters:**
- `period` (optional): Time period (weekly/monthly/yearly/alltime, defaults to weekly)

**Features:**
- Top 10 players per page
- Shows rank, points, and player count
- Period selector dropdown
- Pagination controls

**Example:**
```
/leaderboard
/leaderboard alltime
```

---

### `/rank [@user] [period]`

Check your or another user's rank.

**Parameters:**
- `user` (optional): User to check (defaults to yourself)
- `period` (optional): Time period (defaults to alltime)

**Example:**
```
/rank
/rank @friend weekly
```

---

## Admin Commands

**Required Permission:** Administrator

### `/config`

View current server configuration.

**Shows:**
- Spawn threshold (messages needed)
- Spawn channels (or "all channels")
- Last updated timestamp

---

### `/set-spawn-threshold <threshold>`

Set how many messages trigger a player spawn.

**Parameters:**
- `threshold` (required): Number between 10 and 10,000

**Example:**
```
/set-spawn-threshold 300
```

---

### `/set-spawn-channels <channels>`

Configure which channels can have spawns.

**Parameters:**
- `channels` (required): Space-separated channel mentions

**Example:**
```
/set-spawn-channels #general #spawns #nba
```

**Limit:** Maximum 50 channels

---

### `/clear-spawn-channels`

Remove spawn channel restrictions (allow all channels).

**Example:**
```
/clear-spawn-channels
```

---

### `/backup`

Create a manual database backup.

**Features:**
- Creates timestamped backup
- Verifies integrity automatically
- Shows file size and verification status

**Example:**
```
/backup
```

---

### `/list-backups`

List all available database backups.

**Shows:**
- Up to 10 most recent backups
- Filename, size, and creation date

**Example:**
```
/list-backups
```

---

## Automatic Features

### Player Spawning

- Triggers after X messages (configured by `/set-spawn-threshold`)
- Random player selection weighted by rarity
- Only in configured channels (or all channels if not set)
- Shows player image and rarity

### Daily Leaderboard Snapshots

- Runs at midnight UTC
- Creates snapshots for all periods (weekly/monthly/yearly/alltime)
- Automatic for all servers

### Daily Backups

- Runs at 2 AM UTC
- Creates timestamped backup
- Verifies integrity
- Cleans up backups older than 30 days
- Fully automatic

---

## Rarity Tiers

| Tier | ADP Range | Spawn Weight | Points |
|------|-----------|--------------|--------|
| GOAT | < 2.0 | 1 (rarest) | 1000 |
| Mythic | 2-31.9 | 5 | 500 |
| Legendary | 32-63.9 | 15 | 250 |
| Epic | 64-127.9 | 30 | 100 |
| Rare | 128-255.9 | 50 | 50 |
| Common | 256+ | 100 (common) | 10 |

---

## Support

For issues or questions:
- GitHub Issues: [github.com/yourusername/HooperTwo/issues](https://github.com/yourusername/HooperTwo/issues)
- Discord Support Server: [Your server invite]
```

**Step 3: Commit**

```bash
git add README.md docs/COMMANDS.md
git commit -m "docs: update README and add commands reference"
```

---

## Task 7: Verify Docker Deployment

**Files:**
- Test: `docker-compose.yml`
- Modify: `.dockerignore` if needed

**Step 1: Test Docker build**

```bash
# Build image
docker compose build

# Verify image created
docker images | grep hooper
```

**Step 2: Test Docker run**

```bash
# Start container
docker compose up -d

# Check logs
docker compose logs -f

# Verify bot connected
# Should see "Logged in as HooperTwo" in logs

# Stop container
docker compose down
```

**Step 3: Document any issues and fixes**

Create `docs/DEPLOYMENT.md`:

```markdown
# HooperTwo Deployment Guide

## Docker Deployment (Recommended)

### Prerequisites

- Docker and Docker Compose installed
- Discord bot token

### Steps

1. **Clone and Configure**

```bash
git clone https://github.com/yourusername/HooperTwo.git
cd HooperTwo
cp .env.example .env
```

2. **Edit .env**

Add your Discord bot token:
```
DISCORD_TOKEN=your_token_here
```

3. **Start Bot**

```bash
docker compose up -d
```

4. **View Logs**

```bash
docker compose logs -f
```

5. **Stop Bot**

```bash
docker compose down
```

### Persistent Data

- Database: `./data/hooper.db` (mounted as volume)
- Backups: `./backups/` (mounted as volume)

### Updates

```bash
git pull
docker compose down
docker compose build
docker compose up -d
```

## Manual Deployment

### Prerequisites

- Python 3.10+
- Poetry

### Steps

1. **Install Dependencies**

```bash
poetry install
```

2. **Configure Environment**

```bash
cp .env.example .env
# Edit .env with your token
```

3. **Run Bot**

```bash
poetry run python bot.py
```

### Production Setup (systemd)

Create `/etc/systemd/system/hooper.service`:

```ini
[Unit]
Description=HooperTwo Discord Bot
After=network.target

[Service]
Type=simple
User=hooper
WorkingDirectory=/opt/HooperTwo
Environment="PATH=/opt/HooperTwo/.venv/bin"
ExecStart=/opt/HooperTwo/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable hooper
sudo systemctl start hooper
sudo systemctl status hooper
```

## Monitoring

### Health Checks

- Monitor logs for errors
- Check backup creation (daily at 2 AM UTC)
- Verify snapshot creation (daily at midnight UTC)

### Backup Verification

```bash
# List backups
ls -lh backups/

# Test backup integrity
sqlite3 backups/hooper_backup_TIMESTAMP.db "PRAGMA integrity_check;"
```

## Troubleshooting

### Bot Won't Connect

- Verify Discord token is correct
- Check intents are enabled in Discord Developer Portal
- Ensure bot has proper permissions

### Commands Not Appearing

- Commands sync to guild instantly, global sync takes 1 hour
- Re-invite bot with `applications.commands` scope
- Check logs for sync errors

### Database Issues

- Check `data/hooper.db` exists and has correct permissions
- Verify SQLite version >= 3.35.0
- Check disk space

## Security

- **Never commit `.env`** - token should stay private
- Use environment variables for sensitive data
- Regularly update dependencies
- Monitor backup sizes and clean old backups
```

**Step 4: Commit**

```bash
git add docs/DEPLOYMENT.md
git commit -m "docs: add deployment guide"
```

---

## Task 8: Final Testing Checklist

**Manual Testing Checklist:**

```markdown
## Pre-Deployment Checklist

### Unit Tests
- [ ] All repository tests pass
- [ ] All manager tests pass
- [ ] Coverage >= 80%

### Integration Tests
- [ ] Full workflow test passes
- [ ] Multi-user leaderboard test passes
- [ ] Configuration workflow test passes

### Bot Commands (User)
- [ ] `/recognize` works and adds to collection
- [ ] `/collection` shows correct data with pagination
- [ ] `/collection @user` works for other users
- [ ] `/leaderboard` displays rankings
- [ ] `/leaderboard weekly` period selection works
- [ ] `/rank` shows correct rank
- [ ] `/rank @user monthly` works

### Bot Commands (Admin)
- [ ] `/config` displays settings
- [ ] `/set-spawn-threshold 300` updates threshold
- [ ] `/set-spawn-channels #general` updates channels
- [ ] `/clear-spawn-channels` clears restrictions
- [ ] `/backup` creates backup successfully
- [ ] `/list-backups` shows backups

### Spawning System
- [ ] Players spawn after threshold messages
- [ ] Spawning respects channel restrictions
- [ ] Threshold is configurable per server
- [ ] Player images display correctly

### Background Tasks
- [ ] Daily snapshots task initializes
- [ ] Daily backup task initializes
- [ ] Backups are created automatically
- [ ] Old backups are cleaned up

### Docker Deployment
- [ ] `docker compose build` succeeds
- [ ] `docker compose up` starts bot
- [ ] Bot connects to Discord
- [ ] Database persists between restarts
- [ ] Backups are saved to volume

### Error Handling
- [ ] Invalid commands show helpful errors
- [ ] Permission errors are caught
- [ ] Cooldowns work correctly
- [ ] Database errors are logged

### Documentation
- [ ] README is complete
- [ ] COMMANDS.md lists all commands
- [ ] DEPLOYMENT.md has clear instructions
- [ ] Code has docstrings
```

**Run full test suite:**

```bash
# Unit tests
poetry run pytest tests/database/ tests/managers/ -v

# Integration tests
poetry run pytest tests/integration/ -v

# Coverage report
poetry run pytest --cov=src --cov-report=html
```

**Step 5: Commit final checklist**

```bash
git add docs/TESTING_CHECKLIST.md
git commit -m "docs: add pre-deployment testing checklist"
```

---

## Task 9: Create Final Release Tag

**Step 1: Ensure all tests pass**

```bash
poetry run pytest -v
```

**Step 2: Create version tag**

```bash
git tag -a v1.0.0 -m "Release v1.0.0 - Full HooperTwo Implementation

Features:
- Player spawning system with configurable thresholds
- Collection system with pagination
- Leaderboard system (weekly/monthly/yearly/all-time)
- Admin configuration commands
- Automated daily backups with retention
- Full Docker deployment support

Batches 7-11 complete:
- Batch 7: Collection System
- Batch 8: Leaderboard System
- Batch 9: Admin Configuration
- Batch 10: Backup System
- Batch 11: Final Integration
"

git push origin v1.0.0
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: prepare v1.0.0 release"
git push
```

---

## References

**Testing:**
- [Pytest Integration Testing](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Python Testing Best Practices](https://realpython.com/python-testing/)

**Docker:**
- [Docker Bot Deployment](https://medium.com/@thomaschaigneau.ai/building-and-launching-your-discord-bot-a-step-by-step-guide-f803f7943d33)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

**Discord.py:**
- [Bot Best Practices](https://guide.pycord.dev/getting-started/rules-and-common-practices)
- [Command Sync Guide](https://discordpy.readthedocs.io/en/stable/interactions/api.html)

---

**Plan saved to:** `docs/plans/2026-01-18-batch-11-final-integration.md`
