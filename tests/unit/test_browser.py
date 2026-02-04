"""Unit tests for PlaywrightBrowser wrapper.

Tests cover:
- Initialization and headless flag configuration
- RuntimeError when methods called before browser launch
- ElementNotFound exception when click selectors fail
- Module exports
- CDP connection support
- Persistent profile support
- ARIA fallback in click()
- CDP-aware close() behavior
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.core.browser import PlaywrightBrowser
from subterminator.utils.exceptions import (
    CDPConnectionError,
    ElementNotFound,
    ProfileLoadError,
)


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
        assert "Element not found" in str(exc_info.value)
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


class TestCDPConnectionInit:
    """Tests for CDP connection initialization (Step 3.1)."""

    def test_cdp_url_stored_in_init(self) -> None:
        """cdp_url should be stored in __init__ (3.1.1)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
        assert browser.cdp_url == "http://localhost:9222"

    def test_is_cdp_connection_true_when_cdp_url_set(self) -> None:
        """is_cdp_connection should return True when cdp_url is set (3.1.2)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
        assert browser.is_cdp_connection is True

    def test_is_cdp_connection_false_when_no_cdp_url(self) -> None:
        """is_cdp_connection should return False when cdp_url is not set."""
        browser = PlaywrightBrowser()
        assert browser.is_cdp_connection is False

    def test_value_error_if_both_cdp_url_and_user_data_dir(self) -> None:
        """ValueError if both cdp_url and user_data_dir provided (3.1.3)."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            PlaywrightBrowser(
                cdp_url="http://localhost:9222",
                user_data_dir="/path/to/profile",
            )

    def test_created_page_defaults_to_false(self) -> None:
        """_created_page should default to False (3.1.4)."""
        browser = PlaywrightBrowser()
        assert browser._created_page is False

    def test_cdp_timeout_stored(self) -> None:
        """cdp_timeout should be stored in __init__."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222", cdp_timeout=5000)
        assert browser.cdp_timeout == 5000

    def test_cdp_timeout_default(self) -> None:
        """cdp_timeout should default to 10000."""
        browser = PlaywrightBrowser()
        assert browser.cdp_timeout == 10000


class TestCDPConnectionLaunch:
    """Tests for CDP launch behavior (Step 3.1)."""

    @pytest.mark.asyncio
    async def test_launch_calls_connect_over_cdp_when_cdp_url_set(self) -> None:
        """launch() should call connect_over_cdp when cdp_url is set (3.1.5)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        # Create mock playwright and browser
        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser = AsyncMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "subterminator.core.browser.async_playwright",
            return_value=mock_async_playwright,
        ):
            await browser.launch()

        mock_chromium.connect_over_cdp.assert_called_once_with(
            "http://localhost:9222",
            timeout=10000,
        )

    @pytest.mark.asyncio
    async def test_stealth_not_applied_for_cdp(self) -> None:
        """Stealth should NOT be applied for CDP connections (3.1.6)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser = AsyncMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        mock_stealth = MagicMock()
        mock_stealth.apply_stealth_async = AsyncMock()

        with (
            patch(
                "subterminator.core.browser.async_playwright",
                return_value=mock_async_playwright,
            ),
            patch(
                "subterminator.core.browser.Stealth",
                return_value=mock_stealth,
            ) as stealth_class,
        ):
            await browser.launch()

        # Stealth should not be instantiated for CDP
        stealth_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_cdp_connection_error_raised_on_failure(self) -> None:
        """CDPConnectionError should be raised on connection failure (3.1.7)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with (
            patch(
                "subterminator.core.browser.async_playwright",
                return_value=mock_async_playwright,
            ),
            pytest.raises(CDPConnectionError) as exc_info,
        ):
            await browser.launch()

        assert "http://localhost:9222" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_page_reuse_from_existing_context(self) -> None:
        """CDP should reuse existing page from context (3.1.8)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_page = AsyncMock()
        mock_page.url = "https://example.com"  # Non-system URL
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser = AsyncMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "subterminator.core.browser.async_playwright",
            return_value=mock_async_playwright,
        ):
            await browser.launch()

        assert browser._page is mock_page
        assert browser._created_page is False

    @pytest.mark.asyncio
    async def test_new_page_created_when_none_suitable(self) -> None:
        """New page created when no suitable page exists, _created_page=True (3.1.9)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        # Mock page with system URL
        mock_system_page = AsyncMock()
        mock_system_page.url = "chrome://newtab"
        mock_new_page = AsyncMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_system_page]
        mock_context.new_page = AsyncMock(return_value=mock_new_page)

        mock_browser = AsyncMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "subterminator.core.browser.async_playwright",
            return_value=mock_async_playwright,
        ):
            await browser.launch()

        assert browser._page is mock_new_page
        assert browser._created_page is True

    @pytest.mark.asyncio
    async def test_skips_chrome_extension_pages(self) -> None:
        """CDP should skip chrome-extension:// pages."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_ext_page = AsyncMock()
        mock_ext_page.url = "chrome-extension://abcdef/popup.html"
        mock_good_page = AsyncMock()
        mock_good_page.url = "https://example.com"

        mock_context = MagicMock()
        mock_context.pages = [mock_ext_page, mock_good_page]

        mock_browser = AsyncMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "subterminator.core.browser.async_playwright",
            return_value=mock_async_playwright,
        ):
            await browser.launch()

        assert browser._page is mock_good_page
        assert browser._created_page is False

    @pytest.mark.asyncio
    async def test_skips_about_pages(self) -> None:
        """CDP should skip about: pages."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_about_page = AsyncMock()
        mock_about_page.url = "about:blank"
        mock_new_page = AsyncMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_about_page]
        mock_context.new_page = AsyncMock(return_value=mock_new_page)

        mock_browser = AsyncMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = AsyncMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "subterminator.core.browser.async_playwright",
            return_value=mock_async_playwright,
        ):
            await browser.launch()

        assert browser._page is mock_new_page
        assert browser._created_page is True


