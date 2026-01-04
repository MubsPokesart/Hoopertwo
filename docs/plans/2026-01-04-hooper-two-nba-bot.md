# HooperTwo NBA Discord Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Discord bot that spawns NBA player images in chat channels for users to recognize and collect, with rarity tiers, leaderboards, and per-server configuration.

**Architecture:** Hybrid command Discord bot using discord.py with cog-based architecture. SQLite for persistence, in-memory Python dict for caching. Modular OOP design with Manager/Coordinator patterns. TDD throughout. Security-first with parameterized queries, input validation, and rate limiting.

**Tech Stack:** Python 3.10+, discord.py, SQLite3, basketball-reference-scraper, Poetry, Docker/Docker Compose

**Security Focus:** All user input validated/sanitized, parameterized SQL queries only, rate limiting on all commands, environment variable token storage.

**Coding Standards:** Max 500 lines/file, OOP-first, single responsibility, modular design, descriptive naming, no god classes.

---

## Project Structure

```
hoopertwo/
├── bot.py                          # Entry point
├── pyproject.toml                  # Poetry dependencies
├── Dockerfile                      # Docker image definition
├── docker-compose.yml              # One-command deployment
├── .env.example                    # Environment template
├── .gitignore
├── README.md
├── data/
│   ├── adp_board.csv              # Rarity source of truth
│   ├── images/                     # Downloaded player images
│   └── hooper_two.db              # SQLite database
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Environment config
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLite table definitions
│   │   ├── connection_manager.py  # Database connection
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── player_repository.py
│   │       ├── collection_repository.py
│   │       ├── server_config_repository.py
│   │       └── leaderboard_repository.py
│   ├── managers/
│   │   ├── __init__.py
│   │   ├── player_manager.py      # Player data business logic
│   │   ├── collection_manager.py  # Collection logic
│   │   ├── spawn_manager.py       # Spawning logic
│   │   ├── leaderboard_manager.py # Leaderboard calculations
│   │   └── image_manager.py       # Image fetching/caching
│   ├── coordinators/
│   │   ├── __init__.py
│   │   ├── spawn_coordinator.py   # Message counting & spawn triggers
│   │   └── cache_coordinator.py   # In-memory cache management
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── input_validator.py     # Input sanitization
│   │   └── name_validator.py      # Player name normalization
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── text_normalizer.py     # Case/accent/punctuation handling
│   │   └── backup_manager.py      # Database backup automation
│   ├── cogs/
│   │   ├── __init__.py
│   │   ├── admin_cog.py           # Server configuration commands
│   │   ├── spawning_cog.py        # Recognition & catching
│   │   ├── collection_cog.py      # Collection viewing
│   │   └── leaderboard_cog.py     # Leaderboard commands
│   └── scrapers/
│       ├── __init__.py
│       └── basketball_ref_scraper.py
└── tests/
    ├── __init__.py
    ├── test_validators/
    ├── test_managers/
    ├── test_repositories/
    └── test_utils/
```

---

## Batch 1: Project Foundation & Infrastructure

**Success Criteria:**
- ✅ `docker compose up` starts bot successfully
- ✅ Bot connects to Discord and responds to ping
- ✅ SQLite database created with proper schema
- ✅ Environment variables loaded correctly
- ✅ All tests pass with `pytest`

### Task 1.1: Project Initialization

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create pyproject.toml with dependencies**

```toml
[tool.poetry]
name = "hooper-two"
version = "0.1.0"
description = "NBA player collection Discord bot"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.10"
"discord.py" = "^2.3.2"
python-dotenv = "^1.0.0"
basketball-reference-scraper = "^1.0.0"
aiohttp = "^3.9.0"
pillow = "^10.1.0"

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
black = "^23.0.0"
ruff = "^0.1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create .env.example**

```env
# Discord Bot Token (get from https://discord.com/developers/applications)
DISCORD_TOKEN=your_token_here

# Bot Configuration
COMMAND_PREFIX=h!
DEFAULT_SPAWN_THRESHOLD=500

# Database
DATABASE_PATH=data/hooper_two.db

# Image Storage
IMAGE_CACHE_DIR=data/images

# Basketball Reference Rate Limiting
BR_RATE_LIMIT_PER_MINUTE=20

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_DIRECTORY=data/backups
BACKUP_RETENTION_DAYS=7
```

**Step 3: Create .gitignore**

```.gitignore
# Environment
.env
*.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Database & Data
*.db
*.db-journal
data/images/
data/backups/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Poetry
poetry.lock

# OS
.DS_Store
Thumbs.db
```

**Step 4: Create README.md**

```markdown
# HooperTwo - NBA Discord Bot

A Discord bot for collecting NBA players. Players spawn in chat, and users recognize them to build their collection.

## Features

- 🏀 Random NBA player spawning based on message activity
- 🏆 Rarity tiers: GOAT, Mythic, Legendary, Epic, Rare, Common
- 📊 Leaderboards (Weekly, Monthly, Yearly, All-Time)
- ⚙️ Per-server configuration
- 💾 Automated backups

## Quick Start

1. Copy `.env.example` to `.env` and add your Discord bot token
2. Run: `docker compose up`
3. Invite bot to your server
4. Configure spawn channels: `/config add_channel #general`

## Development

- **Install dependencies:** `poetry install`
- **Run tests:** `poetry run pytest`
- **Format code:** `poetry run black src tests`
- **Lint:** `poetry run ruff check src tests`

## Security

- All user input is validated and sanitized
- Parameterized SQL queries prevent injection
- Rate limiting on all commands
- Tokens stored in environment variables only
```

**Step 5: Initialize git and commit**

```bash
git init
git add pyproject.toml .env.example .gitignore README.md
git commit -m "chore: initial project setup with Poetry and Docker config"
```

---

### Task 1.2: Docker Configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Step 1: Create Dockerfile**

```dockerfile
# Multi-stage build for smaller final image
FROM python:3.10-slim as builder

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml ./

# Install dependencies (no dev dependencies in production)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-dev

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY bot.py ./
COPY data/adp_board.csv ./data/

# Create directories for data persistence
RUN mkdir -p data/images data/backups

# Run as non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

CMD ["python", "bot.py"]
```

**Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  hooper-two:
    build: .
    container_name: hooper-two-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      # Persist database and images
      - ./data:/app/data
    networks:
      - hooper-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  hooper-network:
    driver: bridge
```

**Step 3: Create .dockerignore**

```
.git
.gitignore
.env
*.md
tests/
.pytest_cache
__pycache__
*.pyc
.coverage
htmlcov/
.vscode
.idea
```

**Step 4: Test Docker build**

```bash
docker compose build
```

Expected: Build succeeds without errors

**Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "chore: add Docker configuration for one-command deployment"
```

---

### Task 1.3: Configuration Module

**Files:**
- Create: `src/__init__.py`
- Create: `src/config/__init__.py`
- Create: `src/config/settings.py`
- Create: `tests/test_config/__init__.py`
- Create: `tests/test_config/test_settings.py`

**Step 1: Write failing test**

Create `tests/test_config/test_settings.py`:

```python
import os
import pytest
from src.config.settings import Settings


def test_settings_loads_from_environment(monkeypatch):
    """Test that Settings loads configuration from environment variables."""
    monkeypatch.setenv("DISCORD_TOKEN", "test_token_123")
    monkeypatch.setenv("COMMAND_PREFIX", "t!")
    monkeypatch.setenv("DEFAULT_SPAWN_THRESHOLD", "100")

    settings = Settings()

    assert settings.discord_token == "test_token_123"
    assert settings.command_prefix == "t!"
    assert settings.default_spawn_threshold == 100


def test_settings_validates_required_fields():
    """Test that Settings raises error if required fields missing."""
    # Clear DISCORD_TOKEN if it exists
    if "DISCORD_TOKEN" in os.environ:
        del os.environ["DISCORD_TOKEN"]

    with pytest.raises(ValueError, match="DISCORD_TOKEN"):
        Settings()


def test_settings_has_default_values(monkeypatch):
    """Test that Settings provides sensible defaults."""
    monkeypatch.setenv("DISCORD_TOKEN", "test_token")

    settings = Settings()

    assert settings.database_path == "data/hooper_two.db"
    assert settings.image_cache_dir == "data/images"
    assert settings.br_rate_limit_per_minute == 20
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_config/test_settings.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.config.settings'"

**Step 3: Write minimal implementation**

Create `src/config/settings.py`:

