"""Manager for collection-related business logic."""
import math
from typing import Dict, Any, List
from src.database.repositories.collection_repository import CollectionRepository


class CollectionManager:
    """Manages collection business logic.

    Responsibilities:
    - Coordinate catching players
    - Retrieve collections with formatting
    - Calculate and format statistics
    """

    def __init__(self, repository: CollectionRepository):
        """Initialize manager with repository.

        Args:
            repository: Collection repository instance
        """
        self.repository = repository

    def catch_player(
        self,
        user_id: int,
        player_id: int,
        server_id: int
    ) -> Dict[str, Any]:
        """Attempt to catch a player and add to collection.

        Args:
            user_id: Discord user ID
            player_id: Player database ID
            server_id: Discord server ID

        Returns:
            Dictionary indicating whether the name was recognized and whether the
            player was already owned instead of newly captured
        """
        was_added = self.repository.add_player_to_collection(
            user_id, player_id, server_id
        )

        return {
            "success": True,
            "already_owned": not was_added
        }

    def get_collection(
        self,
        user_id: int,
        server_id: int,
        page: int = 0,
        page_size: int = 10,
        sort_by: str = "time_new"
    ) -> Dict[str, Any]:
        """Get a user's collection with pagination and stats.

        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            page: Page number (0-indexed)
            page_size: Number of players per page
            sort_by: Sort order - "time_new", "time_old", "rarity_best", "rarity_common"

        Returns:
            Dictionary with players, stats, and pagination info
        """
        # Get stats first to determine total pages
        stats = self.repository.get_collection_stats(user_id, server_id)
        total_pages = math.ceil(stats["total_players"] / page_size) if stats["total_players"] > 0 else 1

        # Get players for current page
        offset = page * page_size
        players = self.repository.get_user_collection(
            user_id, server_id, limit=page_size, offset=offset, sort_by=sort_by
        )

        return {
            "players": players,
            "stats": stats,
            "total_pages": total_pages,
            "current_page": page
        }
