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
        # Cogs will be loaded here in future tasks

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

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
