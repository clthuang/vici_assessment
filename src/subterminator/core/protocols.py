"""Core protocols and data types for SubTerminator.

This module defines the foundational types and protocols that all other
components depend on. It includes:
- State enum for representing cancellation flow states
- Data classes for AI interpretations and results
- Protocol definitions for browser, AI interpreter, and service abstractions
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Protocol


class State(Enum):
    """Represents the possible states in a subscription cancellation flow.

    States are organized into logical groups:
    - Entry states: START, LOGIN_REQUIRED
    - Account states: ACCOUNT_ACTIVE, ACCOUNT_CANCELLED, THIRD_PARTY_BILLING
    - Flow states: RETENTION_OFFER, EXIT_SURVEY, FINAL_CONFIRMATION
    - Terminal states: COMPLETE, ABORTED, FAILED, UNKNOWN
    """

    START = auto()
    LOGIN_REQUIRED = auto()
    ACCOUNT_ACTIVE = auto()
    ACCOUNT_CANCELLED = auto()
    THIRD_PARTY_BILLING = auto()
    RETENTION_OFFER = auto()
    EXIT_SURVEY = auto()
    FINAL_CONFIRMATION = auto()
    COMPLETE = auto()
    ABORTED = auto()
    FAILED = auto()
    UNKNOWN = auto()


@dataclass
class AIInterpretation:
    """Result of AI interpretation of a page screenshot.

    Attributes:
        state: The detected page state.
        confidence: Confidence score between 0.0 and 1.0.
        reasoning: Explanation of how the state was determined.
        actions: List of suggested actions as dictionaries,
            e.g., [{"action": "click", "selector": "#cancel-btn"}]
    """

    state: State
    confidence: float
    reasoning: str
    actions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence is within valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


@dataclass
class CancellationResult:
    """Result of a cancellation operation.

    Attributes:
        success: Whether the cancellation completed successfully.
        state: The final state reached during the operation.
        message: Human-readable description of the result.
        session_dir: Path to the session directory containing logs/screenshots.
        effective_date: The date when cancellation takes effect (if applicable).
    """

    success: bool
    state: State
    message: str
    session_dir: Path | None = None
    effective_date: str | None = None


class BrowserProtocol(Protocol):
    """Protocol defining the browser automation interface.

    This protocol abstracts browser operations, allowing for different
    implementations (e.g., Playwright, Selenium) or mock implementations
    for testing.
    """

    async def launch(self) -> None:
        """Launch the browser instance."""
        ...

    async def navigate(self, url: str, timeout: int = 30000) -> None:
        """Navigate to the specified URL.

        Args:
            url: The URL to navigate to.
            timeout: Maximum time to wait for navigation in milliseconds.
        """
        ...

    async def click(
        self,
        selector: str | list[str],
        fallback_role: tuple[str, str] | None = None,
        timeout: int = 5000,
    ) -> None:
        """Click an element matching the selector.

        Args:
            selector: CSS selector or list of selectors to try in order.
            fallback_role: Optional ARIA role tuple (role, name) to try if CSS
                selectors fail. Example: ("button", "Submit")
            timeout: Maximum time to wait for element in milliseconds.
                Defaults to 5000ms.
        """
        ...

    async def fill(self, selector: str, value: str) -> None:
        """Fill an input element with the specified value.

        Args:
            selector: CSS selector for the input element.
            value: The value to fill in.
        """
        ...

    async def select_option(self, selector: str, value: str | None = None) -> None:
        """Select an option from a dropdown/select element.

        Args:
            selector: CSS selector for the select element.
            value: The value to select. If None, selects the first option.
        """
        ...

    async def screenshot(self, path: str | None = None) -> bytes:
        """Capture a screenshot of the current page.

        Args:
            path: Optional file path to save the screenshot.

        Returns:
            The screenshot as PNG bytes.
        """
        ...

    async def html(self) -> str:
        """Get the current page HTML content.

        Returns:
            The full HTML content of the page.
        """
        ...

    async def url(self) -> str:
        """Get the current page URL.

        Returns:
            The current URL.
        """
        ...

    async def text_content(self) -> str:
        """Get the text content of the page.

        Returns:
            The visible text content of the page.
        """
        ...

    async def close(self) -> None:
        """Close the browser instance."""
        ...

    @property
    def is_cdp_connection(self) -> bool:
        """Check if this browser is connected via CDP.

        Returns:
            True if connected to an existing browser via CDP
            (Chrome DevTools Protocol), False if this is a managed
            browser instance.
        """
        ...


class AIInterpreterProtocol(Protocol):
    """Protocol for AI-based page interpretation.

    Implementations of this protocol analyze screenshots to determine
    the current state of a subscription cancellation flow.
    """

    async def interpret(self, screenshot: bytes) -> AIInterpretation:
        """Interpret a page screenshot to determine its state.

        Args:
            screenshot: PNG image bytes of the page.

        Returns:
            An AIInterpretation containing the detected state,
            confidence level, reasoning, and suggested actions.
        """
        ...


class ServiceConfigProtocol(Protocol):
    """Protocol for service configuration objects.

    Implementations must provide at minimum a name property identifying
    the service.
    """

    @property
    def name(self) -> str:
        """Get the service name.

        Returns:
            The human-readable name of the service (e.g., "Netflix").
        """
        ...


class ServiceProtocol(Protocol):
    """Protocol for service-specific cancellation configurations.

    Each supported service (Netflix, Spotify, etc.) implements this
    protocol to provide service-specific settings and selectors.
    """

    @property
    def config(self) -> ServiceConfigProtocol:
        """Get the service configuration.

        Returns:
            Configuration object satisfying ServiceConfigProtocol.
        """
        ...

    @property
    def service_id(self) -> str:
        """Get the unique service identifier.

        Returns:
            A lowercase string identifier for the service (e.g., "netflix").
        """
        ...

    @property
    def entry_url(self) -> str:
        """Get the entry URL for the cancellation flow.

        Returns:
            The URL where the cancellation process begins.
        """
        ...

    @property
    def selectors(self) -> Any:
        """Get the selectors for UI elements.

        Returns:
            Object with selector attributes (e.g., .cancel_link, .decline_offer).
            Each attribute is a SelectorConfig with css and aria fields.
        """
        ...
