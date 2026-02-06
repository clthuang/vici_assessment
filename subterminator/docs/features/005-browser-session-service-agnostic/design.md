# Design: Browser Session Reuse & Service-Agnostic Architecture

**Feature:** 005-browser-session-service-agnostic
**Status:** Draft
**Created:** 2026-02-04

## 1. Architecture Overview

This design extends SubTerminator's browser automation layer with session reuse capabilities and refactors the engine/CLI for service-agnostic operation.

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ --cdp-url    │  │ --profile-dir│  │ --service (via factory)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┬───────────────┘  │
└─────────┼─────────────────┼──────────────────────────┼──────────────────┘
          │                 │                          │
          v                 v                          v
┌─────────────────────────────────────────┐   ┌──────────────────────────┐
│           PlaywrightBrowser             │   │    ServiceFactory        │
│  ┌─────────────────────────────────┐    │   │  ┌────────────────────┐  │
│  │     BrowserLaunchStrategy       │    │   │  │ create_service()   │  │
│  │  ┌─────────┐ ┌────────┐ ┌────┐  │    │   │  │   - netflix        │  │
│  │  │  CDP    │ │Persist │ │New │  │    │   │  │   - (future...)    │  │
│  │  └─────────┘ └────────┘ └────┘  │    │   │  └────────────────────┘  │
│  └─────────────────────────────────┘    │   └──────────────┬───────────┘
│  ┌─────────────────────────────────┐    │                  │
│  │      ElementClickStrategy       │    │                  │
│  │  ┌─────────┐ ┌───────────────┐  │    │                  │
│  │  │   CSS   │→│ ARIA Fallback │  │    │                  │
│  │  └─────────┘ └───────────────┘  │    │                  │
│  └─────────────────────────────────┘    │                  │
└─────────────────────────────────────────┘                  │
          │                                                   │
          v                                                   v
┌─────────────────────────────────────────────────────────────────────────┐
│                         CancellationEngine                               │
│                                                                          │
│   service: ServiceProtocol  ←─────────────────────────────────────────  │
│   browser: BrowserProtocol  ←─────────────────────────────────────────  │
│                                                                          │
│   Checkpoint messages: "Please log in to {service.config.name}..."       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction Flow

```
User starts Chrome with --remote-debugging-port=9222
                        │
                        v
User runs: subterminator cancel --cdp-url http://localhost:9222 --service netflix
                        │
                        v
┌───────────────────────┴───────────────────────┐
│                   CLI main.py                  │
│                                                │
│  1. Parse flags (cdp_url, profile_dir)         │
│  2. service = create_service("netflix", target)│
│  3. browser = PlaywrightBrowser(cdp_url=...)   │
│  4. engine = CancellationEngine(service, ...)  │
└───────────────────────┬───────────────────────┘
                        │
                        v
┌───────────────────────┴───────────────────────┐
│           PlaywrightBrowser.launch()           │
│                                                │
│  if cdp_url:                                   │
│    connect_over_cdp(cdp_url)  ─────────────┐   │
│  elif user_data_dir:                       │   │
│    launch_persistent_context(user_data_dir)│   │
│  else:                                     │   │
│    chromium.launch() (current behavior)    │   │
│                                            │   │
│  ← Reuses existing session ────────────────┘   │
└───────────────────────────────────────────────┘
                        │
                        v
┌───────────────────────┴───────────────────────┐
│            Engine executes flow                │
│                                                │
│  State detection → Action → Transition         │
│  Uses service.selectors with ARIA fallback     │
└───────────────────────────────────────────────┘
```

## 2. Components

### 2.1 PlaywrightBrowser (Extended)

**Location:** `src/subterminator/core/browser.py`

**Current State:**
- Launches new Chromium browser on every run
- Applies playwright-stealth for anti-detection
- Supports headless mode toggle
- Click method accepts CSS selector or list of fallback selectors

**New Capabilities:**
1. **CDP Connection** - Connect to existing browser via Chrome DevTools Protocol
2. **Persistent Profile** - Use browser profile directory for session persistence
3. **ARIA Fallback** - Fall back to accessibility-based selectors when CSS fails

**Design Decision: Strategy Selection**

The browser will support three mutually exclusive launch strategies:

