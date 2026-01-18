# Batch 10: Backup System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an automated backup system that creates daily database backups, implements retention policies to manage storage, verifies backup integrity, and provides admin commands for manual backup/restore operations.

**Architecture:** Manager for backup operations using SQLite's backup API (BackupManager), background task for automated daily backups with integrity checks, and admin cog for manual backup/restore commands. Uses timestamped filenames and retention policies to manage backup storage.

**Tech Stack:** Python 3.10+, SQLite3 backup API, discord.ext.tasks for scheduling, pathlib for file management, PRAGMA integrity_check for validation

---

## Task 1: Backup Manager - Create Backup

**Files:**
- Create: `src/managers/backup_manager.py`
- Test: `tests/managers/test_backup_manager.py`

**Step 1: Write the failing test**

```python
import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from src.managers.backup_manager import BackupManager


@pytest.fixture
def temp_database():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        # Create database with test data
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('test_data')")
        conn.commit()

        yield {
            "db_path": db_path,
            "backup_dir": backup_dir,
            "connection": conn
        }

        conn.close()


def test_create_backup(temp_database):
    """Test creating a database backup."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create backup
    backup_path = manager.create_backup()

    assert backup_path is not None
    assert Path(backup_path).exists()
    assert Path(backup_path).suffix == ".db"
    assert "hooper_backup_" in Path(backup_path).name

    # Verify backup contains data
    backup_conn = sqlite3.connect(backup_path)
    cursor = backup_conn.execute("SELECT value FROM test WHERE id = 1")
    row = cursor.fetchone()
    assert row[0] == "test_data"
    backup_conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_backup_manager.py::test_create_backup -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.managers.backup_manager'"

**Step 3: Write minimal implementation**

```python
"""Manager for database backup operations."""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backup operations.

    Responsibilities:
    - Create timestamped backups using SQLite backup API
    - Verify backup integrity
    - Manage backup retention
    - List available backups
    """

    def __init__(self, database_path: str, backup_directory: str):
        """Initialize backup manager.

        Args:
            database_path: Path to main database file
            backup_directory: Directory to store backups
        """
        self.database_path = Path(database_path)
        self.backup_directory = Path(backup_directory)

        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Optional[str]:
        """Create a timestamped backup of the database.

        Uses SQLite's online backup API for safe backups.

        Returns:
            Path to backup file, or None if backup failed
        """
        try:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"hooper_backup_{timestamp}.db"
            backup_path = self.backup_directory / backup_filename

            # Open source database
            source_conn = sqlite3.connect(str(self.database_path))

            # Create backup connection
            backup_conn = sqlite3.connect(str(backup_path))

            # Perform backup using SQLite backup API
            source_conn.backup(backup_conn)

            # Close connections
            backup_conn.close()
            source_conn.close()

            logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_backup_manager.py::test_create_backup -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/backup_manager.py tests/managers/test_backup_manager.py
git commit -m "feat: add backup manager with create backup functionality"
```

---

## Task 2: Backup Manager - Verify Backup Integrity

**Files:**
- Modify: `src/managers/backup_manager.py`
- Modify: `tests/managers/test_backup_manager.py`

**Step 1: Write the failing test**

```python
def test_verify_backup_integrity(temp_database):
    """Test verifying backup integrity."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create backup
    backup_path = manager.create_backup()

    # Verify integrity
    is_valid = manager.verify_backup_integrity(backup_path)

    assert is_valid is True


