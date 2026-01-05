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