| Priority | Strategy | Condition | Stealth Applied |
|----------|----------|-----------|-----------------|
| 1 | CDP | `cdp_url` provided | No (user's browser) |
| 2 | Persistent | `user_data_dir` provided | Yes |
| 3 | Fresh | Neither provided | Yes (current behavior) |

### 2.2 ServiceFactory

**Location:** `src/subterminator/services/__init__.py`

**Purpose:** Centralized service instantiation with consistent interface.

**Design Decision: Simple Factory Function**

Rather than a complex factory class, a simple function provides sufficient abstraction:

```
create_service(service_id, target) → ServiceProtocol
```

This keeps the codebase simple while enabling future service additions.

### 2.3 Enhanced Selector Format

**Location:** Service definition files (e.g., `netflix.py`)

**Current Format:**
```python
selectors = ServiceSelectors(
    cancel_link=["[data-uia='action-cancel-membership']", ...],
)
```

**New Format (backward compatible):**
```python
selectors = ServiceSelectors(
    cancel_link=SelectorConfig(
        css=["[data-uia='action-cancel-membership']", ...],
        aria=("button", "Cancel Membership"),  # (role, name)
    ),
)
```

**Design Decision: Optional ARIA**

ARIA fallback is optional per selector. This allows gradual migration without breaking existing functionality.

### 2.4 Engine Abstraction

**Location:** `src/subterminator/core/engine.py`

**Current Issue:**
```python
def __init__(self, service: NetflixService, ...):
```

**Fix:**
```python
def __init__(self, service: ServiceProtocol, ...):
```

This is a type annotation change only - the engine already uses the protocol interface.

### 2.5 Generic Checkpoint Messages

**Location:** `src/subterminator/core/engine.py`

**Current:**
```python
"Please log in to Netflix in the browser..."
```

**New:**
```python
f"Please log in to {self.service.config.name} in the browser..."
```

## 3. Technical Decisions

### 3.1 CDP vs WebSocket

**Decision:** Use Playwright's `connect_over_cdp()` method.

**Rationale:**
- Playwright provides a stable abstraction over raw CDP
- Handles browser version differences internally
- Well-documented API with proper TypeScript typings
- No additional dependencies required

**Alternative Considered:** Raw CDP via `websockets` library
- Rejected: More code, version-specific handling, no benefit

### 3.2 Stealth Mode Handling

**Decision:** Do NOT apply stealth when connecting via CDP.

**Rationale:**
- CDP connects to user's existing browser session
- User's browser has its own fingerprint
- Applying stealth could conflict with existing extensions
- If user needs stealth, they can configure their browser
- Technical limitation: `playwright-stealth` hooks page creation events, which don't fire for existing pages from CDP connections

**Implementation:**
```python
if not self._cdp_url:
    await stealth.apply_stealth_async(self._page)
```

### 3.2.1 CDP Tab Selection Strategy

**Decision:** Use the first navigable page, or create a new one.

**Rationale:**
- Simple and predictable behavior
- Skips system pages (chrome://, about:blank) that can't be used
- Creating new tab is safe fallback

**Implementation:**
```python
async def _launch_cdp(self) -> None:
    """Connect to existing browser via CDP."""
    try:
        self._browser = await self._playwright.chromium.connect_over_cdp(
            self._cdp_url,
            timeout=self._cdp_timeout,
        )
    except Exception as e:
        raise CDPConnectionError(self._cdp_url, e)

    # Get existing pages or create new one
    contexts = self._browser.contexts
    self._page = None
    self._created_page = False

    if contexts and contexts[0].pages:  # Check both contexts AND pages exist
        # Find first navigable page (skip chrome://, about:blank, etc.)
        for page in contexts[0].pages:
            url = page.url
            if not url.startswith(("chrome://", "about:", "chrome-extension://")):
                self._page = page
                break

    if self._page is None:
        # No suitable pages, create new context and page
        context = await self._browser.new_context()
        self._page = await context.new_page()
        self._created_page = True  # Track that we created this page

    # Do NOT apply stealth - this is user's browser
```

### 3.2.3 CDP Page Reuse and Navigation

**Question:** What happens when we reuse a tab that's on google.com?

**Answer:** The engine calls `navigate(entry_url)` which will:
1. Replace whatever page content is there (google.com, reddit.com, etc.)
2. Playwright's `goto()` handles this cleanly - it navigates to the new URL
3. `waitUntil='networkidle'` ensures page is fully loaded before continuing

**Implementation in engine.py START state:**
```python
async def _handle_start(self) -> State:
    """Navigate to service entry URL."""
    await self.browser.navigate(self.service.entry_url)  # Navigates regardless of current page
    return await self._detect_state()
```

**No race condition risk:** Playwright's `page.goto()` is a blocking call that waits for navigation to complete. If the page was mid-navigation, `goto()` will cancel it and navigate to the new URL.

**User expectation:** When user runs SubTerminator with `--cdp-url`, they expect the tool to take over their browser tab and navigate to the service. This matches expected behavior.

### 3.2.2 CDP Close Behavior

**Decision:** For CDP connections, only close the page if we created it; disconnect (don't close) the browser.

**Rationale:**
- Closing user's browser would be destructive and unexpected
- If user opened the tab, they expect it to remain
- If we created the tab, we should clean it up

**Implementation:**
```python
async def close(self) -> None:
    """Close browser/page and clean up resources."""
    if self._is_cdp_connection:
        # For CDP: only close page if we created it
        if self._created_page and self._page:
            await self._page.close()

        # IMPORTANT: Do NOT call browser.close() for CDP connections!
        # Playwright's browser.close() on CDP-connected browser closes Chrome entirely.
        # Instead, just disconnect by stopping playwright (which releases the CDP connection)
        # The user's Chrome will continue running.
    else:
        # For launched browsers: close everything
        if self._browser:
            await self._browser.close()

    if self._playwright:
        await self._playwright.stop()
```

**Note on Playwright CDP behavior:** When connected via `connect_over_cdp()`, calling `browser.close()` will close the actual Chrome browser, not just disconnect. We avoid this by only calling `playwright.stop()` which releases the CDP connection without affecting Chrome.

### 3.3 Profile Directory Auto-Creation

**Decision:** Auto-create profile directory with info message.

**Rationale:**
- Reduces friction for first-time users
- Consistent with Playwright's behavior
- Clear messaging avoids confusion

**Implementation:**
```python
if user_data_dir and not user_data_dir.exists():
    user_data_dir.mkdir(parents=True)
    logger.info(f"Created profile directory: {user_data_dir}")
```

### 3.4 ARIA Selector Priority

**Decision:** CSS first, ARIA as fallback only.

**Rationale:**
- CSS selectors are faster (no accessibility tree traversal)
- Preserves existing behavior
- ARIA is safety net, not primary strategy

**Browser click() Implementation:**
```python
async def click(
    self,
    selector: str | list[str],
    fallback_role: tuple[str, str] | None = None,
    timeout: int = 5000,
) -> None:
    """Click element with CSS selectors and optional ARIA fallback."""
    css_selectors = [selector] if isinstance(selector, str) else selector

    # Try all CSS selectors first
    for css in css_selectors:
        try:
            element = await self._page.wait_for_selector(css, timeout=timeout)
            if element:
                await element.scroll_into_view_if_needed()
                await element.click()
                return
        except Exception:
            continue

    # Fall back to ARIA if provided
    if fallback_role:
        role, name = fallback_role
        try:
            locator = self._page.get_by_role(role, name=name)
            await locator.click(timeout=timeout)
            return
        except Exception:
            pass

    # Build detailed error message
    msg = f"Could not find element.\n  CSS selectors tried: {css_selectors}"
    if fallback_role:
        msg += f"\n  ARIA fallback tried: {role} \"{name}\""
    raise ElementNotFound(msg)
```

**Engine Calling Pattern:**

The engine extracts `css` and `aria` from `SelectorConfig` when calling browser.click():

```python
# In engine.py - example for clicking cancel link
selector_config = self.service.selectors.cancel_link  # SelectorConfig object
await self.browser.click(
    selector_config.css,          # list[str] of CSS selectors
    fallback_role=selector_config.aria,  # tuple[str, str] or None
)

# Helper method in engine (optional refactor)
async def _click_selector(self, selector_config: SelectorConfig) -> None:
    """Click using SelectorConfig with automatic CSS/ARIA extraction."""
    await self.browser.click(
        selector_config.css,
        fallback_role=selector_config.aria,
    )
```

This pattern keeps browser.click() generic (accepts raw CSS and ARIA) while engine handles the SelectorConfig extraction.

### 3.5 Service Factory Location

**Decision:** Place `create_service()` in `services/__init__.py`.

**Rationale:**
- Natural import path: `from subterminator.services import create_service`
- Close to service implementations
- Registry already exists in same package

**Alternative Considered:** Separate `factory.py` module
- Rejected: Over-engineering for a single function

### 3.6 Error Message Format

**Decision:** Include both CSS and ARIA in error messages.

**Rationale:**
- Aids debugging
- Shows what was attempted
- Helps users understand fallback behavior

**Format:**
```
ElementNotFound: Could not find element.
  CSS selectors tried: ['[data-uia="cancel-btn"]', '.cancel-button']
  ARIA fallback tried: button "Cancel Membership"
```

## 4. Risks and Mitigations

### 4.1 CDP Connection Reliability

**Risk:** CDP connection may fail due to Chrome not running or wrong port.

**Mitigation:**
- Clear error message with setup instructions
- Connection timeout (default 10s, configurable via `PlaywrightBrowser.__init__`)
- Suggest checking if Chrome is running with debugging enabled

**CDP Timeout Configuration:**
```python
class PlaywrightBrowser:
    def __init__(
        self,
        headless: bool = False,
        cdp_url: str | None = None,
        user_data_dir: Path | None = None,
        cdp_timeout: int = 10000,  # 10 seconds default
    ) -> None:
        self._cdp_timeout = cdp_timeout
```

### 4.2 Profile Corruption

**Risk:** Corrupted profile directory could break launches.

**Mitigation:**
- Catch specific Playwright profile errors
- Log warning with suggestion to delete profile
- Raise `ProfileLoadError` with actionable message

**Profile Corruption Detection:**
```python
async def _launch_persistent(self) -> None:
    """Launch browser with persistent profile."""
    try:
        if not self._user_data_dir.exists():
            self._user_data_dir.mkdir(parents=True)
            logger.info(f"Created profile directory: {self._user_data_dir}")

        context = await self._playwright.chromium.launch_persistent_context(
            self._user_data_dir,
            headless=self._headless,
        )
        self._context = context
        self._page = context.pages[0] if context.pages else await context.new_page()

        # Apply stealth to persistent context pages
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)

    except PlaywrightError as e:
        error_msg = str(e).lower()
        if "profile" in error_msg or "lock" in error_msg or "corrupt" in error_msg:
            raise ProfileLoadError(self._user_data_dir, e)
        raise  # Re-raise other Playwright errors
```

**Note:** We do NOT automatically fall back to fresh browser on corruption. This would silently lose the user's session state. Instead, we raise an error with clear instructions so the user can make an informed decision.

### 4.3 ARIA Selector Localization

**Risk:** ARIA names may differ by locale (e.g., "Cancel" vs "Cancelar").

**Mitigation:**
- Document limitation in user docs
- Use English locale for initial implementation
- Future: Support multiple ARIA names per selector

### 4.4 Breaking Existing Tests

**Risk:** Changes could break the existing 420+ tests.

**Mitigation:**
- All changes are additive (new parameters with defaults)
- Default behavior unchanged
- Run full test suite after each change

### 4.5 CDP Security Exposure

**Risk:** CDP port exposed to network could allow remote browser control.

**Mitigation:**
- Document that CDP should only bind to localhost
- Default Chrome behavior already binds to 127.0.0.1
- Add security note in CLI help text

## 5. Dependencies

### 5.1 External Dependencies

| Dependency | Current | Required | Notes |
|------------|---------|----------|-------|
| Playwright | 1.40+ | 1.40+ | `connect_over_cdp()` available since 1.10 |
| playwright-stealth | 1.0+ | 1.0+ | No changes needed |

No new external dependencies required.

### 5.2 Internal Dependencies

| Component | Depends On | Notes |
|-----------|------------|-------|
| CLI | ServiceFactory | New import |
| CLI | PlaywrightBrowser | New parameters |
| Engine | ServiceProtocol | Type annotation only |
| PlaywrightBrowser | Playwright CDP API | New code path |

## 6. Interfaces

This section provides detailed interface contracts for all components.

### 6.0 Protocol Updates Required

This feature requires updates to two existing protocols in `src/subterminator/core/protocols.py`.

#### 6.0.1 BrowserProtocol Update

**Current:**
```python
class BrowserProtocol(Protocol):
    async def launch(self) -> None: ...
    async def click(self, selector: str | list[str]) -> None: ...
    # ... other methods
```

**Updated:**
```python
class BrowserProtocol(Protocol):
    """Protocol for browser automation implementations."""

    async def launch(self) -> None:
        """
        Launch or connect to browser.

        Configuration (cdp_url, user_data_dir) is passed at __init__ time,
        not at launch() time. This preserves backward compatibility.
        """
        ...

    async def click(
        self,
        selector: str | list[str],
        fallback_role: tuple[str, str] | None = None,
        timeout: int = 5000,
    ) -> None:
        """
        Click an element with optional ARIA fallback.

        Args:
            selector: CSS selector(s) to try
            fallback_role: Optional (role, name) for ARIA fallback
            timeout: Timeout in milliseconds for each selector attempt (default 5000)
        """
        ...

    async def close(self) -> None:
        """Close browser/page and clean up resources."""
        ...

    @property
    def is_cdp_connection(self) -> bool:
        """True if this browser was connected via CDP."""
        ...
```

**Rationale:** The `click()` signature adds an optional parameter with a default, maintaining backward compatibility. The `is_cdp_connection` property is added to allow engine/CLI to adjust behavior for CDP connections.

#### 6.0.2 ServiceProtocol Update

**Current:**
```python
class ServiceProtocol(Protocol):
    @property
    def config(self) -> dict[str, Any]: ...

    @property
    def entry_url(self) -> str: ...

    @property
    def selectors(self) -> dict[str, str | list[str]]: ...
```

**Updated:**
```python
from subterminator.services.selectors import SelectorConfig


class ServiceConfig(Protocol):
    """
    Protocol for service configuration.

    Note: This is a minimal protocol - existing ServiceConfig dataclass
    already satisfies it (has 'name' and other fields).
    """

    @property
    def name(self) -> str:
        """Human-readable service name (e.g., 'Netflix')."""
        ...


class ServiceProtocol(Protocol):
    """Protocol for subscription service implementations."""

    @property
    def config(self) -> ServiceConfig:
        """Service configuration including name."""
        ...

    @property
    def entry_url(self) -> str:
        """Starting URL for the cancellation flow."""
        ...

    @property
    def selectors(self) -> "ServiceSelectors":
        """
        Element selectors for the cancellation flow.

        Returns ServiceSelectors dataclass with named attributes (cancel_link, etc.)
        Engine accesses via attribute: self.service.selectors.cancel_link
        """
        ...

    @property
    def service_id(self) -> str:
        """Unique identifier for mock path derivation (e.g., 'netflix')."""
        ...
```

**Rationale:**
- `config` returns `ServiceConfig` protocol (minimal, existing dataclass satisfies it)
- `selectors` returns `ServiceSelectors` dataclass (attribute access, not dict access)
- Engine accesses `selectors.cancel_link` (attribute), not `selectors['cancel_link']` (dict)
- Added `service_id` property to derive mock page paths: `mock_pages/{service_id}/`

### 6.1 PlaywrightBrowser Interface

**File:** `src/subterminator/core/browser.py`

```python
from pathlib import Path
from typing import Protocol


class PlaywrightBrowser:
    """Browser automation wrapper with CDP and profile support."""

    def __init__(
        self,
        headless: bool = False,
        cdp_url: str | None = None,
        user_data_dir: Path | None = None,
        cdp_timeout: int = 10000,
    ) -> None:
        """
        Initialize browser configuration.

        Args:
            headless: Run browser without visible window. Ignored for CDP connections.
            cdp_url: Chrome DevTools Protocol URL (e.g., "http://localhost:9222").
                     When provided, connects to existing browser instead of launching.
            user_data_dir: Path to browser profile directory for session persistence.
                          Auto-created if missing.
            cdp_timeout: Connection timeout in milliseconds for CDP (default 10000).

        Raises:
            ValueError: If both cdp_url and user_data_dir are provided.

        Note:
            Launch strategy priority: CDP > Persistent Profile > Fresh Browser.
            Stealth mode is NOT applied when connecting via CDP.
        """
        # Instance variables for tracking state
        self._cdp_url = cdp_url
        self._user_data_dir = user_data_dir
        self._cdp_timeout = cdp_timeout
        self._headless = headless
        self._is_cdp_connection = cdp_url is not None
        self._created_page = False  # Track if we created the page (for close)

    async def launch(self) -> None:
        """
        Launch or connect to browser based on configuration.

        Behavior by configuration:
        - cdp_url set: Connect via CDP, reuse first tab or create new
        - user_data_dir set: Launch with persistent context
        - Neither: Launch fresh browser with stealth (current behavior)

        Raises:
            CDPConnectionError: CDP connection failed (Chrome not running, wrong port)
            ProfileLoadError: Profile directory corrupted
            NavigationError: Browser launch failed
        """

    async def click(
        self,
        selector: str | list[str],
        fallback_role: tuple[str, str] | None = None,
        timeout: int = 5000,
    ) -> None:
        """
        Click an element with CSS selector(s) and optional ARIA fallback.

        Args:
            selector: CSS selector string or list of fallback selectors.
            fallback_role: Optional ARIA (role, name) tuple for accessibility fallback.
                          Only tried if ALL CSS selectors fail.
            timeout: Timeout in milliseconds for each selector attempt (default 5000).

        Raises:
            ElementNotFound: No matching element found after trying all selectors.
                            Error message includes all attempted selectors.

        Example:
            # CSS only (current behavior)
            await browser.click("[data-uia='cancel-btn']")

            # CSS with fallback list
            await browser.click(["[data-uia='cancel-btn']", ".cancel-button"])

            # CSS with ARIA fallback
            await browser.click(
                ["[data-uia='cancel-btn']"],
                fallback_role=("button", "Cancel Membership")
            )
        """

    async def navigate(self, url: str, timeout: int = 30000) -> None:
        """Navigate to URL and wait for network idle."""

    async def screenshot(self, path: Path | None = None) -> bytes:
        """Capture screenshot, optionally saving to path."""

    async def close(self) -> None:
        """
        Close browser and clean up resources.

        Note:
            For CDP connections, this only closes the page, not the browser.
            The user's Chrome remains running.
        """

    @property
    def url(self) -> str:
        """Current page URL."""

    @property
    def is_cdp_connection(self) -> bool:
        """True if connected via CDP to existing browser."""
```

### 6.2 SelectorConfig Type

**File:** `src/subterminator/services/selectors.py` (new file)

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SelectorConfig:
    """
    Configuration for element selection with CSS and ARIA support.

    All selectors use this type - no backward compatibility with raw strings needed
    since this is a pre-production codebase.

    Attributes:
        css: List of CSS selectors to try in order.
        aria: Optional (role, name) tuple for ARIA-based selection.
              Only used as fallback when all CSS selectors fail.

    Example:
        SelectorConfig(
            css=["[data-uia='cancel-btn']", "button.cancel"],
            aria=("button", "Cancel Membership")
        )
    """
    css: list[str]
    aria: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.css:
            raise ValueError("css list cannot be empty")
```

**Note:** No backward compatibility layer needed. All existing selectors will be migrated to `SelectorConfig` format directly.

### 6.3 ServiceFactory Interface

**File:** `src/subterminator/services/__init__.py`

```python
from typing import Callable
from subterminator.core.protocols import ServiceProtocol
from subterminator.services.registry import suggest_service  # Already exists in registry.py
from subterminator.services.netflix import NetflixService


# Service factory registry: maps service_id to constructor
# Each constructor takes (target: str) and returns ServiceProtocol
_SERVICE_FACTORIES: dict[str, Callable[[str], ServiceProtocol]] = {
    "netflix": lambda target: NetflixService(target=target),
    # Future services:
    # "disney": lambda target: DisneyService(target=target),
    # "hulu": lambda target: HuluService(target=target),
}


def create_service(
    service_id: str,
    target: str = "live",
) -> ServiceProtocol:
    """
    Create a service instance by ID.

    This is the canonical way to instantiate services. Use this instead
    of importing service classes directly.

    Args:
        service_id: Service identifier (e.g., "netflix"). Case-insensitive.
        target: Execution target - "live" for real service, "mock" for testing.

    Returns:
        ServiceProtocol implementation configured for the target.

    Raises:
        ValueError: Unknown service_id. Error message includes suggestion
                   if a similar service ID exists.

    Example:
        # Create Netflix service for live execution
        service = create_service("netflix", target="live")

        # Create Netflix service for mock testing
        service = create_service("netflix", target="mock")

        # Unknown service with suggestion
        create_service("netflx")  # ValueError: Unknown service 'netflx'. Did you mean 'netflix'?
    """
    normalized_id = service_id.lower().strip()

    if normalized_id in _SERVICE_FACTORIES:
        return _SERVICE_FACTORIES[normalized_id](target)

    # Unknown service - try to suggest a correction
    suggestion = suggest_service(normalized_id)
    if suggestion:
        raise ValueError(
            f"Unknown service '{service_id}'. Did you mean '{suggestion}'?"
        )
    else:
        available = ", ".join(sorted(_SERVICE_FACTORIES.keys()))
        raise ValueError(
            f"Unknown service '{service_id}'. Available services: {available}"
        )


def get_mock_pages_dir(service_id: str) -> str:
    """
    Get the mock pages directory path for a service.

    Args:
        service_id: Service identifier (e.g., "netflix")

    Returns:
        Relative path to mock pages directory (e.g., "mock_pages/netflix")
    """
    return f"mock_pages/{service_id.lower()}"
```

### 6.4 CLI Interface

**File:** `src/subterminator/cli/main.py`

```
USAGE: subterminator cancel [OPTIONS]

Cancel a subscription service.

OPTIONS:
  --service TEXT       Service to cancel. Use 'list' to see available.
                       If not provided, shows interactive selection menu.

  --target TEXT        Execution target [default: live]
                       - live: Real service (requires authentication)
                       - mock: Local mock server for testing

  --cdp-url TEXT       Connect to existing Chrome browser via CDP.
                       Chrome must be started with: --remote-debugging-port=9222
                       Example: --cdp-url http://localhost:9222
                       Note: Stealth mode is NOT applied for CDP connections.
                       Security: Only use localhost URLs.

  --profile-dir PATH   Use persistent browser profile for session reuse.
                       Login state is saved between runs.
                       Directory auto-created if missing.
                       Example: --profile-dir ~/.subterminator/chrome-profile

  --headless           Run browser in headless mode (no visible window).
                       Ignored for CDP connections.

  --dry-run            Execute flow but stop before final confirmation.
                       Useful for testing without actual cancellation.

  -h, --help           Show this message and exit.

EXAMPLES:
  # Interactive service selection
  subterminator cancel

  # Connect to existing Chrome with Netflix logged in
  subterminator cancel --service netflix --cdp-url http://localhost:9222

  # Use persistent profile (login persists between runs)
  subterminator cancel --service netflix --profile-dir ~/.subterminator/netflix

  # Test with mock server
  subterminator cancel --service netflix --target mock

EXIT CODES:
  0: Success - cancellation completed
  1: Failure - cancellation failed
  2: Aborted - user cancelled operation
  3: Invalid - invalid service or configuration
  4: Config  - configuration error
```

### 6.5 Engine Interface Changes

**File:** `src/subterminator/core/engine.py`

```python
from subterminator.core.protocols import ServiceProtocol, BrowserProtocol


class CancellationEngine:
    """
    Orchestrates the cancellation flow for any service.

    The engine is service-agnostic - it works with any ServiceProtocol
    implementation. Service-specific behavior comes from:
    - service.entry_url: Starting URL
    - service.selectors: Element locators
    - service.config.name: Human-readable name for messages
    """

    def __init__(
        self,
        service: ServiceProtocol,  # Changed from NetflixService
        browser: BrowserProtocol,
        heuristic: HeuristicInterpreter,
        ai: AIInterpreterProtocol | None,
        session: SessionLogger,
        config: AppConfig,
        output_callback: Callable[[str], None],
        input_callback: Callable[[str, int], str],
    ) -> None:
        """
        Initialize the cancellation engine.

        Args:
            service: Any ServiceProtocol implementation (Netflix, Disney, etc.)
            browser: Browser automation interface
            heuristic: Fast rule-based state detection
            ai: Optional AI-based state detection fallback
            session: Logging and artifact management
            config: Application configuration
            output_callback: Display progress messages to user
            input_callback: Request input from user (for checkpoints)
        """
```

**Checkpoint Message Templates:**

```python
# Authentication checkpoint (LOGIN_REQUIRED state)
# {service_name} from service.config.name
# {timeout} from config.auth_timeout (AppConfig, in seconds)
AUTH_PROMPT = """
Please log in to {service_name} in the browser window.
You have {timeout} seconds to complete authentication.
Press Enter when done, or type 'abort' to cancel.
"""

# Confirmation checkpoint (FINAL_CONFIRMATION state)
CONFIRM_PROMPT = """
WARNING: This will cancel your {service_name} subscription.
This action cannot be undone.

Type 'confirm' to proceed, or 'abort' to cancel:
"""

# Unknown state checkpoint
UNKNOWN_PROMPT = """
Could not determine page state for {service_name}.
Please review the browser and navigate to the correct page.
Press Enter when ready, or type 'abort' to cancel.
"""
```

### 6.6 Error Types

**File:** `src/subterminator/core/errors.py`

```python
class CDPConnectionError(PermanentError):
    """
    Failed to connect to Chrome browser via CDP.

    This is a PermanentError (not TransientError) because the issue
    won't resolve on retry - user needs to start Chrome with correct flags.

    Common causes:
    - Chrome not running
    - Chrome not started with --remote-debugging-port
    - Wrong port number
    - Firewall blocking connection

    Attributes:
        url: The CDP URL that was attempted
        original_error: The underlying connection error
    """

    def __init__(self, url: str, original_error: Exception | None = None):
        self.url = url
        self.original_error = original_error
        super().__init__(
            f"Cannot connect to Chrome at {url}. "
            "Is Chrome running with --remote-debugging-port=9222?"
        )


class ProfileLoadError(PermanentError):
    """
    Failed to load browser profile from directory.

    This is a PermanentError because profile corruption won't resolve
    on retry - user needs to delete the profile directory.

    Common causes:
    - Profile corrupted
    - Profile locked by another Chrome instance
    - Insufficient permissions

    Attributes:
        path: The profile directory path
        original_error: The underlying error
    """

    def __init__(self, path: Path, original_error: Exception | None = None):
        self.path = path
        self.original_error = original_error
        super().__init__(
            f"Failed to load browser profile from {path}. "
            "Try deleting the profile directory and running again."
        )
```

**Note:** These errors inherit from `PermanentError` (not `TransientError`) because retrying won't help - the user must take action (start Chrome, fix profile).

### 6.7 Updated NetflixService

**File:** `src/subterminator/services/netflix.py`

```python
from dataclasses import dataclass
from subterminator.services.selectors import SelectorConfig


@dataclass
class ServiceSelectors:
    """Selectors for Netflix cancellation flow."""

    cancel_link: SelectorConfig
    decline_offer: SelectorConfig
    survey_option: SelectorConfig
    survey_submit: SelectorConfig
    confirm_cancel: SelectorConfig


class NetflixService:
    """Netflix subscription cancellation service."""

    def __init__(self, target: str = "live") -> None:
        self.target = target
        self._config = ServiceConfig(...)  # existing
        self._selectors = NETFLIX_SELECTORS  # Store reference to selectors

    @property
    def service_id(self) -> str:
        """Unique identifier for mock path derivation."""
        return "netflix"

    @property
    def config(self) -> ServiceConfig:
        """Service configuration including name."""
        return self._config

    @property
    def entry_url(self) -> str:
        """Starting URL based on target."""
        if self.target == "mock":
            return self._config.mock_entry_url
        return self._config.entry_url

    @property
    def selectors(self) -> ServiceSelectors:
        """
        Element selectors with ARIA fallbacks.

        Returns ServiceSelectors dataclass - access via attributes:
          self.selectors.cancel_link  (not self.selectors['cancel_link'])
        """
        return self._selectors


# Netflix selector definitions with ARIA fallbacks
NETFLIX_SELECTORS = ServiceSelectors(
    cancel_link=SelectorConfig(
        css=[
            "[data-uia='action-cancel-membership']",
            "a:has-text('Cancel Membership')",
            "button:has-text('Cancel Membership')",
        ],
        aria=("link", "Cancel Membership"),
    ),
    decline_offer=SelectorConfig(
        css=[
            "[data-uia='continue-cancel-btn']",
            "button:has-text('Continue to Cancel')",
            "button:has-text('Continue cancellation')",
        ],
        aria=("button", "Continue to Cancel"),
    ),
    survey_option=SelectorConfig(
        css=[
            "[data-uia='survey-option']",
            "input[type='radio']",
            "label:has-text('Other')",
        ],
        aria=("radio", "Other"),
    ),
    survey_submit=SelectorConfig(
        css=[
            "[data-uia='survey-submit-btn']",
            "button[type='submit']",
            "button:has-text('Submit')",
        ],
        aria=("button", "Submit"),
    ),
    confirm_cancel=SelectorConfig(
        css=[
            "[data-uia='confirm-cancel-btn']",
            "button:has-text('Finish Cancellation')",
            "button:has-text('Confirm Cancellation')",
        ],
        aria=("button", "Finish Cancellation"),
    ),
)
```

## 7. File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/subterminator/core/protocols.py` | Modify | Update BrowserProtocol.click() signature, ServiceProtocol.config type |
| `src/subterminator/core/browser.py` | Modify | Add CDP, profile, ARIA support, cdp_timeout param |
| `src/subterminator/core/engine.py` | Modify | Type annotation, generic messages |
| `src/subterminator/core/errors.py` | Modify | Add CDPConnectionError, ProfileLoadError |
| `src/subterminator/services/__init__.py` | Modify | Add create_service() factory, get_mock_pages_dir() |
| `src/subterminator/services/selectors.py` | Create | SelectorConfig dataclass |
| `src/subterminator/services/netflix.py` | Modify | Use SelectorConfig for selectors, add service_id property |
| `src/subterminator/cli/main.py` | Modify | Add --cdp-url, --profile-dir flags; use factory |
| `tests/unit/test_browser.py` | Modify | Add CDP, profile, ARIA tests |
| `tests/unit/test_selectors.py` | Create | SelectorConfig tests |
| `tests/unit/test_factory.py` | Create | Service factory unit tests |
| `tests/integration/test_cli.py` | Modify | Add flag integration tests |

## 8. Testing Strategy

### 8.1 Unit Tests

- **CDP Connection:** Mock `connect_over_cdp`, verify correct Playwright calls
- **Persistent Profile:** Mock `launch_persistent_context`, verify user_data_dir
- **ARIA Fallback:** CSS fails → ARIA succeeds → click completes
- **ARIA Both Fail:** CSS fails → ARIA fails → ElementNotFound raised
- **Service Factory:** Known ID returns service, unknown raises ValueError

### 8.2 Integration Tests

- **CLI CDP Flag:** Verify browser receives cdp_url parameter
- **CLI Profile Flag:** Verify browser receives user_data_dir parameter
- **Mock Flow ARIA:** Run against mock page with modified selectors

### 8.3 Manual Testing

- Start Chrome with remote debugging, connect via CDP
- Verify existing Netflix session is accessible
- Test profile persistence across runs
- Test ARIA fallback by temporarily breaking a selector
