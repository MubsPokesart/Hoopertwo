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

    def _create_embed(self) -> discord.Embed:
        """Create embed for current page."""
        stats = self.collection_data["stats"]
        players = self.collection_data["players"]

        embed = discord.Embed(
            title=f"🏀 {self.user_name}'s Collection",
            description=f"**Total Players:** {stats['total_players']} | **Points:** {stats['total_points']:,}",
            color=discord.Color.gold()
        )

        # Add rarity breakdown
        rarity_text = " | ".join([
            f"{tier}: {count}" for tier, count in stats["rarity_counts"].items()
        ])
        embed.add_field(name="Rarity Breakdown", value=rarity_text, inline=False)

        # Add players on this page
        if players:
            for player in players:
                embed.add_field(
                    name=f"{player['name']} ({player['rarity_tier']})",
                    value=f"Caught: {player['caught_at'][:10]}",
                    inline=True
                )
        else:
            embed.add_field(name="No players yet!", value="Start recognizing players to build your collection.", inline=False)

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")

        return embed

    def _update_buttons(self):
        """Update button disabled states based on current page."""
        # Get buttons
        first_button = self.children[0]
        prev_button = self.children[1]
        page_button = self.children[2]
        next_button = self.children[3]
        last_button = self.children[4]

        # Disable first/prev if on first page
        first_button.disabled = self.current_page == 0
        prev_button.disabled = self.current_page == 0

        # Disable next/last if on last page
        next_button.disabled = self.current_page >= self.total_pages - 1
        last_button.disabled = self.current_page >= self.total_pages - 1

        # Update page indicator
        page_button.label = f"Page {self.current_page + 1}/{self.total_pages}"

    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.gray, custom_id="first")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to first page."""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.blurple, custom_id="prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.green, custom_id="page", disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page indicator (disabled button)."""
        pass

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.blurple, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="Last ⏭️", style=discord.ButtonStyle.gray, custom_id="last")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to last page."""
        self.current_page = self.total_pages - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    async def on_timeout(self):
        """Disable all buttons when view times out."""
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(view=self)
