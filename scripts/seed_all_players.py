"""Seed database with all NBA players who have >1000 career minutes.

This script fetches all NBA players from nba_api, filters for those with
>1000 career minutes, verifies they have valid images, and adds them to
the database as Common rarity. Skips players already in the database
(preserves ADP board data).

Run from project root: python scripts/seed_all_players.py
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import time
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MIN_CAREER_MINUTES = 1000
BATCH_COMMIT_SIZE = 100
RATE_LIMIT_PER_MINUTE = 20
RATE_LIMIT_DELAY = 60 / RATE_LIMIT_PER_MINUTE  # seconds between requests


def verify_image_exists(image_url: str) -> bool:
    """Verify that a player image exists and is not a generic silhouette.

    Args:
        image_url: URL to player image

    Returns:
        True if image exists and is a real player photo, False otherwise
    """
    try:
        # Use HEAD request first (faster, doesn't download image)
        response = requests.head(image_url, timeout=5, allow_redirects=True)

        # Check if image exists (200 OK)
        if response.status_code != 200:
            return False

        # Check Content-Type is an image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return False

        # Check Content-Length to exclude generic silhouette
        # Generic silhouette: ~12 KB
        # Real player images: ~180-210 KB
        # Threshold: 50 KB (safely distinguishes real photos from placeholder)
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) < 50000:  # Less than 50KB = generic silhouette
            return False

        return True

    except Exception as e:
        logger.debug(f"Image verification failed for {image_url}: {e}")
        return False


def get_player_career_minutes(player_id: int) -> Optional[int]:
    """Fetch total career minutes for a player from NBA API.

    Args:
        player_id: NBA player ID

    Returns:
        Total career minutes or None if error/no data
    """
    try:
        # Fetch career stats
        career = playercareerstats.PlayerCareerStats(player_id=str(player_id))

        # Get career totals (regular season)
        data_frames = career.get_data_frames()

        if not data_frames or len(data_frames) == 0:
            return None

        # First DataFrame contains career totals
        career_totals = data_frames[0]

        # Check if MIN column exists and has data
        if 'MIN' in career_totals.columns and len(career_totals) > 0:
            # Sum all minutes across all seasons (career totals)
            total_minutes = career_totals['MIN'].sum()
            return int(total_minutes) if total_minutes else None

        return None

    except Exception as e:
        logger.error(f"Error fetching stats for player {player_id}: {e}")
        return None


def seed_all_players():
    """Main function to seed database with all NBA players >1000 minutes."""
    logger.info("Starting player seeding process...")

    # Get settings
    settings = get_settings()

    # Initialize database
    db = ConnectionManager(settings.database_path)
    repo = PlayerRepository(db)

    # Get all NBA players from static data (no API call)
    logger.info("Fetching all NBA players from nba_api...")
    all_players = players.get_players()
    logger.info(f"Found {len(all_players)} total NBA players")

    # Track statistics
    stats = {
        'total_checked': 0,
        'already_exists': 0,
        'below_threshold': 0,
        'no_image': 0,
        'api_errors': 0,
        'added': 0
    }

    start_time = time.time()
    last_commit = 0

    for idx, player in enumerate(all_players, 1):
        player_name = player['full_name']
        player_id = player['id']

        stats['total_checked'] += 1

        # Check if player already exists in database
        existing = repo.get_player_by_name(player_name)
        if existing:
            stats['already_exists'] += 1
            logger.debug(f"Skipping {player_name} (already in database)")
            continue

        # Fetch career minutes (with rate limiting)
        logger.info(f"[{idx}/{len(all_players)}] Fetching stats for {player_name}...")
        career_minutes = get_player_career_minutes(player_id)

        # Rate limiting delay
        time.sleep(RATE_LIMIT_DELAY)

        if career_minutes is None:
            stats['api_errors'] += 1
            logger.warning(f"Could not fetch stats for {player_name}, skipping")
            continue

        # Check minimum threshold
        if career_minutes < MIN_CAREER_MINUTES:
            stats['below_threshold'] += 1
            logger.debug(f"Skipping {player_name} ({career_minutes} minutes < {MIN_CAREER_MINUTES})")
            continue

        # Verify player has a valid image
        image_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
        if not verify_image_exists(image_url):
            stats['no_image'] += 1
            logger.debug(f"Skipping {player_name} (no valid image)")
            continue

        # Add player to database as Common rarity
        try:

            repo.create_player(
                name=player_name,
                adp_value=None,  # Not on ADP board
                rarity_tier="Common",
                image_url=image_url,
                career_minutes=career_minutes
            )
            stats['added'] += 1
            logger.info(f"✓ Added {player_name} ({career_minutes:,} minutes)")

        except Exception as e:
            logger.error(f"Error adding {player_name} to database: {e}")
            stats['api_errors'] += 1
            continue

        # Batch commit every 100 players
        if stats['added'] - last_commit >= BATCH_COMMIT_SIZE:
            db.get_connection().commit()
            last_commit = stats['added']

            # Calculate progress
            elapsed = time.time() - start_time
            rate = stats['total_checked'] / elapsed if elapsed > 0 else 0
            remaining = len(all_players) - stats['total_checked']
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_hours = eta_seconds / 3600

            logger.info(f"Progress: {stats['added']} added, {stats['total_checked']}/{len(all_players)} checked")
            logger.info(f"ETA: {eta_hours:.1f} hours remaining")

    # Final commit
    db.get_connection().commit()

    # Print final statistics
    elapsed_time = time.time() - start_time
    logger.info("\n" + "="*60)
    logger.info("SEEDING COMPLETE!")
    logger.info("="*60)
    logger.info(f"Total players checked: {stats['total_checked']}")
    logger.info(f"Already in database: {stats['already_exists']}")
    logger.info(f"Below {MIN_CAREER_MINUTES} min threshold: {stats['below_threshold']}")
    logger.info(f"No valid image: {stats['no_image']}")
    logger.info(f"API errors: {stats['api_errors']}")
    logger.info(f"Successfully added: {stats['added']}")
    logger.info(f"Total time: {elapsed_time/3600:.2f} hours")
    logger.info("="*60)

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
