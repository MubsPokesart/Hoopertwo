# HooperTwo - NBA Player Collection Discord Bot

Discord bot for collecting NBA players. Players spawn in chat after X messages, users recognize them to build collections. Rarity based on community ADP board, compete on leaderboards.

## Features

- 🏀 **Player Spawning**: Players appear after configurable message thresholds
- ✅ **Recognition System**: Use `/recognize` to catch spawned players
- 📦 **Collections**: View your collection with `/collection` (paginated)
- 🏆 **Leaderboards**: Compete on weekly/monthly/yearly/all-time leaderboards
- ⚙️ **Admin Controls**: Configure spawn channels and thresholds
- 💾 **Auto Backups**: Daily database backups with retention policy
- 🎯 **Rarity Tiers**: GOAT, Cosmic, Mythic, Legendary, Epic, Rare, Uncommon, Common
- 🌑 **Phantom Editions**: A rarer collectible edition of every player

## Quick Start

### Prerequisites

- Python 3.10+
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Poetry (for dependency management)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/HooperTwo.git
cd HooperTwo

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env and add your Discord bot token

# Run bot
poetry run python bot.py
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Commands

See [COMMANDS.md](docs/COMMANDS.md) for complete command reference.

### User Commands

- `/recognize <player>` - Catch a spawned player
- `/collection [@user]` - View your or someone's collection
- `/leaderboard [period]` - View server leaderboard
- `/rank [@user] [period]` - Check your or someone's rank

### Admin Commands (Require Administrator Permission)

- `/config` - View server configuration
- `/set-spawn-threshold <number>` - Set messages needed for spawn
- `/set-spawn-channels <channels>` - Configure spawn channels
- `/clear-spawn-channels` - Allow spawns in all channels
- `/backup` - Create manual database backup
- `/list-backups` - List available backups

## Development

```bash
# Run tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src

# Format code
poetry run black src tests

# Lint
poetry run ruff check src tests
```

## Project Structure

```
HooperTwo/
├── src/
│   ├── cogs/           # Discord command cogs
│   ├── managers/       # Business logic
│   ├── repositories/   # Database operations
│   ├── coordinators/   # State management
│   ├── tasks/          # Background tasks
│   └── utils/          # Utilities
├── tests/              # Test suite
├── data/               # ADP board and player data
├── backups/            # Database backups
└── docs/               # Documentation
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
