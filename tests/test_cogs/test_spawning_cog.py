"""Tests for SpawningCog.

Tests cover:
- Message counting and spawn triggering
- Player recognition with validation
- Rate limiting
- Error handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from src.cogs.spawning_cog import SpawningCog
from src.coordinators.cache_coordinator import CacheCoordinator
from src.managers.spawn_manager import SpawnManager
from src.validators.input_validator import ValidationError


# Helper to create mock discord objects
def create_mock_bot():
    """Create a mock Discord bot."""
    bot = MagicMock(spec=commands.Bot)
    bot.get_context = AsyncMock()
    return bot


def create_mock_message(author_is_bot=False, is_command=False):
    """Create a mock Discord message."""
    message = MagicMock(spec=discord.Message)
    message.author = MagicMock()
    message.author.bot = author_is_bot
    message.channel = MagicMock()
    message.channel.id = 123456789
    message.channel.send = AsyncMock()
    return message


def create_mock_context(channel_id=123456789, author_id=987654321, author_name="TestUser"):
    """Create a mock command context."""
    ctx = MagicMock(spec=commands.Context)
    ctx.channel = MagicMock()
    ctx.channel.id = channel_id
    ctx.author = MagicMock()
    ctx.author.id = author_id
    ctx.author.name = author_name
    ctx.author.mention = f"<@{author_id}>"
    ctx.send = AsyncMock()
    return ctx


def create_mock_spawn_manager():
    """Create a mock spawn manager."""
    spawn_manager = MagicMock(spec=SpawnManager)
    spawn_manager.select_random_player = MagicMock(return_value={
        "id": 1,
        "name": "Michael Jordan",
        "rarity_tier": "GOAT",
        "adp_value": 1.5,
        "image_url": "https://example.com/mj.jpg"
    })
    return spawn_manager


@pytest.fixture
def cache():
    """Fixture for cache coordinator."""
    return CacheCoordinator()


@pytest.fixture
def spawn_manager():
    """Fixture for spawn manager."""
    return create_mock_spawn_manager()


@pytest.fixture
def bot():
    """Fixture for Discord bot."""
    return create_mock_bot()


@pytest.fixture
def spawning_cog(bot, cache, spawn_manager):
    """Fixture for SpawningCog."""
    from unittest.mock import MagicMock
    collection_manager = MagicMock()
    config_manager = MagicMock()
    # Mock get_config to return default threshold
    config_manager.get_config.return_value = {"spawn_threshold": 500, "spawn_channels": []}
    return SpawningCog(bot, cache, spawn_manager, collection_manager, config_manager)


# Test: Message Listener
@pytest.mark.asyncio
async def test_on_message_ignores_bot_messages(spawning_cog, cache):
    """Test that bot messages are ignored."""
    message = create_mock_message(author_is_bot=True)

    await spawning_cog.on_message(message)

    # Message count should not increment
    assert cache.get_message_count(message.channel.id) == 0


@pytest.mark.asyncio
async def test_on_message_ignores_commands(spawning_cog, bot, cache):
    """Test that command messages are ignored."""
    message = create_mock_message()

    # Mock get_context to return a valid command context
    mock_ctx = MagicMock()
    mock_ctx.valid = True
    bot.get_context.return_value = mock_ctx

    await spawning_cog.on_message(message)

    # Message count should not increment
    assert cache.get_message_count(message.channel.id) == 0


@pytest.mark.asyncio
async def test_on_message_increments_count(spawning_cog, bot, cache):
    """Test that regular messages increment count."""
    message = create_mock_message()

    # Mock get_context to return invalid command context
    mock_ctx = MagicMock()
    mock_ctx.valid = False
    bot.get_context.return_value = mock_ctx

    await spawning_cog.on_message(message)

    assert cache.get_message_count(message.channel.id) == 1

    await spawning_cog.on_message(message)
    assert cache.get_message_count(message.channel.id) == 2


@pytest.mark.asyncio
async def test_on_message_triggers_spawn_at_threshold(spawning_cog, bot, cache, spawn_manager):
    """Test that spawn triggers at threshold."""
    message = create_mock_message()

    # Mock get_context to return invalid command context
    mock_ctx = MagicMock()
    mock_ctx.valid = False
    bot.get_context.return_value = mock_ctx

    # Increment to just below threshold
    for _ in range(499):
        cache.increment_message_count(message.channel.id)

    # This message should trigger spawn
    await spawning_cog.on_message(message)

    # Count should be reset to 0
    assert cache.get_message_count(message.channel.id) == 0

    # Active spawn should be set
    active_spawn = cache.get_active_spawn(message.channel.id)
    assert active_spawn is not None
    assert active_spawn["name"] == "Michael Jordan"

    # Channel should have received embed
    message.channel.send.assert_called_once()


# Test: Recognize Command - Success Cases
@pytest.mark.asyncio
async def test_recognize_correct_player(spawning_cog, cache):
    """Test recognizing the correct player."""
    ctx = create_mock_context()

    # Set active spawn
    player = {
        "id": 1,
        "name": "Michael Jordan",
        "rarity_tier": "GOAT",
        "adp_value": 1.5,
        "image_url": "https://example.com/mj.jpg"
    }
    cache.set_active_spawn(ctx.channel.id, player)

    # Recognize with exact name - call callback directly
    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="Michael Jordan")

    # Should send success message
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args
    embed = call_args.kwargs.get('embed')
    assert embed is not None
    assert "caught" in embed.description.lower()

    # Active spawn should be cleared
    assert cache.get_active_spawn(ctx.channel.id) is None


@pytest.mark.asyncio
async def test_recognize_case_insensitive(spawning_cog, cache):
    """Test recognition is case insensitive."""
    ctx = create_mock_context()

    player = {"id": 1, "name": "Michael Jordan", "rarity_tier": "GOAT"}
    cache.set_active_spawn(ctx.channel.id, player)

    # Try different cases
    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="MICHAEL JORDAN")

    ctx.send.assert_called_once()
    assert cache.get_active_spawn(ctx.channel.id) is None


@pytest.mark.asyncio
async def test_recognize_accent_insensitive(spawning_cog, cache):
    """Test recognition handles accents properly."""
    ctx = create_mock_context()

    player = {"id": 1, "name": "Nikola Jokić", "rarity_tier": "GOAT"}
    cache.set_active_spawn(ctx.channel.id, player)

    # Try without accent
    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="Nikola Jokic")

    ctx.send.assert_called_once()
    assert cache.get_active_spawn(ctx.channel.id) is None


@pytest.mark.asyncio
async def test_recognize_punctuation_insensitive(spawning_cog, cache):
    """Test recognition handles punctuation properly."""
    ctx = create_mock_context()

    player = {"id": 1, "name": "J.R. Smith", "rarity_tier": "Common"}
    cache.set_active_spawn(ctx.channel.id, player)

    # Try without dots
    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="JR Smith")

    ctx.send.assert_called_once()
    assert cache.get_active_spawn(ctx.channel.id) is None


# Test: Recognize Command - Error Cases
@pytest.mark.asyncio
async def test_recognize_no_active_spawn(spawning_cog, cache):
    """Test recognizing when no player is spawned."""
    ctx = create_mock_context()

    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="Michael Jordan")

    # Should send error message
    ctx.send.assert_called_once()
    call_args = str(ctx.send.call_args)
    assert "No player to recognize" in call_args


@pytest.mark.asyncio
async def test_recognize_wrong_player(spawning_cog, cache):
    """Test recognizing the wrong player."""
    ctx = create_mock_context()

    player = {"id": 1, "name": "Michael Jordan", "rarity_tier": "GOAT"}
    cache.set_active_spawn(ctx.channel.id, player)

    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="LeBron James")

    # Should send error message
    ctx.send.assert_called_once()
    call_args = str(ctx.send.call_args)
    assert "not the right player" in call_args.lower()

    # Active spawn should NOT be cleared
    assert cache.get_active_spawn(ctx.channel.id) is not None


@pytest.mark.asyncio
async def test_recognize_empty_name(spawning_cog, cache):
    """Test recognizing with empty name triggers validation error."""
    ctx = create_mock_context()

    player = {"id": 1, "name": "Michael Jordan", "rarity_tier": "GOAT"}
    cache.set_active_spawn(ctx.channel.id, player)

    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name="")

    # Should send validation error
    ctx.send.assert_called_once()
    call_args = str(ctx.send.call_args)
    assert "invalid input" in call_args.lower()


@pytest.mark.asyncio
async def test_recognize_too_long_name(spawning_cog, cache):
    """Test recognizing with too long name triggers validation error."""
    ctx = create_mock_context()

    player = {"id": 1, "name": "Michael Jordan", "rarity_tier": "GOAT"}
    cache.set_active_spawn(ctx.channel.id, player)

    # Create name longer than max length (100 characters)
    long_name = "A" * 101
    await spawning_cog.recognize.callback(spawning_cog, ctx, player_name=long_name)

    # Should send validation error
    ctx.send.assert_called_once()
    call_args = str(ctx.send.call_args)
    assert "invalid input" in call_args.lower()


# Test: Error Handler
@pytest.mark.asyncio
async def test_recognize_error_cooldown(spawning_cog):
    """Test error handler for cooldown errors."""
    ctx = create_mock_context()

    # Create cooldown error
    error = commands.CommandOnCooldown(
        cooldown=MagicMock(),
        retry_after=5.5,
        type=commands.BucketType.user
    )

    await spawning_cog.recognize_error(ctx, error)

    # Should send cooldown message
    ctx.send.assert_called_once()
    call_args = str(ctx.send.call_args)
    assert "5.5 seconds" in call_args.lower() or "slow down" in call_args.lower()


@pytest.mark.asyncio
async def test_trigger_spawn_with_no_players(spawning_cog, spawn_manager):
    """Test spawn triggering when no players exist."""
    # Make select_random_player raise ValueError
    spawn_manager.select_random_player.side_effect = ValueError("No players in database")

    channel = MagicMock()
    channel.id = 123456789
    channel.send = AsyncMock()

    # Should not raise error, just log it
    await spawning_cog._trigger_spawn(channel)

    # Channel should not receive a message
    channel.send.assert_not_called()