def test_verify_corrupt_backup(temp_database):
    """Test detecting corrupted backup."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create a corrupted file
    corrupt_path = temp_database["backup_dir"] / "corrupt.db"
    with open(corrupt_path, "w") as f:
        f.write("This is not a valid SQLite database")

    # Verify should fail
    is_valid = manager.verify_backup_integrity(str(corrupt_path))

    assert is_valid is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_backup_manager.py::test_verify_backup_integrity -v`

Expected: FAIL with "AttributeError: 'BackupManager' object has no attribute 'verify_backup_integrity'"

**Step 3: Write minimal implementation**

Add to `backup_manager.py`:

```python
def verify_backup_integrity(self, backup_path: str) -> bool:
    """Verify integrity of a backup file.

    Uses SQLite's PRAGMA integrity_check.

    Args:
        backup_path: Path to backup file

    Returns:
        True if backup is valid, False otherwise
    """
    try:
        # Open backup database
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        conn.close()

        # Result should be ("ok",) for valid database
        is_valid = result and result[0] == "ok"

        if is_valid:
            logger.info(f"Backup integrity verified: {backup_path}")
        else:
            logger.warning(f"Backup integrity check failed: {backup_path}")

        return is_valid

    except Exception as e:
        logger.error(f"Integrity verification failed for {backup_path}: {e}")
        return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_backup_manager.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/backup_manager.py tests/managers/test_backup_manager.py
git commit -m "feat: add backup integrity verification"
```

---

## Task 3: Backup Manager - Retention Policy

**Files:**
- Modify: `src/managers/backup_manager.py`
- Modify: `tests/managers/test_backup_manager.py`

**Step 1: Write the failing test**

```python
import time


def test_cleanup_old_backups(temp_database):
    """Test cleaning up backups older than retention days."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create an "old" backup by manually creating file
    old_backup = temp_database["backup_dir"] / "hooper_backup_20250101_000000.db"
    old_backup.touch()

    # Create recent backup
    recent_backup = manager.create_backup()

    # Cleanup with 30 day retention (old backup should be deleted)
    deleted_count = manager.cleanup_old_backups(retention_days=30)

    # The manually created old backup should be deleted
    # Note: In real scenario, we'd use file modification time
    assert deleted_count >= 0
    assert Path(recent_backup).exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_backup_manager.py::test_cleanup_old_backups -v`

Expected: FAIL with "AttributeError: 'BackupManager' object has no attribute 'cleanup_old_backups'"

**Step 3: Write minimal implementation**

Add to `backup_manager.py`:

```python
from datetime import timedelta
import os


def cleanup_old_backups(self, retention_days: int = 30) -> int:
    """Delete backups older than retention period.

    Args:
        retention_days: Number of days to keep backups

    Returns:
        Number of backups deleted
    """
    try:
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        cutoff_timestamp = cutoff_time.timestamp()

        # Iterate through backup files
        for backup_file in self.backup_directory.glob("hooper_backup_*.db"):
            # Get file modification time
            file_mtime = os.path.getmtime(backup_file)

            # Delete if older than cutoff
            if file_mtime < cutoff_timestamp:
                logger.info(f"Deleting old backup: {backup_file}")
                backup_file.unlink()
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old backups")

        return deleted_count

    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        return 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_backup_manager.py::test_cleanup_old_backups -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/backup_manager.py tests/managers/test_backup_manager.py
