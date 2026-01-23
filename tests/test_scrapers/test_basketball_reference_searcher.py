"""Tests for BasketballReferenceSearcher.

This module tests the Basketball Reference search functionality for resolving
player ID collisions. Includes both unit tests with mocked responses and
integration tests with real Basketball Reference searches.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.scrapers.basketball_reference_searcher import BasketballReferenceSearcher


class TestBasketballReferenceSearcher:
    """Test suite for BasketballReferenceSearcher."""

    @pytest.fixture
    def searcher(self):
        """Create searcher instance for testing."""
        return BasketballReferenceSearcher(rate_limit_delay=0.1)

    @pytest.fixture
    async def searcher_with_browser(self):
        """Create searcher with initialized browser for testing."""
        searcher = BasketballReferenceSearcher(rate_limit_delay=0.1)
        # Browser will be lazy-initialized on first use
        yield searcher
        # Cleanup
        await searcher.close()

    # Unit Tests - Mocked HTML Parsing

    def test_parse_search_results_with_matching_years(self, searcher):
        """Test parsing search results with matching year range."""
        html = """
        <div class="search-item">
            <a href="/players/p/paxsoji02.html">Jim Paxson</a>
            <span>1980-1990</span>
        </div>
        """
        result = searcher._parse_search_results(html, "Jim Paxson", 1980, 1990)
        assert result == "paxsoji02"

    def test_parse_search_results_with_year_overlap(self, searcher):
        """Test parsing search results with overlapping year ranges."""
        html = """
        <div class="search-item">
            <a href="/players/b/bridgmi02.html">Miles Bridges</a>
            <span>2018-2025</span>
        </div>
        """
        # Target years 2019-2025 should match 2018-2025 (overlap allowed)
        result = searcher._parse_search_results(html, "Miles Bridges", 2019, 2025)
        assert result == "bridgmi02"

    def test_parse_search_results_no_year_match(self, searcher):
        """Test parsing when year ranges don't match."""
        html = """
        <div class="search-item">
            <a href="/players/p/paxsoji01.html">Jim Paxson</a>
            <span>1950-1958</span>
        </div>
        """
        # Looking for 1980-1990, but result is 1950-1958 (no overlap)
        result = searcher._parse_search_results(html, "Jim Paxson", 1980, 1990)
        assert result is None

    def test_parse_search_results_multiple_players(self, searcher):
        """Test parsing with multiple results, returns first matching year range."""
        html = """
        <div class="search-item">
            <a href="/players/p/paxsoji01.html">Jim Paxson</a>
            <span>1950-1958</span>
        </div>
        <div class="search-item">
            <a href="/players/p/paxsoji02.html">Jim Paxson</a>
            <span>1980-1990</span>
        </div>
        """
        result = searcher._parse_search_results(html, "Jim Paxson", 1980, 1990)
        assert result == "paxsoji02"

    def test_parse_search_results_redirect_to_player_page(self, searcher):
        """Test parsing when BR redirects directly to player page (single perfect match)."""
        html = """
        <html>
            <body>
                <h1>LeBron James</h1>
                <a href="/players/j/jamesle01.html">Player Profile</a>
            </body>
        </html>
        """
        result = searcher._parse_search_results(html, "LeBron James", 2003, 2025)
        assert result == "jamesle01"

    def test_parse_search_results_no_results(self, searcher):
        """Test parsing when no search results found."""
        html = """
        <html>
            <body>
                <p>No results found</p>
            </body>
        </html>
        """
        result = searcher._parse_search_results(html, "Nonexistent Player", 2000, 2010)
        assert result is None

    def test_parse_search_results_malformed_html(self, searcher):
        """Test parsing gracefully handles malformed HTML."""
        html = "<div><incomplete"
        result = searcher._parse_search_results(html, "Test Player", 2000, 2010)
        assert result is None

    # Unit Tests - Rate Limiting

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self, searcher):
        """Test that rate limiting delay is enforced between requests."""
        import time

        # Set delay to 0.2s for testing
        searcher._rate_limit_delay = 0.2

        # First call should not wait
        start = time.time()
        await searcher._enforce_rate_limit_async()
        first_elapsed = time.time() - start
        assert first_elapsed < 0.1  # Should be nearly instant

        # Second call immediately after should wait
        start = time.time()
        await searcher._enforce_rate_limit_async()
        second_elapsed = time.time() - start
        assert second_elapsed >= 0.15  # Should wait ~0.2s

    # Integration Tests - Real Basketball Reference Searches
    # These tests make actual HTTP requests and may be slow

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_jim_paxson_integration(self, searcher_with_browser):
        """Integration test: Search for Jim Paxson (1980-1990) -> paxsoji02."""
        result = await searcher_with_browser.search_player_by_name_and_years(
            "Jim Paxson", 1980, 1990
        )
        assert result == "paxsoji02"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_miles_bridges_integration(self, searcher_with_browser):
        """Integration test: Search for Miles Bridges (2019-2025) -> bridgmi02."""
        result = await searcher_with_browser.search_player_by_name_and_years(
            "Miles Bridges", 2019, 2025
        )
        assert result == "bridgmi02"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_mikal_bridges_integration(self, searcher_with_browser):
        """Integration test: Search for Mikal Bridges (2019-2025) -> bridgmi01."""
        result = await searcher_with_browser.search_player_by_name_and_years(
            "Mikal Bridges", 2019, 2025
        )
        assert result == "bridgmi01"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_nonexistent_player_integration(self, searcher_with_browser):
        """Integration test: Search for nonexistent player returns None."""
        result = await searcher_with_browser.search_player_by_name_and_years(
            "Fake Player Name", 2000, 2010
        )
        assert result is None

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_search_without_browser_initialization(self, searcher):
        """Test that browser is lazy-initialized on first search."""
        # Browser should be None initially
        assert searcher._browser is None

        # Mock the browser and search to avoid real initialization
        with patch.object(searcher, '_search_and_parse', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = "testid01"

            result = await searcher.search_player_by_name_and_years(
                "Test Player", 2000, 2010
            )

            assert result == "testid01"

    @pytest.mark.asyncio
    async def test_search_with_retry_on_failure(self, searcher):
        """Test that search retries on transient failures."""
        with patch.object(searcher, '_search_and_parse', new_callable=AsyncMock) as mock_search:
            # First two attempts fail, third succeeds
            mock_search.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                "paxsoji02"
            ]

            result = await searcher.search_player_by_name_and_years(
                "Jim Paxson", 1980, 1990, max_retries=3
            )

            assert result == "paxsoji02"
            assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_search_returns_none_after_max_retries(self, searcher):
        """Test that search returns None after exhausting retries."""
        with patch.object(searcher, '_search_and_parse', new_callable=AsyncMock) as mock_search:
            # All attempts fail
            mock_search.side_effect = Exception("Persistent error")

            result = await searcher.search_player_by_name_and_years(
                "Test Player", 2000, 2010, max_retries=3
            )

            assert result is None
            assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_close_without_browser(self, searcher):
        """Test that close() works even if browser was never initialized."""
        # Should not raise exception
        await searcher.close()
        assert searcher._browser is None

    @pytest.mark.asyncio
    async def test_close_with_browser(self):
        """Test that close() properly cleans up browser."""
        searcher = BasketballReferenceSearcher(rate_limit_delay=0.1)

        # Mock browser
        mock_browser = AsyncMock()
        searcher._browser = mock_browser

        await searcher.close()

        # Verify stop() was called
        mock_browser.stop.assert_called_once()
        assert searcher._browser is None

    # Edge Cases

    def test_parse_search_results_with_year_at_boundary(self, searcher):
        """Test parsing with year ranges at exact boundary (off-by-one tolerance)."""
        html = """
        <div class="search-item">
            <a href="/players/t/testpl01.html">Test Player</a>
            <span>2000-2010</span>
        </div>
        """
        # Target 1999-2011 should match 2000-2010 (±1 year tolerance)
        result = searcher._parse_search_results(html, "Test Player", 1999, 2011)
        assert result == "testpl01"

    def test_parse_search_results_with_special_characters(self, searcher):
        """Test parsing player names with special characters."""
        html = """
        <div class="search-item">
            <a href="/players/o/onealsh01.html">Shaquille O'Neal</a>
            <span>1992-2011</span>
        </div>
        """
        result = searcher._parse_search_results(html, "Shaquille O'Neal", 1992, 2011)
        assert result == "onealsh01"
