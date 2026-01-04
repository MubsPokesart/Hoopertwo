# HooperTwo - Development Guide

## Project Overview

Discord bot for collecting NBA players. Players spawn in chat after X messages, users recognize them to build collections. Rarity based on community ADP board, compete on leaderboards.

**Key Details:**
- NBA version of PokeTwo
- Python 3.10+, discord.py, SQLite, Docker
- Single-server focus, designed to scale
- Read full plan: `docs/plans/2026-01-04-hooper-two-nba-bot.md`

## Architecture

**Stack:** Python 3.10+, discord.py (hybrid commands), SQLite, in-memory cache, Poetry, Docker

**Patterns:**
- Managers: Business logic (PlayerManager, SpawnManager)
- Repositories: Database ops (PlayerRepository)
- Coordinators: State management (CacheCoordinator)
- Cogs: Discord commands (AdminCog, SpawningCog)

**Rarity Tiers:** Based on `data/adp_board.csv`
- GOAT (< 2.0 ADP): 1 spawn weight
- Mythic (2-31.9): 5 weight
- Legendary (32-63.9): 15 weight
- Epic (64-127.9): 30 weight
- Rare (128-255.9): 50 weight
- Common (256+): 100 weight

## Coding Standards

**File Structure:**
- Max 500 lines per file (strict)
- Split at 400 lines
- No god classes

**OOP:**
- Single Responsibility Principle
- Functions under 30-40 lines
- Classes under 200 lines
- Descriptive names (no `data`, `temp`, `helper`)

**Security (Critical):**
- ONLY parameterized SQL: `cursor.execute("SELECT * FROM x WHERE y = ?", (value,))`
- Validate ALL user input
- Rate limit all commands: `@commands.cooldown(1, 5, commands.BucketType.user)`
- Tokens in environment variables only

## Development Commands

```bash
# Setup
cp .env.example .env  # Add Discord token
poetry install

# Run locally
poetry run python bot.py

# Test
poetry run pytest -v
poetry run pytest --cov=src

# Docker (one command)
docker compose up

# Format/Lint
poetry run black src tests
poetry run ruff check src tests
```

## Testing (TDD Required)

1. Write failing test
2. Run to verify fail
3. Implement minimal code
4. Run to verify pass
5. Commit

**Coverage:** 80%+ overall, 100% for critical paths (spawning, collection)

## Repository Rules

**Never:**
- Push directly to `main`
- Commit secrets/tokens
- String concatenate SQL queries
- Skip input validation
- Create 500+ line files

**Always:**
- Branch: `feature/<name>` or `fix/<name>`
- Commit format: `<type>: <description>` (feat, fix, test, refactor, docs, chore)
- PR required for `main`
- All tests pass before merge

## Key Files

**Docs:**
- `docs/plans/2026-01-04-hooper-two-nba-bot.md`: Implementation plan
- `data/adp_board.csv`: Rarity source of truth

**Config:**
- `.env.example`: Environment template
- `pyproject.toml`: Dependencies
- `docker-compose.yml`: Deployment

**Code:**
- `bot.py`: Entry point
- `src/managers/`: Business logic
- `src/repositories/`: Database
- `src/cogs/`: Commands
