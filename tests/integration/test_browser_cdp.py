"""Integration tests for CDP connection support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.core.browser import PlaywrightBrowser
from subterminator.utils.exceptions import CDPConnectionError


class TestCDPIntegration:
    """Integration tests for CDP connection."""

    @pytest.fixture
    def mock_playwright(self):
        """Create mock playwright with CDP support."""
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        # Setup page with non-system URL
        mock_page.url = "https://example.com"
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]

        mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)
        mock_pw.stop = AsyncMock()

        return mock_pw

    @pytest.mark.asyncio
    async def test_cdp_connection_uses_connect_over_cdp(self, mock_playwright):
        """CDP connection should use connect_over_cdp."""
        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
            await browser.launch()

            mock_playwright.chromium.connect_over_cdp.assert_called_once_with(
                "http://localhost:9222",
                timeout=10000,
            )

    @pytest.mark.asyncio
    async def test_cdp_close_does_not_close_browser(self, mock_playwright):
        """CDP close() should not close the browser."""
        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
            await browser.launch()
            await browser.close()

            # browser.close() should NOT be called
            mock_playwright.chromium.connect_over_cdp.return_value.close.assert_not_called()
            # playwright.stop() should be called
            mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_flow_with_cdp(self, mock_playwright):
        """Full flow should work with CDP connection."""
        # Setup mock page for navigation and actions
        mock_page = mock_playwright.chromium.connect_over_cdp.return_value.contexts[
            0
        ].pages[0]
        mock_page.goto = AsyncMock()
        mock_page.url = "https://netflix.com/account"
        mock_page.wait_for_selector = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.text_content = AsyncMock(return_value="some text")
        mock_page.screenshot = AsyncMock(return_value=b"png data")

        # Setup mock element for click
        mock_element = MagicMock()
        mock_element.scroll_into_view_if_needed = AsyncMock()
        mock_element.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
            await browser.launch()

            # Simulate flow actions
            await browser.navigate("https://netflix.com/account")
            await browser.click(["#cancel-btn"])

            mock_page.goto.assert_called()
            mock_element.click.assert_called()

    @pytest.mark.asyncio
    async def test_cdp_connection_error_wraps_exception(self, mock_playwright):
        """CDP connection failure should raise CDPConnectionError."""
        mock_playwright.chromium.connect_over_cdp = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

            with pytest.raises(CDPConnectionError) as exc_info:
                await browser.launch()

            assert "http://localhost:9222" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cdp_reuses_existing_page(self, mock_playwright):
        """CDP should reuse existing non-system page."""
        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
            await browser.launch()

            # Should not have created a new page
            assert not browser._created_page

    @pytest.mark.asyncio
    async def test_cdp_skips_system_pages(self):
        """CDP should skip chrome:// and about: pages."""
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()

        # System page that should be skipped
        system_page = MagicMock()
        system_page.url = "chrome://newtab"

        # Normal page that should be used
        normal_page = MagicMock()
        normal_page.url = "https://example.com"

        mock_context.pages = [system_page, normal_page]
        mock_browser.contexts = [mock_context]
        mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)
        mock_pw.stop = AsyncMock()

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
            await browser.launch()

            # Should have selected the normal page, not the system page
            assert browser._page == normal_page

    @pytest.mark.asyncio
    async def test_cdp_creates_page_when_only_system_pages(self):
        """CDP should create page when only system pages exist."""
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_new_page = MagicMock()

        # Only system page
        system_page = MagicMock()
        system_page.url = "chrome://newtab"

        mock_context.pages = [system_page]
        mock_context.new_page = AsyncMock(return_value=mock_new_page)
        mock_browser.contexts = [mock_context]
        mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)
        mock_pw.stop = AsyncMock()

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
            await browser.launch()

            # Should have created a new page
            assert browser._created_page
            mock_context.new_page.assert_called_once()
