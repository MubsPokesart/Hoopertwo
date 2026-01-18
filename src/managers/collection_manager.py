"""Manager for collection-related business logic."""
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
            Dictionary with success status and already_owned flag
        """
        was_added = self.repository.add_player_to_collection(
            user_id, player_id, server_id
        )

        return {
            "success": True,
            "already_owned": not was_added
        }
