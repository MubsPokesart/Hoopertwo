# Batch 9: Admin Configuration System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an admin configuration system that allows server administrators to customize bot behavior including spawn channels, spawn thresholds, and other server-specific settings with proper permission checks.

**Architecture:** Repository for server configuration persistence (ServerConfigRepository), manager for config logic and validation (ConfigManager), and admin-only Discord cog with permission decorators. Uses discord.ui.Modal for interactive configuration and validates all admin permissions before execution.

**Tech Stack:** Python 3.10+, discord.py 2.0+, SQLite3 with parameterized queries, discord.ui.Modal for forms, role-based permission checks

---

## Task 1: Server Config Repository - Create/Get Config

**Files:**
- Create: `src/database/repositories/server_config_repository.py`
- Test: `tests/database/repositories/test_server_config_repository.py`
- Reference: `src/database/models.py:32-40` (server_configs table schema)

**Step 1: Write the failing test**

```python
import pytest
import sqlite3
from src.database.repositories.server_config_repository import ServerConfigRepository
from src.database.connection_manager import ConnectionManager


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    manager = ConnectionManager(":memory:")
    conn = manager.get_connection()
    yield conn
    manager.close()


def test_get_or_create_config_new_server(db_connection):
    """Test getting config for a new server creates defaults."""
    repo = ServerConfigRepository(db_connection)

    config = repo.get_or_create_config(server_id=987654321)

    assert config is not None
    assert config["server_id"] == 987654321
    assert config["spawn_threshold"] == 500  # Default
    assert config["spawn_channels"] == []  # Default empty list
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/repositories/test_server_config_repository.py::test_get_or_create_config_new_server -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.database.repositories.server_config_repository'"

**Step 3: Write minimal implementation**

```python
"""Repository for server configuration database operations."""
import sqlite3
import json
from typing import Dict, Any, List, Optional