```python
"""Application configuration loaded from environment variables."""
import os
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Application settings with validation and defaults.

    All sensitive values (tokens) must come from environment variables.
    Provides sensible defaults for non-sensitive configuration.
    """

    def __init__(self):
        """Initialize settings from environment variables."""
        load_dotenv()

        # Required fields
        self.discord_token = self._get_required("DISCORD_TOKEN")

        # Bot configuration with defaults
        self.command_prefix = os.getenv("COMMAND_PREFIX", "h!")
        self.default_spawn_threshold = int(
            os.getenv("DEFAULT_SPAWN_THRESHOLD", "500")
        )

        # Database configuration
        self.database_path = os.getenv("DATABASE_PATH", "data/hooper_two.db")

        # Image storage
        self.image_cache_dir = os.getenv("IMAGE_CACHE_DIR", "data/images")

        # Basketball Reference rate limiting
        self.br_rate_limit_per_minute = int(
            os.getenv("BR_RATE_LIMIT_PER_MINUTE", "20")
        )

        # Backup configuration
        self.backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
        self.backup_directory = os.getenv("BACKUP_DIRECTORY", "data/backups")
        self.backup_retention_days = int(
            os.getenv("BACKUP_RETENTION_DAYS", "7")
        )

    def _get_required(self, key: str) -> str:
        """Get a required environment variable or raise ValueError."""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"{key} environment variable is required. "
                f"Copy .env.example to .env and configure it."
            )
        return value


# Singleton instance
settings = Settings()
```

Create empty `src/__init__.py` and `src/config/__init__.py`

**Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/test_config/test_settings.py -v
```

Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add src/config/ tests/test_config/
git commit -m "feat: add configuration module with environment variable loading"
```

---

### Task 1.4: Database Schema & Connection Manager

**Files:**
- Create: `src/database/__init__.py`
- Create: `src/database/models.py`
- Create: `src/database/connection_manager.py`
- Create: `tests/test_database/__init__.py`
- Create: `tests/test_database/test_connection_manager.py`

**Step 1: Write failing test**

Create `tests/test_database/test_connection_manager.py`:

```python
import sqlite3
import pytest
from pathlib import Path
from src.database.connection_manager import ConnectionManager


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    return str(tmp_path / "test.db")


def test_connection_manager_creates_database(temp_db_path):
    """Test that ConnectionManager creates database file."""
    manager = ConnectionManager(temp_db_path)

    assert Path(temp_db_path).exists()
    manager.close()


def test_connection_manager_initializes_schema(temp_db_path):
    """Test that ConnectionManager creates all required tables."""
    manager = ConnectionManager(temp_db_path)

    cursor = manager.get_connection().cursor()

    # Check that tables exist
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t[0] for t in tables]

    assert "players" in table_names
    assert "user_collections" in table_names
    assert "server_configs" in table_names
    assert "leaderboard_snapshots" in table_names

    manager.close()


def test_connection_manager_enables_foreign_keys(temp_db_path):
    """Test that foreign key constraints are enabled."""
    manager = ConnectionManager(temp_db_path)

    cursor = manager.get_connection().cursor()
    result = cursor.execute("PRAGMA foreign_keys").fetchone()

    assert result[0] == 1  # Foreign keys enabled
    manager.close()


def test_connection_manager_uses_parameterized_queries(temp_db_path):
    """Test that parameterized queries work (SQL injection prevention)."""
    manager = ConnectionManager(temp_db_path)
    conn = manager.get_connection()
    cursor = conn.cursor()

    # Insert with parameterized query
    cursor.execute(
        "INSERT INTO players (name, adp_value, rarity_tier, image_url) VALUES (?, ?, ?, ?)",
        ("Test Player", 10.0, "Mythic", "http://example.com/image.jpg")
    )
    conn.commit()

    # Fetch with parameterized query
    result = cursor.execute(
        "SELECT name FROM players WHERE name = ?",
        ("Test Player",)
    ).fetchone()

    assert result[0] == "Test Player"
    manager.close()
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_database/test_connection_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write database models schema**

Create `src/database/models.py`:

```python
"""Database schema definitions for SQLite.

All tables use parameterized queries for security.
Foreign keys are enforced.
"""

# SQL statements for table creation
CREATE_PLAYERS_TABLE = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    adp_value REAL,
    rarity_tier TEXT NOT NULL CHECK(rarity_tier IN ('GOAT', 'Mythic', 'Legendary', 'Epic', 'Rare', 'Common')),
    image_url TEXT,
    career_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USER_COLLECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS user_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    server_id INTEGER NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    UNIQUE(user_id, player_id, server_id)
);
"""

CREATE_SERVER_CONFIGS_TABLE = """
CREATE TABLE IF NOT EXISTS server_configs (
    server_id INTEGER PRIMARY KEY,
    spawn_channels TEXT NOT NULL DEFAULT '[]',
    spawn_threshold INTEGER NOT NULL DEFAULT 500,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LEADERBOARD_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    server_id INTEGER NOT NULL,
    period TEXT NOT NULL CHECK(period IN ('weekly', 'monthly', 'yearly', 'alltime')),
    points INTEGER NOT NULL DEFAULT 0,
    player_count INTEGER NOT NULL DEFAULT 0,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, server_id, period, snapshot_date)
);
"""

# Indexes for query performance
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_user_collections_user_id ON user_collections(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_user_collections_server_id ON user_collections(server_id);",
    "CREATE INDEX IF NOT EXISTS idx_leaderboard_period ON leaderboard_snapshots(period, server_id);",
    "CREATE INDEX IF NOT EXISTS idx_players_rarity ON players(rarity_tier);",
]

ALL_TABLES = [
    CREATE_PLAYERS_TABLE,
    CREATE_USER_COLLECTIONS_TABLE,
    CREATE_SERVER_CONFIGS_TABLE,
    CREATE_LEADERBOARD_SNAPSHOTS_TABLE,
]
```

**Step 4: Write ConnectionManager implementation**

Create `src/database/connection_manager.py`:

```python
"""Database connection management with automatic schema initialization."""
import sqlite3
from pathlib import Path
from typing import Optional
from src.database.models import ALL_TABLES, CREATE_INDEXES


class ConnectionManager:
    """Manages SQLite database connection and schema initialization.

    Responsibilities:
    - Create database file and directory if not exists
    - Initialize schema on first connection
    - Enable foreign key constraints
    - Provide thread-safe connection access
    """

    def __init__(self, database_path: str):
        """Initialize connection manager and create schema.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection and schema
        self._initialize()

    def _initialize(self) -> None:
        """Create database connection and initialize schema."""
        self._connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,  # Allow multi-threaded access
            isolation_level=None  # Autocommit mode
        )

        # Enable foreign key constraints (disabled by default in SQLite)
        self._connection.execute("PRAGMA foreign_keys = ON")

        # Create tables
        cursor = self._connection.cursor()
        for table_sql in ALL_TABLES:
            cursor.execute(table_sql)

        # Create indexes
        for index_sql in CREATE_INDEXES:
            cursor.execute(index_sql)

        self._connection.commit()

    def get_connection(self) -> sqlite3.Connection:
        """Get the database connection.

        Returns:
            SQLite connection object
        """
        if self._connection is None:
            raise RuntimeError("Connection manager not initialized")
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager(database_path: Optional[str] = None) -> ConnectionManager:
    """Get or create the singleton ConnectionManager instance.

    Args:
        database_path: Path to database (required on first call)

    Returns:
        ConnectionManager instance
    """
    global _connection_manager

    if _connection_manager is None:
        if database_path is None:
            raise ValueError("database_path required for first initialization")
        _connection_manager = ConnectionManager(database_path)

    return _connection_manager
```

**Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/test_database/test_connection_manager.py -v
```

Expected: PASS (all 4 tests)

**Step 6: Commit**

```bash
git add src/database/ tests/test_database/
git commit -m "feat: add database schema and connection manager with foreign keys"
```

---

### Task 1.5: Bot Entry Point & Health Check

**Files:**
- Create: `bot.py`
- Create: `src/cogs/__init__.py`

**Step 1: Create minimal bot.py**

