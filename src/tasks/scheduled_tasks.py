"""Background scheduled tasks for bot maintenance."""
import logging
from datetime import datetime, timezone, time
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
        backup_manager: BackupManager,
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

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))
    async def create_daily_snapshots(self):
        """Create snapshots for all servers at midnight UTC."""
        await self.refresh_leaderboard_snapshots(datetime.now(timezone.utc))

    async def refresh_leaderboard_snapshots(self, snapshot_at: datetime) -> None:
        """Refresh every period for all connected guilds at one UTC boundary."""
        logger.info("Starting leaderboard snapshot refresh...")
        for guild in self.bot.guilds:
            try:
                counts = self.leaderboard_manager.refresh_snapshots_for_server(
                    server_id=guild.id,
                    snapshot_at=snapshot_at,
                )
                for period, count in counts.items():
                    logger.info(f"Created {count} {period} snapshots for server {guild.id}")
            except Exception as e:
                logger.error(f"Error creating snapshots for server {guild.id}: {e}")

        logger.info("Leaderboard snapshot refresh complete")

    @tasks.loop(time=time(hour=2, minute=0, tzinfo=timezone.utc))
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
        """Refresh once after startup, then wait for scheduled runs."""
        logger.info("Waiting for bot to be ready before starting snapshot task...")
        await self.bot.wait_until_ready()
        await self.refresh_leaderboard_snapshots(datetime.now(timezone.utc))

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
