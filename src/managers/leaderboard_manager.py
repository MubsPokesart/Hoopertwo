"""Manager for leaderboard business logic."""
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.database.repositories.collection_repository import CollectionRepository
from src.database.repositories.leaderboard_repository import LeaderboardRepository


class LeaderboardManager:
    """Manages leaderboard calculations, publication, and pagination."""

    PERIOD_DURATIONS: Dict[str, Optional[timedelta]] = {
        "weekly": timedelta(days=7),
        "monthly": timedelta(days=30),
        "yearly": timedelta(days=365),
        "alltime": None,
    }

    def __init__(
        self,
        leaderboard_repository: LeaderboardRepository,
        collection_repository: CollectionRepository,
    ):
        """Initialize manager with repositories."""
        self.leaderboard_repo = leaderboard_repository
        self.collection_repo = collection_repository

    def refresh_snapshots_for_server(
        self,
        server_id: int,
        snapshot_at: datetime,
    ) -> Dict[str, int]:
        """Calculate and atomically publish every period for one server."""
        if snapshot_at.tzinfo is None or snapshot_at.utcoffset() is None:
            raise ValueError("Snapshot boundary must be timezone-aware")

        snapshot_at = snapshot_at.astimezone(timezone.utc)
        period_rankings = {
            period: self._get_period_rankings(server_id, snapshot_at, duration)
            for period, duration in self.PERIOD_DURATIONS.items()
        }
        return self.leaderboard_repo.replace_server_snapshots(
            server_id=server_id,
            snapshot_date=snapshot_at.date(),
            period_rankings=period_rankings,
        )

    def _get_period_rankings(
        self,
        server_id: int,
        snapshot_at: datetime,
        duration: Optional[timedelta],
    ) -> List[Dict[str, Any]]:
        """Calculate one period at the refresh's shared UTC boundary."""
        caught_after = snapshot_at - duration if duration is not None else None
        return self.collection_repo.get_all_server_users(
            server_id=server_id,
            caught_after=caught_after,
            caught_before=snapshot_at,
        )

    def get_rankings(
        self,
        server_id: int,
        period: str,
        page: int = 0,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Get formatted and paginated leaderboard rankings."""
        if period not in self.PERIOD_DURATIONS:
            raise ValueError(f"Unsupported leaderboard period: {period}")

        all_rankings = self.leaderboard_repo.get_rankings(
            server_id=server_id,
            period=period,
            limit=1000,
        )
        total_count = len(all_rankings)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        rankings = self.leaderboard_repo.get_rankings(
            server_id=server_id,
            period=period,
            limit=page_size,
            offset=page * page_size,
        )

        return {
            "rankings": rankings,
            "period": period,
            "current_page": page,
            "total_pages": total_pages,
        }
