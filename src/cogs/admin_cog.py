"""Admin configuration Discord cog."""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
from pathlib import Path
from src.managers.config_manager import ConfigManager, ConfigValidationError
from src.managers.backup_manager import BackupManager


class AdminCog(commands.Cog):
    """Admin-only commands for server configuration.

    All commands require Administrator permission.
    """

    def __init__(
        self,
        bot: commands.Bot,
        config_manager: ConfigManager,
        backup_manager: BackupManager
    ):
        """Initialize cog.

        Args:
            bot: Discord bot instance
            config_manager: Config manager instance
            backup_manager: Backup manager instance
        """
        self.bot = bot
        self.config_manager = config_manager
        self.backup_manager = backup_manager

    @app_commands.command(name="config", description="View current server configuration")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
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

    @app_commands.command(
        name="set-spawn-threshold",
        description="Set how many messages trigger a spawn"
    )
    @app_commands.describe(threshold="Number of messages before spawn (10-10000)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_spawn_threshold(
        self,
        interaction: discord.Interaction,
        threshold: app_commands.Range[int, 10, 10000]
    ):
        """Set spawn threshold for the server.

        Args:
            interaction: Discord interaction
            threshold: Messages needed to trigger spawn
        """
        try:
            result = self.config_manager.set_spawn_threshold(
                server_id=interaction.guild_id,
                threshold=threshold
            )

            if result["success"]:
                embed = discord.Embed(
                    title="✅ Spawn Threshold Updated",
                    description=f"Players will now spawn after **{threshold} messages**",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Update Failed",
                    description="Failed to update spawn threshold",
                    color=discord.Color.red()
                )

        except ConfigValidationError as e:
            embed = discord.Embed(
                title="❌ Invalid Configuration",
                description=str(e),
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-spawn-channels",
        description="Configure which channels can have player spawns"
    )
    @app_commands.describe(
        channels="Channels where spawns are allowed (mention multiple with space)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_spawn_channels(
        self,
        interaction: discord.Interaction,
        channels: str
    ):
        """Set spawn channels for the server.

        Args:
            interaction: Discord interaction
            channels: Space-separated channel mentions
        """
        # Parse channel mentions
        channel_ids = []
        for mention in channels.split():
            # Extract channel ID from mention <#123456>
            if mention.startswith("<#") and mention.endswith(">"):
                try:
                    channel_id = int(mention[2:-1])
                    channel_ids.append(channel_id)
                except ValueError:
                    pass

        if not channel_ids:
            embed = discord.Embed(
                title="❌ No Valid Channels",
                description="Please mention channels using #channel-name",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            result = self.config_manager.set_spawn_channels(
                server_id=interaction.guild_id,
                channel_ids=channel_ids
            )

            if result["success"]:
                channels_list = "\n".join([f"<#{cid}>" for cid in channel_ids])
                embed = discord.Embed(
                    title="✅ Spawn Channels Updated",
                    description=f"Players will spawn in these channels:\n{channels_list}",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Update Failed",
                    description="Failed to update spawn channels",
                    color=discord.Color.red()
                )

        except ConfigValidationError as e:
            embed = discord.Embed(
                title="❌ Invalid Configuration",
                description=str(e),
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="clear-spawn-channels",
        description="Allow spawns in all channels (remove restrictions)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_spawn_channels(self, interaction: discord.Interaction):
        """Clear spawn channel restrictions.

        Args:
            interaction: Discord interaction
        """
        result = self.config_manager.set_spawn_channels(
            server_id=interaction.guild_id,
            channel_ids=[]
        )

        if result["success"]:
            embed = discord.Embed(
                title="✅ Spawn Channels Cleared",
                description="Players can now spawn in any channel",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Clear Failed",
                description="Failed to clear spawn channels",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="backup", description="Create a manual database backup")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
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
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
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


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize in bot.py with proper dependencies
    pass