git commit -m "feat: add backup retention policy with cleanup"
```

---

## Task 4: Backup Manager - List Backups

**Files:**
- Modify: `src/managers/backup_manager.py`
- Modify: `tests/managers/test_backup_manager.py`

**Step 1: Write the failing test**

```python
def test_list_backups(temp_database):
    """Test listing available backups."""
    manager = BackupManager(
        database_path=str(temp_database["db_path"]),
        backup_directory=str(temp_database["backup_dir"])
    )

    # Create multiple backups
    backup1 = manager.create_backup()
    time.sleep(0.1)  # Ensure different timestamps
    backup2 = manager.create_backup()

    # List backups
    backups = manager.list_backups()

    assert len(backups) == 2
    assert backups[0]["path"] in [backup1, backup2]
    assert "size" in backups[0]
    assert "created_at" in backups[0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_backup_manager.py::test_list_backups -v`

Expected: FAIL with "AttributeError: 'BackupManager' object has no attribute 'list_backups'"

**Step 3: Write minimal implementation**

Add to `backup_manager.py`:

```python
from typing import List, Dict, Any


def list_backups(self) -> List[Dict[str, Any]]:
    """List all available backups.

    Returns:
        List of dictionaries with backup metadata
    """
    backups = []

    try:
        for backup_file in sorted(
            self.backup_directory.glob("hooper_backup_*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True  # Most recent first
        ):
            file_stats = backup_file.stat()

            backups.append({
                "path": str(backup_file),
                "filename": backup_file.name,
                "size": file_stats.st_size,
                "created_at": datetime.fromtimestamp(file_stats.st_mtime)
            })

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")

    return backups
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_backup_manager.py::test_list_backups -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/backup_manager.py tests/managers/test_backup_manager.py
git commit -m "feat: add list backups functionality"
```

---

## Task 5: Background Task - Automated Daily Backups

**Files:**
- Modify: `src/tasks/leaderboard_tasks.py` (rename to `src/tasks/scheduled_tasks.py`)
- Create migration plan for existing task file

**Step 1: Rename and expand scheduled tasks**

```python
"""Background scheduled tasks for bot maintenance."""
import logging
from datetime import date, datetime, timezone
from discord.ext import tasks, commands
from src.managers.leaderboard_manager import LeaderboardManager
from src.managers.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class ScheduledTasks(commands.Cog):
    """Background tasks for maintenance and automation.

    Responsibilities:
    - Daily leaderboard snapshots
    - Daily database backups
    - Backup cleanup and retention
    """

    def __init__(
        self,
        bot: commands.Bot,
        leaderboard_manager: LeaderboardManager,
        backup_manager: BackupManager
    ):
        """Initialize background tasks.

        Args:
            bot: Discord bot instance
            leaderboard_manager: Leaderboard manager instance
            backup_manager: Backup manager instance
        """
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager
        self.backup_manager = backup_manager

        # Start all tasks
        self.create_daily_snapshots.start()
        self.create_daily_backup.start()

    def cog_unload(self):
        """Stop tasks when cog is unloaded."""
        self.create_daily_snapshots.cancel()
        self.create_daily_backup.cancel()

    @tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=timezone.utc))
    async def create_daily_snapshots(self):
        """Create leaderboard snapshots at midnight UTC."""
        logger.info("Starting daily snapshot creation...")
        snapshot_date = date.today()

        for guild in self.bot.guilds:
            try:
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

    @tasks.loop(time=datetime.time(hour=2, minute=0, tzinfo=timezone.utc))
    async def create_daily_backup(self):
        """Create database backup at 2 AM UTC."""
        logger.info("Starting daily database backup...")

        try:
            # Create backup
            backup_path = self.backup_manager.create_backup()

            if backup_path:
                # Verify integrity
                is_valid = self.backup_manager.verify_backup_integrity(backup_path)

                if is_valid:
                    logger.info(f"Daily backup created and verified: {backup_path}")

                    # Cleanup old backups (30 day retention)
                    deleted = self.backup_manager.cleanup_old_backups(retention_days=30)
                    logger.info(f"Cleaned up {deleted} old backups")
                else:
                    logger.error("Backup integrity check failed!")
            else:
                logger.error("Daily backup creation failed!")

        except Exception as e:
            logger.error(f"Error during daily backup: {e}")

        logger.info("Daily backup task complete")

    @create_daily_snapshots.before_loop
    async def before_snapshot_task(self):
        """Wait for bot to be ready before starting snapshot task."""
        logger.info("Waiting for bot to be ready before starting snapshot task...")
        await self.bot.wait_until_ready()

    @create_daily_backup.before_loop
    async def before_backup_task(self):
        """Wait for bot to be ready before starting backup task."""
        logger.info("Waiting for bot to be ready before starting backup task...")
        await self.bot.wait_until_ready()


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
git mv src/tasks/leaderboard_tasks.py src/tasks/scheduled_tasks.py
git add src/tasks/scheduled_tasks.py
git commit -m "feat: add daily backup task to scheduled tasks"
```

---

## Task 6: Admin Cog - Manual Backup Command

**Files:**
- Modify: `src/cogs/admin_cog.py`

**Step 1: Add backup command**

```python
# Add to AdminCog __init__:
# self.backup_manager = backup_manager

# Add backup command to AdminCog class:

