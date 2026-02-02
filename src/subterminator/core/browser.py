"""Playwright-based browser automation wrapper with stealth capabilities.

This module provides a browser automation wrapper built on Playwright with
anti-detection features via playwright-stealth. It implements the BrowserProtocol
for use in subscription cancellation flows.
"""

from playwright.async_api import Browser, Page, Playwright, async_playwright
from playwright_stealth import Stealth

from subterminator.utils.exceptions import ElementNotFound, NavigationError


class PlaywrightBrowser:
    """Playwright-based browser automation with stealth.

    This class wraps Playwright's browser automation with stealth capabilities
    to avoid detection by anti-bot systems. It provides a clean interface for
    common browser operations needed for subscription cancellation flows.

    Attributes:
        headless: Whether to run browser in headless mode.

    Example:
        >>> browser = PlaywrightBrowser(headless=True)
        >>> await browser.launch()
        >>> await browser.navigate("https://example.com")
        >>> await browser.click("#button")
        >>> await browser.close()
    """

    def __init__(self, headless: bool = False) -> None:
        """Initialize the browser wrapper.

        Args:
            headless: Whether to run browser in headless mode. Defaults to False
                for better compatibility with anti-bot detection.
        """
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def launch(self) -> None:
        """Launch browser with stealth settings.

        Starts Playwright, launches a Chromium browser, creates a new page,
        and applies stealth settings to avoid detection.
        """
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()
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

    async def click(self, selector: str | list[str]) -> None:
        """Click element by selector(s). Tries each until success.

        Args:
            selector: CSS selector or list of selectors to try in order.

        Raises:
            RuntimeError: If browser not launched.
            ElementNotFound: If none of the selectors match any element.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        selectors = [selector] if isinstance(selector, str) else selector
        for sel in selectors:
            try:
                element = await self._page.wait_for_selector(sel, timeout=5000)
                if element:
                    await element.scroll_into_view_if_needed()
                    await element.click()
                    return
            except Exception:
                continue
        raise ElementNotFound(f"None of selectors found: {selectors}")

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
        """Close browser and clean up resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None
