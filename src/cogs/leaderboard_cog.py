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
        # Will implement after adding buttons
        pass

    async def on_timeout(self):
        """Disable all components on timeout."""
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(view=self)
