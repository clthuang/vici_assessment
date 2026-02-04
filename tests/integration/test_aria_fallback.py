"""Integration tests for ARIA fallback in element selection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.core.browser import PlaywrightBrowser
from subterminator.utils.exceptions import ElementNotFound


class TestARIAFallbackIntegration:
    """Integration tests for ARIA fallback."""

    @pytest.fixture
    def mock_playwright(self):
        """Create mock playwright with ARIA support."""
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.stop = AsyncMock()

        return mock_pw, mock_page

    @pytest.mark.asyncio
    async def test_aria_fallback_succeeds_when_css_fails(self, mock_playwright):
        """ARIA fallback should succeed when all CSS selectors fail."""
        mock_pw, mock_page = mock_playwright

        # Setup browser to return the page
        mock_browser = mock_pw.chromium.launch.return_value
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        # CSS fails
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Not found"))

        # ARIA succeeds
        mock_locator = MagicMock()
        mock_locator.click = AsyncMock()
        mock_page.get_by_role = MagicMock(return_value=mock_locator)

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            # Patch Stealth to avoid issues
            with patch("subterminator.core.browser.Stealth") as mock_stealth:
                mock_stealth.return_value.apply_stealth_async = AsyncMock()

                browser = PlaywrightBrowser()
                await browser.launch()

                # Should succeed via ARIA fallback
                await browser.click(
                    ["#nonexistent-selector"],
                    fallback_role=("button", "Cancel Membership"),
                )

                mock_page.get_by_role.assert_called_with(
                    "button", name="Cancel Membership"
                )
                mock_locator.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_message_when_both_css_and_aria_fail(self, mock_playwright):
        """Error should include both CSS and ARIA info when both fail."""
        mock_pw, mock_page = mock_playwright

        # Setup browser to return the page
        mock_browser = mock_pw.chromium.launch.return_value
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        # Both CSS and ARIA fail
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Not found"))
        mock_locator = MagicMock()
        mock_locator.click = AsyncMock(side_effect=Exception("ARIA failed"))
        mock_page.get_by_role = MagicMock(return_value=mock_locator)

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            # Patch Stealth to avoid issues
            with patch("subterminator.core.browser.Stealth") as mock_stealth:
                mock_stealth.return_value.apply_stealth_async = AsyncMock()

                browser = PlaywrightBrowser()
                await browser.launch()

                with pytest.raises(ElementNotFound) as exc_info:
                    await browser.click(
                        ["#selector1", "#selector2"],
                        fallback_role=("link", "Cancel Membership"),
                    )

                error_msg = str(exc_info.value)
                assert "#selector1" in error_msg
                assert "#selector2" in error_msg
                assert "link" in error_msg
                assert "Cancel Membership" in error_msg

    @pytest.mark.asyncio
    async def test_css_selector_succeeds_skips_aria(self, mock_playwright):
        """When CSS selector succeeds, ARIA fallback should not be tried."""
        mock_pw, mock_page = mock_playwright

        # Setup browser to return the page
        mock_browser = mock_pw.chromium.launch.return_value
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        # CSS succeeds
        mock_element = MagicMock()
        mock_element.scroll_into_view_if_needed = AsyncMock()
        mock_element.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)

        # ARIA should not be called
        mock_page.get_by_role = MagicMock()

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            # Patch Stealth to avoid issues
            with patch("subterminator.core.browser.Stealth") as mock_stealth:
                mock_stealth.return_value.apply_stealth_async = AsyncMock()

                browser = PlaywrightBrowser()
                await browser.launch()

                # Should succeed via CSS
                await browser.click(
                    ["#existing-selector"],
                    fallback_role=("button", "Cancel Membership"),
                )

                # CSS was used
                mock_element.click.assert_called_once()
                # ARIA was not tried
                mock_page.get_by_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_css_selectors_tries_all_before_aria(self, mock_playwright):
        """Should try all CSS selectors before falling back to ARIA."""
        mock_pw, mock_page = mock_playwright

        # Setup browser to return the page
        mock_browser = mock_pw.chromium.launch.return_value
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        # Track CSS selector attempts
        css_attempts = []

        async def mock_wait_for_selector(sel, timeout=None):
            css_attempts.append(sel)
            raise Exception("Not found")

        mock_page.wait_for_selector = mock_wait_for_selector

        # ARIA succeeds
        mock_locator = MagicMock()
        mock_locator.click = AsyncMock()
        mock_page.get_by_role = MagicMock(return_value=mock_locator)

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            # Patch Stealth to avoid issues
            with patch("subterminator.core.browser.Stealth") as mock_stealth:
                mock_stealth.return_value.apply_stealth_async = AsyncMock()

                browser = PlaywrightBrowser()
                await browser.launch()

                await browser.click(
                    ["#first", "#second", "#third"],
                    fallback_role=("button", "Submit"),
                )

                # All CSS selectors were tried
                assert css_attempts == ["#first", "#second", "#third"]
                # Then ARIA was used
                mock_locator.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_role_raises_on_css_failure(self, mock_playwright):
        """Without fallback_role, CSS failure should raise ElementNotFound."""
        mock_pw, mock_page = mock_playwright

        # Setup browser to return the page
        mock_browser = mock_pw.chromium.launch.return_value
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        # CSS fails
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Not found"))

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            # Patch Stealth to avoid issues
            with patch("subterminator.core.browser.Stealth") as mock_stealth:
                mock_stealth.return_value.apply_stealth_async = AsyncMock()

                browser = PlaywrightBrowser()
                await browser.launch()

                with pytest.raises(ElementNotFound) as exc_info:
                    await browser.click(["#nonexistent"])

                # Error should mention the selector
                assert "#nonexistent" in str(exc_info.value)
                # Error should NOT mention ARIA (no fallback provided)
                assert "ARIA" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_second_css_selector_succeeds(self, mock_playwright):
        """Second CSS selector succeeding should not try ARIA or third selector."""
        mock_pw, mock_page = mock_playwright

        # Setup browser to return the page
        mock_browser = mock_pw.chromium.launch.return_value
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        # First CSS fails, second succeeds
        mock_element = MagicMock()
        mock_element.scroll_into_view_if_needed = AsyncMock()
        mock_element.click = AsyncMock()

        call_count = [0]

        async def mock_wait_for_selector(sel, timeout=None):
            call_count[0] += 1
            if sel == "#second":
                return mock_element
            raise Exception("Not found")

        mock_page.wait_for_selector = mock_wait_for_selector

        # ARIA should not be called
        mock_page.get_by_role = MagicMock()

        with patch("subterminator.core.browser.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)

            # Patch Stealth to avoid issues
            with patch("subterminator.core.browser.Stealth") as mock_stealth:
                mock_stealth.return_value.apply_stealth_async = AsyncMock()

                browser = PlaywrightBrowser()
                await browser.launch()

                await browser.click(
                    ["#first", "#second", "#third"],
                    fallback_role=("button", "Submit"),
                )

                # Only first two selectors were tried
                assert call_count[0] == 2
                # Element was clicked
                mock_element.click.assert_called_once()
                # ARIA was not tried
                mock_page.get_by_role.assert_not_called()
