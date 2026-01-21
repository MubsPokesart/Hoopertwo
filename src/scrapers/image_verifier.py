"""Image URL verification for Basketball Reference using nodriver (Cloudflare bypass).

This module provides verification for Basketball Reference image URLs that are protected
by Cloudflare. Uses nodriver (lightweight Chrome automation) to bypass Cloudflare
protection and verify images exist before adding players to the database.

Key Features:
- Automatic Cloudflare bypass via nodriver
- Rate limiting (2-3 seconds between requests)
- Browser instance reuse for efficiency
- Retry logic with exponential backoff
- Async/await pattern for concurrent operations

Performance:
- First run: ~3-4 hours for 4000+ players (2.5s per player)
- Subsequent runs: Minutes only (skip list caching avoids re-verification)
"""

import asyncio
import logging
import time
from typing import Optional

try:
    import nodriver as uc
except ImportError:
    raise ImportError(
        "nodriver is required for image verification. "
        "Install with: poetry add nodriver"
    )


class ImageVerifier:
    """Verifies Basketball Reference image URLs using nodriver (Cloudflare bypass).

    This class uses nodriver (successor to undetected-chromedriver) to verify
    Basketball Reference image URLs. Nodriver communicates directly with Chrome
    via DevTools Protocol, leaving fewer automation traces than Selenium.

    Usage:
        verifier = ImageVerifier(rate_limit_delay=2.5)
        is_valid = await verifier.verify_image_url(image_url)
        await verifier.close()

    Attributes:
        _browser: Nodriver browser instance (lazy-initialized)
        _rate_limit_delay: Seconds to wait between verification requests
        _last_request_time: Timestamp of last verification request
        _logger: Logger instance for debugging
    """

    def __init__(self, rate_limit_delay: float = 2.5):
        """Initialize verifier with rate limiting.

        Args:
            rate_limit_delay: Seconds to wait between verification requests.
                             Default 2.5s balances speed and Cloudflare safety.
        """
        self._browser: Optional[uc.Browser] = None
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0
        self._logger = logging.getLogger(__name__)

    async def verify_image_url(self, url: str, max_retries: int = 3) -> bool:
        """Verify if image URL returns valid image (200) or 404.

        Navigates to the image URL using nodriver and checks if the page
        content indicates a 404 error. Basketball Reference returns HTML
        pages with "Page Not Found (404 error)" for missing images.

        Args:
            url: Basketball Reference image URL to verify
            max_retries: Number of retry attempts for transient failures

        Returns:
            True if image exists (200 OK), False if 404 or error

        Raises:
            Exception: Only after max_retries exhausted (logged and returns False)
        """
        # Enforce rate limiting
        await self._enforce_rate_limit_async()

        # Lazy-initialize browser on first use
        if self._browser is None:
            self._browser = await uc.start()
            self._logger.info("Nodriver browser initialized")

        # Try with exponential backoff
        for attempt in range(max_retries):
            try:
                result = await self._navigate_and_check(url)
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    backoff = 2**attempt
                    self._logger.warning(
                        f"Verification failed (attempt {attempt+1}/{max_retries}), "
                        f"retrying in {backoff}s: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    self._logger.error(
                        f"Verification failed after {max_retries} attempts for {url}: {e}"
                    )
                    return False

        return False

    async def _navigate_and_check(self, url: str) -> bool:
        """Navigate to image URL and check response status.

        Basketball Reference returns different content for valid vs invalid images:
        - Valid image: Binary image data
        - Invalid image: HTML page with "Page Not Found (404 error)"

        Args:
            url: Image URL to check

        Returns:
            True if 200 OK (image exists), False if 404 or other error

        Raises:
            Exception: Network errors, navigation failures, etc.
        """
        if self._browser is None:
            raise RuntimeError("Browser not initialized")

        tab = await self._browser.get()

        try:
            # Navigate directly to image URL
            await tab.get(url)

            # Wait a moment for page to fully load
            await asyncio.sleep(0.5)

            # Check page content for 404 indicators
            page_content = await tab.get_content()

            # Basketball Reference returns HTML with specific text for missing images
            if "Page Not Found" in page_content or "404 error" in page_content:
                self._logger.debug(f"Image not found (404): {url}")
                return False

            # If we get here without 404 content, image likely exists
            self._logger.debug(f"Image verified (200): {url}")
            return True

        except Exception as e:
            self._logger.error(f"Error navigating to {url}: {e}")
            raise

    async def _enforce_rate_limit_async(self):
        """Ensure minimum delay between requests.

        Enforces rate limiting by sleeping if needed to maintain the
        configured delay between verification requests. This prevents
        triggering Basketball Reference's Cloudflare rate limits.
        """
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - elapsed
            await asyncio.sleep(sleep_time)
        self._last_request_time = time.time()

    async def close(self):
        """Cleanup browser resources.

        Must be called when done with verification to properly close
        the browser instance and free resources.

        Usage:
            verifier = ImageVerifier()
            try:
                result = await verifier.verify_image_url(url)
            finally:
                await verifier.close()
        """
        if self._browser:
            try:
                await self._browser.stop()
                self._logger.info("Nodriver browser closed")
            except Exception as e:
                self._logger.error(f"Error closing browser: {e}")
            finally:
                self._browser = None
