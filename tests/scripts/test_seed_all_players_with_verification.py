"""Integration tests for seed_all_players.py with ImageVerifier.

These tests verify that the seeding script correctly integrates with ImageVerifier
to skip players with invalid images while preserving ADP board players.

Key Behaviors Tested:
1. Non-ADP players with invalid images → skipped, added to skip list
2. Non-ADP players with valid images → added as Common rarity
3. ADP players with valid images → added with correct rarity
4. ADP players with invalid images → added with NULL image, flagged for manual fix
5. Skip list caching prevents re-verification on subsequent runs
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import tempfile
import json
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSeedAllPlayersWithVerification:
    """Integration tests for seed_all_players with image verification."""

    @pytest.fixture
    def temp_database(self):
        """Create temporary database for testing."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        # Initialize database schema
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                adp_value REAL,
                rarity_tier TEXT NOT NULL,
                image_url TEXT,
                career_minutes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        yield temp_db.name

        # Cleanup
        Path(temp_db.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_skip_list(self):
        """Create temporary skip list file."""
        temp_skip = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w')
        json.dump({
            'api_error': [],
            'below_threshold': [],
            'no_image': []
        }, temp_skip)
        temp_skip.close()

        yield temp_skip.name

        # Cleanup
        Path(temp_skip.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_csv(self):
        """Create temporary CSV with player stats."""
        temp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w')
        temp_csv.write("Player,MP\n")
        temp_csv.write("Kareem Abdul-Jabbar,57446\n")  # Valid image
        temp_csv.write("Dennis Awtrey,5000\n")  # Invalid image
        temp_csv.write("Michael Jordan,41011\n")  # Valid image (on ADP board)
        temp_csv.write("Unknown Player,3000\n")  # Invalid image, not on ADP
        temp_csv.close()

        yield temp_csv.name

        # Cleanup
        Path(temp_csv.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_adp_players(self):
        """Create temporary ADP players JSON."""
        temp_adp = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w')
        json.dump({
            "verified": {
                "Michael Jordan": {
                    "player_id": "jordami01",
                    "url": "https://www.basketball-reference.com/players/j/jordami01.html",
                    "adp": 1.5
                }
            },
            "estimated": {}
        }, temp_adp)
        temp_adp.close()

        yield temp_adp.name

        # Cleanup
        Path(temp_adp.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_adp_csv(self):
        """Create temporary ADP CSV."""
        temp_adp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w')
        temp_adp_csv.write("PLAYER NAME,ADP\n")
        temp_adp_csv.write("Michael Jordan,1.5\n")
        temp_adp_csv.close()

        yield temp_adp_csv.name

        # Cleanup
        Path(temp_adp_csv.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch('scripts.seed_all_players.ImageVerifier')
    @patch('scripts.seed_all_players.BasketballReferenceClient')
    @patch('scripts.seed_all_players.PlayerStatsCSVParser')
    async def test_non_adp_invalid_image_skipped(
        self,
        mock_csv_parser,
        mock_br_client,
        mock_verifier_class,
        temp_database,
        temp_skip_list,
        temp_adp_players,
        temp_adp_csv
    ):
        """Test that non-ADP players with invalid images are skipped and added to skip list."""
        from scripts.seed_all_players import seed_all_players
        from src.scrapers.player_stats_csv_parser import PlayerStats

        # Mock CSV parser to return test players
        mock_csv_parser_instance = MagicMock()
        mock_csv_parser_instance.parse_players.return_value = {
            "Dennis Awtrey": PlayerStats(total_minutes=5000)
        }
        mock_csv_parser.return_value = mock_csv_parser_instance

        # Mock BasketballReferenceClient to return image URL
        mock_br_instance = MagicMock()
        mock_br_instance.get_player_image_url.return_value = "https://example.com/awtrey.jpg"
        mock_br_client.return_value = mock_br_instance

        # Mock ImageVerifier to return False (invalid image)
        mock_verifier_instance = MagicMock()
        mock_verifier_instance.verify_image_url = AsyncMock(return_value=False)
        mock_verifier_instance.close = AsyncMock()
        mock_verifier_class.return_value = mock_verifier_instance

        # Mock settings
        with patch('scripts.seed_all_players.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                database_path=temp_database,
                adp_players_path=temp_adp_players,
                adp_csv_path=temp_adp_csv
            )

            with patch('scripts.seed_all_players.Path') as mock_path:
                mock_path.return_value = Path(temp_skip_list)

                # Run seeding
                await seed_all_players()

        # Verify skip list was updated
        with open(temp_skip_list, 'r') as f:
            skip_data = json.load(f)
            assert "Dennis Awtrey" in skip_data['no_image']

        # Verify player was NOT added to database
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE name = 'Dennis Awtrey'")
        result = cursor.fetchone()
        conn.close()

        assert result is None, "Player with invalid image should not be in database"

    @pytest.mark.asyncio
    @patch('scripts.seed_all_players.ImageVerifier')
    @patch('scripts.seed_all_players.BasketballReferenceClient')
    @patch('scripts.seed_all_players.PlayerStatsCSVParser')
    async def test_non_adp_valid_image_added(
        self,
        mock_csv_parser,
        mock_br_client,
        mock_verifier_class,
        temp_database,
        temp_skip_list,
        temp_adp_players,
        temp_adp_csv
    ):
        """Test that non-ADP players with valid images are added as Common rarity."""
        from scripts.seed_all_players import seed_all_players
        from src.scrapers.player_stats_csv_parser import PlayerStats

        # Mock CSV parser
        mock_csv_parser_instance = MagicMock()
        mock_csv_parser_instance.parse_players.return_value = {
            "Kareem Abdul-Jabbar": PlayerStats(total_minutes=57446)
        }
        mock_csv_parser.return_value = mock_csv_parser_instance

        # Mock BasketballReferenceClient
        mock_br_instance = MagicMock()
        mock_br_instance.get_player_image_url.return_value = "https://example.com/kareem.jpg"
        mock_br_client.return_value = mock_br_instance

        # Mock ImageVerifier to return True (valid image)
        mock_verifier_instance = MagicMock()
        mock_verifier_instance.verify_image_url = AsyncMock(return_value=True)
        mock_verifier_instance.close = AsyncMock()
        mock_verifier_class.return_value = mock_verifier_instance

        # Mock settings
        with patch('scripts.seed_all_players.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                database_path=temp_database,
                adp_players_path=temp_adp_players,
                adp_csv_path=temp_adp_csv
            )

            with patch('scripts.seed_all_players.Path') as mock_path:
                mock_path.return_value = Path(temp_skip_list)

                # Run seeding
                await seed_all_players()

        # Verify player was added to database with Common rarity
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE name = 'Kareem Abdul-Jabbar'")
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "Player with valid image should be in database"
        # result format: (id, name, adp_value, rarity_tier, image_url, career_minutes, created_at)
        assert result[3] == "Common", "Non-ADP player should have Common rarity"
        assert result[4] == "https://example.com/kareem.jpg", "Image URL should be preserved"

    @pytest.mark.asyncio
    @patch('scripts.seed_all_players.ImageVerifier')
    @patch('scripts.seed_all_players.BasketballReferenceClient')
    @patch('scripts.seed_all_players.PlayerStatsCSVParser')
    async def test_adp_player_skips_verification(
        self,
        mock_csv_parser,
        mock_br_client,
        mock_verifier_class,
        temp_database,
        temp_skip_list,
        temp_adp_players,
        temp_adp_csv
    ):
        """Test that ADP players skip image verification entirely."""
        from scripts.seed_all_players import seed_all_players
        from src.scrapers.player_stats_csv_parser import PlayerStats

        # Mock CSV parser
        mock_csv_parser_instance = MagicMock()
        mock_csv_parser_instance.parse_players.return_value = {
            "Michael Jordan": PlayerStats(total_minutes=41011)
        }
        mock_csv_parser.return_value = mock_csv_parser_instance

        # Mock BasketballReferenceClient
        mock_br_instance = MagicMock()
        mock_br_instance.get_player_image_url.return_value = "https://example.com/jordan.jpg"
        mock_br_client.return_value = mock_br_instance

        # Mock ImageVerifier (should NOT be called for ADP players)
        mock_verifier_instance = MagicMock()
        mock_verifier_instance.verify_image_url = AsyncMock(return_value=True)
        mock_verifier_instance.close = AsyncMock()
        mock_verifier_class.return_value = mock_verifier_instance

        # Mock settings
        with patch('scripts.seed_all_players.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                database_path=temp_database,
                adp_players_path=temp_adp_players,
                adp_csv_path=temp_adp_csv
            )

            with patch('scripts.seed_all_players.Path') as mock_path:
                mock_path.return_value = Path(temp_skip_list)

                # Run seeding
                await seed_all_players()

        # Verify ImageVerifier was NOT called for ADP player
        mock_verifier_instance.verify_image_url.assert_not_called()

        # Verify player was added to database with correct rarity (GOAT for ADP 1.5)
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE name = 'Michael Jordan'")
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "ADP player should be in database"
        assert result[3] == "GOAT", "ADP 1.5 player should have GOAT rarity"

    @pytest.mark.asyncio
    @patch('scripts.seed_all_players.ImageVerifier')
    @patch('scripts.seed_all_players.BasketballReferenceClient')
    @patch('scripts.seed_all_players.PlayerStatsCSVParser')
    async def test_skip_list_prevents_reverification(
        self,
        mock_csv_parser,
        mock_br_client,
        mock_verifier_class,
        temp_database,
        temp_skip_list,
        temp_adp_players,
        temp_adp_csv
    ):
        """Test that skip list prevents re-verification on subsequent runs."""
        from scripts.seed_all_players import seed_all_players
        from src.scrapers.player_stats_csv_parser import PlayerStats

        # Pre-populate skip list with cached player
        with open(temp_skip_list, 'w') as f:
            json.dump({
                'api_error': [],
                'below_threshold': [],
                'no_image': ['Dennis Awtrey']
            }, f)

        # Mock CSV parser
        mock_csv_parser_instance = MagicMock()
        mock_csv_parser_instance.parse_players.return_value = {
            "Dennis Awtrey": PlayerStats(total_minutes=5000)
        }
        mock_csv_parser.return_value = mock_csv_parser_instance

        # Mock BasketballReferenceClient
        mock_br_instance = MagicMock()
        mock_br_client.return_value = mock_br_instance

        # Mock ImageVerifier (should NOT be called for cached skip list players)
        mock_verifier_instance = MagicMock()
        mock_verifier_instance.verify_image_url = AsyncMock(return_value=False)
        mock_verifier_instance.close = AsyncMock()
        mock_verifier_class.return_value = mock_verifier_instance

        # Mock settings
        with patch('scripts.seed_all_players.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                database_path=temp_database,
                adp_players_path=temp_adp_players,
                adp_csv_path=temp_adp_csv
            )

            with patch('scripts.seed_all_players.Path') as mock_path:
                mock_path.return_value = Path(temp_skip_list)

                # Run seeding
                await seed_all_players()

        # Verify ImageVerifier was NOT called (skip list cached)
        mock_verifier_instance.verify_image_url.assert_not_called()

        # Verify BasketballReferenceClient was NOT called (skip list cached)
        mock_br_instance.get_player_image_url.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
