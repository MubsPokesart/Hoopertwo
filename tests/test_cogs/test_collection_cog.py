import pytest
import discord
from unittest.mock import AsyncMock, Mock
from src.cogs.collection_cog import CollectionView


@pytest.mark.asyncio
async def test_collection_view_initialization():
    """Test CollectionView initializes with correct pages."""
    mock_interaction = Mock(spec=discord.Interaction)

    collection_data = {
        "players": [
            {"name": "LeBron James", "rarity_tier": "GOAT", "caught_at": "2026-01-18"}
        ],
        "stats": {"total_players": 1, "total_points": 1000},
        "total_pages": 1,
        "current_page": 0
    }

    view = CollectionView(mock_interaction, collection_data, user_name="TestUser")

    assert view.current_page == 0
    assert view.total_pages == 1