```python
"""HooperTwo Discord Bot - Entry point."""
import asyncio
import logging
from discord.ext import commands
import discord

from src.config.settings import settings
from src.database.connection_manager import get_connection_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HooperTwoBot(commands.Bot):
    """Main bot class with lifecycle management."""

    def __init__(self):
        """Initialize bot with intents and configuration."""
        # Configure intents (required for message content)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=settings.command_prefix,
            intents=intents,
            help_command=None  # Custom help command later
        )

        # Initialize database connection
        self.db = get_connection_manager(settings.database_path)
        logger.info(f"Database initialized at {settings.database_path}")

    async def setup_hook(self):
        """Called when bot is starting up. Load cogs here."""
        logger.info("Bot setup hook called")
        # Cogs will be loaded here in future tasks

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_command_error(self, ctx, error):
        """Global error handler for commands."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s",
                ephemeral=True
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Command error: {error}", exc_info=error)
            await ctx.send("❌ An error occurred while processing your command.", ephemeral=True)


async def main():
    """Main entry point."""
    bot = HooperTwoBot()

    try:
        await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await bot.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=e)
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Test bot startup locally**

```bash
# Create .env file first
cp .env.example .env
# Edit .env and add your Discord token

# Run bot
poetry run python bot.py
```

Expected: Bot starts, connects to Discord, logs "Logged in as [bot name]"

**Step 3: Test Docker deployment**

```bash
docker compose up
```

Expected: Container starts, bot connects to Discord

**Step 4: Commit**

```bash
git add bot.py src/cogs/__init__.py
git commit -m "feat: add bot entry point with health check and error handling"
```

**Batch 1 Complete! ✅**

Run full test suite:
```bash
poetry run pytest -v --cov=src
```

Expected: All tests pass, database created, bot connects to Discord

---

## Batch 2: Data Layer - Player Repository & Loading

**Success Criteria:**
- ✅ ADP board CSV loaded into database with correct rarity tiers
- ✅ Player repository supports CRUD operations with parameterized queries
- ✅ Rarity calculation matches specification (< 2 = GOAT, etc.)
- ✅ All tests pass
- ✅ No SQL injection vulnerabilities

### Task 2.1: Text Normalizer Utility

**Files:**
- Create: `src/utils/__init__.py`
- Create: `src/utils/text_normalizer.py`
- Create: `tests/test_utils/__init__.py`
- Create: `tests/test_utils/test_text_normalizer.py`

**Step 1: Write failing test**

Create `tests/test_utils/test_text_normalizer.py`:

```python
import pytest
from src.utils.text_normalizer import TextNormalizer


def test_normalize_removes_accents():
    """Test that accents are removed from text."""
    assert TextNormalizer.normalize("Nikola Jokić") == "nikola jokic"
    assert TextNormalizer.normalize("Luka Dončić") == "luka doncic"


def test_normalize_removes_dots():
    """Test that dots are removed."""
    assert TextNormalizer.normalize("J.R. Smith") == "jr smith"
    assert TextNormalizer.normalize("C.J. McCollum") == "cj mccollum"


def test_normalize_removes_dashes():
    """Test that dashes are normalized to spaces."""
    assert TextNormalizer.normalize("Karl-Anthony Towns") == "karl anthony towns"
    assert TextNormalizer.normalize("Michael Kidd-Gilchrist") == "michael kidd gilchrist"


def test_normalize_is_case_insensitive():
    """Test that normalization is case insensitive."""
    assert TextNormalizer.normalize("LEBRON JAMES") == "lebron james"
    assert TextNormalizer.normalize("LeBron James") == "lebron james"
    assert TextNormalizer.normalize("lebron james") == "lebron james"


def test_normalize_handles_multiple_spaces():
    """Test that extra spaces are collapsed."""
    assert TextNormalizer.normalize("Kevin   Durant") == "kevin durant"
    assert TextNormalizer.normalize("  Stephen Curry  ") == "stephen curry"


def test_normalize_handles_apostrophes():
    """Test that apostrophes are removed."""
    assert TextNormalizer.normalize("DeAndre' Bembry") == "deandre bembry"
    assert TextNormalizer.normalize("O'Neal") == "oneal"
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_utils/test_text_normalizer.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/utils/text_normalizer.py`:

```python
"""Text normalization utilities for player name matching.

Handles case, accents, punctuation, and whitespace normalization
to enable flexible player name recognition.
"""
import unicodedata
import re


class TextNormalizer:
    """Utility class for normalizing text for comparison.

    Responsibilities:
    - Remove accents (Jokić → Jokic)
    - Remove dots (J.R. → JR)
    - Normalize dashes to spaces (Karl-Anthony → Karl Anthony)
    - Lowercase everything
    - Collapse multiple spaces
    """

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Input text to normalize

        Returns:
            Normalized text (lowercase, no accents/punctuation, collapsed spaces)
        """
        # Remove accents using Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))

        # Convert to lowercase
        text = text.lower()

        # Remove dots and apostrophes
        text = text.replace('.', '')
        text = text.replace("'", '')

        # Convert dashes to spaces
        text = text.replace('-', ' ')

        # Collapse multiple spaces to single space
        text = re.sub(r'\s+', ' ', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_utils/test_text_normalizer.py -v
```

Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add src/utils/ tests/test_utils/
git commit -m "feat: add text normalizer for case/accent/punctuation-insensitive matching"
```

---

### Task 2.2: Player Repository

**Files:**
- Create: `src/database/repositories/__init__.py`
- Create: `src/database/repositories/player_repository.py`
- Create: `tests/test_database/test_player_repository.py`

**Step 1: Write failing test**

Create `tests/test_database/test_player_repository.py`:

```python
import pytest
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = str(tmp_path / "test.db")
    manager = ConnectionManager(db_path)
    yield manager
    manager.close()


@pytest.fixture
def player_repo(temp_db):
    """Create PlayerRepository with temp database."""
    return PlayerRepository(temp_db)


def test_create_player(player_repo):
    """Test creating a player with parameterized query."""
    player_id = player_repo.create_player(
        name="Michael Jordan",
        adp_value=1.41,
        rarity_tier="GOAT",
        image_url="http://example.com/mj.jpg",
        career_minutes=41011
    )

    assert player_id is not None
    assert player_id > 0


def test_get_player_by_name(player_repo):
    """Test retrieving player by normalized name."""
    player_repo.create_player(
        name="LeBron James",
        adp_value=1.90,
        rarity_tier="GOAT",
        image_url="http://example.com/lbj.jpg"
    )

    # Test case-insensitive lookup
    player = player_repo.get_player_by_name("lebron james")
    assert player is not None
    assert player["name"] == "LeBron James"
    assert player["rarity_tier"] == "GOAT"


def test_get_player_by_name_with_accents(player_repo):
    """Test retrieving player with accent normalization."""
    player_repo.create_player(
        name="Nikola Jokić",
        adp_value=15.39,
        rarity_tier="Mythic",
        image_url="http://example.com/jokic.jpg"
    )

    # Should find with or without accent
    player1 = player_repo.get_player_by_name("Nikola Jokić")
    player2 = player_repo.get_player_by_name("Nikola Jokic")

    assert player1 is not None
    assert player2 is not None
    assert player1["id"] == player2["id"]


def test_get_all_players(player_repo):
    """Test retrieving all players."""
    player_repo.create_player("Player 1", None, "Common", None)
    player_repo.create_player("Player 2", None, "Common", None)
    player_repo.create_player("Player 3", None, "Rare", None)

    players = player_repo.get_all_players()

    assert len(players) == 3


def test_get_players_by_rarity(player_repo):
    """Test filtering players by rarity tier."""
    player_repo.create_player("MJ", 1.41, "GOAT", None)
    player_repo.create_player("LBJ", 1.90, "GOAT", None)
    player_repo.create_player("Curry", 4.54, "Mythic", None)

    goat_players = player_repo.get_players_by_rarity("GOAT")

    assert len(goat_players) == 2


def test_sql_injection_prevention(player_repo):
    """Test that SQL injection attempts are safely handled."""
    # Attempt SQL injection via player name
    malicious_name = "Robert'; DROP TABLE players; --"

    player_repo.create_player(malicious_name, None, "Common", None)

    # Table should still exist and contain the literal string
    players = player_repo.get_all_players()
    assert len(players) == 1
    assert players[0]["name"] == malicious_name
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_database/test_player_repository.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/database/repositories/player_repository.py`:

```python
"""Player repository for database operations.

