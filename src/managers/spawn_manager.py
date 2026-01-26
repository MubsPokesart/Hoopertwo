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
        "GOAT": 1,        # 0.025% spawn rate (2 players)
        "Mythic": 19,     # 0.475% spawn rate (31 players)
        "Legendary": 80,  # 2.0% spawn rate (42 players)
        "Epic": 300,      # 7.5% spawn rate (81 players)
        "Rare": 400,      # 10.0% spawn rate (104 players)
        "Uncommon": 600,  # 15.0% spawn rate (186 players)
        "Common": 2600,   # 65.0% spawn rate (remaining)
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

        Two-step process:
        1. Select a rarity tier based on tier weights
        2. Randomly select a player from that tier

        Returns:
            Player dictionary
        """
        all_players = self.repository.get_all_players()

        if not all_players:
            raise ValueError("No players in database")

        # Group players by rarity tier
        players_by_tier = {}
        for player in all_players:
            tier = player["rarity_tier"]
            if tier not in players_by_tier:
                players_by_tier[tier] = []
            players_by_tier[tier].append(player)

        # Step 1: Select a rarity tier weighted by tier weights
        tiers = list(players_by_tier.keys())
        tier_weights = [self._calculate_spawn_weight(tier) for tier in tiers]
        selected_tier = random.choices(tiers, weights=tier_weights, k=1)[0]

        # Step 2: Randomly select a player from that tier (equal probability)
        selected = random.choice(players_by_tier[selected_tier])
        return selected
