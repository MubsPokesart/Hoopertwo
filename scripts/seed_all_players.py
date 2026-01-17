"""Seed database with all NBA players who have >1000 career minutes.

This script parses player stats from CSV (data/scoring.csv), filters for those with
>1000 career minutes, verifies they have valid images, and adds them to
the database as Common rarity. Skips players already in the database
(preserves ADP board data).

Run from project root: python scripts/seed_all_players.py
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Set
import time
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.config.settings import get_settings
from src.scrapers.basketball_reference_client import BasketballReferenceClient
from src.scrapers.player_stats_csv_parser import PlayerStatsCSVParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MIN_CAREER_MINUTES = 1000
BATCH_COMMIT_SIZE = 100


class SkipListManager:
    """Manages a persistent skip list to avoid re-fetching failed players."""

    def __init__(self, skip_file_path: Path):
        """Initialize skip list manager.

        Args:
            skip_file_path: Path to JSON file storing skip list
        """
        self.skip_file_path = skip_file_path
        self.skip_list: Dict[str, Set[str]] = {
            'api_error': set(),
            'below_threshold': set(),
            'no_image': set()
        }

    def load(self) -> None:
        """Load skip list from JSON file."""
        if not self.skip_file_path.exists():
            logger.info(f"No skip list found at {self.skip_file_path}, starting fresh")
            return

        try:
            with open(self.skip_file_path, 'r') as f:
                data = json.load(f)

            # Convert lists back to sets
            for category in self.skip_list.keys():
                if category in data:
                    self.skip_list[category] = set(data[category])

            total_skipped = sum(len(players) for players in self.skip_list.values())
            logger.info(f"Loaded skip list with {total_skipped} players:")
            for category, players in self.skip_list.items():
                if players:
                    logger.info(f"  - {category}: {len(players)} players")

        except Exception as e:
            logger.error(f"Error loading skip list: {e}")

    def save(self) -> None:
        """Save skip list to JSON file."""
        try:
            # Convert sets to lists for JSON serialization
            data = {
                category: sorted(list(players))
                for category, players in self.skip_list.items()
            }

            with open(self.skip_file_path, 'w') as f:
                json.dump(data, f, indent=2)

            total_skipped = sum(len(players) for players in self.skip_list.values())
            logger.info(f"Saved skip list with {total_skipped} players to {self.skip_file_path}")

        except Exception as e:
            logger.error(f"Error saving skip list: {e}")

    def should_skip(self, player_name: str) -> Optional[str]:
        """Check if player should be skipped.

        Args:
            player_name: Full player name

        Returns:
            Skip reason if player should be skipped, None otherwise
        """
        for category, players in self.skip_list.items():
            if player_name in players:
                return category
        return None

    def add_skipped_player(self, player_name: str, reason: str) -> None:
        """Add player to skip list.

        Args:
            player_name: Full player name
            reason: Skip reason (api_error, below_threshold, no_image)
        """
        if reason in self.skip_list:
            self.skip_list[reason].add(player_name)
        else:
            logger.warning(f"Unknown skip reason: {reason}")


def is_on_adp_board(player_name: str, repo: PlayerRepository) -> bool:
    """Check if player is on ADP board.

    Args:
        player_name: Full player name
        repo: Player repository instance

    Returns:
        True if player exists in database with ADP value
    """
    player = repo.get_player_by_name(player_name)
    return player is not None and player.get('adp_value') is not None


def seed_all_players():
    """Main function to seed database with all NBA players >1000 minutes."""
    logger.info("Starting player seeding process...")

    # Get settings
    settings = get_settings()

    # Initialize database
    db = ConnectionManager(settings.database_path)
    repo = PlayerRepository(db)

    # Initialize Basketball Reference client
    logger.info("Initializing Basketball Reference client...")
    br_client = BasketballReferenceClient(
        player_id_db_path="data/player_ids.json"
    )

    # Initialize skip list manager
    skip_list_path = Path("data/skipped_players.json")
    skip_list = SkipListManager(skip_list_path)
    skip_list.load()

    # Parse players from CSV
    logger.info("Parsing player stats from CSV...")
    csv_parser = PlayerStatsCSVParser(
        csv_path="data/scoring.csv",
        min_career_minutes=MIN_CAREER_MINUTES
    )
    qualified_players = csv_parser.parse_players()
    logger.info(f"Found {len(qualified_players)} players with >{MIN_CAREER_MINUTES} minutes")

    # Track statistics
    stats = {
        'total_checked': 0,
        'already_exists': 0,
        'skipped_cached': 0,
        'no_image': 0,
        'adp_missing_image': 0,
        'added': 0
    }

    start_time = time.time()
    last_commit = 0

    for idx, (player_name, player_stats) in enumerate(qualified_players.items(), 1):
        career_minutes = player_stats.total_minutes

        stats['total_checked'] += 1

        # Check if player is in skip list
        skip_reason = skip_list.should_skip(player_name)
        if skip_reason:
            stats['skipped_cached'] += 1
            logger.debug(f"Skipping {player_name} (cached: {skip_reason})")
            continue

        # Check if player already exists in database
        existing = repo.get_player_by_name(player_name)
        if existing:
            stats['already_exists'] += 1
            logger.debug(f"Skipping {player_name} (already in database)")
            continue

        # Log progress
        logger.info(f"[{idx}/{len(qualified_players)}] Processing {player_name} ({career_minutes:,} minutes)...")

        # Check if player is on ADP board
        on_adp_board = is_on_adp_board(player_name, repo)

        # Get image URL from Basketball Reference
        image_url = br_client.get_player_image_url(player_name)

        # Decision logic
        if image_url:
            # Has image - add to database
            try:
                repo.create_player(
                    name=player_name,
                    adp_value=None,  # Not on ADP board
                    rarity_tier="Common",
                    image_url=image_url,
                    career_minutes=career_minutes
                )
                stats['added'] += 1
                logger.info(f"Added {player_name} ({career_minutes:,} minutes)")

            except Exception as e:
                logger.error(f"Error adding {player_name}: {e}")

        elif on_adp_board:
            # ADP board player without image - LOG and store with NULL
            logger.error(f"ADP BOARD PLAYER MISSING IMAGE: {player_name}")
            logger.error(f"   Manual intervention required!")

            # Check if it was an estimated ID
            player_id_br = br_client.find_player_id(player_name)
            if player_id_br:
                db = br_client._load_player_id_database()
                if player_name in db['estimated']:
                    logger.warning(f"Estimated player ID failed: {player_name} -> {player_id_br}")
                    logger.warning(f"   Consider manual verification and moving to 'verified' section")

            try:
                repo.create_player(
                    name=player_name,
                    adp_value=None,  # Will be set by ADP board loader
                    rarity_tier="Common",
                    image_url=None,  # NULL - needs manual fix
                    career_minutes=career_minutes
                )
                stats['adp_missing_image'] += 1
            except Exception as e:
                logger.error(f"Error adding {player_name}: {e}")

        else:
            # Not on ADP board, no image - skip entirely
            stats['no_image'] += 1
            skip_list.add_skipped_player(player_name, 'no_image')
            logger.debug(f"Skipping {player_name} (no image, not on ADP board)")
            continue

        # Batch commit every 100 players
        if stats['added'] - last_commit >= BATCH_COMMIT_SIZE:
            db.get_connection().commit()
            skip_list.save()  # Save skip list with each batch
            last_commit = stats['added']

            # Calculate progress
            elapsed = time.time() - start_time
            rate = stats['total_checked'] / elapsed if elapsed > 0 else 0
            remaining = len(qualified_players) - stats['total_checked']
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_minutes = eta_seconds / 60

            logger.info(f"Progress: {stats['added']} added, {stats['total_checked']}/{len(qualified_players)} checked")
            logger.info(f"ETA: {eta_minutes:.1f} minutes remaining")
           

    # Final commit and save skip list
    db.get_connection().commit()
    skip_list.save()

    # Print final statistics
    elapsed_time = time.time() - start_time
    logger.info("\n" + "="*60)
    logger.info("SEEDING COMPLETE!")
    logger.info("="*60)
    logger.info(f"Total players checked: {stats['total_checked']}")
    logger.info(f"Already in database: {stats['already_exists']}")
    logger.info(f"Skipped (cached from previous runs): {stats['skipped_cached']}")
    logger.info(f"No valid image: {stats['no_image']}")
    logger.info(f"ADP board players missing images: {stats['adp_missing_image']}")
    logger.info(f"Successfully added: {stats['added']}")
    logger.info(f"Total time: {elapsed_time/60:.2f} minutes ({elapsed_time/3600:.2f} hours)")
    logger.info("="*60)

    if stats['adp_missing_image'] > 0:
        logger.error("\n" + "="*60)
        logger.error("MANUAL INTERVENTION REQUIRED")
        logger.error("="*60)
        logger.error("The following ADP board players need images added manually:")
        logger.error("Check logs above for player names marked with 'ADP BOARD PLAYER MISSING IMAGE'")
        logger.error("="*60)

    db.close()


if __name__ == "__main__":
    try:
        seed_all_players()
    except KeyboardInterrupt:
        logger.info("\nSeeding interrupted by user. Progress has been saved.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
