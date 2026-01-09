"""
Helper script to build Basketball Reference player ID database.

This script helps identify correct player IDs by:
1. Generating estimated IDs for all ADP board players
2. Outputting URLs for manual verification
3. Creating a JSON database of verified IDs
"""

import json
from test_all_players import load_adp_players, generate_player_id, KNOWN_PLAYER_IDS


def generate_player_id_database():
    """Generate complete player ID database with estimates."""
    players = load_adp_players()

    database = {
        "verified": {},
        "estimated": {},
        "needs_verification": []
    }

    for player_name, adp in players:
        player_id = generate_player_id(player_name)

        if player_name in KNOWN_PLAYER_IDS:
            # Known verified ID
            database["verified"][player_name] = {
                "player_id": KNOWN_PLAYER_IDS[player_name],
                "adp": adp,
                "url": f"https://www.basketball-reference.com/players/{KNOWN_PLAYER_IDS[player_name][0]}/{KNOWN_PLAYER_IDS[player_name]}.html"
            }
        elif player_id:
            # Estimated ID (needs verification)
            database["estimated"][player_name] = {
                "player_id": player_id,
                "adp": adp,
                "url": f"https://www.basketball-reference.com/players/{player_id[0]}/{player_id}.html"
            }
        else:
            # Special case
            database["needs_verification"].append({
                "name": player_name,
                "adp": adp
            })

    return database


def print_verification_urls(tier="GOAT", max_count=20):
    """Print URLs for manual verification of high-priority players."""
    players = load_adp_players()

    tier_ranges = {
        "GOAT": (0, 2.0),
        "Mythic": (2.0, 32.0),
        "Legendary": (32.0, 64.0),
        "Epic": (64.0, 128.0),
        "Rare": (128.0, 256.0),
        "Common": (256.0, float('inf'))
    }

    min_adp, max_adp = tier_ranges.get(tier, (0, float('inf')))

    print(f"\n{'=' * 80}")
    print(f"VERIFICATION URLs - {tier} TIER (ADP {min_adp}-{max_adp})")
    print('=' * 80)

    count = 0
    for player_name, adp in players:
        if min_adp <= adp < max_adp and count < max_count:
            player_id = generate_player_id(player_name)
            status = "[VERIFIED]" if player_name in KNOWN_PLAYER_IDS else "[ESTIMATED]"
            url = f"https://www.basketball-reference.com/players/{player_id[0]}/{player_id}.html"

            print(f"\n{count + 1}. {player_name} (ADP: {adp:.2f})")
            print(f"   {status} ID: {player_id}")
            print(f"   URL: {url}")

            count += 1


def export_to_json(filename="player_ids.json"):
    """Export player ID database to JSON file."""
    database = generate_player_id_database()

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(database, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Exported player ID database to {filename}")
    print(f"     Verified IDs: {len(database['verified'])}")
    print(f"     Estimated IDs: {len(database['estimated'])}")
    print(f"     Needs verification: {len(database['needs_verification'])}")


def main():
    print("=" * 80)
    print("BASKETBALL REFERENCE PLAYER ID DATABASE BUILDER")
    print("=" * 80)

    # Generate full database
    database = generate_player_id_database()

    print("\nDATABASE STATISTICS:")
    print("-" * 80)
    print(f"Total players: {len(database['verified']) + len(database['estimated']) + len(database['needs_verification'])}")
    print(f"Verified IDs: {len(database['verified'])}")
    print(f"Estimated IDs (need verification): {len(database['estimated'])}")
    print(f"Special cases: {len(database['needs_verification'])}")

    # Print sample verified IDs
    print("\nSAMPLE VERIFIED IDs (Top 10):")
    print("-" * 80)
    for i, (name, data) in enumerate(list(database['verified'].items())[:10], 1):
        print(f"{i:2d}. {name:30s} {data['player_id']:15s} (ADP: {data['adp']:6.2f})")

    # Print sample estimated IDs that need verification
    print("\nSAMPLE ESTIMATED IDs (Top 10 by ADP - need verification):")
    print("-" * 80)
    estimated_sorted = sorted(database['estimated'].items(), key=lambda x: x[1]['adp'])
    for i, (name, data) in enumerate(estimated_sorted[:10], 1):
        print(f"{i:2d}. {name:30s} {data['player_id']:15s} (ADP: {data['adp']:6.2f})")
        print(f"    Verify: {data['url']}")

    # Export to JSON
    export_to_json()

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Review estimated IDs in player_ids.json")
    print("2. Manually verify URLs for high-priority players (low ADP)")
    print("3. Update KNOWN_PLAYER_IDS dict in test_all_players.py")
    print("4. Re-run test_all_players.py to improve coverage")
    print()


if __name__ == "__main__":
    main()
