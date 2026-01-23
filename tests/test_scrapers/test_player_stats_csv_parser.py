"""Tests for CSV-based player stats parser."""
import pytest
import csv
from pathlib import Path
from src.scrapers.player_stats_csv_parser import PlayerStatsCSVParser, PlayerStats


@pytest.fixture
def temp_csv_single_player(tmp_path):
    """Create temporary CSV with single player, single season."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        writer.writerow(['LeBron James', '0.588', '27.1', '2316', 'CLE', '79', '2004', '2544'])

    return str(csv_path)


@pytest.fixture
def temp_csv_multiple_seasons(tmp_path):
    """Create temporary CSV with one player across multiple seasons."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        # LeBron across 3 seasons
        writer.writerow(['LeBron James', '0.588', '27.1', '2316', 'CLE', '79', '2004', '2544'])
        writer.writerow(['LeBron James', '0.568', '27.2', '2451', 'CLE', '80', '2005', '2544'])
        writer.writerow(['LeBron James', '0.552', '31.4', '3190', 'CLE', '79', '2006', '2544'])

    return str(csv_path)


@pytest.fixture
def temp_csv_with_below_threshold(tmp_path):
    """Create temporary CSV with players above and below threshold."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        # Above threshold (2500 minutes total)
        writer.writerow(['LeBron James', '0.588', '27.1', '2500', 'CLE', '79', '2004', '2544'])
        # Below threshold (500 minutes total)
        writer.writerow(['John Doe', '0.450', '5.2', '500', 'LAL', '20', '2010', '9999'])

    return str(csv_path)


@pytest.fixture
def temp_csv_multiple_players(tmp_path):
    """Create temporary CSV with multiple different players."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        # LeBron - multiple seasons
        writer.writerow(['LeBron James', '0.588', '27.1', '2000', 'CLE', '79', '2004', '2544'])
        writer.writerow(['LeBron James', '0.568', '27.2', '1500', 'CLE', '80', '2005', '2544'])
        # Kobe - single season
        writer.writerow(['Kobe Bryant', '0.559', '35.4', '3277', 'LAL', '80', '2006', '977'])
        # Low minutes player - should be filtered out
        writer.writerow(['Bench Player', '0.400', '2.1', '100', 'NYK', '10', '2010', '8888'])

    return str(csv_path)


@pytest.fixture
def temp_csv_missing_data(tmp_path):
    """Create temporary CSV with missing/invalid data."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        # Valid player
        writer.writerow(['LeBron James', '0.588', '27.1', '2500', 'CLE', '79', '2004', '2544'])
        # Empty MP
        writer.writerow(['Player With Empty MP', '0.450', '5.2', '', 'LAL', '20', '2010', '9999'])
        # Invalid nba_id (should handle gracefully)
        writer.writerow(['Player With Bad ID', '0.500', '10.0', '1500', 'BOS', '50', '2012', 'invalid'])

    return str(csv_path)


@pytest.fixture
def temp_csv_decimal_minutes(tmp_path):
    """Create temporary CSV with decimal format minutes (like real CSV)."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        # Real CSV has decimal format like '333.0'
        writer.writerow(['LeBron James', '0.588', '27.1', '2316.0', 'CLE', '79', '2004', '2544'])
        writer.writerow(['Kobe Bryant', '0.559', '35.4', '3277.5', 'LAL', '80', '2006', '977'])

    return str(csv_path)


def test_parse_single_player_single_season(temp_csv_single_player):
    """Test parsing a single player with one season."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_single_player,
        min_career_minutes=1000
    )

    players = parser.parse_players()

    assert len(players) == 1
    assert 'LeBron James' in players

    lebron = players['LeBron James']
    assert lebron.name == 'LeBron James'
    assert lebron.total_minutes == 2316
    assert lebron.nba_id == 2544
    assert lebron.seasons_played == 1
    assert lebron.year_start == 2004
    assert lebron.year_end == 2004


def test_aggregate_multiple_seasons(temp_csv_multiple_seasons):
    """Test aggregating minutes across multiple seasons for same player."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_multiple_seasons,
        min_career_minutes=1000
    )

    players = parser.parse_players()

    assert len(players) == 1
    assert 'LeBron James' in players

    lebron = players['LeBron James']
    assert lebron.name == 'LeBron James'
    assert lebron.total_minutes == 7957  # 2316 + 2451 + 3190
    assert lebron.nba_id == 2544
    assert lebron.seasons_played == 3
    assert lebron.year_start == 2004
    assert lebron.year_end == 2006


