"""Manager for leaderboard business logic."""
import math
from datetime import date
from typing import Dict, Any, List
from src.database.repositories.leaderboard_repository import LeaderboardRepository
from src.database.repositories.collection_repository import CollectionRepository


class LeaderboardManager:
    """Manages leaderboard business logic.

    Responsibilities:
    - Update snapshots for all users
    - Get formatted rankings
    - Calculate points from collections
    """

    def __init__(
        self,
        leaderboard_repository: LeaderboardRepository,
        collection_repository: CollectionRepository
    ):
        """Initialize manager with repositories.

        Args:
            leaderboard_repository: Leaderboard repository instance
            collection_repository: Collection repository instance
        """
        self.leaderboard_repo = leaderboard_repository
        self.collection_repo = collection_repository

    def update_snapshots_for_server(
        self,
        server_id: int,
        period: str,
        snapshot_date: date
    ) -> int:
        """Create/update snapshots for all users in a server.

        Args:
            server_id: Discord server ID
            period: Time period for snapshot
            snapshot_date: Date of snapshot

        Returns:
            Number of snapshots created
        """
        # Get all users with collections in this server
        users = self.collection_repo.get_all_server_users(server_id)

        count = 0
        for user_data in users:
            self.leaderboard_repo.create_snapshot(
                user_id=user_data["user_id"],
                server_id=server_id,
                period=period,
                points=user_data["total_points"],
                player_count=user_data["player_count"],
                snapshot_date=snapshot_date
            )
            count += 1

        return count

    def get_rankings(
        self,
        server_id: int,
        period: str,
        page: int = 0,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """Get formatted leaderboard rankings.

        Args:
            server_id: Discord server ID
            period: Time period to query
            page: Page number (0-indexed)
            page_size: Number of results per page

        Returns:
            Dictionary with rankings, period, and pagination info
        """
        # Get total count first (query without limit)
        all_rankings = self.leaderboard_repo.get_rankings(
            server_id=server_id,
            period=period,
            limit=1000  # Get all for count
        )
        total_count = len(all_rankings)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        # Get paginated results
        offset = page * page_size
        rankings = self.leaderboard_repo.get_rankings(
            server_id=server_id,
            period=period,
            limit=page_size,
            offset=offset
        )

        return {
            "rankings": rankings,
            "period": period,
            "current_page": page,
            "total_pages": total_pages
        }
