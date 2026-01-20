"""Leaderboard system Discord cog."""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from src.managers.leaderboard_manager import LeaderboardManager


class LeaderboardView(discord.ui.View):
    """Interactive view for displaying leaderboards.

    Features:
    - Period selection dropdown (weekly, monthly, yearly, all-time)
    - Page navigation buttons
    - Auto-disable on timeout
    """

    PERIOD_LABELS = {
        "weekly": "📅 Weekly",
        "monthly": "📆 Monthly",
        "yearly": "🗓️ Yearly",
        "alltime": "♾️ All Time"
    }

    def __init__(
        self,
        interaction: discord.Interaction,
        leaderboard_manager: LeaderboardManager,
        server_id: int,
        initial_period: str = "weekly",
        timeout: float = 180.0
    ):
        """Initialize leaderboard view.

        Args:
            interaction: Original interaction
            leaderboard_manager: Leaderboard manager instance
            server_id: Discord server ID
            initial_period: Starting time period
            timeout: Seconds before timeout
        """
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.manager = leaderboard_manager
        self.server_id = server_id
        self.current_period = initial_period
        self.current_page = 0
        self.rankings_data = None
        self.message: Optional[discord.Message] = None

        # Load initial data
        self._load_rankings()
        self._update_buttons()

    def _load_rankings(self):
        """Load rankings data for current period and page."""
        self.rankings_data = self.manager.get_rankings(
            server_id=self.server_id,
            period=self.current_period,
            page=self.current_page,
            page_size=10
        )

    def _create_embed(self) -> discord.Embed:
        """Create embed for current rankings."""
        period_label = self.PERIOD_LABELS.get(self.current_period, self.current_period)

        embed = discord.Embed(
            title=f"🏆 Leaderboard - {period_label}",
            description="Top players ranked by collection points",
            color=discord.Color.gold()
        )

        # Add rankings
        if self.rankings_data["rankings"]:
            ranking_text = []
            for entry in self.rankings_data["rankings"]:
                rank = entry["rank"]
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"**#{rank}**"
                ranking_text.append(
                    f"{medal} <@{entry['user_id']}> - {entry['points']:,} pts ({entry['player_count']} players)"
                )

            embed.add_field(
                name="Rankings",
                value="\n".join(ranking_text),
                inline=False
            )
        else:
            embed.add_field(
                name="No Rankings Yet",
                value="Start collecting players to appear on the leaderboard!",
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.rankings_data['total_pages']}")

        return embed

    def _update_buttons(self):
        """Update button states based on current page."""
        # Get buttons (skip select menu at index 0)
        first_button = self.children[1]
        prev_button = self.children[2]
        page_button = self.children[3]
        next_button = self.children[4]
        last_button = self.children[5]

        # Disable first/prev if on first page
        first_button.disabled = self.current_page == 0
        prev_button.disabled = self.current_page == 0

        # Disable next/last if on last page
        total_pages = self.rankings_data["total_pages"]
        next_button.disabled = self.current_page >= total_pages - 1
        last_button.disabled = self.current_page >= total_pages - 1

        # Update page indicator
        page_button.label = f"Page {self.current_page + 1}/{total_pages}"

    @discord.ui.select(
        placeholder="Select Time Period",
        options=[
            discord.SelectOption(label="Weekly", value="weekly", emoji="📅", default=True),
            discord.SelectOption(label="Monthly", value="monthly", emoji="📆"),
            discord.SelectOption(label="Yearly", value="yearly", emoji="🗓️"),
            discord.SelectOption(label="All Time", value="alltime", emoji="♾️")
        ]
    )
    async def period_selector(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle period selection."""
        self.current_period = select.values[0]
        self.current_page = 0  # Reset to first page

        # Update dropdown default
        for option in select.options:
            option.default = (option.value == self.current_period)

        self._load_rankings()
        self._update_buttons()

        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.gray, custom_id="lb_first")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to first page."""
        self.current_page = 0
        self._load_rankings()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.blurple, custom_id="lb_prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        self.current_page = max(0, self.current_page - 1)
        self._load_rankings()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.green, custom_id="lb_page", disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page indicator (disabled button)."""
        pass

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.blurple, custom_id="lb_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        self.current_page = min(self.rankings_data["total_pages"] - 1, self.current_page + 1)
        self._load_rankings()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    @discord.ui.button(label="Last ⏭️", style=discord.ButtonStyle.gray, custom_id="lb_last")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to last page."""
        self.current_page = self.rankings_data["total_pages"] - 1
        self._load_rankings()
        self._update_buttons()
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    async def on_timeout(self):
        """Disable all components on timeout."""
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(view=self)


class LeaderboardCog(commands.Cog):
    """Commands for viewing leaderboards and rankings."""

    def __init__(self, bot: commands.Bot, leaderboard_manager: LeaderboardManager):
        """Initialize cog.

        Args:
            bot: Discord bot instance
            leaderboard_manager: Leaderboard manager instance
        """
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager

    @app_commands.command(name="leaderboard", description="View server leaderboard")
    @app_commands.describe(period="Time period to view (defaults to weekly)")
    @app_commands.choices(period=[
        app_commands.Choice(name="Weekly", value="weekly"),
        app_commands.Choice(name="Monthly", value="monthly"),
        app_commands.Choice(name="Yearly", value="yearly"),
        app_commands.Choice(name="All Time", value="alltime")
    ])
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str] = None
    ):
        """Display server leaderboard with rankings.

        Args:
            interaction: Discord interaction
            period: Time period to display
        """
        selected_period = period.value if period else "weekly"

        # Create view
        view = LeaderboardView(
            interaction=interaction,
            leaderboard_manager=self.leaderboard_manager,
            server_id=interaction.guild_id,
            initial_period=selected_period
        )

        # Send initial message
        embed = view._create_embed()
        await interaction.response.send_message(embed=embed, view=view)

        # Store message reference
        callback = await interaction.original_response()
        view.message = callback

    @app_commands.command(name="rank", description="Check your current rank")
    @app_commands.describe(
        period="Time period to check (defaults to all-time)",
        user="User to check rank for (defaults to yourself)"
    )
    @app_commands.choices(period=[
        app_commands.Choice(name="Weekly", value="weekly"),
        app_commands.Choice(name="Monthly", value="monthly"),
        app_commands.Choice(name="Yearly", value="yearly"),
        app_commands.Choice(name="All Time", value="alltime")
    ])
    async def rank(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str] = None,
        user: Optional[discord.Member] = None
    ):
        """Check your or another user's rank.

        Args:
            interaction: Discord interaction
            period: Time period to check
            user: User to check (defaults to command user)
        """
        target_user = user or interaction.user
        selected_period = period.value if period else "alltime"

        # Get user's rank
        rank_data = self.leaderboard_manager.leaderboard_repo.get_user_rank(
            user_id=target_user.id,
            server_id=interaction.guild_id,
            period=selected_period
        )

        period_label = LeaderboardView.PERIOD_LABELS.get(selected_period, selected_period)

        if rank_data:
            embed = discord.Embed(
                title=f"📊 Rank - {period_label}",
                description=f"**{target_user.display_name}'s Stats**",
                color=discord.Color.blue()
            )
            embed.add_field(name="Rank", value=f"#{rank_data['rank']}", inline=True)
            embed.add_field(name="Points", value=f"{rank_data['points']:,}", inline=True)
            embed.add_field(name="Players", value=str(rank_data['player_count']), inline=True)
        else:
            embed = discord.Embed(
                title=f"📊 Rank - {period_label}",
                description=f"{target_user.display_name} has no ranking yet!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Get Started",
                value="Catch players using `/recognize` to start building your collection!",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize in bot.py with proper dependencies
    pass
