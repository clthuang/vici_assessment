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
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    pass


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


class ActionType(Enum):
    """Types of browser actions that can be executed.

    Used by BrowserAction to specify what kind of action to perform.
    """

    CLICK = auto()
    FILL = auto()
    SELECT = auto()
    NAVIGATE = auto()
    WAIT = auto()
    SCREENSHOT = auto()


@dataclass
class BrowserElement:
    """Represents an element on a web page with accessibility information.

    Attributes:
        role: ARIA role of the element (e.g., "button", "link", "textbox").
        name: Accessible name of the element.
        selector: CSS selector to locate the element.
        value: Optional current value of the element (for inputs).
    """

    role: str
    name: str
    selector: str
    value: str | None = None

    def describe(self) -> str:
        """Return ARIA-format description of the element.

        Returns:
            String in format "ARIA: role=<role> name='<name>'"
        """
        return f"ARIA: role={self.role} name='{self.name}'"


@dataclass
class BrowserAction:
    """Represents a browser action to be executed.

    Attributes:
        action_type: The type of action (click, fill, etc.).
        selector: CSS selector for the target element.
        value: Optional value for fill/select actions.
        timeout: Optional timeout in milliseconds.
        fallback_role: Optional ARIA role tuple (role, name) for fallback.
    """

    action_type: ActionType
    selector: str
    value: str | None = None
    timeout: int | None = None
    fallback_role: tuple[str, str] | None = None


@dataclass
class PlannedAction:
    """Represents an AI-planned action with state context.

    Attributes:
        state: The detected page state.
        action: The browser action to execute.
        reasoning: Explanation for why this action was chosen.
        confidence: Confidence score between 0.0 and 1.0.
    """

    state: "State"
    action: BrowserAction
    reasoning: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate confidence is within valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


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


@dataclass(frozen=True)
class ActionRecord:
    """Record of a completed browser action.

    Attributes:
        action_type: The type of action performed (e.g., "click", "fill").
        target_description: Description of the target element.
        success: Whether the action succeeded.
        timestamp: ISO format timestamp of when the action occurred.
    """

    action_type: str
    target_description: str
    success: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with action, target, success, and time keys.
        """
        return {
            "action": self.action_type,
            "target": self.target_description,
            "success": self.success,
            "time": self.timestamp,
        }


@dataclass(frozen=True)
class ErrorRecord:
    """Record of an error that occurred during action execution.

    Attributes:
        action_type: The type of action that failed.
        error_type: Classification of the error (e.g., "ElementNotFound").
        error_message: Detailed error message.
        strategy_attempted: Description of the targeting strategy used.
        timestamp: ISO format timestamp of when the error occurred.
    """

    action_type: str
    error_type: str
    error_message: str
    strategy_attempted: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with action, error, message, strategy, and time keys.
        """
        return {
            "action": self.action_type,
            "error": self.error_type,
            "message": self.error_message,
            "strategy": self.strategy_attempted,
            "time": self.timestamp,
        }


@dataclass
class TargetStrategy:
    """Strategy for locating an element on a page.

    Supports multiple targeting methods: CSS selectors, ARIA attributes,
    text content, or screen coordinates.

    Attributes:
        method: The targeting method to use.
        css_selector: CSS selector (required if method is "css").
        aria_role: ARIA role (required if method is "aria").
        aria_name: ARIA name (optional, used with aria method).
        text_content: Text to search for (required if method is "text").
        coordinates: Screen coordinates (required if method is "coordinates").
    """

    method: Literal["css", "aria", "text", "coordinates"]
    css_selector: str | None = None
    aria_role: str | None = None
    aria_name: str | None = None
    text_content: str | None = None
    coordinates: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        """Validate that required fields are present for the specified method."""
        if self.method == "css" and not self.css_selector:
            raise ValueError("css_selector required when method is 'css'")
        if self.method == "aria" and not self.aria_role:
            raise ValueError("aria_role required when method is 'aria'")
        if self.method == "text" and not self.text_content:
            raise ValueError("text_content required when method is 'text'")
        if self.method == "coordinates" and not self.coordinates:
            raise ValueError("coordinates required when method is 'coordinates'")

    def describe(self) -> str:
        """Return a human-readable description of this targeting strategy.

        Returns:
            String describing the targeting strategy.
        """
        if self.method == "css":
            return f"CSS: {self.css_selector}"
        elif self.method == "aria":
            return f"ARIA: role={self.aria_role} name='{self.aria_name}'"
        elif self.method == "text":
            return f"Text: {self.text_content}"
        elif self.method == "coordinates":
            return f"Coordinates: {self.coordinates}"
        return f"Unknown method: {self.method}"


