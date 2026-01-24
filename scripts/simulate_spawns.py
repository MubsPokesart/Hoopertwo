#!/usr/bin/env python3
"""Simulation script for spawn_manager.py spawn distribution.

Runs 2000 simulations of player spawning and displays the distribution
of each rarity tier to verify the weighted spawn system.
"""
import sys
from collections import Counter
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection_manager import ConnectionManager
from src.database.repositories.player_repository import PlayerRepository
from src.managers.spawn_manager import SpawnManager


def run_spawn_simulation(num_simulations: int = 2000) -> dict[str, int]:
    """Run spawn simulations and count rarity distribution.

    Args:
        num_simulations: Number of spawns to simulate

    Returns:
        Dictionary mapping rarity tier to spawn count
    """
    # Initialize components
    conn_manager = ConnectionManager("data/hooper_two.db")
    player_repo = PlayerRepository(conn_manager)
    spawn_manager = SpawnManager(player_repo)

    # Check if we have players
    all_players = player_repo.get_all_players()
    if not all_players:
        print("Error: No players in database. Run seeder first.")
        sys.exit(1)

    # Count players by tier
    tier_counts = Counter(player["rarity_tier"] for player in all_players)

    print(f"Database contains {len(all_players)} players:")
    for tier in ["GOAT", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]:
        count = tier_counts.get(tier, 0)
        print(f"  {tier}: {count} players")
    print()

    # Run simulations
    print(f"Running {num_simulations} spawn simulations...")
    spawn_counts = Counter()

    for i in range(num_simulations):
        if (i + 1) % 500 == 0:
            print(f"  Completed {i + 1}/{num_simulations} simulations...")

        try:
            player = spawn_manager.select_random_player()
            spawn_counts[player["rarity_tier"]] += 1
        except Exception as e:
            print(f"Error during simulation {i + 1}: {e}")
            break

    return spawn_counts


def display_results(spawn_counts: dict[str, int], total_spawns: int):
    """Display spawn simulation results with statistics.

    Args:
        spawn_counts: Dictionary mapping rarity tier to spawn count
        total_spawns: Total number of spawns simulated
    """
    print("\n" + "="*70)
    print(f"SPAWN SIMULATION RESULTS ({total_spawns} simulations)")
    print("="*70)

    # Display in rarity order
    tier_order = ["GOAT", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]
    weights = SpawnManager.RARITY_WEIGHTS

    print(f"\n{'Rarity':<12} {'Weight':<8} {'Spawns':<8} {'Percentage':<12} {'Bar'}")
    print("-"*70)

    for tier in tier_order:
        count = spawn_counts.get(tier, 0)
        percentage = (count / total_spawns * 100) if total_spawns > 0 else 0
        weight = weights.get(tier, 0)
        bar = "#" * int(percentage / 2)  # Scale bar to fit screen

        print(f"{tier:<12} {weight:<8} {count:<8} {percentage:>6.2f}%      {bar}")

    print("-"*70)
    print(f"{'TOTAL':<12} {'':<8} {total_spawns:<8} {'100.00%':<12}")
    print()

    # Calculate expected probabilities based on weights
    total_weight = sum(weights.values())
    print("\nExpected vs Actual Spawn Rates:")
    print("-"*70)
    print(f"{'Rarity':<12} {'Expected %':<12} {'Actual %':<12} {'Difference'}")
    print("-"*70)

    for tier in tier_order:
        weight = weights.get(tier, 0)
        expected_pct = (weight / total_weight * 100)
        actual_pct = (spawn_counts.get(tier, 0) / total_spawns * 100) if total_spawns > 0 else 0
        diff = actual_pct - expected_pct
        sign = "+" if diff > 0 else ""

        print(f"{tier:<12} {expected_pct:>6.2f}%       {actual_pct:>6.2f}%       {sign}{diff:>6.2f}%")

    print("="*70)


def main():
    """Main entry point for simulation script."""
    print("HooperTwo Spawn Distribution Simulator")
    print("="*70)
    print()

    # Run simulation
    num_sims = 2000
    spawn_counts = run_spawn_simulation(num_sims)

    # Display results
    display_results(spawn_counts, num_sims)

    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
