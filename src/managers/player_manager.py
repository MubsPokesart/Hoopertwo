"""Player manager for business logic operations.

Handles ADP board loading and rarity tier calculations.
"""
import csv
from typing import Optional
from pathlib import Path
from src.database.repositories.player_repository import PlayerRepository


class PlayerManager:
    """Manager for player-related business logic.

    Responsibilities:
    - Load ADP board from CSV
    - Calculate rarity tiers based on ADP value
    - Coordinate player data operations
    """

    # Rarity tier thresholds (based on ADP rank ranges)
    GOAT_THRESHOLD = 2.0      # M.Jordan (1.41) - L.James (1.90): 2 players
    MYTHIC_THRESHOLD = 33.0   
    LEGENDARY_THRESHOLD = 75.0 
    EPIC_THRESHOLD = 155.25 
    RARE_THRESHOLD = 260.1
    UNCOMMON_THRESHOLD = 260.1  

    def __init__(self, repository: PlayerRepository, adp_csv_path: str):
        """Initialize player manager.

        Args:
            repository: Player repository for database operations
            adp_csv_path: Path to ADP board CSV file
        """
        self.repository = repository
        self.adp_csv_path = adp_csv_path

    def calculate_rarity_tier(self, adp_value: Optional[float]) -> str:
        """Calculate rarity tier based on ADP value.

        Args:
            adp_value: Average draft position value (None for non-ADP players)

        Returns:
            Rarity tier string
        """
        if adp_value is None:
            return "Common"
        elif adp_value >= self.UNCOMMON_THRESHOLD:
            return "Uncommon"
        elif adp_value < self.GOAT_THRESHOLD:
            return "GOAT"
        elif adp_value < self.MYTHIC_THRESHOLD:
            return "Mythic"
        elif adp_value < self.LEGENDARY_THRESHOLD:
            return "Legendary"
        elif adp_value < self.EPIC_THRESHOLD:
            return "Epic"
        else:  # adp_value < RARE_THRESHOLD
            return "Rare"

    def load_adp_board(self) -> int:
        """Load ADP board from CSV into database.

        Returns:
            Number of players loaded
        """
        if not Path(self.adp_csv_path).exists():
            raise FileNotFoundError(f"ADP CSV not found: {self.adp_csv_path}")

        loaded_count = 0

        with open(self.adp_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row["Player"].strip()
                adp_value = float(row["ADP (31-)"])
                rarity_tier = self.calculate_rarity_tier(adp_value)

                # Create player (image URL will be added later by scraper)
                self.repository.create_player(
                    name=name,
                    adp_value=adp_value,
                    rarity_tier=rarity_tier,
                    image_url=None  # Will be populated by image scraper
                )
                loaded_count += 1

        return loaded_count

    def recalculate_all_rarities(self) -> int:
        """Recalculate rarity tiers for all players with ADP values.

        Uses current threshold values to recalculate and update rarities
        for all players that have an ADP value.

        Returns:
            Number of players updated
        """
        players_with_adp = self.repository.get_players_with_adp()
        updated_count = 0

        for player in players_with_adp:
            adp_value = player["adp_value"]
            current_rarity = player["rarity_tier"]
            new_rarity = self.calculate_rarity_tier(adp_value)

            # Only update if rarity changed
            if new_rarity != current_rarity:
                self.repository.update_player_rarity(player["id"], new_rarity)
                updated_count += 1

        return updated_count
