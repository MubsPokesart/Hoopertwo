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
        collection_manager,
        user_id: int,
        server_id: int,
        page_size: int = 9,
        sort_by: str = "time_new",
        timeout: float = 180.0
    ):
        """Initialize pagination view.

        Args:
            interaction: Original interaction that triggered the view
            collection_data: Dictionary with players, stats, and pagination info
            user_name: Display name of the collection owner
            collection_manager: Manager to fetch new pages
            user_id: Discord user ID
            server_id: Discord server ID
            page_size: Number of players per page
            sort_by: Current sort order
            timeout: Seconds before view times out (default 180)
        """
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.collection_data = collection_data
        self.user_name = user_name
        self.collection_manager = collection_manager
        self.user_id = user_id
        self.server_id = server_id
        self.page_size = page_size
        self.sort_by = sort_by
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

    def _fetch_page_data(self):
        """Fetch data for the current page."""
        self.collection_data = self.collection_manager.get_collection(
            user_id=self.user_id,
            server_id=self.server_id,
            page=self.current_page,
            page_size=self.page_size,
            sort_by=self.sort_by
        )
        self.total_pages = self.collection_data["total_pages"]

    def _update_buttons(self):
        """Update button disabled states based on current page."""
        # Get buttons (skip first element which is the select menu)
        first_button = self.children[1]
        prev_button = self.children[2]
        page_button = self.children[3]
        next_button = self.children[4]
        last_button = self.children[5]

        # Disable first/prev if on first page
        first_button.disabled = self.current_page == 0
        prev_button.disabled = self.current_page == 0

        # Disable next/last if on last page
        next_button.disabled = self.current_page >= self.total_pages - 1
        last_button.disabled = self.current_page >= self.total_pages - 1

        # Update page indicator
        page_button.label = f"Page {self.current_page + 1}/{self.total_pages}"

    @discord.ui.select(
        placeholder="Sort by...",
        custom_id="sort_select",
        options=[
            discord.SelectOption(
                label="Time Caught (Newest)",
                value="time_new",
                description="Sort by most recently caught",
                emoji="🕐"
            ),
            discord.SelectOption(
                label="Time Caught (Oldest)",
                value="time_old",
                description="Sort by first caught",
                emoji="🕰️"
            ),
            discord.SelectOption(
                label="Rarity (Best First)",
                value="rarity_best",
                description="Sort by rarest players first",
                emoji="💎"
            ),
            discord.SelectOption(
                label="Rarity (Common First)",
                value="rarity_common",
                description="Sort by most common players first",
                emoji="📊"
            )
        ]
    )
    async def sort_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle sort selection changes."""
        self.sort_by = select.values[0]
        self.current_page = 0  # Reset to first page when changing sort
        self._fetch_page_data()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.gray, custom_id="first")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to first page."""
        self.current_page = 0
        self._fetch_page_data()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.blurple, custom_id="prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._fetch_page_data()
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
        self._fetch_page_data()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="Last ⏭️", style=discord.ButtonStyle.gray, custom_id="last")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to last page."""
        self.current_page = self.total_pages - 1
        self._fetch_page_data()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    async def on_timeout(self):
        """Disable all buttons when view times out."""
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(view=self)


class CollectionCog(commands.Cog):
    """Commands for managing and viewing player collections."""

    def __init__(self, bot: commands.Bot, collection_manager: CollectionManager):
        """Initialize cog.

        Args:
            bot: Discord bot instance
            collection_manager: Collection manager instance
        """
        self.bot = bot
        self.collection_manager = collection_manager

    @app_commands.command(name="collection", description="View your player collection")
    @app_commands.describe(user="User whose collection to view (defaults to yourself)")
    async def collection(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """Display a user's collection with pagination.

        Args:
            interaction: Discord interaction
            user: User to view (defaults to command user)
        """
        # Default to command user
        target_user = user or interaction.user
        page_size = 9  # 3x3 grid in embed
        sort_by = "time_new"  # Default sort

        # Get collection data
        collection_data = self.collection_manager.get_collection(
            user_id=target_user.id,
            server_id=interaction.guild_id,
            page=0,
            page_size=page_size,
            sort_by=sort_by
        )

        # Create view
        view = CollectionView(
            interaction=interaction,
            collection_data=collection_data,
            user_name=target_user.display_name,
            collection_manager=self.collection_manager,
            user_id=target_user.id,
            server_id=interaction.guild_id,
            page_size=page_size,
            sort_by=sort_by
        )

        # Send initial message
        embed = view._create_embed()
        await interaction.response.send_message(embed=embed, view=view)

        # Store message reference for timeout handling
        callback = await interaction.original_response()
        view.message = callback


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize dependencies properly in bot.py
    # from src.database.connection_manager import get_connection_manager
    # from src.database.repositories.collection_repository import CollectionRepository
    # from src.managers.collection_manager import CollectionManager
    #
    # conn = get_connection_manager().get_connection()
    # repo = CollectionRepository(conn)
    # manager = CollectionManager(repo)
    # await bot.add_cog(CollectionCog(bot, manager))
    pass
