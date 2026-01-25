"""Check player image URLs using nodriver image verification.

This script verifies Basketball Reference image URLs for all players in player_ids.json.
It identifies players with:
1. Missing images on Basketball Reference (404s)
2. Potentially incorrect player_id mappings
3. Valid images (for verification)

Usage:
    poetry run python scripts/check_player_images.py

Output:
    - Console output with progress and summary
    - results/image_check_results.json with detailed findings
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.image_verifier import ImageVerifier


# Basketball Reference image URL template
IMAGE_URL_TEMPLATE = "https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg"


class PlayerImageChecker:
    """Checks player image URLs for validity and proper mapping."""

    def __init__(self, player_ids_path: str, rate_limit_delay: float = 2.5):
        """Initialize checker with player IDs file path.

        Args:
            player_ids_path: Path to player_ids.json
            rate_limit_delay: Delay between image verification requests
        """
        self.player_ids_path = player_ids_path
        self.rate_limit_delay = rate_limit_delay
        self.logger = logging.getLogger(__name__)

        # Results tracking
        self.valid_images: List[Dict[str, Any]] = []
        self.missing_images: List[Dict[str, Any]] = []
        self.verification_errors: List[Dict[str, Any]] = []

    def load_player_ids(self) -> Dict[str, Any]:
        """Load player IDs from JSON file.

        Returns:
            Dict containing verified player data
        """
        with open(self.player_ids_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('verified', {}) | data.get('estimated', {})

    async def check_all_players(self) -> Dict[str, Any]:
        """Check image URLs for all players in player_ids.json.

        Returns:
            Dict containing categorized results and summary statistics
        """
        players = self.load_player_ids()
        total_players = len(players)

        self.logger.info(f"Starting image verification for {total_players} players...")
        print(f"\n{'='*70}")
        print(f"Basketball Reference Image URL Verification")
        print(f"{'='*70}")
        print(f"Total players to check: {total_players}")
        print(f"Rate limit delay: {self.rate_limit_delay}s per request")
        print(f"Estimated time: {(total_players * self.rate_limit_delay / 60):.1f} minutes\n")

        verifier = ImageVerifier(rate_limit_delay=self.rate_limit_delay)

        try:
            count = 0
            for player_name, player_data in players.items():
                count += 1
                player_id = player_data.get('player_id')
                adp = player_data.get('adp')

                if not player_id:
                    self.logger.warning(f"No player_id for {player_name}")
                    self.verification_errors.append({
                        'name': player_name,
                        'error': 'Missing player_id in data',
                        'adp': adp
                    })
                    continue

                # Construct image URL
                image_url = IMAGE_URL_TEMPLATE.format(player_id=player_id)

                # Log progress
                if count % 10 == 0:
                    print(f"Progress: {count}/{total_players} ({(count/total_players*100):.1f}%)")

                # Verify image URL
                try:
                    is_valid = await verifier.verify_image_url(image_url)

                    result_data = {
                        'name': player_name,
                        'player_id': player_id,
                        'image_url': image_url,
                        'adp': adp
                    }

                    if is_valid:
                        self.valid_images.append(result_data)
                        self.logger.debug(f"✓ {player_name} ({player_id}): Image exists")
                    else:
                        self.missing_images.append(result_data)
                        self.logger.warning(f"✗ {player_name} ({player_id}): Image NOT found (404)")
                        print(f"  ⚠️  Missing image: {player_name} (player_id: {player_id})")

                except Exception as e:
                    self.verification_errors.append({
                        'name': player_name,
                        'player_id': player_id,
                        'error': str(e),
                        'adp': adp
                    })
                    self.logger.error(f"Error verifying {player_name}: {e}")

        finally:
            await verifier.close()

        # Compile results
        results = {
            'summary': {
                'total_checked': total_players,
                'valid_images': len(self.valid_images),
                'missing_images': len(self.missing_images),
                'verification_errors': len(self.verification_errors),
                'check_date': datetime.now().isoformat()
            },
            'valid_images': self.valid_images,
            'missing_images': self.missing_images,
            'verification_errors': self.verification_errors
        }

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print summary of verification results.

        Args:
            results: Results dict from check_all_players()
        """
        summary = results['summary']

        print(f"\n{'='*70}")
        print(f"VERIFICATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total players checked: {summary['total_checked']}")
        print(f"Valid images: {summary['valid_images']} ({summary['valid_images']/summary['total_checked']*100:.1f}%)")
        print(f"Missing images: {summary['missing_images']} ({summary['missing_images']/summary['total_checked']*100:.1f}%)")
        print(f"Verification errors: {summary['verification_errors']}")

        if self.missing_images:
            print(f"\n{'='*70}")
            print(f"PLAYERS WITH MISSING IMAGES ({len(self.missing_images)})")
            print(f"{'='*70}")

            # Sort by ADP (most important players first)
            sorted_missing = sorted(self.missing_images, key=lambda x: x.get('adp', 999999))

            for player in sorted_missing[:50]:  # Show first 50
                adp_str = f"ADP: {player.get('adp', 'N/A')}" if player.get('adp') else "No ADP"
                print(f"  - {player['name']} (player_id: {player['player_id']}) [{adp_str}]")

            if len(self.missing_images) > 50:
                print(f"  ... and {len(self.missing_images) - 50} more")

        if self.verification_errors:
            print(f"\n{'='*70}")
            print(f"VERIFICATION ERRORS ({len(self.verification_errors)})")
            print(f"{'='*70}")
            for error in self.verification_errors[:20]:  # Show first 20
                print(f"  - {error['name']}: {error.get('error', 'Unknown error')}")

            if len(self.verification_errors) > 20:
                print(f"  ... and {len(self.verification_errors) - 20} more")

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save detailed results to JSON file.

        Args:
            results: Results dict from check_all_players()
            output_path: Path to save results JSON
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Detailed results saved to {output_path}")
        print(f"\n✓ Detailed results saved to: {output_path}")


async def main():
    """Main entry point for image verification script."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Paths
    project_root = Path(__file__).parent.parent
    player_ids_path = project_root / 'data' / 'player_ids.json'
    output_path = project_root / 'results' / 'image_check_results.json'

    # Check if player_ids.json exists
    if not player_ids_path.exists():
        print(f"Error: player_ids.json not found at {player_ids_path}")
        sys.exit(1)

    # Run verification
    checker = PlayerImageChecker(
        player_ids_path=str(player_ids_path),
        rate_limit_delay=2.5  # 2.5 seconds between requests
    )

    results = await checker.check_all_players()
    checker.print_summary(results)
    checker.save_results(results, str(output_path))

    print(f"\n{'='*70}")
    print("Verification complete!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    asyncio.run(main())