class TestPersistentProfile:
    """Tests for persistent browser profile support (Step 3.2)."""

    def test_user_data_dir_stored_in_init(self) -> None:
        """user_data_dir should be stored in __init__ (3.2.1)."""
        browser = PlaywrightBrowser(user_data_dir="/path/to/profile")
        assert browser.user_data_dir == "/path/to/profile"

    @pytest.mark.asyncio
    async def test_launch_persistent_context_called_with_path(self, tmp_path) -> None:
        """launch_persistent_context should be called with profile path (3.2.2)."""
        profile_path = str(tmp_path / "profile")
        browser = PlaywrightBrowser(user_data_dir=profile_path)

        mock_page = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]

        mock_chromium = AsyncMock()
        mock_chromium.launch_persistent_context = AsyncMock(return_value=mock_context)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        mock_stealth = MagicMock()
        mock_stealth.apply_stealth_async = AsyncMock()

        with (
            patch(
                "subterminator.core.browser.async_playwright",
                return_value=mock_async_playwright,
            ),
            patch(
                "subterminator.core.browser.Stealth",
                return_value=mock_stealth,
            ),
        ):
            await browser.launch()

        mock_chromium.launch_persistent_context.assert_called_once_with(
            profile_path,
            headless=False,
        )

    @pytest.mark.asyncio
    async def test_directory_auto_created_if_missing(self, tmp_path) -> None:
        """Directory should be auto-created if missing (3.2.3)."""
        profile_path = tmp_path / "new_profile"
        assert not profile_path.exists()

        browser = PlaywrightBrowser(user_data_dir=str(profile_path))

        mock_page = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]

        mock_chromium = AsyncMock()
        mock_chromium.launch_persistent_context = AsyncMock(return_value=mock_context)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        mock_stealth = MagicMock()
        mock_stealth.apply_stealth_async = AsyncMock()

        with (
            patch(
                "subterminator.core.browser.async_playwright",
                return_value=mock_async_playwright,
            ),
            patch(
                "subterminator.core.browser.Stealth",
                return_value=mock_stealth,
            ),
        ):
            await browser.launch()

        assert profile_path.exists()

    @pytest.mark.asyncio
    async def test_profile_load_error_raised_on_corruption(self, tmp_path) -> None:
        """ProfileLoadError should be raised on profile corruption (3.2.4)."""
        profile_path = str(tmp_path / "corrupted_profile")
        browser = PlaywrightBrowser(user_data_dir=profile_path)

        mock_chromium = AsyncMock()
        mock_chromium.launch_persistent_context = AsyncMock(
            side_effect=Exception("Profile corrupted")
        )

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        with (
            patch(
                "subterminator.core.browser.async_playwright",
                return_value=mock_async_playwright,
            ),
            pytest.raises(ProfileLoadError) as exc_info,
        ):
            await browser.launch()

        assert profile_path in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stealth_applied_for_persistent(self, tmp_path) -> None:
        """Stealth should be applied for persistent profile mode."""
        profile_path = str(tmp_path / "profile")
        browser = PlaywrightBrowser(user_data_dir=profile_path)

        mock_page = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]

        mock_chromium = AsyncMock()
        mock_chromium.launch_persistent_context = AsyncMock(return_value=mock_context)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        mock_async_playwright = MagicMock()
        mock_async_playwright.start = AsyncMock(return_value=mock_playwright)

        mock_stealth = MagicMock()
        mock_stealth.apply_stealth_async = AsyncMock()

        with (
            patch(
                "subterminator.core.browser.async_playwright",
                return_value=mock_async_playwright,
            ),
            patch(
                "subterminator.core.browser.Stealth",
                return_value=mock_stealth,
            ) as stealth_class,
        ):
            await browser.launch()

        stealth_class.assert_called_once()
        mock_stealth.apply_stealth_async.assert_called_once_with(mock_page)


