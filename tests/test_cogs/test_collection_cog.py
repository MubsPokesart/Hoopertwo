import pytest
import discord
from unittest.mock import Mock
from src.cogs.collection_cog import CollectionView


@pytest.mark.asyncio
async def test_collection_view_initialization():
    """Test CollectionView initializes with correct pages."""
    mock_interaction = Mock(spec=discord.Interaction)
    mock_manager = Mock()

    collection_data = {
        "players": [{"name": "LeBron James", "rarity_tier": "GOAT", "caught_at": "2026-01-18"}],
        "stats": {"total_players": 1, "total_points": 1000, "rarity_counts": {"GOAT": 1}},
        "total_pages": 1,
        "current_page": 0,
    }

    view = CollectionView(
        interaction=mock_interaction,
        collection_data=collection_data,
        user_name="TestUser",
        collection_manager=mock_manager,
        user_id=123456789,
        server_id=987654321,
    )

    assert view.current_page == 0
    assert view.total_pages == 1


@pytest.mark.asyncio
async def test_collection_view_labels_phantom_editions():
    mock_interaction = Mock(spec=discord.Interaction)
    collection_data = {
        "players": [
            {
                "name": "Kevin Garnett",
                "rarity_tier": "Cosmic",
                "edition": "Phantom",
                "caught_at": "2026-07-30",
            }
        ],
        "stats": {
            "total_players": 1,
            "total_points": 900,
            "rarity_counts": {"Cosmic": 1},
            "phantom_count": 1,
        },
        "total_pages": 1,
        "current_page": 0,
    }
    view = CollectionView(
        interaction=mock_interaction,
        collection_data=collection_data,
        user_name="TestUser",
        collection_manager=Mock(),
        user_id=123456789,
        server_id=987654321,
    )

    embed = view._create_embed()

    assert any(field.name == "Phantom Kevin Garnett (Cosmic)" for field in embed.fields)
    assert any(field.name == "Phantom Editions" and field.value == "1" for field in embed.fields)
