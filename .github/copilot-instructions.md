# HooperTwo Copilot Instructions

## Project overview and architecture

HooperTwo is a Python 3.10+ Discord bot built with `discord.py`, Poetry, and SQLite.
It spawns NBA players in chat, lets users recognize them, stores per-server
collections, and builds snapshot-based leaderboards.

- `bot.py` is the application entry point and composition root. `HooperTwoBot.setup_hook`
  creates the shared connection/cache, repositories, managers, cogs, and scheduled
  tasks. Wire new runtime dependencies there; the `setup()` functions in several cogs
  are currently stubs and are not the active loading path.
- The main request flow is Discord cog -> manager -> repository -> SQLite. Cogs own
  Discord interactions, embeds, views, and command-facing validation; managers own
  business rules; repositories own SQL and return dictionaries/lists.
- `ConnectionManager` creates the schema in `src/database/models.py`, enables foreign
  keys, and exposes one SQLite connection. `PlayerRepository` receives the
  `ConnectionManager`; the collection, leaderboard, and config repositories receive
  the raw `sqlite3.Connection`.
- `CacheCoordinator` stores per-channel message counts and active spawns in memory.
  This state is intentionally process-local and is lost on restart. Durable player,
  collection, config, and leaderboard state belongs in SQLite.
- Leaderboards read daily snapshots, not live collection queries. `ScheduledTasks`
  creates all period snapshots at midnight UTC and a verified SQLite backup at 02:00
  UTC.
- The player-data pipeline is separate from bot runtime. `scripts/seed_all_players.py`
  combines `data/scoring.csv`, ADP/player-ID data, Basketball Reference image lookup,
  and manual/skip-list JSON files. `NBAApiClient` is deprecated for seeding.
  `scripts/init_database.py` can bootstrap from `data/hooper_two_players_only.sql`;
  normal `ConnectionManager` initialization creates schema but does not seed players.

## Setup, run, build, test, and lint

```bash
# Install all runtime and development dependencies
poetry install

# Configure DISCORD_TOKEN and other overrides before starting the bot
cp .env.example .env
poetry run python bot.py

# Container build and run
docker compose build
docker compose up -d

# Full test suite and coverage
poetry run pytest -v
poetry run pytest --cov=src

# One test file, or one test by node ID
poetry run pytest tests/test_managers/test_spawn_manager.py -v
poetry run pytest tests/test_managers/test_spawn_manager.py::test_select_random_player_returns_player -v

# Integration tests
poetry run pytest tests/integration/test_full_workflow.py -v

# Lint and formatting checks; Black uses a 100-character line length
poetry run ruff check src tests
poetry run black --check src tests

# Apply formatting
poetry run black src tests
```

Pytest uses `asyncio_mode = "auto"`. Async Discord tests still commonly use
`@pytest.mark.asyncio`.

## Repository-specific conventions

- Use absolute imports rooted at `src`.
- Keep SQL in repositories and always bind values with `?` parameters. When SQL syntax
  cannot be parameterized, such as collection sort order, select it from a fixed
  allowlist before interpolating it.
- Repository query results are dictionaries keyed by database column name. Preserve
  that contract through managers because cogs and integration tests consume it
  directly.
- Collections are unique by `(user_id, player_id, server_id)`. A repeated catch is a
  successful recognition with `already_owned=True`, not another collection row.
  Server configuration is also server-scoped; `spawn_channels` is stored as JSON and
  an empty list means all channels.
- Validate command input before business logic. Player-name matching must go through
  `InputValidator` and `TextNormalizer`, which deliberately make recognition
  case-, accent-, dot-, apostrophe-, dash-, and whitespace-insensitive.
- For new Discord commands, follow the command type already used by the owning cog
  (`app_commands` for slash-only commands and `hybrid_command` where both forms are
  required). Add a per-user cooldown appropriate to that command. Admin commands use
  both `@app_commands.default_permissions(administrator=True)` and
  `@app_commands.checks.has_permissions(administrator=True)`.
- Rarity is a cross-module contract. A tier or threshold change may require coordinated
  updates to the schema `CHECK` in `src/database/models.py`, thresholds in
  `PlayerManager`, weights in `SpawnManager`, points and SQL `CASE` expressions in
  `collection_repository.py`, spawn embed colors, seed/recalculation scripts, and
  tests. Do not update only one of these surfaces.
- Treat `data/adp_board.csv` and the versioned player-ID/SQL data as source data, not
  disposable fixtures. Database-changing scripts should use configured paths and
  preserve existing data unless an explicit destructive option such as `--clear` was
  requested.
- Repository tests create real temporary SQLite databases with `tmp_path` and
  `ConnectionManager`. Manager tests inject mocked repositories. Cog tests use
  `MagicMock`/`AsyncMock`; decorated commands are generally invoked through
  `command.callback(cog, context, ...)`. Integration fixtures wire the real
  repository/manager graph against a temporary database.
- `Settings` loads `.env` and requires `DISCORD_TOKEN`; settings tests must isolate
  environment changes with `monkeypatch`.
- Follow the limits recorded in `CLAUDE.md`: split files around 400 lines and never
  exceed 500 lines; keep classes below 200 lines and functions around 30-40 lines.
- Use `feature/<name>` or `fix/<name>` branches. Commit messages use
  `<type>: <description>` with `feat`, `fix`, `test`, `refactor`, `docs`, or `chore`;
  changes reach `main` through a pull request.
