"""HooperTwo Discord Bot - Entry point."""
import asyncio
import logging
import os
from discord.ext import commands
import discord

from src.config.settings import Settings
from src.database.connection_manager import get_connection_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HooperTwoBot(commands.Bot):
    """Main bot class with lifecycle management."""

    def __init__(self):
        """Initialize bot with intents and configuration."""
        # Load settings
        self.settings = Settings()

        # Configure intents (required for message content)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # DIAGNOSTIC: Log exact intents being used
        logger.info("=== DIAGNOSTIC: Intents Configuration ===")
        logger.info(f"Intents value: {intents.value}")
        logger.info(f"guilds: {intents.guilds}")
        logger.info(f"members: {intents.members}")
        logger.info(f"message_content: {intents.message_content}")
        logger.info(f"presences: {intents.presences}")
        logger.info("========================================")

        super().__init__(
            command_prefix=self.settings.command_prefix,
            intents=intents,
            help_command=None  # Custom help command later
        )

        # Initialize database connection
        self.db = get_connection_manager(
            self.settings.database_path,
            self.settings.backup_directory,
        )
        logger.info(f"Database initialized at {self.settings.database_path}")

    async def setup_hook(self):
        """Called when bot is starting up. Load cogs here."""
        logger.info("Bot setup hook called")

        # Import cogs and dependencies
        from src.cogs.spawning_cog import SpawningCog
        from src.cogs.collection_cog import CollectionCog
        from src.cogs.leaderboard_cog import LeaderboardCog
        from src.cogs.admin_cog import AdminCog
        from src.tasks.scheduled_tasks import ScheduledTasks
        from src.coordinators.cache_coordinator import CacheCoordinator
        from src.managers.spawn_manager import SpawnManager
        from src.managers.collection_manager import CollectionManager
        from src.managers.leaderboard_manager import LeaderboardManager
        from src.managers.config_manager import ConfigManager
        from src.managers.backup_manager import BackupManager
        from src.database.repositories.player_repository import PlayerRepository
        from src.database.repositories.collection_repository import CollectionRepository
        from src.database.repositories.leaderboard_repository import LeaderboardRepository
        from src.database.repositories.server_config_repository import ServerConfigRepository

        # Initialize shared dependencies
        cache = CacheCoordinator()

        # Initialize repositories
        player_repo = PlayerRepository(self.db)
        collection_repo = CollectionRepository(self.db.get_connection())
        leaderboard_repo = LeaderboardRepository(self.db.get_connection())
        config_repo = ServerConfigRepository(self.db.get_connection())

        # Initialize managers
        spawn_manager = SpawnManager(player_repo)
        collection_manager = CollectionManager(collection_repo)
        leaderboard_manager = LeaderboardManager(leaderboard_repo, collection_repo)
        config_manager = ConfigManager(config_repo)
        backup_manager = BackupManager(
            database_path=self.settings.database_path,
            backup_directory=self.settings.backup_directory
        )

        # Load SpawningCog (Batch 6) with collection integration (Batch 7) and config (Batch 9)
        await self.add_cog(SpawningCog(self, cache, spawn_manager, collection_manager, config_manager))
        logger.info("✅ SpawningCog loaded")

        # Load CollectionCog (Batch 7)
        await self.add_cog(CollectionCog(self, collection_manager))
        logger.info("✅ CollectionCog loaded")

        # Load LeaderboardCog (Batch 8)
        await self.add_cog(LeaderboardCog(self, leaderboard_manager))
        logger.info("✅ LeaderboardCog loaded")

        # Load ScheduledTasks (Batch 8 & 10 - Background Tasks)
        await self.add_cog(ScheduledTasks(self, leaderboard_manager, backup_manager))
        logger.info("✅ ScheduledTasks loaded")

        # Load AdminCog (Batch 9 & 10)
        await self.add_cog(AdminCog(self, config_manager, backup_manager))
        logger.info("✅ AdminCog loaded")

        # Log all registered commands
        logger.info(f"Registered prefix commands: {[cmd.name for cmd in self.commands]}")
        logger.info(f"Registered slash commands: {[cmd.name for cmd in self.tree.get_commands()]}")

    async def on_message(self, message):
        """Override to log all messages for debugging."""
        if not message.author.bot:
            logger.info(f"Message received: '{message.content}' from {message.author.name}")
        await self.process_commands(message)

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Command prefix: '{self.command_prefix}'")

        # DIAGNOSTIC: Detailed guild information
        logger.info("=== DIAGNOSTIC: Guild Connection Status ===")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Guild objects: {self.guilds}")
        logger.info(f"Is bot ready: {self.is_ready()}")
        logger.info(f"Latency: {self.latency * 1000:.2f}ms")

        # List each guild if any
        if self.guilds:
            for guild in self.guilds:
                logger.info(f"  - {guild.name} (ID: {guild.id})")
        else:
            logger.warning("No guilds found in cache!")
        logger.info("==========================================")

        # Sync slash commands
        try:
            sync_mode = os.getenv('COMMAND_SYNC_MODE', 'guild')

            if sync_mode == 'global':
                # Production: global sync for all servers
                synced = await self.tree.sync()
                logger.info(f"✅ Synced {len(synced)} command(s) globally (takes ~1 hour)")
            elif self.guilds:
                # Development: instant guild sync for testing
                test_guild = self.guilds[0]
                self.tree.clear_commands(guild=test_guild)
                self.tree.copy_global_to(guild=test_guild)
                synced = await self.tree.sync(guild=test_guild)
                logger.info(f"✅ Synced {len(synced)} command(s) to '{test_guild.name}' (INSTANT)")
            else:
                # Fallback to global
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} command(s) globally")

            logger.info(f"Synced commands: {[cmd.name for cmd in synced]}")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            if hasattr(e, 'status') and e.status == 403:
                logger.error("❌ Missing 'applications.commands' scope! Re-invite bot with proper permissions.")

    async def on_guild_join(self, guild):
        """DIAGNOSTIC: Track when bot joins a guild."""
        logger.info(f"=== DIAGNOSTIC: GUILD_JOIN event fired ===")
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        logger.info(f"Total guilds now: {len(self.guilds)}")
        logger.info("=========================================")

    async def on_guild_remove(self, guild):
        """DIAGNOSTIC: Track when bot is removed from a guild."""
        logger.info(f"=== DIAGNOSTIC: GUILD_REMOVE event fired ===")
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")
        logger.info(f"Total guilds now: {len(self.guilds)}")
        logger.info("============================================")

    async def on_guild_available(self, guild):
        """DIAGNOSTIC: Track when guild becomes available."""
        logger.info(f"=== DIAGNOSTIC: GUILD_AVAILABLE event ===")
        logger.info(f"Guild available: {guild.name} (ID: {guild.id})")
        logger.info("=========================================")

    async def on_guild_unavailable(self, guild):
        """DIAGNOSTIC: Track when guild becomes unavailable."""
        logger.warning(f"=== DIAGNOSTIC: GUILD_UNAVAILABLE event ===")
        logger.warning(f"Guild unavailable: {guild.name} (ID: {guild.id})")
        logger.warning("===========================================")

    async def on_command_error(self, ctx, error):
        """Global error handler for commands."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s",
                ephemeral=True
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Command error: {error}", exc_info=error)
            await ctx.send("❌ An error occurred while processing your command.", ephemeral=True)


async def main():
    """Main entry point."""
    bot = HooperTwoBot()

    # Apply production database optimizations if in production mode
    if os.getenv('ENVIRONMENT') == 'production':
        from src.utils.db_optimizer import optimize_database
        optimize_database(bot.settings.database_path)

    try:
        await bot.start(bot.settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await bot.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=e)
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
