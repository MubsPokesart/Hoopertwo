"""Application configuration loaded from environment variables."""
import os
from typing import Optional
from pathlib import Path
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

        # ADP Board Configuration
        self.adp_csv_path = os.getenv("ADP_CSV_PATH", "data/adp_board.csv")
        self.adp_players_path = os.getenv("PLAYER_ID_PATH", "data/player_ids.json")

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

        # Ensure backup directory exists
        Path(self.backup_directory).mkdir(parents=True, exist_ok=True)

    def _get_required(self, key: str) -> str:
        """Get a required environment variable or raise ValueError."""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"{key} environment variable is required. "
                f"Copy .env.example to .env and configure it."
            )
        return value


# Lazy singleton instance
_settings_instance = None


def get_settings() -> Settings:
    """Get or create the singleton Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
