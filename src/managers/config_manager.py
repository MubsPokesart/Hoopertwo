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
