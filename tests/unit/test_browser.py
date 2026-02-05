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
- launch_system_chrome function
- click_by_bbox method
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.core.browser import PlaywrightBrowser, launch_system_chrome
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


# --- Phase 2: Browser Extensions for AI-Driven Control ---


class TestAccessibilitySnapshot:
    """Tests for accessibility_snapshot() method (Tasks 2.2-2.3)."""

    @pytest.mark.asyncio
    async def test_accessibility_snapshot_returns_dict(self) -> None:
        """accessibility_snapshot() should return accessibility tree as dict."""
        browser = PlaywrightBrowser()

        mock_accessibility = MagicMock()
        mock_accessibility.snapshot = AsyncMock(return_value={
            "role": "WebArea",
            "name": "Test Page",
            "children": [
                {"role": "button", "name": "Submit"},
                {"role": "textbox", "name": "Email"},
            ]
        })
        mock_page = AsyncMock()
        mock_page.accessibility = mock_accessibility
        browser._page = mock_page

        result = await browser.accessibility_snapshot()

        assert isinstance(result, dict)
        assert result["role"] == "WebArea"
        assert "children" in result

    @pytest.mark.asyncio
    async def test_accessibility_snapshot_raises_error_when_not_launched(
        self,
    ) -> None:
        """accessibility_snapshot() raises RuntimeError when not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.accessibility_snapshot()

    @pytest.mark.asyncio
    async def test_accessibility_snapshot_calls_page_accessibility(self) -> None:
        """accessibility_snapshot() should call page.accessibility.snapshot()."""
        browser = PlaywrightBrowser()

        mock_accessibility = MagicMock()
        snapshot_data = {"role": "WebArea", "name": ""}
        mock_accessibility.snapshot = AsyncMock(return_value=snapshot_data)
        mock_page = AsyncMock()
        mock_page.accessibility = mock_accessibility
        browser._page = mock_page

        await browser.accessibility_snapshot()

        mock_accessibility.snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_accessibility_snapshot_returns_empty_children(self) -> None:
        """accessibility_snapshot() handles pages with no interactive elements."""
        browser = PlaywrightBrowser()

        mock_accessibility = MagicMock()
        mock_accessibility.snapshot = AsyncMock(return_value={
            "role": "WebArea",
            "name": "",
            "children": []
        })
        mock_page = AsyncMock()
        mock_page.accessibility = mock_accessibility
        browser._page = mock_page

        result = await browser.accessibility_snapshot()

        assert result["children"] == []


class TestGetElement:
    """Tests for get_element() method (Tasks 2.4-2.5)."""

    @pytest.mark.asyncio
    async def test_get_element_returns_browser_element(self) -> None:
        """get_element() should return BrowserElement for matching selector."""
        from subterminator.core.protocols import BrowserElement

        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "role": "button",
            "aria-label": "Submit Form",
        }.get(attr))
        mock_element.inner_text = AsyncMock(return_value="Submit")

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        result = await browser.get_element("#submit-btn")

        assert isinstance(result, BrowserElement)
        assert result.selector == "#submit-btn"

    @pytest.mark.asyncio
    async def test_get_element_raises_runtime_error_when_not_launched(self) -> None:
        """get_element() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.get_element("#button")

    @pytest.mark.asyncio
    async def test_get_element_returns_none_when_not_found(self) -> None:
        """get_element() should return None when element not found."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        browser._page = mock_page

        result = await browser.get_element("#nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_element_extracts_role_from_element(self) -> None:
        """get_element() should extract role attribute."""

        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "role": "link",
        }.get(attr))
        mock_element.inner_text = AsyncMock(return_value="Click here")

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        result = await browser.get_element("a.link")

        assert result is not None
        assert result.role == "link"

    @pytest.mark.asyncio
    async def test_get_element_extracts_name_from_aria_label(self) -> None:
        """get_element() should extract name from aria-label."""

        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "role": "button",
            "aria-label": "Submit Form",
        }.get(attr))
        mock_element.inner_text = AsyncMock(return_value="Submit")

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        result = await browser.get_element("#btn")

        assert result is not None
        assert result.name == "Submit Form"

    @pytest.mark.asyncio
    async def test_get_element_falls_back_to_inner_text(self) -> None:
        """get_element() should use inner_text when aria-label not present."""

        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value=None)
        mock_element.inner_text = AsyncMock(return_value="Click Me")

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        result = await browser.get_element("#btn")

        assert result is not None
        assert result.name == "Click Me"

    @pytest.mark.asyncio
    async def test_get_element_defaults_role_to_generic(self) -> None:
        """get_element() should default role to 'generic' when not specified."""

        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value=None)
        mock_element.inner_text = AsyncMock(return_value="Text")

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        result = await browser.get_element("#elem")

        assert result is not None
        assert result.role == "generic"


class TestWaitForNavigation:
    """Tests for wait_for_navigation() method (Tasks 2.6-2.7)."""

    @pytest.mark.asyncio
    async def test_wait_for_navigation_calls_wait_for_load_state(self) -> None:
        """wait_for_navigation() should call page.wait_for_load_state()."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        browser._page = mock_page

        await browser.wait_for_navigation()

        mock_page.wait_for_load_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_navigation_raises_error_when_not_launched(
        self,
    ) -> None:
        """wait_for_navigation() raises RuntimeError when not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.wait_for_navigation()

    @pytest.mark.asyncio
    async def test_wait_for_navigation_accepts_timeout(self) -> None:
        """wait_for_navigation() should accept timeout parameter."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        browser._page = mock_page

        await browser.wait_for_navigation(timeout=10000)

        mock_page.wait_for_load_state.assert_called_once_with(
            "networkidle", timeout=10000
        )

    @pytest.mark.asyncio
    async def test_wait_for_navigation_default_timeout(self) -> None:
        """wait_for_navigation() should use default timeout of 30000ms."""
        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        browser._page = mock_page

        await browser.wait_for_navigation()

        mock_page.wait_for_load_state.assert_called_once_with(
            "networkidle", timeout=30000
        )