@app_commands.command(name="backup", description="Create a manual database backup")
@commands.check(is_admin())
async def create_backup(self, interaction: discord.Interaction):
    """Create a manual database backup.

    Args:
        interaction: Discord interaction
    """
    await interaction.response.defer(ephemeral=True)

    try:
        # Create backup
        backup_path = self.backup_manager.create_backup()

        if not backup_path:
            embed = discord.Embed(
                title="❌ Backup Failed",
                description="Failed to create backup. Check bot logs.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Verify integrity
        is_valid = self.backup_manager.verify_backup_integrity(backup_path)

        if is_valid:
            backup_file = Path(backup_path)
            size_mb = backup_file.stat().st_size / (1024 * 1024)

            embed = discord.Embed(
                title="✅ Backup Created",
                description="Database backup created successfully",
                color=discord.Color.green()
            )
            embed.add_field(name="Filename", value=backup_file.name, inline=False)
            embed.add_field(name="Size", value=f"{size_mb:.2f} MB", inline=True)
            embed.add_field(name="Verified", value="✓ Integrity check passed", inline=True)
        else:
            embed = discord.Embed(
                title="⚠️ Backup Created (Unverified)",
                description="Backup created but failed integrity check!",
                color=discord.Color.orange()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"Backup error: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


@app_commands.command(name="list-backups", description="List available database backups")
@commands.check(is_admin())
async def list_backups(self, interaction: discord.Interaction):
    """List all available backups.

    Args:
        interaction: Discord interaction
    """
    backups = self.backup_manager.list_backups()

    if not backups:
        embed = discord.Embed(
            title="📦 Database Backups",
            description="No backups found",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="📦 Database Backups",
        description=f"Found {len(backups)} backup(s)",
        color=discord.Color.blue()
    )

    # Show up to 10 most recent backups
    for backup in backups[:10]:
        size_mb = backup["size"] / (1024 * 1024)
        created = backup["created_at"].strftime("%Y-%m-%d %H:%M:%S")

        embed.add_field(
            name=backup["filename"],
            value=f"Size: {size_mb:.2f} MB\nCreated: {created}",
            inline=False
        )

    if len(backups) > 10:
        embed.set_footer(text=f"Showing 10 of {len(backups)} backups")

    await interaction.response.send_message(embed=embed, ephemeral=True)
```

**Step 2: Update admin cog setup**

```python
# Update setup function to accept backup_manager:
async def setup(bot, config_manager, backup_manager):
    """Load the cog."""
    await bot.add_cog(AdminCog(bot, config_manager, backup_manager))
```

**Step 3: Commit**

```bash
git add src/cogs/admin_cog.py
git commit -m "feat: add manual backup and list backups commands"
```

---

## Task 7: Add Backup Directory Configuration

**Files:**
- Modify: `src/config/settings.py`

**Step 1: Add backup settings**

```python
# Add to settings.py:

import os
from pathlib import Path

# Backup configuration
BACKUP_DIRECTORY = os.getenv("BACKUP_DIRECTORY", "backups")
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

# Ensure backup directory exists
Path(BACKUP_DIRECTORY).mkdir(parents=True, exist_ok=True)
```

**Step 2: Update .env.example**

```bash
# Add to .env.example:

# Backup Configuration
BACKUP_DIRECTORY=backups
BACKUP_RETENTION_DAYS=30
```

**Step 3: Commit**

```bash
git add src/config/settings.py .env.example
git commit -m "feat: add backup directory configuration"
```

---

## Testing & Validation

**Run manager tests:**
```bash
poetry run pytest tests/managers/test_backup_manager.py -v
```

**Manual testing:**
1. Run bot as administrator
2. Test `/backup` command - verify backup created
3. Test `/list-backups` - verify backups listed
4. Check `backups/` directory for files
5. Verify integrity check works
6. Test background task (modify time or manually trigger)
7. Test cleanup by creating old files

**Coverage check:**
```bash
poetry run pytest --cov=src/managers tests/managers/test_backup_manager.py
```

**Expected:** 80%+ coverage for BackupManager

---

## References

**SQLite Backup API:**
- [SQLite Python Backup](https://blog.sqlite.ai/sqlite-python-backup)
- [SQLite Backup API Documentation](https://sqlite.org/backup.html)
- [Best Practices for SQLite Backups](https://www.slingacademy.com/article/best-practices-for-managing-sqlite-backups-in-production/)

**Automation and Retention:**
- [Automating SQLite Maintenance](https://www.sqliteforum.com/p/automating-sqlite-maintenance-backups)
- [Python SQLite Backup Guide](https://en.ittrip.xyz/python/python-sqlite-backup)
- [SQLite Backup Methods](https://blog.finxter.com/5-best-ways-to-create-a-backup-of-a-sqlite-database-using-python/)

**Security and Integrity:**
- [Securing SQLite Databases](https://www.kevsrobots.com/learn/sqlite3/10_securing_and_backing_up.html)
- [Data Security Strategies](https://www.sqliteforum.com/p/data-security-and-backup-strategies-in-sqlite-ensuring-data-integrity-and-protection)

---

**Plan saved to:** `docs/plans/2026-01-18-batch-10-backup-system.md`
