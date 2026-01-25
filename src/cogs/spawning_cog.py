"""Spawning cog for player recognition and catching.

Handles message counting, player spawning, and recognition commands.
Follows discord.py best practices for cogs and hybrid commands.
"""
import discord
from discord import app_commands
from discord.ext import commands
import logging

from src.coordinators.cache_coordinator import CacheCoordinator
from src.managers.spawn_manager import SpawnManager
from src.managers.collection_manager import CollectionManager
from src.managers.config_manager import ConfigManager
from src.validators.input_validator import InputValidator, ValidationError
from src.utils.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class SpawningCog(commands.Cog):
    """Cog for player spawning and recognition.

    Responsibilities:
    - Listen to messages and track counts
    - Trigger spawns at threshold
    - Handle player recognition

    Security:
    - Rate limiting on all commands
    - Input validation on all user input
    - Ephemeral error messages to reduce spam
    """

    def __init__(
        self,
        bot: commands.Bot,
        cache: CacheCoordinator,
        spawn_manager: SpawnManager,
        collection_manager: CollectionManager,
        config_manager: ConfigManager
    ):
        """Initialize spawning cog.

        Args:
            bot: Discord bot instance
            cache: Cache coordinator for message counts and active spawns
            spawn_manager: Spawn manager for player selection
            collection_manager: Collection manager for player collections
            config_manager: Config manager for server configuration
        """
        self.bot = bot
        self.cache = cache
        self.spawn_manager = spawn_manager
        self.collection_manager = collection_manager
        self.config_manager = config_manager

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen to messages for spawn triggering.

        Args:
            message: Discord message object
        """
        # Ignore bot messages
        if message.author.bot:
            return

        # Ignore DMs
        if not message.guild:
            return

        # Ignore commands (don't count them toward spawn threshold)
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # Get server config
        config = self.config_manager.get_config(message.guild.id)

        # Check if spawns are allowed in this channel
        if config["spawn_channels"]:  # If list is not empty
            if message.channel.id not in config["spawn_channels"]:
                return  # Skip this channel

        # Increment message count
        channel_id = message.channel.id
        count = self.cache.increment_message_count(channel_id)

        # Get spawn threshold from config
        threshold = config["spawn_threshold"]

        if count >= threshold:
            await self._trigger_spawn(message.channel)

    async def _trigger_spawn(self, channel: discord.TextChannel):
        """Trigger a player spawn in a channel.

        Args:
            channel: Discord text channel to spawn in
        """
        try:
            # Reset counter
            self.cache.reset_message_count(channel.id)

            # Select random player
            player = self.spawn_manager.select_random_player()

            # Set as active spawn
            self.cache.set_active_spawn(channel.id, player)

            # Create spawn embed
            embed = discord.Embed(
                title="🏀 A wild NBA player appeared!",
                description="Use `/recognize <player name>` to catch them!",
                color=discord.Color.gold()
            )

            # Add image if available
            if player.get("image_url"):
                embed.set_image(url=player["image_url"])

            # Add rarity hint (color-coded)
            rarity_colors = {
                "GOAT": discord.Color.red(),
                "Mythic": discord.Color.blue(),
                "Legendary": discord.Color.pink(),
                "Epic": discord.Color.purple(),
                "Rare": discord.Color.gold(),
                "Uncommon": discord.Color.orange(),
                "Common": discord.Color.light_embed(),
            }
            embed.color = rarity_colors.get(player["rarity_tier"], discord.Color.gold())

            await channel.send(embed=embed)
            logger.info(f"Spawned {player['name']} ({player['rarity_tier']}) in channel {channel.id}")

        except ValueError as e:
            logger.error(f"Failed to trigger spawn: {e}")
            # Don't send error to channel, just log it

    @commands.hybrid_command(name="recognize")
    @app_commands.describe(player_name="The full name of the NBA player")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def recognize(self, ctx: commands.Context, *, player_name: str):
        """Recognize and catch a spawned player.

        Args:
            ctx: Command context
            player_name: Full player name (case/accent/punctuation insensitive)
        """
        # Validate input
        try:
            player_name = InputValidator.validate_player_name(player_name)
        except ValidationError as e:
            await ctx.send(f"❌ Invalid input: {e}", ephemeral=True)
            return

        # Check if there's an active spawn
        active_spawn = self.cache.get_active_spawn(ctx.channel.id)
        if not active_spawn:
            await ctx.send("❌ No player to recognize right now!", ephemeral=True)
            return

        # Check if name matches (using TextNormalizer for flexible matching)
        if TextNormalizer.normalize(player_name) != \
           TextNormalizer.normalize(active_spawn["name"]):
            await ctx.send(f"❌ That's not the right player!", ephemeral=True)
            return

        # Correct! Add to collection
        result = self.collection_manager.catch_player(
            user_id=ctx.author.id,
            player_id=active_spawn["id"],
            server_id=ctx.guild.id
        )

        self.cache.clear_active_spawn(ctx.channel.id)

        # Create success embed
        if result["already_owned"]:
            embed = discord.Embed(
                title="✅ Player Caught!",
                description=f"**{ctx.author.mention}** caught **{active_spawn['name']}**!",
                color=discord.Color.dark_theme()
            )
            embed.add_field(name="Rarity", value=active_spawn["rarity_tier"], inline=True)
            if active_spawn.get("adp_value"):
                embed.add_field(name="ADP", value=f"{active_spawn['adp_value']:.1f}", inline=True)
            embed.add_field(name="Status", value="⚠️ You already owned this player!", inline=False)
        else:
            embed = discord.Embed(
                title="✅ Player Caught!",
                description=f"**{ctx.author.mention}** caught **{active_spawn['name']}**!",
                color=discord.Color.green()
            )
            embed.add_field(name="Rarity", value=active_spawn["rarity_tier"], inline=True)
            if active_spawn.get("adp_value"):
                embed.add_field(name="ADP", value=f"{active_spawn['adp_value']:.1f}", inline=True)
            embed.add_field(name="Status", value="🆕 New player added to your collection!", inline=False)

        if active_spawn.get("image_url"):
            embed.set_thumbnail(url=active_spawn["image_url"])

        await ctx.send(embed=embed)

        logger.info(f"User {ctx.author.id} caught {active_spawn['name']} (already_owned={result['already_owned']})")

    @recognize.error
    async def recognize_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors for the recognize command.

        Args:
            ctx: Command context
            error: The error that occurred
        """
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏱️ Slow down! Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
        else:
            logger.error(f"Error in recognize command: {error}")
            await ctx.send("❌ An error occurred. Please try again.", ephemeral=True)


async def setup(bot: commands.Bot, cache, spawn_manager, collection_manager, config_manager):
    """Load the cog.

    Args:
        bot: Discord bot instance
        cache: Cache coordinator instance
        spawn_manager: Spawn manager instance
        collection_manager: Collection manager instance
        config_manager: Config manager instance
    """
    await bot.add_cog(SpawningCog(bot, cache, spawn_manager, collection_manager, config_manager))
