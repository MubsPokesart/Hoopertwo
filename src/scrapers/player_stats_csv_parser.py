"""CSV-based player statistics parser."""
from dataclasses import dataclass
from typing import Dict, Optional
from collections import defaultdict
import csv
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlayerStats:
    """Player statistics aggregated from CSV data."""
    name: str
    total_minutes: int
    nba_id: Optional[int]
    seasons_played: int


class PlayerStatsCSVParser:
    """Parse player statistics from CSV file."""

    def __init__(self, csv_path: str, min_career_minutes: int = 1000):
        """Initialize parser with CSV path and minimum minutes threshold.

        Args:
            csv_path: Path to CSV file with player stats
            min_career_minutes: Minimum career minutes to include player
        """
        self.csv_path = csv_path
        self.min_career_minutes = min_career_minutes

    def parse_players(self) -> Dict[str, PlayerStats]:
        """Parse CSV and return players with >min_career_minutes.

        Returns:
            Dict[player_name, PlayerStats] for all qualified players
        """
        # Aggregate data by player name
        player_data = defaultdict(lambda: {
            'minutes': 0,
            'seasons': 0,
            'nba_id': None
        })

        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                player_name = row['Player']

                # Parse minutes - skip row if invalid
                try:
                    mp_value = row['MP'].strip()
                    if not mp_value:
                        logger.warning(f"Skipping row for {player_name}: missing MP value")
                        continue
                    # Convert to float first (CSV has decimal format like '333.0'), then to int
                    minutes = int(float(mp_value))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping row for {player_name}: invalid MP value - {e}")
                    continue

                # Parse nba_id - store as None if invalid
                try:
                    nba_id = int(row['nba_id'])
                except (ValueError, KeyError):
                    logger.debug(f"Invalid nba_id for {player_name}, storing as None")
                    nba_id = None

                # Aggregate minutes and count seasons
                player_data[player_name]['minutes'] += minutes
                player_data[player_name]['seasons'] += 1
                player_data[player_name]['nba_id'] = nba_id

        # Convert aggregated data to PlayerStats objects, filtering by minimum minutes
        players = {}
        for name, data in player_data.items():
            if data['minutes'] >= self.min_career_minutes:
                players[name] = PlayerStats(
                    name=name,
                    total_minutes=data['minutes'],
                    nba_id=data['nba_id'],
                    seasons_played=data['seasons']
                )

        return players