class TestWaitForElement:
    """Tests for wait_for_element() method (Tasks 2.8-2.9)."""

    @pytest.mark.asyncio
    async def test_wait_for_element_calls_wait_for_selector(self) -> None:
        """wait_for_element() should call page.wait_for_selector()."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        await browser.wait_for_element("#button")

        mock_page.wait_for_selector.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_element_raises_error_when_not_launched(self) -> None:
        """wait_for_element() raises RuntimeError when not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.wait_for_element("#button")

    @pytest.mark.asyncio
    async def test_wait_for_element_accepts_timeout(self) -> None:
        """wait_for_element() should accept timeout parameter."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        await browser.wait_for_element("#button", timeout=5000)

        mock_page.wait_for_selector.assert_called_once_with("#button", timeout=5000)

    @pytest.mark.asyncio
    async def test_wait_for_element_returns_true_when_found(self) -> None:
        """wait_for_element() should return True when element is found."""
        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        result = await browser.wait_for_element("#button")

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_element_returns_false_on_timeout(self) -> None:
        """wait_for_element() should return False on timeout."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(
            side_effect=PlaywrightTimeoutError("Timeout")
        )
        browser._page = mock_page

        result = await browser.wait_for_element("#button", timeout=100)

        assert result is False


class TestExecuteAction:
    """Tests for execute_action() method (Tasks 2.10-2.11)."""

    @pytest.mark.asyncio
    async def test_execute_action_click(self) -> None:
        """execute_action() should handle CLICK action type."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_element = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_element)
        browser._page = mock_page

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        await browser.execute_action(action)

        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_fill(self) -> None:
        """execute_action() should handle FILL action type."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.fill = AsyncMock()
        browser._page = mock_page

        action = BrowserAction(
            action_type=ActionType.FILL,
            selector="#email",
            value="test@example.com",
        )
        await browser.execute_action(action)

        mock_page.fill.assert_called_once_with("#email", "test@example.com")

    @pytest.mark.asyncio
    async def test_execute_action_raises_runtime_error_when_not_launched(self) -> None:
        """execute_action() should raise RuntimeError when browser not launched."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.execute_action(action)

    @pytest.mark.asyncio
    async def test_execute_action_navigate(self) -> None:
        """execute_action() should handle NAVIGATE action type."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        browser._page = mock_page

        action = BrowserAction(action_type=ActionType.NAVIGATE, selector="https://example.com")
        await browser.execute_action(action)

        mock_page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_select(self) -> None:
        """execute_action() should handle SELECT action type."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.select_option = AsyncMock()
        browser._page = mock_page

        action = BrowserAction(
            action_type=ActionType.SELECT,
            selector="#dropdown",
            value="option1",
        )
        await browser.execute_action(action)

        mock_page.select_option.assert_called_once_with("#dropdown", "option1")

    @pytest.mark.asyncio
    async def test_execute_action_wait(self) -> None:
        """execute_action() should handle WAIT action type."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        browser._page = mock_page

        action = BrowserAction(action_type=ActionType.WAIT, selector="", timeout=1000)
        await browser.execute_action(action)

        mock_page.wait_for_timeout.assert_called_once_with(1000)

    @pytest.mark.asyncio
    async def test_execute_action_screenshot(self) -> None:
        """execute_action() should handle SCREENSHOT action type."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"png_data")
        browser._page = mock_page

        action = BrowserAction(
            action_type=ActionType.SCREENSHOT, selector="/path/to/file.png"
        )
        result = await browser.execute_action(action)

        mock_page.screenshot.assert_called_once()
        assert result == b"png_data"

    @pytest.mark.asyncio
    async def test_execute_action_click_with_fallback_role(self) -> None:
        """execute_action() CLICK should use fallback_role when provided."""
        from subterminator.core.protocols import ActionType, BrowserAction

        browser = PlaywrightBrowser()

        mock_locator = AsyncMock()
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Not found"))
        mock_page.get_by_role = MagicMock(return_value=mock_locator)
        browser._page = mock_page

        action = BrowserAction(
            action_type=ActionType.CLICK,
            selector="#btn",
            fallback_role=("button", "Submit")
        )
        await browser.execute_action(action)

        mock_page.get_by_role.assert_called_once_with("button", name="Submit")
        mock_locator.click.assert_called_once()


# --- Phase 2: Browser Extensions for AI-Driven Control (Tasks 2.12-2.21) ---


class TestEvaluate:
    """Tests for evaluate() method (Task 2.12)."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_result(self) -> None:
        """evaluate() should return JavaScript evaluation result."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock(return_value="hello")

        result = await browser.evaluate("document.getElementById('test').textContent")

        assert result == "hello"
        browser._page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_raises_runtime_error_when_not_launched(self) -> None:
        """evaluate() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.evaluate("1 + 1")

    @pytest.mark.asyncio
    async def test_evaluate_passes_script_to_page(self) -> None:
        """evaluate() should pass the script to page.evaluate()."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock(return_value=42)

        await browser.evaluate("1 + 1")

        browser._page.evaluate.assert_called_once_with("1 + 1")


class TestPruneA11yTree:
    """Tests for _prune_a11y_tree() helper (Task 2.13)."""

    def test_prune_empty_node(self) -> None:
        """_prune_a11y_tree() should handle empty node."""
        browser = PlaywrightBrowser()

        result = browser._prune_a11y_tree(None)

        assert result is None

    def test_prune_simple_node(self) -> None:
        """_prune_a11y_tree() should prune simple node."""
        browser = PlaywrightBrowser()

        node = {"role": "button", "name": "Click me"}
        result = browser._prune_a11y_tree(node)

        assert result == {"role": "button", "name": "Click me"}

    def test_prune_truncates_long_names(self) -> None:
        """_prune_a11y_tree() should truncate names over 100 chars."""
        browser = PlaywrightBrowser()

        long_name = "a" * 150
        node = {"role": "button", "name": long_name}
        result = browser._prune_a11y_tree(node)

        assert result is not None
        assert len(result["name"]) == 100

    def test_prune_respects_max_depth(self) -> None:
        """_prune_a11y_tree() should respect max_depth."""
        browser = PlaywrightBrowser()

        # Create a deeply nested tree
        node = {"role": "root", "name": ""}
        current = node
        for i in range(10):
            child = {"role": f"level{i}", "name": ""}
            current["children"] = [child]
            current = child

        result = browser._prune_a11y_tree(node, max_depth=3)

        # Verify depth is limited
        depth = 0
        current = result
        while current and "children" in current and current["children"]:
            depth += 1
            current = current["children"][0]
        assert depth <= 3

    def test_prune_handles_children(self) -> None:
        """_prune_a11y_tree() should handle children nodes."""
        browser = PlaywrightBrowser()

        node = {
            "role": "WebArea",
            "name": "Page",
            "children": [
                {"role": "button", "name": "Submit"},
                {"role": "textbox", "name": "Email"},
            ]
        }
        result = browser._prune_a11y_tree(node)

        assert result is not None
        assert "children" in result
        assert len(result["children"]) == 2

    def test_prune_filters_none_children(self) -> None:
        """_prune_a11y_tree() should filter out None children."""
        browser = PlaywrightBrowser()

        node = {
            "role": "WebArea",
            "name": "Page",
            "children": [None, {"role": "button", "name": "Submit"}]
        }
        result = browser._prune_a11y_tree(node)

        assert result is not None
        assert "children" in result
        assert len(result["children"]) == 1


class TestAccessibilityTree:
    """Tests for accessibility_tree() method (Task 2.14)."""

    @pytest.mark.asyncio
    async def test_accessibility_tree_returns_json_string(self) -> None:
        """accessibility_tree() should return JSON string."""
        import json

        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_accessibility = MagicMock()
        snapshot_data = {"role": "button", "name": "Click me"}
        mock_accessibility.snapshot = AsyncMock(return_value=snapshot_data)
        browser._page.accessibility = mock_accessibility

        tree = await browser.accessibility_tree()

        # Should be valid JSON
        parsed = json.loads(tree)
        assert "button" in parsed["role"].lower() or "button" in tree.lower()

    @pytest.mark.asyncio
    async def test_accessibility_tree_null_snapshot(self) -> None:
        """accessibility_tree() should return '{}' for null snapshot."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_accessibility = MagicMock()
        mock_accessibility.snapshot = AsyncMock(return_value=None)
        browser._page.accessibility = mock_accessibility

        tree = await browser.accessibility_tree()

        assert tree == "{}"

    @pytest.mark.asyncio
    async def test_accessibility_tree_raises_error_when_not_launched(self) -> None:
        """accessibility_tree() raises RuntimeError when not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.accessibility_tree()


class TestClickCoordinates:
    """Tests for click_coordinates() method (Task 2.15)."""

    @pytest.mark.asyncio
    async def test_click_coordinates_calls_mouse_click(self) -> None:
        """click_coordinates() should call page.mouse.click()."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.mouse = AsyncMock()
        browser._page.mouse.click = AsyncMock()

        await browser.click_coordinates(100, 200)

        browser._page.mouse.click.assert_called_once_with(100, 200)

    @pytest.mark.asyncio
    async def test_click_coordinates_raises_error_when_not_launched(self) -> None:
        """click_coordinates() raises RuntimeError when not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.click_coordinates(100, 200)

    @pytest.mark.asyncio
    async def test_click_coordinates_rejects_negative_x(self) -> None:
        """click_coordinates() should reject negative x coordinate."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()

        with pytest.raises(ValueError, match="non-negative"):
            await browser.click_coordinates(-1, 200)

    @pytest.mark.asyncio
    async def test_click_coordinates_rejects_negative_y(self) -> None:
        """click_coordinates() should reject negative y coordinate."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()

        with pytest.raises(ValueError, match="non-negative"):
            await browser.click_coordinates(100, -1)


class TestClickByRole:
    """Tests for click_by_role() method (Task 2.16)."""

    @pytest.mark.asyncio
    async def test_click_by_role_calls_get_by_role(self) -> None:
        """click_by_role() should call page.get_by_role()."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_locator = AsyncMock()
        browser._page.get_by_role = MagicMock(return_value=mock_locator)

        await browser.click_by_role("button", "Submit")

        browser._page.get_by_role.assert_called_once()
        mock_locator.click.assert_called_once_with(timeout=3000)

    @pytest.mark.asyncio
    async def test_click_by_role_raises_runtime_error_when_not_launched(self) -> None:
        """click_by_role() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.click_by_role("button", "Submit")

    @pytest.mark.asyncio
    async def test_click_by_role_raises_element_not_found_on_timeout(self) -> None:
        """click_by_role() should raise ElementNotFound on timeout."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_locator = AsyncMock()
        mock_locator.click = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))
        browser._page.get_by_role = MagicMock(return_value=mock_locator)

        with pytest.raises(ElementNotFound, match="No element with role=button"):
            await browser.click_by_role("button", "Submit")


