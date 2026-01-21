"""Permission checking utilities for admin commands."""
from discord import Interaction
from discord.ext import commands


def is_admin():
    """Check if user has administrator permission.

    Returns:
        Function that checks permissions in interaction context
    """
    async def predicate(interaction: Interaction) -> bool:
        """Check if user is administrator.

        Args:
            interaction: Discord interaction

        Returns:
            True if user has administrator permission

        Raises:
            commands.MissingPermissions: If user lacks permission
        """
        if not interaction.user.guild_permissions.administrator:
            raise commands.MissingPermissions(["administrator"])
        return True

    return commands.check(predicate)