@dataclass
class ActionPlan:
    """Plan for executing a browser action with fallback strategies.

    Attributes:
        action_type: The type of action to perform (click, fill, select, wait, none).
        primary_target: The primary targeting strategy.
        fallback_targets: Alternative strategies if primary fails (max 3).
        value: Value for fill/select actions.
        reasoning: Explanation of why this action was planned.
        confidence: Confidence score between 0.0 and 1.0.
        expected_state: The expected state after action completes.
        continue_after: Whether to continue the agentic loop after this action.
        detected_state: Claude's assessment of the current page state.
    """

    action_type: Literal["click", "fill", "select", "wait", "none"]
    primary_target: TargetStrategy
    fallback_targets: list[TargetStrategy] = field(default_factory=list)
    value: str | None = None
    reasoning: str = ""
    confidence: float = 0.0
    expected_state: "State | None" = None
    continue_after: bool = True
    detected_state: "State | None" = None

    def __post_init__(self) -> None:
        """Validate action plan constraints."""
        if len(self.fallback_targets) > 3:
            raise ValueError("max 3 fallbacks")
        if not 0 <= self.confidence <= 1:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        if self.action_type in ("fill", "select") and not self.value:
            raise ValueError(
                f"value required for {self.action_type} actions"
            )

    def all_targets(self) -> list[TargetStrategy]:
        """Return all targeting strategies in order of preference.

        Returns:
            List containing primary target followed by fallback targets.
        """
        return [self.primary_target] + self.fallback_targets


@dataclass
class AgentContext:
    """Context information provided to the AI agent for decision making.

    Attributes:
        screenshot: PNG bytes of the current page.
        accessibility_tree: Text representation of the accessibility tree.
        html_snippet: Relevant HTML snippet from the page.
        url: Current page URL.
        visible_text: Visible text content on the page.
        previous_actions: History of completed actions.
        error_history: History of errors encountered.
        viewport_size: Browser viewport dimensions (width, height).
        scroll_position: Current scroll position (x, y).
    """

    screenshot: bytes
    accessibility_tree: str
    html_snippet: str
    url: str
    visible_text: str
    previous_actions: list[ActionRecord]
    error_history: list[ErrorRecord]
    viewport_size: tuple[int, int]
    scroll_position: tuple[int, int]

    def to_prompt_context(self) -> str:
        """Convert context to a formatted string for AI prompts.

        Returns:
            Formatted string with all context information.
        """
        def format_action(a: ActionRecord) -> str:
            status = "success" if a.success else "failed"
            return f"- {a.action_type} on {a.target_description}: {status}"

        actions_summary = "\n".join(
            format_action(a) for a in self.previous_actions
        ) or "None"

        errors_summary = "\n".join(
            f"- {e.action_type}: {e.error_type} - {e.error_message}"
            for e in self.error_history
        ) or "None"

        # Truncate visible_text to avoid token bloat (max 2000 chars)
        visible_text_truncated = (
            self.visible_text[:2000] + "..."
            if len(self.visible_text) > 2000
            else self.visible_text
        )

        return (
            f"URL: {self.url}\n"
            f"Viewport: {self.viewport_size[0]}x{self.viewport_size[1]}\n"
            f"Scroll: ({self.scroll_position[0]}, {self.scroll_position[1]})\n"
            f"VISIBLE TEXT:\n{visible_text_truncated}\n"
            f"ACCESSIBILITY TREE:\n{self.accessibility_tree}\n"
            f"HTML SNIPPET:\n{self.html_snippet}\n"
            f"PREVIOUS ACTIONS:\n{actions_summary}\n"
            f"ERRORS:\n{errors_summary}"
        )


@dataclass
class ExecutionResult:
    """Result of executing an action plan.

    Attributes:
        success: Whether the action succeeded.
        action_plan: The action plan that was executed.
        strategy_used: The targeting strategy that succeeded (if any).
        error: Error message if the action failed.
        screenshot_after: Screenshot taken after action execution.
        elapsed_ms: Time taken to execute the action in milliseconds.
    """

    success: bool
    action_plan: ActionPlan
    strategy_used: TargetStrategy | None = None
    error: str | None = None
    screenshot_after: bytes | None = None
    elapsed_ms: int = 0


@dataclass
class ValidationResult:
    """Result of validating the page state after an action.

    Attributes:
        success: Whether validation succeeded (actual matches expected).
        expected_state: The state that was expected.
        actual_state: The state that was observed.
        confidence: Confidence in the state detection.
        message: Human-readable description of the validation result.
    """

    success: bool
    expected_state: "State"
    actual_state: "State"
    confidence: float
    message: str


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
