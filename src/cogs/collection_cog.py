"""Collection system Discord cog."""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from src.managers.collection_manager import CollectionManager


class CollectionView(discord.ui.View):
    """Paginated view for displaying user collections.

    Features:
    - Next/Previous page navigation
    - Jump to first/last page
    - Auto-disable buttons on timeout
    - Shows current page number
    """

    def __init__(
        self,
        interaction: discord.Interaction,
        collection_data: dict,
        user_name: str,
        timeout: float = 180.0
    ):
        """Initialize pagination view.

        Args:
            interaction: Original interaction that triggered the view
            collection_data: Dictionary with players, stats, and pagination info
            user_name: Display name of the collection owner
            timeout: Seconds before view times out (default 180)
        """
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.collection_data = collection_data
        self.user_name = user_name
        self.current_page = collection_data["current_page"]
        self.total_pages = collection_data["total_pages"]
        self.message: Optional[discord.Message] = None

        # Update button states
        self._update_buttons()

    def _update_buttons(self):
        """Update button disabled states based on current page."""
        # Buttons will be added in next task
        pass

    async def on_timeout(self):
        """Disable all buttons when view times out."""
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(view=self)