class TestClickWithARIAFallback:
    """Tests for click() with ARIA fallback (Step 3.3)."""

    @pytest.mark.asyncio
    async def test_click_css_only_succeeds(self) -> None:
        """click() with CSS only should succeed (3.3.1)."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        await browser.click("#button", timeout=3000)

        mock_page.wait_for_selector.assert_called_once_with("#button", timeout=3000)
        mock_element.scroll_into_view_if_needed.assert_called_once()
        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_css_list_tries_each_in_order(self) -> None:
        """click() should try CSS selectors in order (3.3.2)."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        # First two selectors fail, third succeeds
        mock_page.wait_for_selector = AsyncMock(
            side_effect=[
                Exception("Not found"),
                Exception("Not found"),
                mock_element,
            ]
        )
        browser._page = mock_page

        await browser.click(["#first", "#second", "#third"])

        assert mock_page.wait_for_selector.call_count == 3
        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_fallback_role_tries_aria_after_css_fails(self) -> None:
        """fallback_role should try ARIA after CSS fails (3.3.3)."""
        browser = PlaywrightBrowser()

        mock_locator = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Not found"))
        mock_page.get_by_role = MagicMock(return_value=mock_locator)
        browser._page = mock_page

        await browser.click("#button", fallback_role=("button", "Submit"))

        mock_page.get_by_role.assert_called_once_with("button", name="Submit")
        mock_locator.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_aria_fallback_succeeds_when_css_fails(self) -> None:
        """ARIA fallback should succeed when CSS fails (3.3.4)."""
        browser = PlaywrightBrowser()

        mock_locator = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.get_by_role = MagicMock(return_value=mock_locator)
        browser._page = mock_page

        # Should not raise
        await browser.click("#nonexistent", fallback_role=("button", "OK"))

        mock_locator.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_element_not_found_includes_css_selectors_no_aria(self) -> None:
        """ElementNotFound includes CSS selectors when no ARIA provided (3.3.5)."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        browser._page = mock_page

        with pytest.raises(ElementNotFound) as exc_info:
            await browser.click(["#first", "#second"])

        error_msg = str(exc_info.value)
        assert "#first" in error_msg
        assert "#second" in error_msg
        assert "ARIA" not in error_msg

    @pytest.mark.asyncio
    async def test_element_not_found_includes_aria_when_both_fail(self) -> None:
        """ElementNotFound should include ARIA when both CSS and ARIA fail (3.3.6)."""
        browser = PlaywrightBrowser()

        mock_locator = AsyncMock()
        mock_locator.click = AsyncMock(side_effect=Exception("Not found"))
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.get_by_role = MagicMock(return_value=mock_locator)
        browser._page = mock_page

        with pytest.raises(ElementNotFound) as exc_info:
            await browser.click("#button", fallback_role=("button", "Submit"))

        error_msg = str(exc_info.value)
        assert "#button" in error_msg
        assert "button" in error_msg
        assert "Submit" in error_msg

    @pytest.mark.asyncio
    async def test_explicit_fallback_role_none_shows_css_only_error(self) -> None:
        """Explicit fallback_role=None should show CSS-only error (3.3.7)."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        browser._page = mock_page

        with pytest.raises(ElementNotFound) as exc_info:
            await browser.click("#button", fallback_role=None)

        error_msg = str(exc_info.value)
        assert "#button" in error_msg
        assert "ARIA" not in error_msg

    @pytest.mark.asyncio
    async def test_timeout_passed_to_wait_for_selector(self) -> None:
        """timeout should be passed to wait_for_selector (3.3.8)."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        await browser.click("#button", timeout=10000)

        mock_page.wait_for_selector.assert_called_once_with("#button", timeout=10000)

    @pytest.mark.asyncio
    async def test_timeout_passed_to_aria_locator(self) -> None:
        """timeout should be passed to ARIA locator click."""
        browser = PlaywrightBrowser()

        mock_locator = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.get_by_role = MagicMock(return_value=mock_locator)
        browser._page = mock_page

        await browser.click("#button", fallback_role=("button", "Submit"), timeout=8000)

        mock_locator.click.assert_called_once_with(timeout=8000)


class TestCDPClose:
    """Tests for CDP-aware close() behavior (Step 3.4)."""

    @pytest.mark.asyncio
    async def test_cdp_close_does_not_close_browser(self) -> None:
        """CDP close() should not close browser (3.4.1)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page
        browser._created_page = False

        await browser.close()

        # Browser should NOT be closed for CDP
        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_cdp_close_only_closes_page_if_created_page_true(self) -> None:
        """CDP close() should only close page if _created_page=True (3.4.2)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page
        browser._created_page = True  # We created this page

        await browser.close()

        # Page should be closed since we created it
        mock_page.close.assert_called_once()
        # Browser still should NOT be closed for CDP
        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_cdp_close_does_not_close_page_if_not_created(self) -> None:
        """CDP close() should not close page if _created_page=False."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page
        browser._created_page = False  # We did not create this page

        await browser.close()

        # Page should NOT be closed since we didn't create it
        mock_page.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_cdp_close_closes_browser_normally(self) -> None:
        """Non-CDP close() should close browser normally (3.4.3)."""
        browser = PlaywrightBrowser()  # Normal mode, no CDP

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page

        await browser.close()

        # Browser should be closed for non-CDP
        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_playwright_stop_called_for_cdp(self) -> None:
        """playwright.stop() should be called for CDP mode (3.4.4)."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page
        browser._created_page = False

        await browser.close()

        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_playwright_stop_called_for_non_cdp(self) -> None:
        """playwright.stop() should be called for non-CDP mode (3.4.4)."""
        browser = PlaywrightBrowser()  # Normal mode, no CDP

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page

        await browser.close()

        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_resets_internal_state(self) -> None:
        """close() should reset internal state."""
        browser = PlaywrightBrowser(cdp_url="http://localhost:9222")

        mock_browser = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()
        mock_page = AsyncMock()

        browser._browser = mock_browser
        browser._playwright = mock_playwright
        browser._page = mock_page
        browser._created_page = True

        await browser.close()

        assert browser._browser is None
        assert browser._page is None
        assert browser._playwright is None