class ServerConfigRepository:
    """Handles database operations for server configurations.

    Responsibilities:
    - Create/retrieve server configs
    - Update configuration values
    - All operations use parameterized queries for security
    """

    DEFAULT_SPAWN_THRESHOLD = 500
    DEFAULT_SPAWN_CHANNELS = "[]"

    def __init__(self, connection: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            connection: SQLite database connection
        """
        self.connection = connection

    def get_or_create_config(self, server_id: int) -> Dict[str, Any]:
        """Get server config or create with defaults if not exists.

        Args:
            server_id: Discord server ID

        Returns:
            Dictionary with server configuration
        """
        cursor = self.connection.cursor()

        # Try to get existing config
        cursor.execute(
            """
            SELECT server_id, spawn_channels, spawn_threshold, created_at, updated_at
            FROM server_configs
            WHERE server_id = ?
            """,
            (server_id,)
        )

        row = cursor.fetchone()

        if row:
            return {
                "server_id": row[0],
                "spawn_channels": json.loads(row[1]),
                "spawn_threshold": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }

        # Create default config
        cursor.execute(
            """
            INSERT INTO server_configs (server_id, spawn_channels, spawn_threshold)
            VALUES (?, ?, ?)
            """,
            (server_id, self.DEFAULT_SPAWN_CHANNELS, self.DEFAULT_SPAWN_THRESHOLD)
        )
        self.connection.commit()

        # Return newly created config
        return self.get_or_create_config(server_id)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/repositories/test_server_config_repository.py::test_get_or_create_config_new_server -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/database/repositories/server_config_repository.py tests/database/repositories/test_server_config_repository.py
git commit -m "feat: add server config repository with get or create"
```

---

## Task 2: Server Config Repository - Update Spawn Threshold

**Files:**
- Modify: `src/database/repositories/server_config_repository.py`
- Modify: `tests/database/repositories/test_server_config_repository.py`

**Step 1: Write the failing test**

```python
def test_update_spawn_threshold(db_connection):
    """Test updating spawn threshold."""
    repo = ServerConfigRepository(db_connection)

    # Create config
    repo.get_or_create_config(987654321)

    # Update threshold
    result = repo.update_spawn_threshold(
        server_id=987654321,
        threshold=300
    )

    assert result is True

    # Verify update
    config = repo.get_or_create_config(987654321)
    assert config["spawn_threshold"] == 300
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/repositories/test_server_config_repository.py::test_update_spawn_threshold -v`

Expected: FAIL with "AttributeError: 'ServerConfigRepository' object has no attribute 'update_spawn_threshold'"

**Step 3: Write minimal implementation**

Add to `server_config_repository.py`:

```python
def update_spawn_threshold(self, server_id: int, threshold: int) -> bool:
    """Update spawn threshold for a server.

    Args:
        server_id: Discord server ID
        threshold: New spawn threshold (number of messages)

    Returns:
        True if updated successfully
    """
    cursor = self.connection.cursor()

    cursor.execute(
        """
        UPDATE server_configs
        SET spawn_threshold = ?, updated_at = CURRENT_TIMESTAMP
        WHERE server_id = ?
        """,
        (threshold, server_id)
    )
    self.connection.commit()

    return cursor.rowcount > 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/repositories/test_server_config_repository.py::test_update_spawn_threshold -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/database/repositories/server_config_repository.py tests/database/repositories/test_server_config_repository.py
git commit -m "feat: add update spawn threshold functionality"
```

---

## Task 3: Server Config Repository - Update Spawn Channels

**Files:**
- Modify: `src/database/repositories/server_config_repository.py`
- Modify: `tests/database/repositories/test_server_config_repository.py`

**Step 1: Write the failing test**

```python
def test_update_spawn_channels(db_connection):
    """Test updating spawn channels list."""
    repo = ServerConfigRepository(db_connection)

    # Create config
    repo.get_or_create_config(987654321)

    # Update channels
    channel_ids = [111111, 222222, 333333]
    result = repo.update_spawn_channels(
        server_id=987654321,
        channel_ids=channel_ids
    )

    assert result is True

    # Verify update
    config = repo.get_or_create_config(987654321)
    assert config["spawn_channels"] == channel_ids
    assert len(config["spawn_channels"]) == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/repositories/test_server_config_repository.py::test_update_spawn_channels -v`

Expected: FAIL with "AttributeError: 'ServerConfigRepository' object has no attribute 'update_spawn_channels'"

**Step 3: Write minimal implementation**

Add to `server_config_repository.py`:

```python
def update_spawn_channels(self, server_id: int, channel_ids: List[int]) -> bool:
    """Update spawn channels for a server.

    Args:
        server_id: Discord server ID
        channel_ids: List of channel IDs where spawns are allowed

    Returns:
        True if updated successfully
    """
    cursor = self.connection.cursor()

    # Serialize channel IDs to JSON
    channels_json = json.dumps(channel_ids)

    cursor.execute(
        """
        UPDATE server_configs
        SET spawn_channels = ?, updated_at = CURRENT_TIMESTAMP
        WHERE server_id = ?
        """,
        (channels_json, server_id)
    )
    self.connection.commit()

    return cursor.rowcount > 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/repositories/test_server_config_repository.py::test_update_spawn_channels -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/database/repositories/server_config_repository.py tests/database/repositories/test_server_config_repository.py
git commit -m "feat: add update spawn channels functionality"
```

---

## Task 4: Config Manager - Business Logic Layer

**Files:**
- Create: `src/managers/config_manager.py`
- Test: `tests/managers/test_config_manager.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import Mock
from src.managers.config_manager import ConfigManager, ConfigValidationError


def test_set_spawn_threshold_valid():
    """Test setting spawn threshold with valid value."""
    mock_repo = Mock()
    mock_repo.update_spawn_threshold.return_value = True

    manager = ConfigManager(mock_repo)

    result = manager.set_spawn_threshold(
        server_id=987654321,
        threshold=300
    )

    assert result["success"] is True
    mock_repo.update_spawn_threshold.assert_called_once_with(987654321, 300)


def test_set_spawn_threshold_invalid():
    """Test that invalid threshold raises error."""
    mock_repo = Mock()
    manager = ConfigManager(mock_repo)

    # Too low
    with pytest.raises(ConfigValidationError, match="between 10 and 10000"):
        manager.set_spawn_threshold(987654321, 5)

    # Too high
    with pytest.raises(ConfigValidationError, match="between 10 and 10000"):
        manager.set_spawn_threshold(987654321, 15000)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_config_manager.py::test_set_spawn_threshold_valid -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.managers.config_manager'"

**Step 3: Write minimal implementation**

```python
"""Manager for configuration business logic."""
from typing import Dict, Any, List
from src.database.repositories.server_config_repository import ServerConfigRepository


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages configuration business logic.

    Responsibilities:
    - Validate configuration values
    - Coordinate config updates
    - Provide formatted config data
    """

    MIN_SPAWN_THRESHOLD = 10
    MAX_SPAWN_THRESHOLD = 10000
    MAX_SPAWN_CHANNELS = 50

    def __init__(self, repository: ServerConfigRepository):
        """Initialize manager with repository.

        Args:
            repository: Server config repository instance
        """
        self.repository = repository

    def set_spawn_threshold(
        self,
        server_id: int,
        threshold: int
    ) -> Dict[str, Any]:
        """Set spawn threshold with validation.

        Args:
            server_id: Discord server ID
            threshold: New threshold value

        Returns:
            Dictionary with success status

        Raises:
            ConfigValidationError: If threshold is invalid
        """
        # Validate threshold
        if not (self.MIN_SPAWN_THRESHOLD <= threshold <= self.MAX_SPAWN_THRESHOLD):
            raise ConfigValidationError(
                f"Spawn threshold must be between {self.MIN_SPAWN_THRESHOLD} "
                f"and {self.MAX_SPAWN_THRESHOLD}"
            )

        # Update in database
        success = self.repository.update_spawn_threshold(server_id, threshold)

        return {"success": success, "threshold": threshold}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_config_manager.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/config_manager.py tests/managers/test_config_manager.py
git commit -m "feat: add config manager with validation"
```

---

## Task 5: Config Manager - Manage Spawn Channels

**Files:**
- Modify: `src/managers/config_manager.py`
- Modify: `tests/managers/test_config_manager.py`

**Step 1: Write the failing test**

```python
def test_set_spawn_channels_valid():
    """Test setting spawn channels with valid IDs."""
    mock_repo = Mock()
    mock_repo.update_spawn_channels.return_value = True

    manager = ConfigManager(mock_repo)

    result = manager.set_spawn_channels(
        server_id=987654321,
        channel_ids=[111111, 222222]
    )

    assert result["success"] is True
    assert result["channel_count"] == 2


def test_set_spawn_channels_too_many():
    """Test that too many channels raises error."""
    mock_repo = Mock()
    manager = ConfigManager(mock_repo)

    # Create list exceeding limit
    too_many_channels = list(range(51))

    with pytest.raises(ConfigValidationError, match="maximum of 50"):
        manager.set_spawn_channels(987654321, too_many_channels)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/managers/test_config_manager.py::test_set_spawn_channels_valid -v`

Expected: FAIL with "AttributeError: 'ConfigManager' object has no attribute 'set_spawn_channels'"

**Step 3: Write minimal implementation**

Add to `config_manager.py`:

```python
def set_spawn_channels(
    self,
    server_id: int,
    channel_ids: List[int]
) -> Dict[str, Any]:
    """Set spawn channels with validation.

    Args:
        server_id: Discord server ID
        channel_ids: List of channel IDs

    Returns:
        Dictionary with success status and channel count

    Raises:
        ConfigValidationError: If channel list is invalid
    """
    # Validate channel count
    if len(channel_ids) > self.MAX_SPAWN_CHANNELS:
        raise ConfigValidationError(
            f"Cannot configure more than {self.MAX_SPAWN_CHANNELS} spawn channels"
        )

    # Remove duplicates while preserving order
    unique_channels = list(dict.fromkeys(channel_ids))

    # Update in database
    success = self.repository.update_spawn_channels(server_id, unique_channels)

    return {
        "success": success,
        "channel_count": len(unique_channels)
    }

def get_config(self, server_id: int) -> Dict[str, Any]:
    """Get server configuration.

    Args:
        server_id: Discord server ID

    Returns:
        Server configuration dictionary
    """
    return self.repository.get_or_create_config(server_id)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/managers/test_config_manager.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/managers/config_manager.py tests/managers/test_config_manager.py
git commit -m "feat: add spawn channels management with validation"
```

---

## Task 6: Admin Cog - Permission Checks

**Files:**
- Create: `src/cogs/admin_cog.py`
- Create: `src/utils/permission_checks.py`
- Test: Manual testing (Discord permission checks require server context)

**Step 1: Write permission checker utility**

```python
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
```

**Step 2: Create admin cog structure**

```python
"""Admin configuration Discord cog."""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
from src.managers.config_manager import ConfigManager, ConfigValidationError
from src.utils.permission_checks import is_admin


class AdminCog(commands.Cog):
    """Admin-only commands for server configuration.

    All commands require Administrator permission.
    """

    def __init__(self, bot: commands.Bot, config_manager: ConfigManager):
        """Initialize cog.

        Args:
            bot: Discord bot instance
            config_manager: Config manager instance
        """
        self.bot = bot
        self.config_manager = config_manager

    @app_commands.command(name="config", description="View current server configuration")
    @commands.check(is_admin())
    async def view_config(self, interaction: discord.Interaction):
        """Display current server configuration.

        Args:
            interaction: Discord interaction
        """
        config = self.config_manager.get_config(interaction.guild_id)

        embed = discord.Embed(
            title="⚙️ Server Configuration",
            description=f"Settings for {interaction.guild.name}",
            color=discord.Color.blue()
        )

        # Spawn threshold
        embed.add_field(
            name="Spawn Threshold",
            value=f"{config['spawn_threshold']} messages",
            inline=False
        )

        # Spawn channels
        if config["spawn_channels"]:
            channels_text = "\n".join([
                f"<#{channel_id}>" for channel_id in config["spawn_channels"]
            ])
        else:
            channels_text = "All channels (not configured)"

        embed.add_field(
            name="Spawn Channels",
            value=channels_text,
            inline=False
        )

        embed.set_footer(text=f"Last updated: {config['updated_at']}")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Load the cog.

    Args:
        bot: Discord bot instance
    """
    # TODO: Initialize in bot.py with proper dependencies
    pass
```

**Step 3: Commit**

```bash
git add src/cogs/admin_cog.py src/utils/permission_checks.py
git commit -m "feat: add admin cog with permission checks"
```

---

## Task 7: Admin Cog - Set Spawn Threshold Command

**Files:**
- Modify: `src/cogs/admin_cog.py`

**Step 1: Add set threshold command**

```python
# Add after view_config command in AdminCog class

@app_commands.command(
    name="set-spawn-threshold",
    description="Set how many messages trigger a spawn"
)
@app_commands.describe(threshold="Number of messages before spawn (10-10000)")
@commands.check(is_admin())
async def set_spawn_threshold(
    self,
    interaction: discord.Interaction,
    threshold: app_commands.Range[int, 10, 10000]
):
    """Set spawn threshold for the server.

    Args:
        interaction: Discord interaction
        threshold: Messages needed to trigger spawn
    """
    try:
        result = self.config_manager.set_spawn_threshold(
            server_id=interaction.guild_id,
            threshold=threshold
        )

        if result["success"]:
            embed = discord.Embed(
                title="✅ Spawn Threshold Updated",
                description=f"Players will now spawn after **{threshold} messages**",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Update Failed",
                description="Failed to update spawn threshold",
                color=discord.Color.red()
            )

    except ConfigValidationError as e:
        embed = discord.Embed(
            title="❌ Invalid Configuration",
            description=str(e),
            color=discord.Color.red()
        )

    await interaction.response.send_message(embed=embed)
```

**Step 2: Commit**

```bash
git add src/cogs/admin_cog.py
git commit -m "feat: add set spawn threshold command"
```

---

## Task 8: Admin Cog - Set Spawn Channels Command

**Files:**
- Modify: `src/cogs/admin_cog.py`

**Step 1: Add set channels command**

```python
# Add after set_spawn_threshold command in AdminCog class

@app_commands.command(
    name="set-spawn-channels",
    description="Configure which channels can have player spawns"
)
@app_commands.describe(
    channels="Channels where spawns are allowed (mention multiple with space)"
)
@commands.check(is_admin())
async def set_spawn_channels(
    self,
    interaction: discord.Interaction,
    channels: str
):
    """Set spawn channels for the server.

    Args:
        interaction: Discord interaction
        channels: Space-separated channel mentions
    """
    # Parse channel mentions
    channel_ids = []
    for mention in channels.split():
        # Extract channel ID from mention <#123456>
        if mention.startswith("<#") and mention.endswith(">"):
            try:
                channel_id = int(mention[2:-1])
                channel_ids.append(channel_id)
            except ValueError:
                pass

    if not channel_ids:
        embed = discord.Embed(
            title="❌ No Valid Channels",
            description="Please mention channels using #channel-name",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        result = self.config_manager.set_spawn_channels(
            server_id=interaction.guild_id,
            channel_ids=channel_ids
        )

        if result["success"]:
            channels_list = "\n".join([f"<#{cid}>" for cid in channel_ids])
            embed = discord.Embed(
                title="✅ Spawn Channels Updated",
                description=f"Players will spawn in these channels:\n{channels_list}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Update Failed",
                description="Failed to update spawn channels",
                color=discord.Color.red()
            )

    except ConfigValidationError as e:
        embed = discord.Embed(
            title="❌ Invalid Configuration",
            description=str(e),
            color=discord.Color.red()
        )

    await interaction.response.send_message(embed=embed)


@app_commands.command(
    name="clear-spawn-channels",
    description="Allow spawns in all channels (remove restrictions)"
)
@commands.check(is_admin())
async def clear_spawn_channels(self, interaction: discord.Interaction):
    """Clear spawn channel restrictions.

    Args:
        interaction: Discord interaction
    """
    result = self.config_manager.set_spawn_channels(
        server_id=interaction.guild_id,
        channel_ids=[]
    )

    if result["success"]:
        embed = discord.Embed(
            title="✅ Spawn Channels Cleared",
            description="Players can now spawn in any channel",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="❌ Clear Failed",
            description="Failed to clear spawn channels",
            color=discord.Color.red()
        )

    await interaction.response.send_message(embed=embed)
```

**Step 2: Commit**

```bash
git add src/cogs/admin_cog.py
git commit -m "feat: add spawn channel configuration commands"
```

---

## Task 9: Integrate Config with Spawning System

**Files:**
- Modify: `src/cogs/spawning_cog.py`

**Step 1: Update spawning to check config**

```python
# In SpawningCog __init__, add:
# self.config_manager = config_manager

# Update on_message event listener to check spawn channels:

@commands.Cog.listener()
async def on_message(self, message: discord.Message):
    """Track messages and trigger spawns.

    Args:
        message: Discord message
    """
    # Ignore bots and DMs
    if message.author.bot or not message.guild:
        return

    # Get server config
    config = self.config_manager.get_config(message.guild.id)

    # Check if spawns are allowed in this channel
    if config["spawn_channels"]:  # If list is not empty
        if message.channel.id not in config["spawn_channels"]:
            return  # Skip this channel

    # Increment message count
    count = self.cache.increment_message_count(message.channel.id)

    # Get spawn threshold from config
    threshold = config["spawn_threshold"]

    # Trigger spawn if threshold reached
    if count >= threshold:
        await self._trigger_spawn(message.channel)
```

**Step 2: Update spawning_cog setup**

```python
# Update setup function signature:
async def setup(bot, cache, spawn_manager, collection_manager, config_manager):
    """Load the cog."""
    await bot.add_cog(SpawningCog(bot, cache, spawn_manager, collection_manager, config_manager))
```

**Step 3: Commit**

```bash
git add src/cogs/spawning_cog.py
git commit -m "feat: integrate config manager with spawning system"
```

---

## Testing & Validation

**Run repository tests:**
```bash
poetry run pytest tests/database/repositories/test_server_config_repository.py -v
```

**Run manager tests:**
```bash
poetry run pytest tests/managers/test_config_manager.py -v
```

**Manual testing:**
1. Run bot as administrator
2. Test `/config` to view settings
3. Test `/set-spawn-threshold 300`
4. Test `/set-spawn-channels #general #spawns`
5. Test `/clear-spawn-channels`
6. Verify non-admins cannot use commands
7. Verify spawning respects channel restrictions

**Coverage check:**
```bash
poetry run pytest --cov=src/database/repositories --cov=src/managers tests/
```

---

## References

**Discord.py Documentation:**
- [Permission Checks](https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.check)
- [App Commands Ranges](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.app_commands.Range)

**Permission Best Practices:**
- [Discord Role Commands](https://dev.to/swislokdev/discord-role-commands-7p6)
- [Bot Permissions Guide](https://app.studyraid.com/en/read/7183/176794/understanding-bot-permissions-and-scopes)
- [RBAC Implementation](https://app.studyraid.com/en/read/7183/176816/implementing-user-authentication-and-authorization)

**Input Validation:**
- [Discord Input Sanitization](https://guide.pycord.dev/getting-started/rules-and-common-practices)

---

**Plan saved to:** `docs/plans/2026-01-18-batch-09-admin-configuration.md`
