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

    # Rarity tier thresholds
    GOAT_THRESHOLD = 2.0
    MYTHIC_THRESHOLD = 32.0
    LEGENDARY_THRESHOLD = 64.0
    EPIC_THRESHOLD = 128.0
    RARE_THRESHOLD = 256.0
    UNCOMMON_THRESHOLD = 256.0

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

        Rarity tiers:
        - GOAT: ADP < 2
        - Mythic: 2 <= ADP < 32
        - Legendary: 32 <= ADP < 64
        - Epic: 64 <= ADP < 128
        - Rare: 128 <= ADP < 256
        - Uncommon: ADP >= 256 (on ADP board)
        - Common: No ADP value (not on ADP board)

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