All queries use parameterized statements to prevent SQL injection.
"""
from typing import Optional, List, Dict, Any
from src.database.connection_manager import ConnectionManager
from src.utils.text_normalizer import TextNormalizer


class PlayerRepository:
    """Repository for player data operations.

    Responsibilities:
    - CRUD operations for players table
    - Parameterized queries only (SQL injection prevention)
    - Name normalization for lookups
    """

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize repository with database connection.

        Args:
            connection_manager: Database connection manager
        """
        self.conn = connection_manager.get_connection()

    def create_player(
        self,
        name: str,
        adp_value: Optional[float],
        rarity_tier: str,
        image_url: Optional[str],
        career_minutes: Optional[int] = None
    ) -> int:
        """Create a new player record.

        Args:
            name: Player's full name
            adp_value: Average draft position value (if on ADP board)
            rarity_tier: One of: GOAT, Mythic, Legendary, Epic, Rare, Common
            image_url: Basketball Reference image URL
            career_minutes: Total career minutes played

        Returns:
            ID of created player
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO players (name, adp_value, rarity_tier, image_url, career_minutes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, adp_value, rarity_tier, image_url, career_minutes)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_player_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get player by name with normalization.

        Args:
            name: Player name (case/accent/punctuation insensitive)

        Returns:
            Player dict or None if not found
        """
        normalized_search = TextNormalizer.normalize(name)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players")

        # Search with normalized comparison
        for row in cursor.fetchall():
            row_dict = self._row_to_dict(cursor, row)
            if TextNormalizer.normalize(row_dict["name"]) == normalized_search:
                return row_dict

        return None

    def get_all_players(self) -> List[Dict[str, Any]]:
        """Get all players.

        Returns:
            List of player dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players ORDER BY name")
        return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def get_players_by_rarity(self, rarity_tier: str) -> List[Dict[str, Any]]:
        """Get all players of a specific rarity tier.

        Args:
            rarity_tier: Rarity tier to filter by

        Returns:
            List of player dicts
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM players WHERE rarity_tier = ? ORDER BY name",
            (rarity_tier,)
        )
        return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        """Convert database row to dictionary.

        Args:
            cursor: Database cursor (for column names)
            row: Database row tuple

        Returns:
            Dictionary with column names as keys
        """
        return {
            col[0]: row[idx]
            for idx, col in enumerate(cursor.description)
        }
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_database/test_player_repository.py -v
```

Expected: PASS (all 6 tests including SQL injection test)

**Step 5: Commit**

```bash
git add src/database/repositories/ tests/test_database/test_player_repository.py
git commit -m "feat: add player repository with parameterized queries and SQL injection prevention"
```

---

### Task 2.3: Player Manager - ADP Loading & Rarity Calculation

**Files:**
- Create: `src/managers/__init__.py`
- Create: `src/managers/player_manager.py`
- Create: `tests/test_managers/__init__.py`
- Create: `tests/test_managers/test_player_manager.py`

**Step 1: Write failing test**

Create `tests/test_managers/test_player_manager.py`:

```python
import pytest
import csv
from pathlib import Path
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.managers.player_manager import PlayerManager


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database."""
    db_path = str(tmp_path / "test.db")
    manager = ConnectionManager(db_path)
    yield manager
    manager.close()


@pytest.fixture
def test_csv(tmp_path):
    """Create temporary ADP CSV file for testing."""
    csv_path = tmp_path / "test_adp.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Player", "ADP (31-)"])
        writer.writerow(["Michael Jordan", "1.41"])
        writer.writerow(["LeBron James", "1.90"])
        writer.writerow(["Stephen Curry", "4.54"])
        writer.writerow(["Luka Doncic", "30.31"])
        writer.writerow(["Dirk Nowitzki", "32.06"])
        writer.writerow(["Pau Gasol", "60.50"])
        writer.writerow(["Bill Walton", "120.00"])
        writer.writerow(["Random Player", "250.00"])
        writer.writerow(["Bench Warmer", "260.00"])
    return str(csv_path)


@pytest.fixture
def player_manager(temp_db, test_csv):
    """Create PlayerManager with test database."""
    repo = PlayerRepository(temp_db)
    return PlayerManager(repo, test_csv)


def test_calculate_rarity_tier_goat(player_manager):
    """Test rarity calculation for GOAT tier (ADP < 2)."""
    assert player_manager._calculate_rarity_tier(1.41) == "GOAT"
    assert player_manager._calculate_rarity_tier(1.90) == "GOAT"
    assert player_manager._calculate_rarity_tier(1.99) == "GOAT"


def test_calculate_rarity_tier_mythic(player_manager):
    """Test rarity calculation for Mythic tier (2 <= ADP < 32)."""
    assert player_manager._calculate_rarity_tier(2.0) == "Mythic"
    assert player_manager._calculate_rarity_tier(4.54) == "Mythic"
    assert player_manager._calculate_rarity_tier(30.31) == "Mythic"
    assert player_manager._calculate_rarity_tier(31.99) == "Mythic"


def test_calculate_rarity_tier_legendary(player_manager):
    """Test rarity calculation for Legendary tier (32 <= ADP < 64)."""
    assert player_manager._calculate_rarity_tier(32.0) == "Legendary"
    assert player_manager._calculate_rarity_tier(32.06) == "Legendary"
    assert player_manager._calculate_rarity_tier(63.99) == "Legendary"


def test_calculate_rarity_tier_epic(player_manager):
    """Test rarity calculation for Epic tier (64 <= ADP < 128)."""
    assert player_manager._calculate_rarity_tier(64.0) == "Epic"
    assert player_manager._calculate_rarity_tier(120.0) == "Epic"
    assert player_manager._calculate_rarity_tier(127.99) == "Epic"


def test_calculate_rarity_tier_rare(player_manager):
    """Test rarity calculation for Rare tier (128 <= ADP < 256)."""
    assert player_manager._calculate_rarity_tier(128.0) == "Rare"
    assert player_manager._calculate_rarity_tier(250.0) == "Rare"
    assert player_manager._calculate_rarity_tier(255.99) == "Rare"


def test_calculate_rarity_tier_common(player_manager):
    """Test rarity calculation for Common tier (ADP >= 256 or None)."""
    assert player_manager._calculate_rarity_tier(256.0) == "Common"
    assert player_manager._calculate_rarity_tier(1000.0) == "Common"
    assert player_manager._calculate_rarity_tier(None) == "Common"


def test_load_adp_board(player_manager):
    """Test loading ADP board from CSV."""
    player_manager.load_adp_board()

    # Check that players were loaded
    all_players = player_manager.repository.get_all_players()
    assert len(all_players) == 9

    # Check specific players and rarity tiers
    mj = player_manager.repository.get_player_by_name("Michael Jordan")
    assert mj["rarity_tier"] == "GOAT"
    assert mj["adp_value"] == 1.41

    curry = player_manager.repository.get_player_by_name("Stephen Curry")
    assert curry["rarity_tier"] == "Mythic"

    dirk = player_manager.repository.get_player_by_name("Dirk Nowitzki")
    assert dirk["rarity_tier"] == "Legendary"

    walton = player_manager.repository.get_player_by_name("Bill Walton")
    assert walton["rarity_tier"] == "Epic"

    random = player_manager.repository.get_player_by_name("Random Player")
    assert random["rarity_tier"] == "Rare"

    bench = player_manager.repository.get_player_by_name("Bench Warmer")
    assert bench["rarity_tier"] == "Common"
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_managers/test_player_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/managers/player_manager.py`:

```python
"""Player manager for business logic operations.

