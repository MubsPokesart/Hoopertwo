"""Quick sample check of player image URLs using nodriver.

This script checks a sample of player images for quick testing/validation.
Useful for:
1. Testing the verification system
2. Quick checks after updates
3. Spot-checking high-priority players (low ADP)

Usage:
    poetry run python scripts/check_player_images_sample.py [--sample-size 20]

Output:
    - Console output with results
    - results/image_check_sample.json with findings
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.image_verifier import ImageVerifier


# Basketball Reference image URL template
IMAGE_URL_TEMPLATE = "https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg"


class PlayerImageSampleChecker:
    """Checks a sample of player image URLs for quick validation."""

    def __init__(self, player_ids_path: str, sample_size: int = 20, rate_limit_delay: float = 2.5):
        """Initialize checker with sample parameters.

        Args:
            player_ids_path: Path to player_ids.json
            sample_size: Number of players to check
            rate_limit_delay: Delay between image verification requests
        """
        self.player_ids_path = player_ids_path
        self.sample_size = sample_size
        self.rate_limit_delay = rate_limit_delay
        self.logger = logging.getLogger(__name__)

        # Results tracking
        self.results: List[Dict[str, Any]] = []

    def load_player_sample(self) -> List[Dict[str, Any]]:
        """Load a sample of players, prioritizing low ADP (important players).

        Returns:
            List of player dicts with name, player_id, adp
        """
        with open(self.player_ids_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        players = data.get('verified', {})

        # Convert to list and sort by ADP (low ADP = high priority)
        player_list = []
        for name, player_data in players.items():
            player_list.append({
                'name': name,
                'player_id': player_data.get('player_id'),
                'adp': player_data.get('adp', 999999)  # High default for players without ADP
            })

        # Sort by ADP (ascending)
        player_list.sort(key=lambda x: x['adp'])

        # Take top sample_size players
        sample = player_list[:self.sample_size]

        self.logger.info(f"Selected {len(sample)} players (prioritized by ADP)")
        return sample

    async def check_sample(self) -> Dict[str, Any]:
        """Check image URLs for sampled players.

        Returns:
            Dict containing results and summary
        """
        players = self.load_player_sample()
        total_players = len(players)

        print(f"\n{'='*70}")
        print(f"Basketball Reference Image URL Sample Check")
        print(f"{'='*70}")
        print(f"Sample size: {total_players} players")
        print(f"Priority: Top {total_players} by ADP (most important players)")
        print(f"Rate limit: {self.rate_limit_delay}s per request")
        print(f"Estimated time: {(total_players * self.rate_limit_delay):.0f} seconds\n")

        verifier = ImageVerifier(rate_limit_delay=self.rate_limit_delay)

        valid_count = 0
        missing_count = 0
        error_count = 0

        try:
            for idx, player in enumerate(players, 1):
                player_name = player['name']
                player_id = player['player_id']
                adp = player['adp']

                if not player_id:
                    self.logger.warning(f"No player_id for {player_name}")
                    error_count += 1
                    continue

                # Construct image URL
                image_url = IMAGE_URL_TEMPLATE.format(player_id=player_id)

                print(f"[{idx}/{total_players}] Checking: {player_name} (ADP: {adp if adp != 999999 else 'N/A'})...", end=' ')

                # Verify image URL
                try:
                    is_valid = await verifier.verify_image_url(image_url)

                    result = {
                        'name': player_name,
                        'player_id': player_id,
                        'image_url': image_url,
                        'adp': adp if adp != 999999 else None,
                        'status': 'valid' if is_valid else 'missing',
                        'checked_at': datetime.now().isoformat()
                    }

                    self.results.append(result)

                    if is_valid:
                        valid_count += 1
                        print("✓ Image exists")
                    else:
                        missing_count += 1
                        print("✗ Image NOT found (404)")

                except Exception as e:
                    error_count += 1
                    self.results.append({
                        'name': player_name,
                        'player_id': player_id,
                        'status': 'error',
                        'error': str(e),
                        'adp': adp if adp != 999999 else None
                    })
                    print(f"ERROR: {e}")

        finally:
            await verifier.close()

        # Compile summary
        summary = {
            'total_checked': total_players,
            'valid_images': valid_count,
            'missing_images': missing_count,
            'errors': error_count,
            'check_date': datetime.now().isoformat()
        }

        return {
            'summary': summary,
            'results': self.results
        }

    def print_summary(self, data: Dict[str, Any]):
        """Print summary of sample check.

        Args:
            data: Results dict from check_sample()
        """
        summary = data['summary']

        print(f"\n{'='*70}")
        print(f"SAMPLE CHECK SUMMARY")
        print(f"{'='*70}")
        print(f"Total checked: {summary['total_checked']}")
        print(f"Valid images: {summary['valid_images']} ({summary['valid_images']/summary['total_checked']*100:.1f}%)")
        print(f"Missing images: {summary['missing_images']} ({summary['missing_images']/summary['total_checked']*100:.1f}%)")
        print(f"Errors: {summary['errors']}")

        # Show missing images
        missing = [r for r in data['results'] if r.get('status') == 'missing']
        if missing:
            print(f"\nMissing images:")
            for result in missing:
                adp_str = f"ADP: {result.get('adp')}" if result.get('adp') else "No ADP"
                print(f"  - {result['name']} (player_id: {result['player_id']}) [{adp_str}]")

    def save_results(self, data: Dict[str, Any], output_path: str):
        """Save sample results to JSON file.

        Args:
            data: Results dict from check_sample()
            output_path: Path to save results JSON
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Results saved to: {output_path}")


async def main():
    """Main entry point for sample check script."""
    parser = argparse.ArgumentParser(description='Quick sample check of player image URLs')
    parser.add_argument(
        '--sample-size',
        type=int,
        default=20,
        help='Number of players to check (default: 20)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=2.5,
        help='Seconds between requests (default: 2.5)'
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Paths
    project_root = Path(__file__).parent.parent
    player_ids_path = project_root / 'data' / 'player_ids.json'
    output_path = project_root / 'results' / 'image_check_sample.json'

    # Check if player_ids.json exists
    if not player_ids_path.exists():
        print(f"Error: player_ids.json not found at {player_ids_path}")
        sys.exit(1)

    # Run sample check
    checker = PlayerImageSampleChecker(
        player_ids_path=str(player_ids_path),
        sample_size=args.sample_size,
        rate_limit_delay=args.rate_limit
    )

    results = await checker.check_sample()
    checker.print_summary(results)
    checker.save_results(results, str(output_path))

    print(f"\n{'='*70}")
    print("Sample check complete!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    asyncio.run(main())
