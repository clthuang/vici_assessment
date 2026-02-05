"""Playwright-based browser automation wrapper with stealth capabilities.

This module provides a browser automation wrapper built on Playwright with
anti-detection features via playwright-stealth. It implements the BrowserProtocol
for use in subscription cancellation flows.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright_stealth import Stealth

from subterminator.utils.exceptions import (
    CDPConnectionError,
    ElementNotFound,
    NavigationError,
    ProfileLoadError,
)

if TYPE_CHECKING:
    from subterminator.core.protocols import BrowserAction, BrowserElement


def launch_system_chrome(port: int = 9222) -> str:
    """Launch system Chrome with remote debugging enabled.

    Uses a project-local profile directory (.chrome-profile/) to ensure
    Chrome launches as a new instance even if Chrome is already running.
    The profile persists between runs to preserve login state.

    If Chrome is already running on the specified port, returns the CDP URL
    without launching a new instance.

    Args:
        port: The port for Chrome DevTools Protocol. Defaults to 9222.

    Returns:
        CDP URL to connect to (e.g., "http://localhost:9222").

    Raises:
        RuntimeError: If Chrome installation cannot be found or fails to start.
    """
    import urllib.request

    cdp_url = f"http://localhost:{port}"

    # Check if Chrome is already running on this port
    try:
        urllib.request.urlopen(f"{cdp_url}/json/version", timeout=1)
        return cdp_url  # Already running, no need to launch
    except Exception:
        pass  # Not running, continue to launch

    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "google-chrome",  # Linux
        "chrome",  # Linux alternative
    ]

    # Use project-local profile directory for persistence and isolation
    profile_dir = Path.cwd() / ".chrome-profile"
    profile_dir.mkdir(exist_ok=True)

    for path in chrome_paths:
        try:
            subprocess.Popen(
                [
                    path,
                    f"--remote-debugging-port={port}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for Chrome to start and verify it's listening
            cdp_url = f"http://localhost:{port}"
            for _ in range(10):  # Try for up to 5 seconds
                time.sleep(0.5)
                try:
                    urllib.request.urlopen(f"{cdp_url}/json/version", timeout=1)
                    return cdp_url
                except Exception:
                    continue

            raise RuntimeError(
                f"Chrome started but not responding on {cdp_url}. "
                "Try closing Chrome windows from .chrome-profile and retry."
            )
        except FileNotFoundError:
            continue

    raise RuntimeError(
        "Could not find Chrome installation. "
        "Use --use-chromium to use Playwright's bundled Chromium instead."
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

    async def accessibility_snapshot(self) -> dict[str, Any]:
        """Get accessibility tree snapshot of the current page.

        Returns:
            Dictionary representing the accessibility tree with roles and names.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        snapshot = await self._page.accessibility.snapshot()
        return snapshot or {"role": "WebArea", "name": "", "children": []}

    async def get_element(self, selector: str) -> BrowserElement | None:
        """Get element information by selector.

        Args:
            selector: CSS selector for the element.

        Returns:
            BrowserElement with role, name, and selector, or None if not found.

        Raises:
            RuntimeError: If browser not launched.
        """
        from subterminator.core.protocols import BrowserElement

        if not self._page:
            raise RuntimeError("Browser not launched")

        element = await self._page.query_selector(selector)
        if not element:
            return None

        role = await element.get_attribute("role") or "generic"
        aria_label = await element.get_attribute("aria-label")
        name = aria_label if aria_label else await element.inner_text()

        return BrowserElement(role=role, name=name, selector=selector)

    async def wait_for_navigation(self, timeout: int = 30000) -> None:
        """Wait for navigation to complete.

        Args:
            timeout: Maximum time to wait in milliseconds. Defaults to 30000.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.wait_for_load_state("networkidle", timeout=timeout)

    async def wait_for_element(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for an element to appear on the page.

        Args:
            selector: CSS selector for the element.
            timeout: Maximum time to wait in milliseconds. Defaults to 5000.

        Returns:
            True if element found, False if timeout.

        Raises:
            RuntimeError: If browser not launched.
        """
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        if not self._page:
            raise RuntimeError("Browser not launched")

        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    async def execute_action(self, action: BrowserAction) -> Any:
        """Execute a BrowserAction on the page.

        Args:
            action: The BrowserAction to execute.

        Returns:
            Action-specific result (e.g., screenshot bytes for SCREENSHOT).

        Raises:
            RuntimeError: If browser not launched.
        """
        from subterminator.core.protocols import ActionType

        if not self._page:
            raise RuntimeError("Browser not launched")

        if action.action_type == ActionType.CLICK:
            # Try selector first, fall back to ARIA if provided
            try:
                element = await self._page.wait_for_selector(
                    action.selector,
                    timeout=action.timeout or 5000
                )
                if element:
                    await element.click()
                    return None
            except Exception:
                pass

            # Try fallback role
            if action.fallback_role:
                role, name = action.fallback_role
                locator = self._page.get_by_role(cast(Any, role), name=name)
                await locator.click(timeout=action.timeout or 5000)
            return None

        elif action.action_type == ActionType.FILL:
            await self._page.fill(action.selector, action.value or "")
            return None

        elif action.action_type == ActionType.SELECT:
            await self._page.select_option(action.selector, action.value)
            return None

        elif action.action_type == ActionType.NAVIGATE:
            await self._page.goto(
                action.selector,  # URL is stored in selector
                timeout=action.timeout or 30000,
                wait_until="networkidle"
            )
            return None

        elif action.action_type == ActionType.WAIT:
            await self._page.wait_for_timeout(action.timeout or 1000)
            return None

        elif action.action_type == ActionType.SCREENSHOT:
            path = action.selector if action.selector else None
            return await self._page.screenshot(path=path, full_page=True)

        return None

    # =====================================================================
    # NEW OPTIONAL METHODS (for AI agent) - Phase 2
    # =====================================================================

    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript in the browser context.

        Args:
            script: JavaScript code to execute.

        Returns:
            The result of the script execution.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        return await self._page.evaluate(script)

    def _prune_a11y_tree(
        self,
        node: dict | None,
        depth: int = 0,
        max_depth: int = 5,
    ) -> dict | None:
        """Prune accessibility tree to manageable size.

        Args:
            node: Current node in the tree.
            depth: Current depth.
            max_depth: Maximum depth to traverse.

        Returns:
            Pruned node or None if beyond max_depth.
        """
        if depth > max_depth or node is None:
            return None

        pruned = {
            "role": node.get("role", ""),
            "name": node.get("name", "")[:100],  # Truncate long names
        }

        if "children" in node:
            pruned["children"] = [
                self._prune_a11y_tree(c, depth + 1, max_depth)
                for c in node["children"]
                if c
            ]
            pruned["children"] = [c for c in pruned["children"] if c]

        return pruned

    async def accessibility_tree(self) -> str:
        """Get accessibility tree as JSON string.

        Uses Playwright's page.accessibility.snapshot() and prunes
        to max_depth=5 for reasonable context size.

        Returns:
            JSON string of pruned accessibility tree, or "{}" if unavailable.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        try:
            snapshot = await self._page.accessibility.snapshot()
            if snapshot is None:
                return "{}"
            pruned = self._prune_a11y_tree(snapshot, max_depth=5)
            return json.dumps(pruned, indent=2)
        except (AttributeError, NotImplementedError):
            # Accessibility API may not be available in all browser modes (e.g., CDP)
            return "{}"

    async def click_coordinates(self, x: int, y: int) -> None:
        """Click at specific pixel coordinates.

        Args:
            x: X coordinate relative to viewport.
            y: Y coordinate relative to viewport.

        Raises:
            RuntimeError: If browser not launched.
            ValueError: If coordinates are negative.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")
        if x < 0 or y < 0:
            raise ValueError(f"Coordinates must be non-negative: ({x}, {y})")

        await self._page.mouse.click(x, y)

    async def click_by_role(self, role: str, name: str | None = None) -> None:
        """Click element by ARIA role.

        Args:
            role: The ARIA role to search for.
            name: Optional accessible name to match.

        Raises:
            RuntimeError: If browser not launched.
            ElementNotFound: If no matching element found.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        try:
            locator = self._page.get_by_role(cast(Any, role), name=name)
            await locator.click(timeout=3000)
        except PlaywrightTimeoutError:
            raise ElementNotFound(f"No element with role={role} name='{name}'")

    async def click_by_text(self, text: str, exact: bool = False) -> None:
        """Click element by visible text.

        Args:
            text: The text to search for.
            exact: If True, exact match. If False, substring match.

        Raises:
            RuntimeError: If browser not launched.
            ElementNotFound: If no matching element found.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        try:
            locator = self._page.get_by_text(text, exact=exact)
            await locator.click(timeout=3000)
        except PlaywrightTimeoutError:
            raise ElementNotFound(f"No element with text '{text}'")

    async def viewport_size(self) -> tuple[int, int]:
        """Get current viewport dimensions.

        Returns:
            Tuple of (width, height) in pixels.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        size = self._page.viewport_size
        return (size["width"], size["height"]) if size else (1280, 720)

    async def scroll_position(self) -> tuple[int, int]:
        """Get current scroll position.

        Returns:
            Tuple of (x, y) scroll offset in pixels.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        pos = await self._page.evaluate("[window.scrollX, window.scrollY]")
        return (int(pos[0]), int(pos[1]))

    async def scroll_to(self, x: int, y: int) -> None:
        """Scroll viewport to absolute position.

        Args:
            x: Horizontal scroll position in pixels.
            y: Vertical scroll position in pixels.

        Raises:
            RuntimeError: If browser not launched.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        await self._page.evaluate(f"window.scrollTo({x}, {y})")

    def supports_accessibility_tree(self) -> bool:
        """Check if accessibility_tree() is available.

        Returns:
            True - PlaywrightBrowser supports accessibility tree.
        """
        return True

    def supports_coordinate_clicking(self) -> bool:
        """Check if click_coordinates() is available.

        Returns:
            True - PlaywrightBrowser supports coordinate clicking.
        """
        return True

    def supports_text_clicking(self) -> bool:
        """Check if click_by_text() is available.

        Returns:
            True - PlaywrightBrowser supports text clicking.
        """
        return True

    async def click_by_bbox(
        self,
        selector: str | None = None,
        text: str | None = None,
        aria_role: str | None = None,
        aria_name: str | None = None,
    ) -> dict[str, Any]:
        """Find element and click at center using bounding box.

        Uses JavaScript to find the element and get its bounding box,
        then clicks at the center coordinates. This is more reliable
        than Playwright's click() on complex UIs like Netflix.

        Args:
            selector: CSS selector to find element.
            text: Text content to search for.
            aria_role: ARIA role to search for.
            aria_name: ARIA name to match (used with aria_role).

        Returns:
            Dict with 'found', 'clicked', 'element_info' keys.
            element_info contains x, y, width, height, centerX, centerY.

        Raises:
            RuntimeError: If browser not launched.
            ValueError: If no search criteria provided.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        if not any([selector, text, aria_role]):
            raise ValueError("Must provide selector, text, or aria_role")

        # Build JavaScript to find element and get bounding box
        js_find_element = """
        (options) => {
            let el = null;

            // Try CSS selector first
            if (options.selector) {
                el = document.querySelector(options.selector);
            }

            // Try ARIA role/name
            if (!el && options.ariaRole) {
                const roleSelector = '[role="' + options.ariaRole + '"]';
                const elements = document.querySelectorAll(roleSelector);
                for (const e of elements) {
                    if (!options.ariaName ||
                        e.getAttribute('aria-label')?.includes(options.ariaName) ||
                        e.textContent?.includes(options.ariaName)) {
                        if (e.offsetParent !== null) {
                            el = e;
                            break;
                        }
                    }
                }
            }

            // Try text content
            if (!el && options.text) {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    null,
                    false
                );
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    if (node.textContent?.includes(options.text) &&
                        node.offsetParent !== null) {
                        const rect = node.getBoundingClientRect();
                        // Prefer smaller, more specific elements
                        if (rect.width > 0 && rect.width < 600 && rect.height < 200) {
                            el = node;
                            break;
                        }
                    }
                }
            }

            if (el && el.offsetParent !== null) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return {
                        found: true,
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        centerX: rect.x + rect.width / 2,
                        centerY: rect.y + rect.height / 2,
                        tagName: el.tagName,
                        text: el.textContent?.trim().substring(0, 100) || ''
                    };
                }
            }
            return { found: false };
        }
        """

        options = {
            "selector": selector,
            "text": text,
            "ariaRole": aria_role,
            "ariaName": aria_name,
        }

        js_call = f"({js_find_element})({json.dumps(options)})"
        result = await self._page.evaluate(js_call)

        if result.get("found"):
            # Click at center of element
            center_x = int(result["centerX"])
            center_y = int(result["centerY"])
            await self._page.mouse.click(center_x, center_y)
            return {
                "found": True,
                "clicked": True,
                "element_info": result,
            }

        return {"found": False, "clicked": False, "element_info": None}