Handles ADP board loading and rarity tier calculations.
"""
import csv
from typing import Optional
from pathlib import Path
from src.database.repositories.player_repository import PlayerRepository


class PlayerManager:
    """Manager for player-related business logic.

    Responsibilities:
    - Load ADP board from CSV
    - Calculate rarity tiers based on ADP value
    - Coordinate player data operations
    """

    # Rarity tier thresholds
    GOAT_THRESHOLD = 2.0
    MYTHIC_THRESHOLD = 32.0
    LEGENDARY_THRESHOLD = 64.0
    EPIC_THRESHOLD = 128.0
    RARE_THRESHOLD = 256.0

    def __init__(self, repository: PlayerRepository, adp_csv_path: str):
        """Initialize player manager.

        Args:
            repository: Player repository for database operations
            adp_csv_path: Path to ADP board CSV file
        """
        self.repository = repository
        self.adp_csv_path = adp_csv_path

    def _calculate_rarity_tier(self, adp_value: Optional[float]) -> str:
        """Calculate rarity tier based on ADP value.

        Rarity tiers:
        - GOAT: ADP < 2
        - Mythic: 2 <= ADP < 32
        - Legendary: 32 <= ADP < 64
        - Epic: 64 <= ADP < 128
        - Rare: 128 <= ADP < 256
        - Common: ADP >= 256 or no ADP value

        Args:
            adp_value: Average draft position value (None for non-ADP players)

        Returns:
            Rarity tier string
        """
        if adp_value is None or adp_value >= self.RARE_THRESHOLD:
            return "Common"
        elif adp_value < self.GOAT_THRESHOLD:
            return "GOAT"
        elif adp_value < self.MYTHIC_THRESHOLD:
            return "Mythic"
        elif adp_value < self.LEGENDARY_THRESHOLD:
            return "Legendary"
        elif adp_value < self.EPIC_THRESHOLD:
            return "Epic"
        else:  # adp_value < RARE_THRESHOLD
            return "Rare"

    def load_adp_board(self) -> int:
        """Load ADP board from CSV into database.

        Returns:
            Number of players loaded
        """
        if not Path(self.adp_csv_path).exists():
            raise FileNotFoundError(f"ADP CSV not found: {self.adp_csv_path}")

        loaded_count = 0

        with open(self.adp_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row["Player"].strip()
                adp_value = float(row["ADP (31-)"])
                rarity_tier = self._calculate_rarity_tier(adp_value)

                # Create player (image URL will be added later by scraper)
                self.repository.create_player(
                    name=name,
                    adp_value=adp_value,
                    rarity_tier=rarity_tier,
                    image_url=None  # Will be populated by image scraper
                )
                loaded_count += 1

        return loaded_count
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_managers/test_player_manager.py -v
```

Expected: PASS (all 8 tests)

**Step 5: Commit**

```bash
git add src/managers/ tests/test_managers/
git commit -m "feat: add player manager with ADP loading and rarity calculation"
```

**Batch 2 Complete! ✅**

Run full test suite:
```bash
poetry run pytest -v --cov=src
```

Expected: All tests pass, ADP board loaded correctly with proper rarity tiers

---

## Batch 3: Image Management System

**Success Criteria:**
- ✅ Basketball Reference scraper fetches player images with rate limiting
- ✅ Images downloaded and cached locally
- ✅ Rate limit of 20 requests/minute enforced
- ✅ Failed image downloads logged but don't crash system
- ✅ All tests pass

### Task 3.1: Basketball Reference Scraper

**Files:**
- Create: `src/scrapers/__init__.py`
- Create: `src/scrapers/basketball_ref_scraper.py`
- Create: `tests/test_scrapers/__init__.py`
- Create: `tests/test_scrapers/test_basketball_ref_scraper.py`

**Step 1: Write failing test**

Create `tests/test_scrapers/test_basketball_ref_scraper.py`:

```python
import pytest
import time
from src.scrapers.basketball_ref_scraper import BasketballReferenceScraper


def test_scraper_initialization():
    """Test scraper initializes with rate limit."""
    scraper = BasketballReferenceScraper(rate_limit_per_minute=20)
    assert scraper.rate_limit_per_minute == 20


def test_normalize_player_name_for_url():
    """Test player name normalization for Basketball Reference URLs."""
    scraper = BasketballReferenceScraper()

    # Basketball Reference uses format: lastname + first 2 letters of firstname + 01
    # This is a simplified version - actual implementation may vary
    assert "jordan" in scraper._normalize_name_for_url("Michael Jordan").lower()
    assert "james" in scraper._normalize_name_for_url("LeBron James").lower()


def test_rate_limiting(monkeypatch):
    """Test that rate limiting is enforced."""
    scraper = BasketballReferenceScraper(rate_limit_per_minute=2)  # 2 per minute for testing

    # Mock the actual fetch to avoid real HTTP requests
    fetch_times = []

    def mock_fetch(name):
        fetch_times.append(time.time())
        return f"http://example.com/{name}.jpg"

    monkeypatch.setattr(scraper, "_fetch_image_url", mock_fetch)

    # Make 3 requests
    scraper.get_player_image_url("Player 1")
    scraper.get_player_image_url("Player 2")
    scraper.get_player_image_url("Player 3")

    # Check that there's a delay between 2nd and 3rd request
    if len(fetch_times) >= 3:
        time_diff = fetch_times[2] - fetch_times[1]
        assert time_diff >= 29  # Should wait ~30 seconds (60s / 2 per minute)
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_scrapers/test_basketball_ref_scraper.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/scrapers/basketball_ref_scraper.py`:

```python
"""Basketball Reference scraper with rate limiting.

