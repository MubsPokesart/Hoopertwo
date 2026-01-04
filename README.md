# HooperTwo - NBA Discord Bot

A Discord bot for collecting NBA players. Players spawn in chat, and users recognize them to build their collection.

## Features

- Random NBA player spawning based on message activity
- Rarity tiers: GOAT, Mythic, Legendary, Epic, Rare, Common
- Leaderboards (Weekly, Monthly, Yearly, All-Time)
- Per-server configuration
- Automated backups

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
