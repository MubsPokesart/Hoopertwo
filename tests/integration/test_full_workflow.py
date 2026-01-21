"""Integration tests for complete user workflows."""
import pytest
from datetime import date


def test_full_player_collection_workflow(all_repositories, all_managers):
    """Test complete workflow: spawn -> recognize -> collect -> leaderboard."""

    repos = all_repositories
    managers = all_managers

    # Setup: Add test player to database
    player_data = {
        "name": "LeBron James",
        "adp_value": 1.5,
        "rarity_tier": "GOAT",
        "image_url": "https://example.com/lebron.jpg",
        "career_minutes": 50000
    }

    player_id = repos["player"].create_player(**player_data)
    assert player_id is not None

    # Step 1: User "catches" the player
    user_id = 123456789
    server_id = 987654321

    result = managers["collection"].catch_player(
        user_id=user_id,
        player_id=player_id,
        server_id=server_id
    )

    assert result["success"] is True
    assert result["already_owned"] is False

    # Step 2: Verify player in collection
    collection = managers["collection"].get_collection(
        user_id=user_id,
        server_id=server_id,
        page=0,
        page_size=10
    )

    assert len(collection["players"]) == 1
    assert collection["players"][0]["name"] == "LeBron James"
    assert collection["stats"]["total_players"] == 1
    assert collection["stats"]["total_points"] == 1000  # GOAT rarity

    # Step 3: Create leaderboard snapshot
    snapshot_date = date.today()
    count = managers["leaderboard"].update_snapshots_for_server(
        server_id=server_id,
        period="alltime",
        snapshot_date=snapshot_date
    )

    assert count == 1

    # Step 4: Verify user appears in leaderboard
    rankings = managers["leaderboard"].get_rankings(
        server_id=server_id,
        period="alltime",
        page=0,
        page_size=10
    )

    assert len(rankings["rankings"]) == 1
    assert rankings["rankings"][0]["user_id"] == user_id
    assert rankings["rankings"][0]["points"] == 1000
    assert rankings["rankings"][0]["rank"] == 1

    # Step 5: Try to catch same player again
    result2 = managers["collection"].catch_player(
        user_id=user_id,
        player_id=player_id,
        server_id=server_id
    )

    assert result2["success"] is True
    assert result2["already_owned"] is True  # Should indicate duplicate


def test_server_configuration_workflow(all_managers):
    """Test server configuration changes."""

    managers = all_managers
    server_id = 987654321

    # Step 1: Get initial config
    config = managers["config"].get_config(server_id)

    assert config["spawn_threshold"] == 500  # Default
    assert config["spawn_channels"] == []

    # Step 2: Update spawn threshold
    result = managers["config"].set_spawn_threshold(
        server_id=server_id,
        threshold=300
    )

    assert result["success"] is True

    # Step 3: Verify threshold updated
    config = managers["config"].get_config(server_id)
    assert config["spawn_threshold"] == 300

    # Step 4: Set spawn channels
    channel_ids = [111111, 222222, 333333]
    result = managers["config"].set_spawn_channels(
        server_id=server_id,
        channel_ids=channel_ids
    )

    assert result["success"] is True
    assert result["channel_count"] == 3

    # Step 5: Verify channels updated
    config = managers["config"].get_config(server_id)
    assert config["spawn_channels"] == channel_ids


def test_multi_user_leaderboard_workflow(all_repositories, all_managers):
    """Test leaderboard with multiple users."""

    repos = all_repositories
    managers = all_managers
    server_id = 987654321

    # Create test players
    players = [
        {"name": "LeBron James", "adp_value": 1.5, "rarity_tier": "GOAT"},
        {"name": "Michael Jordan", "adp_value": 1.0, "rarity_tier": "GOAT"},
        {"name": "Steph Curry", "adp_value": 15.5, "rarity_tier": "Mythic"}
    ]

    player_ids = []
    for player_data in players:
        pid = repos["player"].create_player(
            **player_data,
            image_url="https://example.com/test.jpg",
            career_minutes=10000
        )
        player_ids.append(pid)

    # User 1 catches 2 GOAT players (2000 points)
    user1 = 111111
    managers["collection"].catch_player(user1, player_ids[0], server_id)
    managers["collection"].catch_player(user1, player_ids[1], server_id)

    # User 2 catches 1 Mythic player (500 points)
    user2 = 222222
    managers["collection"].catch_player(user2, player_ids[2], server_id)

    # Create snapshots
    snapshot_date = date.today()
    managers["leaderboard"].update_snapshots_for_server(
        server_id=server_id,
        period="alltime",
        snapshot_date=snapshot_date
    )

    # Verify rankings
    rankings = managers["leaderboard"].get_rankings(
        server_id=server_id,
        period="alltime",
        page=0,
        page_size=10
    )

    assert len(rankings["rankings"]) == 2

    # User 1 should be rank 1 (more points)
    assert rankings["rankings"][0]["user_id"] == user1
    assert rankings["rankings"][0]["points"] == 2000
    assert rankings["rankings"][0]["rank"] == 1

    # User 2 should be rank 2
    assert rankings["rankings"][1]["user_id"] == user2
    assert rankings["rankings"][1]["points"] == 500
    assert rankings["rankings"][1]["rank"] == 2
