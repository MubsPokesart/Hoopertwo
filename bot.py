"""HooperTwo Discord Bot - Entry point."""
import asyncio
import logging
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
        self.db = get_connection_manager(self.settings.database_path)
        logger.info(f"Database initialized at {self.settings.database_path}")

    async def setup_hook(self):
        """Called when bot is starting up. Load cogs here."""
        logger.info("Bot setup hook called")

        # Import cogs and dependencies
        from src.cogs.spawning_cog import SpawningCog
        from src.cogs.collection_cog import CollectionCog
        from src.coordinators.cache_coordinator import CacheCoordinator
        from src.managers.spawn_manager import SpawnManager
        from src.managers.collection_manager import CollectionManager
        from src.database.repositories.player_repository import PlayerRepository
        from src.database.repositories.collection_repository import CollectionRepository

        # Initialize shared dependencies
        cache = CacheCoordinator()

        # Initialize repositories
        player_repo = PlayerRepository(self.db)
        collection_repo = CollectionRepository(self.db.get_connection())

        # Initialize managers
        spawn_manager = SpawnManager(player_repo)
        collection_manager = CollectionManager(collection_repo)

        # Load SpawningCog (Batch 6) with collection integration (Batch 7)
        await self.add_cog(SpawningCog(self, cache, spawn_manager, collection_manager))
        logger.info("✅ SpawningCog loaded")

        # Load CollectionCog (Batch 7)
        await self.add_cog(CollectionCog(self, collection_manager))
        logger.info("✅ CollectionCog loaded")

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
            # For testing: sync to guild instantly (global sync takes 1 hour!)
            if self.guilds:
                test_guild = self.guilds[0]

                # Clear only guild commands (DON'T clear global - those are our source!)
                logger.info("Clearing old guild commands...")
                self.tree.clear_commands(guild=test_guild)

                # Copy global commands to guild
                self.tree.copy_global_to(guild=test_guild)

                # Sync to guild (instant)
                synced = await self.tree.sync(guild=test_guild)
                logger.info(f"✅ Synced {len(synced)} command(s) to guild '{test_guild.name}' (INSTANT)")
                logger.info(f"Synced commands: {[cmd.name for cmd in synced]}")
            else:
                # Fallback to global sync (takes up to 1 hour to appear)
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} command(s) globally (may take up to 1 hour to appear)")
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
