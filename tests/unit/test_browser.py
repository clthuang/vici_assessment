"""Unit tests for PlaywrightBrowser wrapper.

Tests cover:
- Initialization and headless flag configuration
- RuntimeError when methods called before browser launch
- ElementNotFound exception when click selectors fail
- Module exports
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from subterminator.core.browser import PlaywrightBrowser
from subterminator.utils.exceptions import ElementNotFound


class TestPlaywrightBrowserInit:
    """Tests for PlaywrightBrowser initialization."""

    def test_init_default_headless_false(self) -> None:
        """Default headless should be False."""
        browser = PlaywrightBrowser()
        assert browser.headless is False

    def test_init_headless_true(self) -> None:
        """Should accept headless=True."""
        browser = PlaywrightBrowser(headless=True)
        assert browser.headless is True

    def test_init_headless_false_explicit(self) -> None:
        """Should accept headless=False explicitly."""
        browser = PlaywrightBrowser(headless=False)
        assert browser.headless is False

    def test_init_playwright_is_none(self) -> None:
        """Playwright instance should be None before launch."""
        browser = PlaywrightBrowser()
        assert browser._playwright is None

    def test_init_browser_is_none(self) -> None:
        """Browser instance should be None before launch."""
        browser = PlaywrightBrowser()
        assert browser._browser is None

    def test_init_page_is_none(self) -> None:
        """Page instance should be None before launch."""
        browser = PlaywrightBrowser()
        assert browser._page is None


class TestPlaywrightBrowserNotLaunched:
    """Tests for methods when browser not launched."""

    @pytest.mark.asyncio
    async def test_navigate_raises_runtime_error(self) -> None:
        """navigate should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.navigate("https://example.com")

    @pytest.mark.asyncio
    async def test_click_raises_runtime_error(self) -> None:
        """click should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.click("#button")

    @pytest.mark.asyncio
    async def test_fill_raises_runtime_error(self) -> None:
        """fill should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.fill("#input", "value")

    @pytest.mark.asyncio
    async def test_select_option_raises_runtime_error(self) -> None:
        """select_option should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.select_option("#select", "value")

    @pytest.mark.asyncio
    async def test_screenshot_raises_runtime_error(self) -> None:
        """screenshot should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.screenshot()

    @pytest.mark.asyncio
    async def test_html_raises_runtime_error(self) -> None:
        """html should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.html()

    @pytest.mark.asyncio
    async def test_url_raises_runtime_error(self) -> None:
        """url should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.url()

    @pytest.mark.asyncio
    async def test_text_content_raises_runtime_error(self) -> None:
        """text_content should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.text_content()


class TestPlaywrightBrowserClick:
    """Tests for click method behavior."""

    @pytest.mark.asyncio
    async def test_click_raises_element_not_found_when_no_selectors_match(self) -> None:
        """click should raise ElementNotFound when none of the selectors match."""
        browser = PlaywrightBrowser()

        # Mock the page to simulate no elements found
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        browser._page = mock_page

        selectors = ["#nonexistent1", "#nonexistent2", "#nonexistent3"]
        with pytest.raises(ElementNotFound) as exc_info:
            await browser.click(selectors)
        assert "None of selectors found" in str(exc_info.value)
        assert "#nonexistent1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_click_single_selector_raises_element_not_found(self) -> None:
        """click with single string selector raises ElementNotFound on failure."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        browser._page = mock_page

        with pytest.raises(ElementNotFound) as exc_info:
            await browser.click("#nonexistent")
        assert "#nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_click_succeeds_on_first_selector(self) -> None:
        """click should succeed when first selector matches."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        await browser.click("#button")

        mock_page.wait_for_selector.assert_called_once_with("#button", timeout=5000)
        mock_element.scroll_into_view_if_needed.assert_called_once()
        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_tries_second_selector_on_first_failure(self) -> None:
        """click should try second selector when first fails."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        # First call fails, second succeeds
        mock_page.wait_for_selector = AsyncMock(
            side_effect=[Exception("Timeout"), mock_element]
        )
        browser._page = mock_page

        await browser.click(["#first", "#second"])

        assert mock_page.wait_for_selector.call_count == 2
        mock_element.scroll_into_view_if_needed.assert_called_once()
        mock_element.click.assert_called_once()


class TestPlaywrightBrowserClose:
    """Tests for close method behavior."""

    @pytest.mark.asyncio
    async def test_close_when_not_launched(self) -> None:
        """close should handle case when browser not launched."""
        browser = PlaywrightBrowser()
        # Should not raise
        await browser.close()
        assert browser._browser is None
        assert browser._page is None
        assert browser._playwright is None

    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self) -> None:
        """close should clean up all browser resources."""
        browser = PlaywrightBrowser()

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page

        await browser.close()

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert browser._browser is None
        assert browser._page is None
        assert browser._playwright is None


class TestModuleExports:
    """Tests for module exports."""

    def test_import_from_core(self) -> None:
        """PlaywrightBrowser should be importable from subterminator.core."""
        from subterminator.core import PlaywrightBrowser

        assert PlaywrightBrowser is not None
        assert PlaywrightBrowser.__name__ == "PlaywrightBrowser"

    def test_import_from_browser_module(self) -> None:
        """PlaywrightBrowser should be importable from browser module."""
        from subterminator.core.browser import PlaywrightBrowser

        assert PlaywrightBrowser is not None