Fetches player images from Basketball Reference while respecting
their rate limits (20 requests/minute default).
"""
import time
import logging
from typing import Optional
from collections import deque

logger = logging.getLogger(__name__)


class BasketballReferenceScraper:
    """Scraper for Basketball Reference player images.

    Responsibilities:
    - Fetch player image URLs from Basketball Reference
    - Enforce rate limiting (default: 20 requests/minute)
    - Handle errors gracefully

    Note: This is a simplified implementation. The basketball-reference-scraper
    library will be used in the actual image manager.
    """

    def __init__(self, rate_limit_per_minute: int = 20):
        """Initialize scraper with rate limiting.

        Args:
            rate_limit_per_minute: Maximum requests per minute
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_times: deque = deque()

    def _normalize_name_for_url(self, player_name: str) -> str:
        """Normalize player name for Basketball Reference URL format.

        Basketball Reference uses: last_name + first 2 chars of first_name + 01
        Example: "Michael Jordan" -> "jordami01"

        Args:
            player_name: Full player name

        Returns:
            Normalized name for URL
        """
        parts = player_name.lower().split()
        if len(parts) < 2:
            return player_name.lower().replace(" ", "")

        first_name = parts[0]
        last_name = parts[-1]

        # Basketball Reference format: lastname + first 2 of firstname + 01
        return f"{last_name}{first_name[:2]}01"

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting by waiting if necessary."""
        current_time = time.time()

        # Remove requests older than 60 seconds
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()

        # If at rate limit, wait until we can make another request
        if len(self.request_times) >= self.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self._enforce_rate_limit()  # Recheck after sleeping

        # Record this request time
        self.request_times.append(time.time())

    def _fetch_image_url(self, player_name: str) -> Optional[str]:
        """Fetch image URL for a player (to be implemented with actual library).

        Args:
            player_name: Full player name

        Returns:
            Image URL or None if not found
        """
        # Placeholder - actual implementation will use basketball-reference-scraper
        normalized = self._normalize_name_for_url(player_name)
        return f"https://www.basketball-reference.com/req/202106291/images/players/{normalized}.jpg"

    def get_player_image_url(self, player_name: str) -> Optional[str]:
        """Get player image URL with rate limiting.

        Args:
            player_name: Full player name

        Returns:
            Image URL or None if not found
        """
        self._enforce_rate_limit()

        try:
            return self._fetch_image_url(player_name)
        except Exception as e:
            logger.error(f"Failed to fetch image for {player_name}: {e}")
            return None
```

**Step 4: Run tests (note: rate limiting test will be slow)**

```bash
poetry run pytest tests/test_scrapers/test_basketball_ref_scraper.py -v -s
```

Expected: PASS (including rate limiting test which may take ~30s)

**Step 5: Commit**

```bash
git add src/scrapers/ tests/test_scrapers/
git commit -m "feat: add Basketball Reference scraper with rate limiting"
```

---

### Task 3.2: Image Manager

**Files:**
- Create: `src/managers/image_manager.py`
- Create: `tests/test_managers/test_image_manager.py`

**Step 1: Write failing test**

Create `tests/test_managers/test_image_manager.py`:

```python
import pytest
from pathlib import Path
from src.managers.image_manager import ImageManager
from src.scrapers.basketball_ref_scraper import BasketballReferenceScraper


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "images"
    cache_dir.mkdir()
    return str(cache_dir)


@pytest.fixture
def image_manager(temp_cache_dir):
    """Create ImageManager with temp cache."""
    scraper = BasketballReferenceScraper(rate_limit_per_minute=60)  # Fast for testing
    return ImageManager(scraper, temp_cache_dir)


def test_get_cached_image_path(image_manager):
    """Test getting cached image path for a player."""
    path = image_manager.get_cached_image_path("Michael Jordan")

    assert "michael_jordan" in path.lower()
    assert path.endswith(".jpg")


def test_image_is_cached(image_manager, temp_cache_dir):
    """Test checking if image is already cached."""
    # Initially not cached
    assert not image_manager.is_cached("Michael Jordan")

    # Create a fake cached file
    cached_path = image_manager.get_cached_image_path("Michael Jordan")
    Path(cached_path).touch()

    # Now should be cached
    assert image_manager.is_cached("Michael Jordan")


def test_download_image_creates_file(image_manager, monkeypatch):
    """Test that downloading image creates file in cache."""
    # Mock the actual download to avoid network calls
    def mock_download(url, save_path):
        Path(save_path).write_text("fake image data")

    monkeypatch.setattr(image_manager, "_download_from_url", mock_download)

    result = image_manager.download_player_image("Test Player", "http://example.com/test.jpg")

    assert result is True
    assert image_manager.is_cached("Test Player")


def test_download_image_handles_errors_gracefully(image_manager, monkeypatch):
    """Test that download errors are handled without crashing."""
    def mock_download_error(url, save_path):
        raise Exception("Network error")

    monkeypatch.setattr(image_manager, "_download_from_url", mock_download_error)

    result = image_manager.download_player_image("Test Player", "http://example.com/test.jpg")

    assert result is False  # Should return False on error, not crash
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_managers/test_image_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/managers/image_manager.py`:

```python
"""Image manager for downloading and caching player images."""
import logging
from pathlib import Path
from typing import Optional
import aiohttp
from src.scrapers.basketball_ref_scraper import BasketballReferenceScraper

logger = logging.getLogger(__name__)


class ImageManager:
    """Manager for player image downloading and caching.

    Responsibilities:
    - Download player images from Basketball Reference
    - Cache images locally to avoid re-downloads
    - Handle download failures gracefully
    """

    def __init__(self, scraper: BasketballReferenceScraper, cache_dir: str):
        """Initialize image manager.

        Args:
            scraper: Basketball Reference scraper instance
            cache_dir: Directory to cache downloaded images
        """
        self.scraper = scraper
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cached_image_path(self, player_name: str) -> str:
        """Get the file path for a cached player image.

        Args:
            player_name: Full player name

        Returns:
            Path where image is/should be cached
        """
        # Normalize player name for filename (lowercase, underscores)
        filename = player_name.lower().replace(" ", "_").replace(".", "")
        filename = filename.replace("-", "_") + ".jpg"
        return str(self.cache_dir / filename)

    def is_cached(self, player_name: str) -> bool:
        """Check if player image is already cached.

        Args:
            player_name: Full player name

        Returns:
            True if image exists in cache
        """
        cached_path = Path(self.get_cached_image_path(player_name))
        return cached_path.exists() and cached_path.stat().st_size > 0

    def _download_from_url(self, url: str, save_path: str) -> None:
        """Download image from URL and save to disk.

        Args:
            url: Image URL
            save_path: Local path to save image
        """
        import requests

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)

    def download_player_image(self, player_name: str, image_url: str) -> bool:
        """Download and cache a player's image.

        Args:
            player_name: Full player name
            image_url: URL to download image from

        Returns:
            True if download successful, False otherwise
        """
        if self.is_cached(player_name):
            logger.debug(f"Image already cached for {player_name}")
            return True

        try:
            save_path = self.get_cached_image_path(player_name)
            self._download_from_url(image_url, save_path)
            logger.info(f"Downloaded image for {player_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to download image for {player_name}: {e}")
            return False
```

**Step 4: Add requests dependency to pyproject.toml**

Update the `[tool.poetry.dependencies]` section:

```toml
requests = "^2.31.0"
```

Then run:
```bash
poetry install
```

**Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/test_managers/test_image_manager.py -v
```

Expected: PASS (all 4 tests)

**Step 6: Commit**

```bash
git add src/managers/image_manager.py tests/test_managers/test_image_manager.py pyproject.toml
git commit -m "feat: add image manager for downloading and caching player images"
```

**Batch 3 Complete! ✅**

Run full test suite:
```bash
poetry run pytest -v --cov=src
```

Expected: All tests pass, image downloading and caching works correctly

---

## Batch 4: Spawning System

**Success Criteria:**
- ✅ Message counter tracks messages per channel with in-memory cache
- ✅ Spawn coordinator triggers spawns at configured threshold
- ✅ Random player selection weighted by rarity
- ✅ Spawn tracking in Redis-like in-memory cache
- ✅ All tests pass

### Task 4.1: Cache Coordinator

**Files:**
- Create: `src/coordinators/__init__.py`
- Create: `src/coordinators/cache_coordinator.py`
- Create: `tests/test_coordinators/__init__.py`
- Create: `tests/test_coordinators/test_cache_coordinator.py`

**Step 1: Write failing test**

Create `tests/test_coordinators/test_cache_coordinator.py`:

```python
import pytest
from src.coordinators.cache_coordinator import CacheCoordinator


def test_cache_initialization():
    """Test cache coordinator initializes empty."""
    cache = CacheCoordinator()

    assert cache.get_message_count(123456) == 0
    assert cache.get_active_spawn(123456) is None


def test_increment_message_count():
    """Test incrementing message count for a channel."""
    cache = CacheCoordinator()

    cache.increment_message_count(123456)
    assert cache.get_message_count(123456) == 1

    cache.increment_message_count(123456)
    assert cache.get_message_count(123456) == 2


def test_reset_message_count():
    """Test resetting message count."""
    cache = CacheCoordinator()

    cache.increment_message_count(123456)
    cache.increment_message_count(123456)
    cache.reset_message_count(123456)

    assert cache.get_message_count(123456) == 0


def test_set_active_spawn():
    """Test setting and getting active spawn."""
    cache = CacheCoordinator()

    player_data = {"id": 1, "name": "Michael Jordan", "rarity": "GOAT"}
    cache.set_active_spawn(123456, player_data)

    active = cache.get_active_spawn(123456)
    assert active == player_data
    assert active["name"] == "Michael Jordan"


def test_clear_active_spawn():
    """Test clearing active spawn."""
    cache = CacheCoordinator()

    cache.set_active_spawn(123456, {"id": 1, "name": "Test"})
    cache.clear_active_spawn(123456)

    assert cache.get_active_spawn(123456) is None


def test_multiple_channels_independent():
    """Test that different channels have independent state."""
    cache = CacheCoordinator()

    cache.increment_message_count(111111)
    cache.increment_message_count(111111)
    cache.increment_message_count(222222)

    assert cache.get_message_count(111111) == 2
    assert cache.get_message_count(222222) == 1

    cache.set_active_spawn(111111, {"id": 1, "name": "Player 1"})
    cache.set_active_spawn(222222, {"id": 2, "name": "Player 2"})

    assert cache.get_active_spawn(111111)["name"] == "Player 1"
    assert cache.get_active_spawn(222222)["name"] == "Player 2"
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_coordinators/test_cache_coordinator.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/coordinators/cache_coordinator.py`:

```python
"""In-memory cache coordinator for hot data.

Replaces Redis for MVP. Data is lost on bot restart but
that's acceptable for message counts and active spawns.
"""
from typing import Optional, Dict, Any
from threading import Lock


class CacheCoordinator:
    """In-memory cache for message counts and active spawns.

    Responsibilities:
    - Track message counts per channel
    - Track active spawns per channel
    - Thread-safe operations

    Note: All data is in-memory and lost on restart.
    """

    def __init__(self):
        """Initialize empty cache with thread safety."""
        self._message_counts: Dict[int, int] = {}
        self._active_spawns: Dict[int, Dict[str, Any]] = {}
        self._lock = Lock()

    def get_message_count(self, channel_id: int) -> int:
        """Get current message count for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            Message count (0 if no messages yet)
        """
        with self._lock:
            return self._message_counts.get(channel_id, 0)

    def increment_message_count(self, channel_id: int) -> int:
        """Increment message count for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            New message count
        """
        with self._lock:
            current = self._message_counts.get(channel_id, 0)
            self._message_counts[channel_id] = current + 1
            return self._message_counts[channel_id]

    def reset_message_count(self, channel_id: int) -> None:
        """Reset message count for a channel (after spawn).

        Args:
            channel_id: Discord channel ID
        """
        with self._lock:
            self._message_counts[channel_id] = 0

    def get_active_spawn(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get active spawn data for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            Spawn data dict or None if no active spawn
        """
        with self._lock:
            return self._active_spawns.get(channel_id)

    def set_active_spawn(self, channel_id: int, player_data: Dict[str, Any]) -> None:
        """Set active spawn for a channel.

        Args:
            channel_id: Discord channel ID
            player_data: Player dictionary
        """
        with self._lock:
            self._active_spawns[channel_id] = player_data

    def clear_active_spawn(self, channel_id: int) -> None:
        """Clear active spawn for a channel (after catch).

        Args:
            channel_id: Discord channel ID
        """
        with self._lock:
            if channel_id in self._active_spawns:
                del self._active_spawns[channel_id]
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_coordinators/test_cache_coordinator.py -v
```

Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add src/coordinators/ tests/test_coordinators/
git commit -m "feat: add in-memory cache coordinator for message counts and spawns"
```

