"""Admin configuration Discord cog."""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
from src.managers.config_manager import ConfigManager, ConfigValidationError
from src.utils.permission_checks import is_admin


class AdminCog(commands.Cog):
    """Admin-only commands for server configuration.

    All commands require Administrator permission.
    """

    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        """Initialize cog.

        Args:
            bot: Discord bot instance
            config_manager: Config manager instance
        """
        self.bot = bot
        self.config_manager = config_manager

    @app_commands.command(name="config", description="View current server configuration")
    @commands.check(is_admin())
    async def view_config(self, interaction: discord.Interaction):
        """Display current server configuration.

        Args:
            interaction: Discord interaction
        """
        config = self.config_manager.get_config(interaction.guild_id)

        embed = discord.Embed(
            title="⚙️ Server Configuration",
            description=f"Settings for {interaction.guild.name}",
            color=discord.Color.blue()
        )

        # Spawn threshold
        embed.add_field(
            name="Spawn Threshold",
            value=f"{config['spawn_threshold']} messages",
            inline=False
        )

        # Spawn channels
        if config["spawn_channels"]:
            channels_text = "\n".join([
                f"<#{channel_id}>" for channel_id in config["spawn_channels"]
            ])
        else:
            channels_text = "All channels (not configured)"

        embed.add_field(
            name="Spawn Channels",
            value=channels_text,
            inline=False
        )

        embed.set_footer(text=f"Last updated: {config['updated_at']}")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize in bot.py with proper dependencies
    pass
