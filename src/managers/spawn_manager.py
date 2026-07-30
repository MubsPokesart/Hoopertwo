"""Spawn manager for player spawning logic."""
import random
from typing import Dict, Any
from src.database.repositories.player_repository import PlayerRepository


class SpawnManager:
    """Manager for player spawning logic.

    Responsibilities:
    - Select random players with rarity-weighted probability
    - Calculate spawn weights based on rarity
    """

    SPAWN_WEIGHTS = {
        "GOAT": 25,
        "Cosmic": 100,
        "Mythic": 375,
        "Legendary": 2000,
        "Epic": 7500,
        "Rare": 9500,
        "Uncommon": 12500,
        "Common": 65000,
        "Phantom": 3000,
    }
    BASE_RARITIES = tuple(bucket for bucket in SPAWN_WEIGHTS if bucket != "Phantom")

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
        return self.SPAWN_WEIGHTS.get(rarity_tier, 0)

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
            players_by_tier.setdefault(tier, []).append(player)

        missing_tiers = [tier for tier in self.BASE_RARITIES if tier not in players_by_tier]
        if missing_tiers:
            missing = ", ".join(missing_tiers)
            raise ValueError(f"Player bank is missing spawn tiers: {missing}")

        # Phantom is an edition pool containing every player, not a base rarity.
        spawn_buckets = list(self.SPAWN_WEIGHTS)
        bucket_weights = [self._calculate_spawn_weight(bucket) for bucket in spawn_buckets]
        selected_bucket = random.choices(
            spawn_buckets,
            weights=bucket_weights,
            k=1,
        )[0]

        player_pool = (
            all_players if selected_bucket == "Phantom" else players_by_tier[selected_bucket]
        )
        selected = dict(random.choice(player_pool))
        selected["edition"] = "Phantom" if selected_bucket == "Phantom" else "Standard"
        return selected