def test_filter_by_minimum_minutes(temp_csv_with_below_threshold):
    """Test that players below minimum minutes are filtered out."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_with_below_threshold,
        min_career_minutes=1000
    )

    players = parser.parse_players()

    # Should only include LeBron (2500 minutes), not John Doe (500 minutes)
    assert len(players) == 1
    assert 'LeBron James' in players
    assert 'John Doe' not in players


def test_multiple_players_aggregation(temp_csv_multiple_players):
    """Test parsing and aggregating multiple different players."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_multiple_players,
        min_career_minutes=1000
    )

    players = parser.parse_players()

    # Should include LeBron and Kobe, but not Bench Player
    assert len(players) == 2
    assert 'LeBron James' in players
    assert 'Kobe Bryant' in players
    assert 'Bench Player' not in players

    # Verify LeBron aggregation
    lebron = players['LeBron James']
    assert lebron.total_minutes == 3500  # 2000 + 1500
    assert lebron.seasons_played == 2

    # Verify Kobe single season
    kobe = players['Kobe Bryant']
    assert kobe.total_minutes == 3277
    assert kobe.seasons_played == 1


def test_handle_missing_minutes(temp_csv_missing_data):
    """Test that rows with missing MP are skipped gracefully."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_missing_data,
        min_career_minutes=1000
    )

    # Should not raise an exception
    players = parser.parse_players()

    # Should only include LeBron and Player With Bad ID (1500 minutes)
    # Player With Empty MP should be skipped
    assert 'LeBron James' in players
    assert 'Player With Empty MP' not in players


def test_handle_invalid_nba_id(temp_csv_missing_data):
    """Test that invalid nba_id values are handled gracefully."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_missing_data,
        min_career_minutes=1000
    )

    # Should not raise an exception
    players = parser.parse_players()

    # Player with invalid nba_id should still be included if MP is valid
    assert 'Player With Bad ID' in players
    assert players['Player With Bad ID'].nba_id is None  # Should store as None


def test_parse_decimal_format_minutes(temp_csv_decimal_minutes):
    """Test parsing minutes in decimal format (like real CSV data)."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_decimal_minutes,
        min_career_minutes=1000
    )

    players = parser.parse_players()

    assert len(players) == 2

    # Verify LeBron with decimal '2316.0' → 2316
    lebron = players['LeBron James']
    assert lebron.total_minutes == 2316

    # Verify Kobe with decimal '3277.5' → 3277 (truncated)
    kobe = players['Kobe Bryant']
    assert kobe.total_minutes == 3277


def test_year_range_extraction_single_season(temp_csv_single_player):
    """Test that year_start and year_end are extracted correctly for single season."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_single_player,
        min_career_minutes=1000
    )

    players = parser.parse_players()
    lebron = players['LeBron James']

    assert lebron.year_start == 2004
    assert lebron.year_end == 2004


def test_year_range_extraction_multiple_seasons(temp_csv_multiple_seasons):
    """Test that year_start and year_end span multiple seasons correctly."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_multiple_seasons,
        min_career_minutes=1000
    )

    players = parser.parse_players()
    lebron = players['LeBron James']

    # Seasons: 2004, 2005, 2006
    assert lebron.year_start == 2004
    assert lebron.year_end == 2006


@pytest.fixture
def temp_csv_non_contiguous_years(tmp_path):
    """Create temporary CSV with non-contiguous years."""
    csv_path = tmp_path / "test_scoring.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Player', 'TS%', 'PTS', 'MP', 'Tm', 'G', 'year', 'nba_id'])
        # Player with gap years: 1995, 2001, 2002
        writer.writerow(['Michael Jordan', '0.588', '27.1', '1000', 'CHI', '79', '1995', '893'])
        writer.writerow(['Michael Jordan', '0.568', '27.2', '1000', 'WAS', '80', '2001', '893'])
        writer.writerow(['Michael Jordan', '0.552', '31.4', '1000', 'WAS', '79', '2002', '893'])

    return str(csv_path)


def test_year_range_extraction_non_contiguous(temp_csv_non_contiguous_years):
    """Test that year range uses min/max, not just contiguous years."""
    parser = PlayerStatsCSVParser(
        csv_path=temp_csv_non_contiguous_years,
        min_career_minutes=1000
    )

    players = parser.parse_players()
    mj = players['Michael Jordan']

    # Should span 1995-2002, even though no data for 1996-2000
    assert mj.year_start == 1995
    assert mj.year_end == 2002
