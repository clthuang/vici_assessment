"""Playwright-based browser automation wrapper with stealth capabilities.

This module provides a browser automation wrapper built on Playwright with
anti-detection features via playwright-stealth. It implements the BrowserProtocol
for use in subscription cancellation flows.
"""

from pathlib import Path
from typing import Any, cast

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright_stealth import Stealth  # type: ignore

from subterminator.utils.exceptions import (
    CDPConnectionError,
    ElementNotFound,
    NavigationError,
    ProfileLoadError,
)


class PlaywrightBrowser:
    """Playwright-based browser automation with stealth.

    This class wraps Playwright's browser automation with stealth capabilities
    to avoid detection by anti-bot systems. It provides a clean interface for
    common browser operations needed for subscription cancellation flows.

    Supports three modes:
    - Normal mode: Launches a new browser instance (default)
    - CDP mode: Connects to an existing Chrome via Chrome DevTools Protocol
    - Persistent mode: Uses a persistent browser profile

    Attributes:
        headless: Whether to run browser in headless mode.
        cdp_url: URL for CDP connection (mutually exclusive with user_data_dir).
        user_data_dir: Path to persistent browser profile directory.
        cdp_timeout: Timeout for CDP connection in milliseconds.

    Example:
        >>> # Normal mode
        >>> browser = PlaywrightBrowser(headless=True)
        >>> await browser.launch()
        >>>
        >>> # CDP mode (connect to existing Chrome)
        >>> browser = PlaywrightBrowser(cdp_url="http://localhost:9222")
        >>> await browser.launch()
        >>>
        >>> # Persistent profile mode
        >>> browser = PlaywrightBrowser(user_data_dir="/path/to/profile")
        >>> await browser.launch()
    """

    def __init__(
        self,
        headless: bool = False,
        cdp_url: str | None = None,
        user_data_dir: str | None = None,
        cdp_timeout: int = 10000,
    ) -> None:
        """Initialize the browser wrapper.

        Args:
            headless: Whether to run browser in headless mode. Defaults to False
                for better compatibility with anti-bot detection.
            cdp_url: URL for CDP connection. Mutually exclusive with user_data_dir.
            user_data_dir: Path to persistent browser profile. Mutually exclusive
                with cdp_url.
            cdp_timeout: Timeout for CDP connection in milliseconds. Defaults to
                10000 (10 seconds).

        Raises:
            ValueError: If both cdp_url and user_data_dir are provided.
        """
        if cdp_url and user_data_dir:
            raise ValueError("Cannot specify both cdp_url and user_data_dir")

        self.headless = headless
        self.cdp_url = cdp_url
        self.user_data_dir = user_data_dir
        self.cdp_timeout = cdp_timeout
        self._created_page = False
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def is_cdp_connection(self) -> bool:
        """Check if this browser is connected via CDP.

        Returns:
            True if connected to an existing browser via CDP, False otherwise.
        """
        return self.cdp_url is not None

    async def launch(self) -> None:
        """Launch browser with stealth settings.

        Starts Playwright, launches a Chromium browser, creates a new page,
        and applies stealth settings to avoid detection.

        For CDP connections, connects to an existing Chrome instance without
        applying stealth (as the browser is already configured).

        For persistent profiles, uses launch_persistent_context and applies
        stealth to the context.
        """
        self._playwright = await async_playwright().start()

        if self.cdp_url:
            await self._launch_cdp()
        elif self.user_data_dir:
            await self._launch_persistent()
        else:
            await self._launch_normal()

    async def _launch_normal(self) -> None:
        """Launch a new browser instance with stealth."""
        assert self._playwright is not None
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)

    async def _launch_cdp(self) -> None:
        """Connect to existing Chrome via CDP.

        Does not apply stealth since the browser is externally managed.
        Reuses existing pages, skipping system pages like chrome://, about:,
        and chrome-extension:// URLs.
        """
        assert self._playwright is not None
        assert self.cdp_url is not None
        try:
            browser = await self._playwright.chromium.connect_over_cdp(
                self.cdp_url,
                timeout=self.cdp_timeout,
            )
        except Exception as e:
            raise CDPConnectionError(self.cdp_url) from e

        self._browser = browser
        contexts = browser.contexts

        # Find suitable page (skip system pages)
        system_prefixes = ("chrome://", "about:", "chrome-extension://")
        for context in contexts:
            for page in context.pages:
                if not any(page.url.startswith(p) for p in system_prefixes):
                    self._page = page
                    return

        # No suitable page found, create new
        if contexts:
            self._page = await contexts[0].new_page()
        else:
            context = await browser.new_context()
            self._page = await context.new_page()
        self._created_page = True

    async def _launch_persistent(self) -> None:
        """Launch browser with persistent profile.

        Creates the profile directory if it doesn't exist.
        Applies stealth to the persistent context.
        """
        assert self._playwright is not None
        assert self.user_data_dir is not None
        path = Path(self.user_data_dir)
        if not path.exists():
            path.mkdir(parents=True)

        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                str(path),
                headless=self.headless,
            )
        except Exception as e:
            raise ProfileLoadError(str(path)) from e

        self._page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )
        # Apply stealth to persistent context
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)

    async def navigate(self, url: str, timeout: int = 30000) -> None:
        """Navigate to URL and wait for load.

        Args:
            url: The URL to navigate to.
            timeout: Maximum time to wait for navigation in milliseconds.

        Raises:
            RuntimeError: If browser not launched.
            NavigationError: If navigation fails.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        try:
            await self._page.goto(url, timeout=timeout, wait_until="networkidle")
        except Exception as e:
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    async def click(
        self,
        selector: str | list[str],
        fallback_role: tuple[str, str] | None = None,
        timeout: int = 5000,
    ) -> None:
        """Click element by selector(s). Tries each until success.

        Args:
            selector: CSS selector or list of selectors to try in order.
            fallback_role: Optional ARIA role tuple (role, name) to try if CSS
                selectors fail. Example: ("button", "Submit")
            timeout: Maximum time to wait for element in milliseconds.
                Defaults to 5000ms.

        Raises:
            RuntimeError: If browser not launched.
            ElementNotFound: If none of the selectors match any element.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        selectors = [selector] if isinstance(selector, str) else selector

        # Try CSS selectors first
        for sel in selectors:
            try:
                element = await self._page.wait_for_selector(sel, timeout=timeout)
                if element:
                    await element.scroll_into_view_if_needed()
                    await element.click()
                    return
            except Exception:
                continue

        # Try ARIA fallback if provided
        if fallback_role:
            role, name = fallback_role
            try:
                # Cast role to Any since we accept string for flexibility
                # Playwright expects a Literal type but we allow any string
                locator = self._page.get_by_role(cast(Any, role), name=name)
                await locator.click(timeout=timeout)
                return
            except Exception:
                pass

        # Build error message
        msg = f"Element not found. Tried CSS: {selectors}"
        if fallback_role:
            msg += f", ARIA: role={fallback_role[0]} name={fallback_role[1]}"
        raise ElementNotFound(msg)

    async def fill(self, selector: str, value: str) -> None:
        """Fill form field.

        Args:
            selector: CSS selector for the input element.
            value: The value to fill in.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.fill(selector, value)

    async def select_option(self, selector: str, value: str | None = None) -> None:
        """Select dropdown or radio option.

        Args:
            selector: CSS selector for the select element.
            value: The value to select. If None, clicks first available option.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        if value:
            await self._page.select_option(selector, value)
        else:
            # Click first available option
            await self._page.click(f"{selector} option:first-child")

    async def screenshot(self, path: str | None = None) -> bytes:
        """Capture screenshot. Returns bytes, optionally saves to path.

        Args:
            path: Optional file path to save the screenshot.

        Returns:
            The screenshot as PNG bytes.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        return await self._page.screenshot(path=path, full_page=True)

    async def html(self) -> str:
        """Get full page HTML.

        Returns:
            The full HTML content of the page.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        return await self._page.content()

    async def url(self) -> str:
        """Get current URL.

        Returns:
            The current URL.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        return self._page.url

    async def text_content(self) -> str:
        """Get visible text content.

        Returns:
            The visible text content of the page body.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        return await self._page.inner_text("body")

    async def close(self) -> None:
        """Close browser and clean up resources.

        For CDP connections:
        - Only closes the page if we created it (_created_page=True)
        - Never closes the browser (it's externally managed)
        - Always stops the playwright instance

        For normal/persistent connections:
        - Closes the browser (or context for persistent)
        - Always stops the playwright instance
        """
        if self.is_cdp_connection:
            # CDP mode: only close page if we created it, never close browser
            if self._created_page and self._page:
                await self._page.close()
            # Never close browser for CDP - it's externally managed
        else:
            # Normal/persistent mode: close browser/context
            if self._context:
                await self._context.close()
            elif self._browser:
                await self._browser.close()

        # Always stop playwright
        if self._playwright:
            await self._playwright.stop()

        # Reset internal state
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