class TestClickByText:
    """Tests for click_by_text() method (Task 2.17)."""

    @pytest.mark.asyncio
    async def test_click_by_text_calls_get_by_text(self) -> None:
        """click_by_text() should call page.get_by_text()."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_locator = AsyncMock()
        browser._page.get_by_text = MagicMock(return_value=mock_locator)

        await browser.click_by_text("Click me")

        browser._page.get_by_text.assert_called_once_with("Click me", exact=False)
        mock_locator.click.assert_called_once_with(timeout=3000)

    @pytest.mark.asyncio
    async def test_click_by_text_with_exact_match(self) -> None:
        """click_by_text() should support exact matching."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_locator = AsyncMock()
        browser._page.get_by_text = MagicMock(return_value=mock_locator)

        await browser.click_by_text("Click me", exact=True)

        browser._page.get_by_text.assert_called_once_with("Click me", exact=True)

    @pytest.mark.asyncio
    async def test_click_by_text_raises_runtime_error_when_not_launched(self) -> None:
        """click_by_text() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.click_by_text("Click me")

    @pytest.mark.asyncio
    async def test_click_by_text_raises_element_not_found_on_timeout(self) -> None:
        """click_by_text() should raise ElementNotFound on timeout."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        mock_locator = AsyncMock()
        mock_locator.click = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))
        browser._page.get_by_text = MagicMock(return_value=mock_locator)

        with pytest.raises(ElementNotFound, match="No element with text"):
            await browser.click_by_text("Click me")


