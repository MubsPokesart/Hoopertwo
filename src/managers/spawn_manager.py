"""Spawn manager for player spawning logic."""
import random
from typing import Dict, Any, List
from src.database.repositories.player_repository import PlayerRepository


class SpawnManager:
    """Manager for player spawning logic.

    Responsibilities:
    - Select random players with rarity-weighted probability
    - Calculate spawn weights based on rarity
    """

    # Spawn weights (higher = more common)
    RARITY_WEIGHTS = {
        "GOAT": 1,
        "Mythic": 5,
        "Legendary": 15,
        "Epic": 30,
        "Rare": 50,
        "Common": 100,
    }

    def __init__(self, player_repository: PlayerRepository):
        """Initialize spawn manager.

        Args:
            player_repository: Repository for player data access
        """
        self.repository = player_repository

    def _calculate_spawn_weight(self, rarity_tier: str) -> int:
        """Calculate spawn weight for a rarity tier.

        Args:
            rarity_tier: Rarity tier string

        Returns:
            Spawn weight (higher = more likely to spawn)
        """
        return self.RARITY_WEIGHTS.get(rarity_tier, 100)

    def select_random_player(self) -> Dict[str, Any]:
        """Select a random player weighted by rarity.

        Returns:
            Player dictionary
        """
        all_players = self.repository.get_all_players()

        if not all_players:
            raise ValueError("No players in database")

        # Calculate weights for each player
        weights = [
            self._calculate_spawn_weight(player["rarity_tier"])
            for player in all_players
        ]

        # Select random player using weights
        selected = random.choices(all_players, weights=weights, k=1)[0]
        return selected
