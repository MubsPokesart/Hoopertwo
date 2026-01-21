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