class TestViewportSize:
    """Tests for viewport_size() method (Task 2.18)."""

    @pytest.mark.asyncio
    async def test_viewport_size_returns_dimensions(self) -> None:
        """viewport_size() should return (width, height) tuple."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.viewport_size = {"width": 1920, "height": 1080}

        result = await browser.viewport_size()

        assert result == (1920, 1080)

    @pytest.mark.asyncio
    async def test_viewport_size_raises_runtime_error_when_not_launched(self) -> None:
        """viewport_size() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.viewport_size()

    @pytest.mark.asyncio
    async def test_viewport_size_returns_default_when_none(self) -> None:
        """viewport_size() should return (1280, 720) when viewport_size is None."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.viewport_size = None

        result = await browser.viewport_size()

        assert result == (1280, 720)


class TestScrollPosition:
    """Tests for scroll_position() method (Task 2.19)."""

    @pytest.mark.asyncio
    async def test_scroll_position_returns_position(self) -> None:
        """scroll_position() should return (x, y) tuple."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock(return_value=[100, 200])

        result = await browser.scroll_position()

        assert result == (100, 200)

    @pytest.mark.asyncio
    async def test_scroll_position_raises_runtime_error_when_not_launched(self) -> None:
        """scroll_position() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.scroll_position()

    @pytest.mark.asyncio
    async def test_scroll_position_calls_evaluate(self) -> None:
        """scroll_position() should call page.evaluate()."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock(return_value=[0, 0])

        await browser.scroll_position()

        browser._page.evaluate.assert_called_once_with(
            "[window.scrollX, window.scrollY]"
        )