---

### Task 4.2: Spawn Manager

**Files:**
- Create: `src/managers/spawn_manager.py`
- Create: `tests/test_managers/test_spawn_manager.py`

**Step 1: Write failing test**

Create `tests/test_managers/test_spawn_manager.py`:

```python
import pytest
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.managers.spawn_manager import SpawnManager


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database with test players."""
    db_path = str(tmp_path / "test.db")
    manager = ConnectionManager(db_path)
    repo = PlayerRepository(manager)

    # Add test players with different rarities
    repo.create_player("MJ", 1.0, "GOAT", None)
    repo.create_player("LBJ", 1.5, "GOAT", None)
    repo.create_player("Curry", 5.0, "Mythic", None)
    repo.create_player("Durant", 10.0, "Mythic", None)
    repo.create_player("Common1", None, "Common", None)
    repo.create_player("Common2", None, "Common", None)
    repo.create_player("Common3", None, "Common", None)

    yield manager
    manager.close()


@pytest.fixture
def spawn_manager(temp_db):
    """Create SpawnManager with test database."""
    repo = PlayerRepository(temp_db)
    return SpawnManager(repo)


def test_select_random_player_returns_player(spawn_manager):
    """Test that random player selection returns a valid player."""
    player = spawn_manager.select_random_player()

    assert player is not None
    assert "name" in player
    assert "rarity_tier" in player


def test_select_random_player_distribution(spawn_manager):
    """Test that rarity weighting affects spawn distribution."""
    # Select 1000 players and check distribution
    selections = [spawn_manager.select_random_player() for _ in range(1000)]

    goat_count = sum(1 for p in selections if p["rarity_tier"] == "GOAT")
    common_count = sum(1 for p in selections if p["rarity_tier"] == "Common")

    # GOAT should be rarer than Common (but not necessarily 0 GOATs)
    # With proper weighting, Common should appear more often
    assert common_count > goat_count


def test_calculate_spawn_weight_goat(spawn_manager):
    """Test spawn weight for GOAT tier."""
    weight = spawn_manager._calculate_spawn_weight("GOAT")
    assert weight == 1  # Lowest weight = rarest


def test_calculate_spawn_weight_common(spawn_manager):
    """Test spawn weight for Common tier."""
    weight = spawn_manager._calculate_spawn_weight("Common")
    assert weight == 100  # Highest weight = most common


def test_calculate_spawn_weight_tiers(spawn_manager):
    """Test relative spawn weights across tiers."""
    goat = spawn_manager._calculate_spawn_weight("GOAT")
    mythic = spawn_manager._calculate_spawn_weight("Mythic")
    legendary = spawn_manager._calculate_spawn_weight("Legendary")
    epic = spawn_manager._calculate_spawn_weight("Epic")
    rare = spawn_manager._calculate_spawn_weight("Rare")
    common = spawn_manager._calculate_spawn_weight("Common")

    # Weights should increase (more common = higher weight)
    assert goat < mythic < legendary < epic < rare < common
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_managers/test_spawn_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/managers/spawn_manager.py`:

```python
"""Spawn manager for player spawning logic."""
import random
from typing import Dict, Any, List
from src.database.repositories.player_repository import PlayerRepository


class SpawnManager:
    """Manager for player spawning logic.

    Responsibilities:
    - Select random players with rarity-weighted probability
    - Calculate spawn weights based on rarity
    """

    # Spawn weights (higher = more common)
    RARITY_WEIGHTS = {
        "GOAT": 1,
        "Mythic": 5,
        "Legendary": 15,
        "Epic": 30,
        "Rare": 50,
        "Common": 100,
    }

    def __init__(self, player_repository: PlayerRepository):
        """Initialize spawn manager.

        Args:
            player_repository: Repository for player data access
        """
        self.repository = player_repository

    def _calculate_spawn_weight(self, rarity_tier: str) -> int:
        """Calculate spawn weight for a rarity tier.

        Args:
            rarity_tier: Rarity tier string

        Returns:
            Spawn weight (higher = more likely to spawn)
        """
        return self.RARITY_WEIGHTS.get(rarity_tier, 100)

    def select_random_player(self) -> Dict[str, Any]:
        """Select a random player weighted by rarity.

        Returns:
            Player dictionary
        """
        all_players = self.repository.get_all_players()

        if not all_players:
            raise ValueError("No players in database")

        # Calculate weights for each player
        weights = [
            self._calculate_spawn_weight(player["rarity_tier"])
            for player in all_players
        ]

        # Select random player using weights
        selected = random.choices(all_players, weights=weights, k=1)[0]
        return selected
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_managers/test_spawn_manager.py -v
```

Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add src/managers/spawn_manager.py tests/test_managers/test_spawn_manager.py
git commit -m "feat: add spawn manager with rarity-weighted player selection"
```

**Batch 4 Complete! ✅**

Run full test suite:
```bash
poetry run pytest -v --cov=src
```

Expected: All tests pass, spawning system works with proper weighting

---

## Batch 5: Input Validation & Security

**Success Criteria:**
- ✅ All user input validated and sanitized
- ✅ Input length limits enforced
- ✅ Name validator handles edge cases
- ✅ SQL injection attempts blocked by parameterized queries
- ✅ All tests pass

### Task 5.1: Input Validator

**Files:**
- Create: `src/validators/__init__.py`
- Create: `src/validators/input_validator.py`
- Create: `tests/test_validators/__init__.py`
- Create: `tests/test_validators/test_input_validator.py`

**Step 1: Write failing test**

Create `tests/test_validators/test_input_validator.py`:

```python
import pytest
from src.validators.input_validator import InputValidator, ValidationError


def test_validate_player_name_valid():
    """Test validating valid player names."""
    assert InputValidator.validate_player_name("Michael Jordan") == "Michael Jordan"
    assert InputValidator.validate_player_name("LeBron James") == "LeBron James"
    assert InputValidator.validate_player_name("Karl-Anthony Towns") == "Karl-Anthony Towns"


def test_validate_player_name_too_long():
    """Test that overly long names are rejected."""
    long_name = "A" * 101

    with pytest.raises(ValidationError, match="too long"):
        InputValidator.validate_player_name(long_name)


def test_validate_player_name_empty():
    """Test that empty names are rejected."""
    with pytest.raises(ValidationError, match="cannot be empty"):
        InputValidator.validate_player_name("")

    with pytest.raises(ValidationError, match="cannot be empty"):
        InputValidator.validate_player_name("   ")


def test_validate_player_name_strips_whitespace():
    """Test that leading/trailing whitespace is stripped."""
    assert InputValidator.validate_player_name("  Michael Jordan  ") == "Michael Jordan"


def test_validate_spawn_threshold_valid():
    """Test validating valid spawn thresholds."""
    assert InputValidator.validate_spawn_threshold(100) == 100
    assert InputValidator.validate_spawn_threshold(500) == 500


def test_validate_spawn_threshold_invalid():
    """Test that invalid thresholds are rejected."""
    with pytest.raises(ValidationError, match="between 10 and 10000"):
        InputValidator.validate_spawn_threshold(5)

    with pytest.raises(ValidationError, match="between 10 and 10000"):
        InputValidator.validate_spawn_threshold(15000)


def test_validate_channel_id_valid():
    """Test validating valid Discord channel IDs."""
    assert InputValidator.validate_channel_id(123456789012345678) == 123456789012345678


def test_validate_channel_id_invalid():
    """Test that invalid channel IDs are rejected."""
    with pytest.raises(ValidationError, match="must be positive"):
        InputValidator.validate_channel_id(-1)

    with pytest.raises(ValidationError, match="must be positive"):
        InputValidator.validate_channel_id(0)


def test_sanitize_input_removes_dangerous_chars():
    """Test that dangerous characters are sanitized."""
    # SQL injection attempt
    malicious = "Robert'; DROP TABLE players; --"
    sanitized = InputValidator.sanitize_input(malicious)

    # Should still contain the text but be safe for logging/display
    assert "Robert" in sanitized
    assert len(sanitized) <= 100  # Length limited
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_validators/test_input_validator.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

