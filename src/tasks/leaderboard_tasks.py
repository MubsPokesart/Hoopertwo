"""Background tasks for leaderboard system."""
import logging
from datetime import date, datetime, timezone, timedelta, time
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

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))
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