class TestScrollTo:
    """Tests for scroll_to() method (Task 2.20)."""

    @pytest.mark.asyncio
    async def test_scroll_to_calls_evaluate(self) -> None:
        """scroll_to() should call page.evaluate() with scrollTo."""
        browser = PlaywrightBrowser(headless=True)
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock()

        await browser.scroll_to(100, 200)

        browser._page.evaluate.assert_called_once_with("window.scrollTo(100, 200)")

    @pytest.mark.asyncio
    async def test_scroll_to_raises_runtime_error_when_not_launched(self) -> None:
        """scroll_to() should raise RuntimeError when browser not launched."""
        browser = PlaywrightBrowser()

        with pytest.raises(RuntimeError, match="Browser not launched"):
            await browser.scroll_to(100, 200)


class TestSupportsCapabilities:
    """Tests for supports_*() methods (Task 2.21)."""

    def test_supports_accessibility_tree_returns_true(self) -> None:
        """supports_accessibility_tree() should return True for PlaywrightBrowser."""
        browser = PlaywrightBrowser()

        assert browser.supports_accessibility_tree() is True

    def test_supports_coordinate_clicking_returns_true(self) -> None:
        """supports_coordinate_clicking() should return True for PlaywrightBrowser."""
        browser = PlaywrightBrowser()

        assert browser.supports_coordinate_clicking() is True

    def test_supports_text_clicking_returns_true(self) -> None:
        """supports_text_clicking() should return True for PlaywrightBrowser."""
        browser = PlaywrightBrowser()

        assert browser.supports_text_clicking() is True


