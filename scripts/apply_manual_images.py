"""Apply manual image URLs to players in the database.

This script reads manual_images.json and updates the database with corrected image URLs
for players that have broken or missing images from Basketball Reference.

Usage:
    python scripts/apply_manual_images.py
    python scripts/apply_manual_images.py --dry-run  # Preview changes without applying
"""
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_manual_images(dry_run: bool = False):
    """Apply manual image URLs from manual_images.json to database.

    Args:
        dry_run: If True, only preview changes without applying them
    """
    logger.info("Starting manual image application process...")

    # Get settings
    settings = get_settings()

    # Initialize database
    db = ConnectionManager(settings.database_path)
    repo = PlayerRepository(db)

    # Load manual images
    manual_images_path = Path("data/manual_images.json")
    if not manual_images_path.exists():
        logger.error(f"Manual images file not found: {manual_images_path}")
        return

    with open(manual_images_path, 'r') as f:
        manual_images = json.load(f)

    logger.info(f"Loaded {len(manual_images)} manual image entries")

    # Track statistics
    stats = {
        'total': len(manual_images),
        'updated': 0,
        'not_found': 0,
        'already_correct': 0
    }

    # Preview or apply updates
    logger.info(f"\n{'='*60}")
    if dry_run:
        logger.info("DRY RUN - No changes will be made")
    else:
        logger.info("APPLYING MANUAL IMAGE UPDATES")
    logger.info(f"{'='*60}\n")

    for player_name, new_image_url in manual_images.items():
        # Check if player exists
        player = repo.get_player_by_name(player_name)

        if not player:
            stats['not_found'] += 1
            logger.warning(f"Player not found in database: {player_name}")
            continue

        current_url = player.get('image_url')

        # Check if update is needed
        if current_url == new_image_url:
            stats['already_correct'] += 1
            logger.info(f"✓ {player_name}: Already has correct URL")
            continue

        # Show the change
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Updating {player_name}:")
        logger.info(f"  FROM: {current_url}")
        logger.info(f"  TO:   {new_image_url}")

        # Apply update (if not dry run)
        if not dry_run:
            success = repo.update_player_image(player_name, new_image_url)
            if success:
                stats['updated'] += 1
                logger.info(f"  ✓ Updated successfully")
            else:
                logger.error(f"  ✗ Update failed")
        else:
            stats['updated'] += 1

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total manual images: {stats['total']}")
    logger.info(f"{'Would be updated' if dry_run else 'Updated'}: {stats['updated']}")
    logger.info(f"Already correct: {stats['already_correct']}")
    logger.info(f"Not found in database: {stats['not_found']}")
    logger.info(f"{'='*60}")

    if dry_run:
        logger.info("\nThis was a dry run. Re-run without --dry-run to apply changes.")

    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply manual image URLs to players in the database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )

    args = parser.parse_args()

    try:
        apply_manual_images(dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