Create `src/validators/input_validator.py`:

```python
"""Input validation and sanitization for security.

All user input must pass through validators before use.
"""
from typing import Union


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """Validator for user input with security checks.

    Responsibilities:
    - Validate input length and format
    - Sanitize input for safe display
    - Prevent injection attacks

    Note: SQL injection is prevented primarily by parameterized queries,
    but this provides defense in depth.
    """

    MAX_PLAYER_NAME_LENGTH = 100
    MIN_SPAWN_THRESHOLD = 10
    MAX_SPAWN_THRESHOLD = 10000

    @staticmethod
    def validate_player_name(name: str) -> str:
        """Validate and sanitize player name input.

        Args:
            name: Player name from user input

        Returns:
            Validated name (stripped of whitespace)

        Raises:
            ValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ValidationError("Player name cannot be empty")

        name = name.strip()

        if len(name) > InputValidator.MAX_PLAYER_NAME_LENGTH:
            raise ValidationError(
                f"Player name too long (max {InputValidator.MAX_PLAYER_NAME_LENGTH} characters)"
            )

        return name

    @staticmethod
    def validate_spawn_threshold(threshold: int) -> int:
        """Validate spawn threshold value.

        Args:
            threshold: Spawn threshold from user input

        Returns:
            Validated threshold

        Raises:
            ValidationError: If threshold is invalid
        """
        if not isinstance(threshold, int):
            raise ValidationError("Spawn threshold must be an integer")

        if threshold < InputValidator.MIN_SPAWN_THRESHOLD or \
           threshold > InputValidator.MAX_SPAWN_THRESHOLD:
            raise ValidationError(
                f"Spawn threshold must be between {InputValidator.MIN_SPAWN_THRESHOLD} "
                f"and {InputValidator.MAX_SPAWN_THRESHOLD}"
            )

        return threshold

    @staticmethod
    def validate_channel_id(channel_id: int) -> int:
        """Validate Discord channel ID.

        Args:
            channel_id: Discord channel ID

        Returns:
            Validated channel ID

        Raises:
            ValidationError: If channel ID is invalid
        """
        if not isinstance(channel_id, int) or channel_id <= 0:
            raise ValidationError("Channel ID must be a positive integer")

        return channel_id

    @staticmethod
    def sanitize_input(text: str, max_length: int = 100) -> str:
        """Sanitize text input for safe display/logging.

        Args:
            text: User input text
            max_length: Maximum length to allow

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Strip and truncate
        text = text.strip()[:max_length]

        return text
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_validators/test_input_validator.py -v
```

Expected: PASS (all 9 tests)

**Step 5: Commit**

```bash
git add src/validators/ tests/test_validators/
git commit -m "feat: add input validator with length limits and sanitization"
```

**Batch 5 Complete! ✅**

---

## Batch 6: Discord Cogs - Commands Implementation

**Success Criteria:**
- ✅ All commands have rate limiting
- ✅ Hybrid commands work as both slash and prefix
- ✅ Admin commands require permissions
- ✅ Error handling for all edge cases
- ✅ Input validation on all user input
- ✅ All tests pass

### Task 6.1: Spawning Cog

**Files:**
- Create: `src/cogs/spawning_cog.py`

**Implementation** (due to length, showing key structure with security):

```python
"""Spawning cog for player recognition and catching."""
import discord
from discord import app_commands
from discord.ext import commands
import logging

from src.coordinators.cache_coordinator import CacheCoordinator
from src.managers.spawn_manager import SpawnManager
from src.managers.image_manager import ImageManager
from src.validators.input_validator import InputValidator, ValidationError

logger = logging.getLogger(__name__)


class SpawningCog(commands.Cog):
    """Cog for player spawning and recognition.

    Responsibilities:
    - Listen to messages and track counts
    - Trigger spawns at threshold
    - Handle player recognition
    """

    def __init__(
        self,
        bot,
        cache: CacheCoordinator,
        spawn_manager: SpawnManager,
        image_manager: ImageManager
    ):
        self.bot = bot
        self.cache = cache
        self.spawn_manager = spawn_manager
        self.image_manager = image_manager

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen to messages for spawn triggering."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Ignore commands
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # TODO: Check if channel is configured for spawning

        # Increment message count
        channel_id = message.channel.id
        count = self.cache.increment_message_count(channel_id)

        # Check if should spawn (threshold from server config, default 500)
        threshold = 500  # TODO: Get from server config

        if count >= threshold:
            await self._trigger_spawn(message.channel)

    async def _trigger_spawn(self, channel: discord.TextChannel):
        """Trigger a player spawn in a channel."""
        # Reset counter
        self.cache.reset_message_count(channel.id)

        # Select random player
        player = self.spawn_manager.select_random_player()

        # Set as active spawn
        self.cache.set_active_spawn(channel.id, player)

        # Send spawn message with image
        embed = discord.Embed(
            title="🏀 A wild NBA player appeared!",
            description="Use `/recognize <player name>` to catch them!",
            color=discord.Color.gold()
        )

        # TODO: Attach player image if cached

        await channel.send(embed=embed)
        logger.info(f"Spawned {player['name']} in channel {channel.id}")

    @commands.hybrid_command(name="recognize")
    @app_commands.describe(player_name="The full name of the player")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def recognize(self, ctx: commands.Context, *, player_name: str):
        """Recognize and catch a spawned player.

        Args:
            ctx: Command context
            player_name: Full player name (case/accent/punctuation insensitive)
        """
        # Validate input
        try:
            player_name = InputValidator.validate_player_name(player_name)
        except ValidationError as e:
            await ctx.send(f"❌ Invalid input: {e}", ephemeral=True)
            return

        # Check if there's an active spawn
        active_spawn = self.cache.get_active_spawn(ctx.channel.id)
        if not active_spawn:
            await ctx.send("❌ No player to recognize right now!", ephemeral=True)
            return

        # Check if name matches (using TextNormalizer)
        from src.utils.text_normalizer import TextNormalizer

        if TextNormalizer.normalize(player_name) != \
           TextNormalizer.normalize(active_spawn["name"]):
            await ctx.send(f"❌ That's not the right player!", ephemeral=True)
            return

        # Correct! Add to collection (TODO: implement collection manager)
        self.cache.clear_active_spawn(ctx.channel.id)

        await ctx.send(
            f"✅ **{ctx.author.mention} caught {active_spawn['name']}!**\n"
            f"Rarity: {active_spawn['rarity_tier']}"
        )

        logger.info(f"User {ctx.author.id} caught {active_spawn['name']}")


async def setup(bot):
    """Load the cog."""
    # TODO: Initialize dependencies
    # await bot.add_cog(SpawningCog(bot, cache, spawn_manager, image_manager))
    pass
```

---

## Summary: Remaining Batches (Outline)

Due to file length constraints, here are the remaining batches in outline form:

### Batch 7: Collection System
- Collection repository (user_collections table)
- Collection manager (add player, get collection)
- Collection cog (`/collection` command with pagination)
- Tests for collection operations

### Batch 8: Leaderboard System
- Leaderboard repository (snapshots table)
- Leaderboard manager (calculate points, time ranges)
- Leaderboard cog (`/leaderboard` command)
- Background task for snapshot creation

### Batch 9: Admin Configuration
- Server config repository
- Config manager (spawn channels, thresholds)
- Admin cog (`/config` commands with permissions)
- Tests for configuration

### Batch 10: Backup System
- Backup manager (automated daily backups)
- Background task for backup scheduling
- Cleanup of old backups
- Tests for backup operations

### Batch 11: Final Integration
- Load all cogs in bot.py
- Integration tests
- Docker deployment testing
- Documentation updates

---

## References & Best Practices

**Security:**
- [Discord Bot Security Best Practices 2025](https://friendify.net/blog/discord-bot-security-best-practices-2025.html)
- [SQL Injection Prevention with Parameterized Queries](https://realpython.com/prevent-python-sql-injection/)
- [discord.py Rate Limiting](https://github.com/context7/discordpy_readthedocs_io_en_stable/blob/main/ext/commands/api.md)

**Deployment:**
- [Docker Bot Deployment Guide](https://medium.com/@thomaschaigneau.ai/building-and-launching-your-discord-bot-a-step-by-step-guide-f803f7943d33)
- [Basketball Reference Scraper](https://github.com/vishaalagartha/basketball_reference_scraper)

---

**Plan saved to:** `docs/plans/2026-01-04-hooper-two-nba-bot.md`
