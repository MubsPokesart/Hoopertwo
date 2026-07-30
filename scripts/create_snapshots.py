"""One-time script to create leaderboard snapshots for existing collections."""
from datetime import datetime, timezone
from src.database.connection_manager import get_connection_manager
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.repositories.collection_repository import CollectionRepository
from src.managers.leaderboard_manager import LeaderboardManager


def create_snapshots_for_server(server_id: int):
    """Create snapshots for all users in a server.

    Args:
        server_id: Your Discord server ID
    """
    print(f"Creating snapshots for server {server_id}...")

    # Connect to database
    db = get_connection_manager("data/hooper_two.db")
    conn = db.get_connection()

    # Initialize repos and manager
    leaderboard_repo = LeaderboardRepository(conn)
    collection_repo = CollectionRepository(conn)
    manager = LeaderboardManager(leaderboard_repo, collection_repo)

    snapshot_at = datetime.now(timezone.utc)
    counts = manager.refresh_snapshots_for_server(
        server_id=server_id,
        snapshot_at=snapshot_at,
    )
    for period, count in counts.items():
        print(f"✅ Created {count} {period} snapshots")

    print("\n🎉 Done! Now try /leaderboard and /rank in Discord")

    # Close connection
    db.close()


if __name__ == "__main__":
    # TODO: Replace with your actual Discord server ID
    # To get your server ID:
    # 1. Enable Developer Mode in Discord (Settings > Advanced > Developer Mode)
    # 2. Right-click your server icon
    # 3. Click "Copy Server ID"

    SERVER_ID = 1234567890  # <-- REPLACE THIS WITH YOUR SERVER ID

    if SERVER_ID == 1234567890:
        print(
            "❌ ERROR: Please edit this file and replace SERVER_ID with your actual Discord server ID!"
        )
        print("\nHow to get your server ID:")
        print("1. Enable Developer Mode in Discord (Settings > Advanced > Developer Mode)")
        print("2. Right-click your server icon")
        print("3. Click 'Copy Server ID'")
        print("4. Replace '1234567890' in this file with your server ID")
    else:
        create_snapshots_for_server(SERVER_ID)
