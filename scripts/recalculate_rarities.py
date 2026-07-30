"""Recalculate rarity tiers for all players with ADP values.

This script updates the rarity_tier for all players in the database that have
an ADP value, using the current threshold values defined in PlayerManager.

Use this script when:
- Rarity thresholds have been updated in PlayerManager
- Database rarities need to be synchronized with current thresholds

Usage:
    python scripts/recalculate_rarities.py
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.managers.player_manager import PlayerManager
from src.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Recalculate and update rarity tiers for all players with ADP values."""
    logger.info("Starting rarity recalculation...")

    # Get settings
    settings = get_settings()

    # Initialize database
    db = ConnectionManager(settings.database_path)
    repo = PlayerRepository(db)

    # Initialize PlayerManager
    player_manager = PlayerManager(repo, settings.adp_csv_path)

    # Display current thresholds
    logger.info("\n" + "="*60)
    logger.info("CURRENT RARITY THRESHOLDS")
    logger.info("="*60)
    logger.info(f"GOAT:      ADP < {player_manager.GOAT_THRESHOLD}")
    logger.info(f"Cosmic:    ADP < {player_manager.COSMIC_THRESHOLD}")
    logger.info(f"Mythic:    ADP < {player_manager.MYTHIC_THRESHOLD}")
    logger.info(f"Legendary: ADP < {player_manager.LEGENDARY_THRESHOLD}")
    logger.info(f"Epic:      ADP < {player_manager.EPIC_THRESHOLD}")
    logger.info(f"Rare:      ADP < {player_manager.RARE_THRESHOLD}")
    logger.info(f"Uncommon:  ADP >= {player_manager.UNCOMMON_THRESHOLD}")
    logger.info("="*60 + "\n")

    # Get total count of players with ADP
    players_with_adp = repo.get_players_with_adp()
    total_players = len(players_with_adp)
    logger.info(f"Found {total_players} players with ADP values")

    if total_players == 0:
        logger.warning("No players with ADP values found. Nothing to recalculate.")
        db.close()
        return

    # Recalculate rarities
    logger.info("Recalculating rarities...")
    updated_count = player_manager.recalculate_all_rarities()

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("RECALCULATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total players with ADP: {total_players}")
    logger.info(f"Players updated: {updated_count}")
    logger.info(f"Players unchanged: {total_players - updated_count}")
    logger.info("="*60)

    if updated_count > 0:
        logger.info("\nRarity distribution after update:")
        logger.info("-" * 40)

        # Get count by rarity
        rarity_tiers = [
            "GOAT",
            "Cosmic",
            "Mythic",
            "Legendary",
            "Epic",
            "Rare",
            "Uncommon",
            "Common",
        ]
        for tier in rarity_tiers:
            players = repo.get_players_by_rarity(tier)
            adp_count = sum(1 for p in players if p["adp_value"] is not None)
            if adp_count > 0:
                logger.info(f"{tier:10s}: {adp_count:3d} players")

        logger.info("-" * 40)

    # Close database connection
    db.close()
    logger.info("\nDatabase connection closed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nRecalculation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
