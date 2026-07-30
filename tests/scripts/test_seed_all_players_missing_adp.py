"""Tests for missing ADP board players processing in seed_all_players.py.

These tests verify that the seeding script correctly processes ADP board players
that weren't in the scoring CSV file, ensuring 100% ADP board coverage.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import tempfile
import json
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestClearSeededPlayers:
    """Tests for clear_seeded_players function."""

    def test_clear_empty_database(self, tmp_path):
        """Test clearing an empty database returns 0."""
        from scripts.seed_all_players import clear_seeded_players
        from src.database.connection_manager import ConnectionManager

        db_path = tmp_path / "test.db"
        db = ConnectionManager(str(db_path))
        count = clear_seeded_players(db)
        db.close()

        assert count == 0

    def test_clear_database_with_players(self, tmp_path):
        """Test clearing database with players returns correct count."""
        from scripts.seed_all_players import clear_seeded_players
        from src.database.connection_manager import ConnectionManager

        db_path = tmp_path / "test.db"
        db = ConnectionManager(str(db_path))
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO players (name, rarity_tier, career_minutes) VALUES (?, ?, ?)",
            ("Test Player 1", "Common", 1000),
        )
        cursor.execute(
            "INSERT INTO players (name, rarity_tier, career_minutes) VALUES (?, ?, ?)",
            ("Test Player 2", "Rare", 2000),
        )
        conn.commit()

        count = clear_seeded_players(db)

        # Verify count
        assert count == 2

        # Verify database is empty
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        remaining = cursor.fetchone()[0]
        assert remaining == 0

        db.close()


class TestGetAllADPPlayers:
    """Tests for get_all_adp_players function."""

    def test_get_all_adp_players_both_sections(self, tmp_path):
        """Test getting all ADP players from verified and estimated sections."""
        from scripts.seed_all_players import get_all_adp_players

        # Create temporary ADP players file
        adp_file = tmp_path / "adp_players.json"
        with open(adp_file, 'w') as f:
            json.dump({
                "verified": {
                    "Michael Jordan": {
                        "player_id": "jordami01",
                        "adp": 1.5,
                        "url": "https://example.com/jordan"
                    },
                    "LeBron James": {
                        "player_id": "jamesle01",
                        "adp": 2.3,
                        "url": "https://example.com/lebron"
                    }
                },
                "estimated": {
                    "Stephen Curry": {
                        "player_id": "curryst01",
                        "adp": 5.7,
                        "url": "https://example.com/curry"
                    }
                }
            }, f)

        # Get all ADP players
        all_players = get_all_adp_players(str(adp_file))

        # Verify all players are returned
        assert len(all_players) == 3
        assert "Michael Jordan" in all_players
        assert "LeBron James" in all_players
        assert "Stephen Curry" in all_players
        assert all_players["Michael Jordan"]["adp"] == 1.5
        assert all_players["Stephen Curry"]["adp"] == 5.7

    def test_get_all_adp_players_empty_sections(self, tmp_path):
        """Test getting ADP players with empty sections."""
        from scripts.seed_all_players import get_all_adp_players

        # Create temporary ADP players file
        adp_file = tmp_path / "adp_players.json"
        with open(adp_file, 'w') as f:
            json.dump({
                "verified": {},
                "estimated": {}
            }, f)

        # Get all ADP players
        all_players = get_all_adp_players(str(adp_file))

        # Verify empty dict is returned
        assert len(all_players) == 0


class TestMissingADPPlayersProcessing:
    """Tests for missing ADP board players processing logic."""

    @pytest.mark.asyncio
    @patch('scripts.seed_all_players.BasketballReferenceClient')
    @patch('scripts.seed_all_players.ImageVerifier')
    @patch('scripts.seed_all_players.PlayerStatsCSVParser')
    async def test_missing_adp_players_added(
        self,
        mock_csv_parser,
        mock_verifier_class,
        mock_br_client,
        tmp_path
    ):
        """Test that ADP players not in CSV are added to database."""
        from scripts.seed_all_players import seed_all_players
        from src.scrapers.player_stats_csv_parser import PlayerStats

        # Create temporary database
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                adp_value REAL,
                rarity_tier TEXT NOT NULL,
                image_url TEXT,
                career_minutes INTEGER NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Create temporary ADP players file
        adp_file = tmp_path / "adp_players.json"
        with open(adp_file, 'w') as f:
            json.dump({
                "verified": {
                    "Player In CSV": {
                        "player_id": "playeri01",
                        "adp": 10.0,
                        "url": "https://example.com/player1"
                    },
                    "Player NOT In CSV": {
                        "player_id": "playern01",
                        "adp": 20.0,
                        "url": "https://example.com/player2"
                    }
                },
                "estimated": {}
            }, f)

        # Create temporary ADP CSV
        adp_csv = tmp_path / "adp.csv"
        with open(adp_csv, 'w') as f:
            f.write("PLAYER NAME,ADP\n")
            f.write("Player In CSV,10.0\n")
            f.write("Player NOT In CSV,20.0\n")

        # Create temporary skip list
        skip_list = tmp_path / "skip_list.json"
        with open(skip_list, 'w') as f:
            json.dump({
                'api_error': [],
                'below_threshold': [],
                'no_image': []
            }, f)

        # Mock CSV parser to return only one player (the one in CSV)
        mock_csv_parser_instance = MagicMock()
        mock_csv_parser_instance.parse_players.return_value = {
            "Player In CSV": PlayerStats(total_minutes=5000)
        }
        mock_csv_parser.return_value = mock_csv_parser_instance

        # Mock BasketballReferenceClient to return image URLs
        mock_br_instance = MagicMock()
        mock_br_instance.get_player_image_url.return_value = "https://example.com/image.jpg"
        mock_br_client.return_value = mock_br_instance

        # Mock ImageVerifier
        from unittest.mock import AsyncMock
        mock_verifier_instance = MagicMock()
        mock_verifier_instance.verify_image_url = AsyncMock(return_value=True)
        mock_verifier_instance.close = AsyncMock()
        mock_verifier_class.return_value = mock_verifier_instance

        # Mock settings
        with patch('scripts.seed_all_players.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                database_path=str(db_path),
                adp_players_path=str(adp_file),
                adp_csv_path=str(adp_csv)
            )

            with patch('scripts.seed_all_players.Path') as mock_path:
                mock_path.return_value = Path(skip_list)

                # Run seeding
                await seed_all_players()

        # Verify both players are in database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM players WHERE name = 'Player In CSV'")
        player1 = cursor.fetchone()
        assert player1 is not None, "Player In CSV should be in database"

        cursor.execute("SELECT name FROM players WHERE name = 'Player NOT In CSV'")
        player2 = cursor.fetchone()
        assert player2 is not None, "Player NOT In CSV should be added during missing ADP processing"

        cursor.execute("SELECT COUNT(*) FROM players")
        total = cursor.fetchone()[0]
        assert total == 2, "Should have exactly 2 players in database"

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
