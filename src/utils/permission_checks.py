"""Permission checking utilities for admin commands."""
from discord import Interaction, Permissions
from discord.ext import commands
from discord import app_commands


def is_admin():
    """Check if user has administrator permission (for hybrid commands).

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


def is_moderator():
    """Check if user has moderator permissions (manage messages).

    For commands that should be accessible to moderators and admins.

    Returns:
        Function that checks permissions in interaction context
    """
    async def predicate(ctx) -> bool:
        """Check if user has moderator permissions.

        Args:
            ctx: Command context or interaction

        Returns:
            True if user has moderate permissions

        Raises:
            commands.MissingPermissions: If user lacks permission
        """
        # Get the member object from context or interaction
        member = ctx.author if hasattr(ctx, 'author') else ctx.user

        # Check for admin or manage_messages permission
        has_perms = (
            member.guild_permissions.administrator or
            member.guild_permissions.manage_messages
        )

        if not has_perms:
            raise commands.MissingPermissions(["manage_messages"])
        return True

    return commands.check(predicate)
