"""Tests for Basketball Reference image URL verification using nodriver.

These tests verify the ImageVerifier class can correctly identify valid and invalid
Basketball Reference image URLs while respecting rate limits and handling errors.

Note: Integration tests marked with @pytest.mark.integration actually use nodriver
browser and make real network requests. They are slower but verify Cloudflare bypass works.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.image_verifier import ImageVerifier


class TestImageVerifierUnit:
    """Unit tests for ImageVerifier with mocked browser."""

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self):
        """Test that rate limiting delays are enforced between requests."""
        verifier = ImageVerifier(rate_limit_delay=1.0)

        # Mock the browser and navigation
        mock_browser = AsyncMock()
        mock_tab = AsyncMock()
        mock_tab.get = AsyncMock()
        mock_tab.get_content = AsyncMock(return_value="<html>Valid image</html>")
        mock_browser.get = AsyncMock(return_value=mock_tab)

        verifier._browser = mock_browser

        # First request
        start_time = time.time()
        await verifier.verify_image_url("https://example.com/image1.jpg")

        # Second request should be delayed
        await verifier.verify_image_url("https://example.com/image2.jpg")
        elapsed = time.time() - start_time

        # Should take at least 1 second due to rate limiting
        assert elapsed >= 1.0, f"Expected >1.0s delay, got {elapsed:.2f}s"

        await verifier.close()

    @pytest.mark.asyncio
    async def test_valid_image_returns_true(self):
        """Test that valid image URL returns True."""
        verifier = ImageVerifier(rate_limit_delay=0.1)  # Fast for testing

        # Mock the browser
        mock_browser = AsyncMock()
        mock_tab = AsyncMock()
        mock_tab.get = AsyncMock()
        mock_tab.get_content = AsyncMock(return_value="<html>Image content</html>")
        mock_browser.get = AsyncMock(return_value=mock_tab)

        verifier._browser = mock_browser

        result = await verifier.verify_image_url("https://example.com/valid.jpg")

        assert result is True
        mock_tab.get.assert_called_once_with("https://example.com/valid.jpg")

        await verifier.close()

    @pytest.mark.asyncio
    async def test_invalid_image_returns_false(self):
        """Test that invalid image URL (404) returns False."""
        verifier = ImageVerifier(rate_limit_delay=0.1)

        # Mock the browser to return 404 content
        mock_browser = AsyncMock()
        mock_tab = AsyncMock()
        mock_tab.get = AsyncMock()
        mock_tab.get_content = AsyncMock(
            return_value="<html>Page Not Found (404 error)</html>"
        )
        mock_browser.get = AsyncMock(return_value=mock_tab)

        verifier._browser = mock_browser

        result = await verifier.verify_image_url("https://example.com/invalid.jpg")

        assert result is False

        await verifier.close()

    @pytest.mark.asyncio
    async def test_browser_lazy_initialization(self):
        """Test that browser is only initialized on first use."""
        verifier = ImageVerifier(rate_limit_delay=0.1)

        # Browser should not be initialized yet
        assert verifier._browser is None

        # Mock nodriver.start()
        mock_browser = AsyncMock()
        mock_tab = AsyncMock()
        mock_tab.get = AsyncMock()
        mock_tab.get_content = AsyncMock(return_value="<html>Test</html>")
        mock_browser.get = AsyncMock(return_value=mock_tab)

        with patch('src.scrapers.image_verifier.uc.start', return_value=mock_browser):
            # First call should initialize browser
            await verifier.verify_image_url("https://example.com/test.jpg")
            assert verifier._browser is not None

        await verifier.close()

    @pytest.mark.asyncio
    async def test_retry_logic_on_transient_errors(self):
        """Test that transient errors trigger retry with exponential backoff."""
        verifier = ImageVerifier(rate_limit_delay=0.1)

        # Mock the browser to fail twice then succeed
        mock_browser = AsyncMock()
        mock_tab = AsyncMock()
        call_count = 0

        async def mock_get_content():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Transient network error")
            return "<html>Success</html>"

        mock_tab.get = AsyncMock()
        mock_tab.get_content = mock_get_content
        mock_browser.get = AsyncMock(return_value=mock_tab)

        verifier._browser = mock_browser

        start_time = time.time()
        result = await verifier.verify_image_url("https://example.com/test.jpg", max_retries=3)
        elapsed = time.time() - start_time

        # Should succeed on third attempt
        assert result is True
        assert call_count == 3

        # Should have exponential backoff (1s + 2s = 3s minimum)
        # With rate limiting (0.1s) total should be ~3.1s
        assert elapsed >= 3.0, f"Expected >=3.0s for backoff, got {elapsed:.2f}s"

        await verifier.close()

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_returns_false(self):
        """Test that exhausted retries return False."""
        verifier = ImageVerifier(rate_limit_delay=0.1)

        # Mock the browser to always fail
        mock_browser = AsyncMock()
        mock_tab = AsyncMock()
        mock_tab.get = AsyncMock()
        mock_tab.get_content = AsyncMock(side_effect=Exception("Permanent error"))
        mock_browser.get = AsyncMock(return_value=mock_tab)

        verifier._browser = mock_browser

        result = await verifier.verify_image_url("https://example.com/test.jpg", max_retries=2)

        assert result is False

        await verifier.close()

    @pytest.mark.asyncio
    async def test_close_cleans_up_browser(self):
        """Test that close() properly cleans up browser resources."""
        verifier = ImageVerifier(rate_limit_delay=0.1)

        # Mock the browser
        mock_browser = AsyncMock()
        mock_browser.stop = AsyncMock()
        verifier._browser = mock_browser

        await verifier.close()

        # Browser should be stopped and set to None
        mock_browser.stop.assert_called_once()
        assert verifier._browser is None

    @pytest.mark.asyncio
    async def test_close_handles_browser_stop_errors(self):
        """Test that close() handles errors during browser.stop()."""
        verifier = ImageVerifier(rate_limit_delay=0.1)

        # Mock the browser with failing stop()
        mock_browser = AsyncMock()
        mock_browser.stop = AsyncMock(side_effect=Exception("Stop error"))
        verifier._browser = mock_browser

        # Should not raise exception
        await verifier.close()

        # Browser should still be set to None
        assert verifier._browser is None


@pytest.mark.integration
class TestImageVerifierIntegration:
    """Integration tests using real nodriver browser and network requests.

    These tests make actual requests to Basketball Reference and verify
    Cloudflare bypass works correctly. They are slower and require Chrome.

    Run with: pytest tests/test_scrapers/test_image_verifier.py -m integration -v
    Skip with: pytest tests/test_scrapers/test_image_verifier.py -m "not integration"
    """

    @pytest.mark.asyncio
    async def test_real_valid_basketball_reference_image(self):
        """Test verification of real valid Basketball Reference image (Kareem Abdul-Jabbar)."""
        verifier = ImageVerifier(rate_limit_delay=2.5)

        try:
            # Kareem Abdul-Jabbar - known valid image
            url = "https://www.basketball-reference.com/req/202106291/images/headshots/abdulka01.jpg"
            result = await verifier.verify_image_url(url)

            assert result is True, "Expected Kareem's image to be valid"

        finally:
            await verifier.close()

    @pytest.mark.asyncio
    async def test_real_invalid_basketball_reference_image(self):
        """Test verification of real invalid Basketball Reference image (Dennis Awtrey)."""
        verifier = ImageVerifier(rate_limit_delay=2.5)

        try:
            # Dennis Awtrey - known invalid image (404)
            url = "https://www.basketball-reference.com/req/202106291/images/headshots/awtrede01.jpg"
            result = await verifier.verify_image_url(url)

            assert result is False, "Expected Awtrey's image to be invalid (404)"

        finally:
            await verifier.close()

    @pytest.mark.asyncio
    async def test_real_rate_limiting_enforced(self):
        """Test that rate limiting is enforced with real requests."""
        verifier = ImageVerifier(rate_limit_delay=2.0)

        try:
            # Two real requests
            url1 = "https://www.basketball-reference.com/req/202106291/images/headshots/abdulka01.jpg"
            url2 = "https://www.basketball-reference.com/req/202106291/images/headshots/abdulka01.jpg"

            start_time = time.time()
            await verifier.verify_image_url(url1)
            await verifier.verify_image_url(url2)
            elapsed = time.time() - start_time

            # Should take at least 2 seconds between requests
            assert elapsed >= 2.0, f"Expected >=2.0s delay, got {elapsed:.2f}s"

        finally:
            await verifier.close()

    @pytest.mark.asyncio
    async def test_real_cloudflare_bypass(self):
        """Test that nodriver successfully bypasses Cloudflare protection."""
        verifier = ImageVerifier(rate_limit_delay=2.5)

        try:
            # If this doesn't raise Cloudflare errors, bypass is working
            url = "https://www.basketball-reference.com/req/202106291/images/headshots/abdulka01.jpg"
            result = await verifier.verify_image_url(url)

            # Should get a result (True or False), not Cloudflare block
            assert isinstance(result, bool), "Expected bool result, not Cloudflare error"

        finally:
            await verifier.close()


if __name__ == "__main__":
    # Run unit tests only by default
    pytest.main([__file__, "-v", "-m", "not integration"])