# --- launch_system_chrome Tests ---


class TestLaunchSystemChrome:
    """Tests for launch_system_chrome function."""

    @patch("urllib.request.urlopen")
    def test_returns_url_if_chrome_already_running(self, mock_urlopen: MagicMock) -> None:
        """Should return CDP URL without launching if Chrome already running."""
        mock_urlopen.return_value = MagicMock()  # Simulates Chrome responding

        result = launch_system_chrome(port=9222)

        assert result == "http://localhost:9222"
        mock_urlopen.assert_called_once()  # Only checked, didn't launch

    @patch("subprocess.Popen")
    @patch("urllib.request.urlopen")
    def test_launches_chrome_if_not_running(
        self, mock_urlopen: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Should launch Chrome if not already running."""
        # First call fails (not running), subsequent calls succeed
        mock_urlopen.side_effect = [Exception("Not running"), MagicMock()]

        result = launch_system_chrome(port=9222)

        assert result == "http://localhost:9222"
        mock_popen.assert_called_once()  # Should have launched


# --- click_by_bbox Tests ---


class TestClickByBbox:
    """Tests for click_by_bbox bounding box clicking."""

    @pytest.mark.asyncio
    async def test_click_by_bbox_with_css_selector(self) -> None:
        """Should find element by CSS and click at center."""
        browser = PlaywrightBrowser()
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock(return_value={
            "found": True,
            "centerX": 100,
            "centerY": 200,
            "tagName": "BUTTON",
            "text": "Submit"
        })
        browser._page.mouse = AsyncMock()
        browser._page.mouse.click = AsyncMock()

        result = await browser.click_by_bbox(selector="#submit-btn")

        assert result["found"] is True
        assert result["clicked"] is True
        browser._page.mouse.click.assert_called_once_with(100, 200)

    @pytest.mark.asyncio
    async def test_click_by_bbox_element_not_found(self) -> None:
        """Should return found=False if element not found."""
        browser = PlaywrightBrowser()
        browser._page = AsyncMock()
        browser._page.evaluate = AsyncMock(return_value={"found": False})

        result = await browser.click_by_bbox(selector="#nonexistent")

        assert result["found"] is False
        assert result["clicked"] is False

    @pytest.mark.asyncio
    async def test_click_by_bbox_requires_criteria(self) -> None:
        """Should raise ValueError if no search criteria provided."""
        browser = PlaywrightBrowser()
        browser._page = AsyncMock()

        with pytest.raises(ValueError, match="Must provide"):
            await browser.click_by_bbox()
