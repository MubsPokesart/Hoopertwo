"""Seed database with all NBA players who have >1000 career minutes.

This script parses player stats from CSV (data/scoring.csv), filters for those with
>1000 career minutes, verifies they have valid images, and adds them to
the database with appropriate rarity tiers. After processing the CSV, it also
checks for any ADP board players not in the CSV and adds them to ensure 100%
ADP board coverage.

Usage:
    # Normal run (incremental, preserves existing players)
    python scripts/seed_all_players.py

    # Fresh start (clears database first)
    python scripts/seed_all_players.py --clear

Features:
- Image verification via nodriver (Cloudflare bypass)
- Skip list caching for efficient re-runs
- ADP board players bypass verification (added even without images)
- Processes missing ADP players after CSV processing
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Set
import time
import json
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.config.settings import get_settings
from src.scrapers.basketball_reference_client import BasketballReferenceClient
from src.scrapers.player_stats_csv_parser import PlayerStatsCSVParser
from src.scrapers.image_verifier import ImageVerifier
from src.scrapers.basketball_reference_searcher import BasketballReferenceSearcher
from src.managers.player_manager import PlayerManager

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


def clear_seeded_players(db: ConnectionManager) -> int:
    """Clear all players from the database to prepare for fresh seeding.

    Args:
        db: Database connection manager

    Returns:
        Number of players deleted
    """
    cursor = db.get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM players")
    count = cursor.fetchone()[0]

    if count > 0:
        cursor.execute("DELETE FROM players")
        db.get_connection().commit()
        logger.info(f"Cleared {count} players from database")
    else:
        logger.info("No players to clear from database")

    return count


def is_on_adp_board(player_name: str, adp_players_path: str) -> bool:
    """Check if player is on ADP board.

    Args:
        player_name: Full player name
        adp_players_path: Average draft position instance

    Returns:
        True if player exists in database with ADP value
    """

    with open(adp_players_path, 'r') as file:
        data = json.load(file)
        return player_name in data["verified"] or player_name in data["estimated"]
    return False
        

def get_all_adp_players(adp_players_path: str) -> Dict[str, dict]:
    """Get all players on the ADP board (both verified and estimated).

    Args:
        adp_players_path: Path to ADP players JSON file

    Returns:
        Dictionary mapping player names to their ADP objects
    """
    with open(adp_players_path, 'r') as file:
        data = json.load(file)
        all_players = {}
        all_players.update(data.get("verified", {}))
        all_players.update(data.get("estimated", {}))
        return all_players


def get_adp_object(player_name: str, adp_players_path: str) -> dict:
    """Get the details on a player on the ADP board

    Args:
        player_name: Full player name
        adp_players_path: Average draft position instance

    Returns:
        Object detailing player_id, url, and adp
    """

    with open(adp_players_path, 'r') as file:
        data = json.load(file)
        if player_name in data["verified"]: return data["verified"][player_name]
        if player_name in data["estimated"]: return data["estimated"][player_name]
    
    return None


async def seed_all_players(clear_database: bool = False):
    """Main function to seed database with all NBA players >1000 minutes.

    Process:
    1. (Optional) Clear existing players from database
    2. Parse players from scoring.csv with >1000 career minutes
    3. For each player in CSV:
       - Verify image URL (unless on ADP board)
       - Add to database with appropriate rarity tier
    4. Process ADP board players not in scoring.csv
       - Add any missing ADP players to ensure 100% coverage

    Args:
        clear_database: If True, clears all players before seeding (default: False)
    """
    logger.info("Starting player seeding process...")

    # Get settings
    settings = get_settings()

    # Initialize database
    db = ConnectionManager(settings.database_path)
    repo = PlayerRepository(db)

    # Optional: Clear database for fresh seeding
    if clear_database:
        logger.warning("CLEARING DATABASE - All existing players will be removed!")
        clear_seeded_players(db)
        logger.info("Database cleared. Starting fresh seeding...\n")

    # Initialize Basketball Reference client
    logger.info("Initializing Basketball Reference client...")
    br_client = BasketballReferenceClient(
        player_id_db_path=settings.adp_players_path
    )

    # Initialize ImageVerifier for Cloudflare-protected image URL verification
    logger.info("Initializing ImageVerifier (nodriver browser for Cloudflare bypass)...")
    image_verifier = ImageVerifier(rate_limit_delay=2.5)

    # Initialize BasketballReferenceSearcher for collision resolution
    logger.info("Initializing BasketballReferenceSearcher for player ID collision resolution...")
    br_searcher = BasketballReferenceSearcher(rate_limit_delay=2.5)

    # Initialize skip list manager
    skip_list_path = Path("data/skipped_players.json")
    skip_list = SkipListManager(skip_list_path)
    skip_list.load()

    # Load manual image overrides
    manual_images_path = Path("data/manual_images.json")
    manual_images = {}
    if manual_images_path.exists():
        with open(manual_images_path, 'r') as f:
            manual_images = json.load(f)
        logger.info(f"Loaded {len(manual_images)} manual image overrides")
    else:
        logger.info("No manual image overrides found")

    # Populate the database with players on the adp
    player_manager = PlayerManager(repo, settings.adp_csv_path)

    # Parse players from CSV
    logger.info("Parsing player stats from CSV...")
    csv_parser = PlayerStatsCSVParser(
        csv_path="data/scoring.csv",
        min_career_minutes=MIN_CAREER_MINUTES
    )
    qualified_players = csv_parser.parse_players()
    logger.info(f"Found {len(qualified_players)} players with >{MIN_CAREER_MINUTES} minutes")

    # Calculate cutoff for pure search vs inference approach
    # Last 2/5 of players use pure search to avoid '01' ID collision issues
    total_players = len(qualified_players)
    cutoff_index = int(total_players * 3 / 5)  # Last 2/5 starts at 3/5 mark

    logger.info(f"\n{'='*60}")
    logger.info(f"IMAGE RETRIEVAL STRATEGY")
    logger.info(f"{'='*60}")
    logger.info(f"First {cutoff_index} players: Inference (4-tier lookup)")
    logger.info(f"Last {total_players - cutoff_index} players: Pure search (nodriver)")
    logger.info(f"Cutoff index: {cutoff_index}")
    logger.info(f"{'='*60}\n")

    # Track statistics
    stats = {
        'total_checked': 0,
        'already_exists': 0,
        'skipped_cached': 0,
        'no_image': 0,
        'adp_missing_image': 0,
        'added': 0,
        'pure_search_used': 0,      # NEW
        'pure_search_success': 0,   # NEW
        'pure_search_failed': 0,    # NEW
        'inference_used': 0         # NEW
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
        on_adp_board = is_on_adp_board(player_name, settings.adp_players_path)

        # Get ADP object if player is on board (fetch once for all code paths)
        player_object = None
        if on_adp_board:
            player_object = get_adp_object(player_name, settings.adp_players_path)

        # Check for manual image override first
        if player_name in manual_images:
            image_url = manual_images[player_name]
            logger.info(f"Using manual image override for {player_name}")
        else:
            # Determine approach: pure search (last 2/5) vs inference (first 3/5)
            use_pure_search = idx > cutoff_index

            if use_pure_search:
                # PURE SEARCH PATH: Direct nodriver search to avoid '01' ID collisions
                stats['pure_search_used'] += 1
                logger.info(f"Using pure search for {player_name} (player {idx}/{total_players})")

                # Validate year range exists
                if player_stats.year_start and player_stats.year_end:
                    try:
                        # Direct search via nodriver to get correct player_id
                        player_id = await br_searcher.search_player_by_name_and_years(
                            player_name,
                            player_stats.year_start,
                            player_stats.year_end
                        )

                        if player_id:
                            # Construct image URL from search result
                            image_url = br_client.construct_image_url(player_id)
                            stats['pure_search_success'] += 1
                            logger.info(f"Pure search found: {player_name} -> {player_id}")
                        else:
                            # No matching player found in search results
                            logger.warning(f"Pure search failed for {player_name}, no matching player found")
                            image_url = None
                            stats['pure_search_failed'] += 1

                    except Exception as e:
                        # Network error or search failure
                        logger.error(f"Pure search error for {player_name}: {e}")
                        image_url = None
                        stats['pure_search_failed'] += 1
                else:
                    # Missing year range (unlikely for last 2/5 of players)
                    logger.warning(f"Skipping pure search for {player_name}: missing year range")
                    image_url = None
                    stats['pure_search_failed'] += 1

            else:
                # INFERENCE PATH: Existing 4-tier lookup (first 3/5)
                stats['inference_used'] += 1
                logger.debug(f"Using inference for {player_name} (player {idx}/{total_players})")

                year_range = (player_stats.year_start, player_stats.year_end)
                image_url = await br_client.get_player_image_url(
                    player_name,
                    year_range=year_range,
                    searcher=br_searcher
                )

        # Verify image exists (unless ADP player - those skip verification)
        # ADP players are added even without valid images and flagged for manual fixing
        if image_url and not on_adp_board:
            logger.debug(f"Verifying image URL for {player_name}...")
            is_valid = await image_verifier.verify_image_url(image_url)

            if not is_valid:
                image_url = None  # Mark as invalid
                skip_list.add_skipped_player(player_name, 'no_image')
                logger.info(f"Image verification failed for {player_name}, added to skip list")

        # Decision logic
        if on_adp_board and image_url:
            # On ADP - give it a rarity and adp value
            try:
                repo.create_player(
                    name=player_name,
                    adp_value=player_object["adp"],
                    rarity_tier=player_manager.calculate_rarity_tier(player_object["adp"]),
                    image_url=image_url,
                    career_minutes=career_minutes
                )

                stats['added'] += 1
                rarity_tier = player_manager.calculate_rarity_tier(
                    player_object["adp"]
                )
                logger.info(
                    f"Added {player_name} ({rarity_tier}) "
                    f"({career_minutes:,} minutes)"
                )

            except Exception as e:
                logger.error(f"Error adding {player_name}: {e}")
        
        elif image_url:
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

        elif on_adp_board and not image_url:
            # ADP board player without image - LOG and store with NULL image but correct ADP
            logger.error(f"ADP BOARD PLAYER MISSING IMAGE: {player_name}")
            logger.error(f"   Manual intervention required!")

            try:
                repo.create_player(
                    name=player_name,
                    adp_value=player_object["adp"],  # Use actual ADP value
                    rarity_tier=player_manager.calculate_rarity_tier(player_object["adp"]),
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

    # Process ADP board players that weren't in the scoring CSV
    logger.info("\n" + "="*60)
    logger.info("PROCESSING MISSING ADP BOARD PLAYERS")
    logger.info("="*60)
    logger.info("Checking for ADP board players not in scoring.csv...")

    all_adp_players = get_all_adp_players(settings.adp_players_path)
    missing_adp_players = {
        name: obj for name, obj in all_adp_players.items()
        if name not in qualified_players
    }

    logger.info(f"Found {len(missing_adp_players)} ADP board players not in scoring.csv")

    stats['missing_adp_processed'] = 0
    stats['missing_adp_added'] = 0
    stats['missing_adp_already_exists'] = 0
    stats['missing_adp_no_image'] = 0

    for player_name, player_obj in missing_adp_players.items():
        stats['missing_adp_processed'] += 1

        # Check if player already exists in database
        existing = repo.get_player_by_name(player_name)
        if existing:
            stats['missing_adp_already_exists'] += 1
            logger.debug(f"Skipping {player_name} (already in database)")
            continue

        # Check for manual image override first
        if player_name in manual_images:
            image_url = manual_images[player_name]
            logger.info(f"Using manual image override for missing ADP player: {player_name}")
        else:
            # Get image URL from Basketball Reference
            # Note: Missing ADP players don't have year ranges from CSV, so pass None
            image_url = await br_client.get_player_image_url(
                player_name,
                year_range=None,
                searcher=br_searcher
            )

        # Calculate rarity tier from ADP value
        adp_value = player_obj.get("adp")
        rarity_tier = player_manager.calculate_rarity_tier(adp_value) if adp_value else "Common"

        if image_url:
            # Has image - add to database with ADP rarity
            try:
                repo.create_player(
                    name=player_name,
                    adp_value=adp_value,
                    rarity_tier=rarity_tier,
                    image_url=image_url,
                    career_minutes=0  # No minutes data from scoring.csv
                )
                stats['missing_adp_added'] += 1
                stats['added'] += 1
                logger.info(f"Added missing ADP player: {player_name} ({rarity_tier}, ADP: {adp_value})")

            except Exception as e:
                logger.error(f"Error adding {player_name}: {e}")
        else:
            # ADP board player without image - LOG and store with NULL
            logger.error(f"MISSING ADP PLAYER WITHOUT IMAGE: {player_name}")
            logger.error(f"   Manual intervention required!")

            try:
                repo.create_player(
                    name=player_name,
                    adp_value=adp_value,
                    rarity_tier=rarity_tier,
                    image_url=None,  # NULL - needs manual fix
                    career_minutes=0  # No minutes data from scoring.csv
                )
                stats['missing_adp_no_image'] += 1
                stats['adp_missing_image'] += 1
                stats['added'] += 1

            except Exception as e:
                logger.error(f"Error adding {player_name}: {e}")

    # Final commit for missing ADP players
    db.get_connection().commit()

    logger.info(f"\nMissing ADP board players summary:")
    logger.info(f"  Processed: {stats['missing_adp_processed']}")
    logger.info(f"  Added with image: {stats['missing_adp_added']}")
    logger.info(f"  Added without image (needs manual fix): {stats['missing_adp_no_image']}")
    logger.info(f"  Already existed: {stats['missing_adp_already_exists']}")

    # Print final statistics
    elapsed_time = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"IMAGE RETRIEVAL STATISTICS")
    logger.info(f"{'='*60}")
    logger.info(f"Inference path used: {stats['inference_used']} players")
    logger.info(f"Pure search path used: {stats['pure_search_used']} players")
    logger.info(f"  - Pure search successes: {stats['pure_search_success']}")
    logger.info(f"  - Pure search failures: {stats['pure_search_failed']}")
    logger.info(f"{'='*60}\n")
    logger.info("\n" + "="*60)
    logger.info("SEEDING COMPLETE!")
    logger.info("="*60)
    logger.info(f"Total players checked: {stats['total_checked']}")
    logger.info(f"Already in database: {stats['already_exists']}")
    logger.info(f"Skipped (cached from previous runs): {stats['skipped_cached']}")
    logger.info(f"Total time: {elapsed_time/3600:.2f} hours")
    logger.info("="*60)

    if stats['adp_missing_image'] > 0:
        logger.error("\n" + "="*60)
        logger.error("MANUAL INTERVENTION REQUIRED")
        logger.error("="*60)
        logger.error("The following ADP board players need images added manually:")
        logger.error("Check logs above for player names marked with 'ADP BOARD PLAYER MISSING IMAGE'")
        logger.error("="*60)

    # Cleanup browser resources
    logger.info("Closing ImageVerifier browser...")
    await image_verifier.close()

    logger.info("Closing BasketballReferenceSearcher browser...")
    await br_searcher.close()

    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed database with NBA players from scoring.csv and ADP board"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing players before seeding (fresh start)"
    )

    args = parser.parse_args()

    try:
        asyncio.run(seed_all_players(clear_database=args.clear))
    except KeyboardInterrupt:
        logger.info("\nSeeding interrupted by user. Progress has been saved.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
