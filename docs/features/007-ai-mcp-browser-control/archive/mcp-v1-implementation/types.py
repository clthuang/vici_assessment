"""Data types for MCP (Model Context Protocol) style AI-led browser control.

This module defines the core data structures used throughout the MCP system:
- BoundingBox, ElementInfo: Element representation
- PageInfo, ViewportInfo, Snapshot: Page state representation
- Message, ToolCall, AIResponse: AI conversation types
- ToolResult, TaskResult, CompletionCriteria: Execution result types
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Literal
from uuid import uuid4


@dataclass
class BoundingBox:
    """Element position in viewport coordinates."""

    x: int
    y: int
    width: int
    height: int

    def center(self) -> tuple[int, int]:
        """Return center point of bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class ElementInfo:
    """Element information for snapshots.

    Attributes:
        ref: Reference assigned by registry (e.g., "@e7").
        role: ARIA role of the element.
        name: Accessible name of the element.
        state: List of state indicators (e.g., ["visible", "enabled"]).
        bbox: Bounding box in viewport coordinates.
        value: Current value for input elements.
        level: Heading level (1-6) for heading elements.
        selector: CSS selector for action execution (not serialized to AI).
        children: List of child element refs.
    """

    ref: str = ""
    role: str = ""
    name: str = ""
    state: list[str] = field(default_factory=list)
    bbox: BoundingBox | None = None
    value: str | None = None
    level: int | None = None
    selector: str | None = None
    children: list[str] = field(default_factory=list)


@dataclass
class PageInfo:
    """Page metadata."""

    url: str
    title: str


@dataclass
class ViewportInfo:
    """Viewport dimensions and scroll position."""

    width: int
    height: int
    scroll_x: int
    scroll_y: int


@dataclass
class Snapshot:
    """Complete page state at a point in time.

    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        timestamp: ISO 8601 timestamp of when the snapshot was taken.
        elements: List of elements extracted from the accessibility tree.
        focused: Reference of the currently focused element.
        page: Page metadata (URL and title).
        screenshot: Base64-encoded PNG screenshot.
        viewport: Viewport dimensions and scroll position.
    """

    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    elements: list[ElementInfo] = field(default_factory=list)
    focused: str | None = None
    page: PageInfo = field(default_factory=lambda: PageInfo("", ""))
    screenshot: str = ""
    viewport: ViewportInfo = field(default_factory=lambda: ViewportInfo(1024, 768, 0, 0))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "elements": [
                {
                    "ref": e.ref,
                    "role": e.role,
                    "name": e.name,
                    "state": e.state,
                    "bbox": (
                        {
                            "x": e.bbox.x,
                            "y": e.bbox.y,
                            "width": e.bbox.width,
                            "height": e.bbox.height,
                        }
                        if e.bbox
                        else None
                    ),
                    "value": e.value,
                    "level": e.level,
                    "children": e.children if e.children else None,
                }
                for e in self.elements
            ],
            "focused": self.focused,
            "page": {"url": self.page.url, "title": self.page.title},
            "screenshot": self.screenshot,
            "viewport": {
                "width": self.viewport.width,
                "height": self.viewport.height,
                "scroll_x": self.viewport.scroll_x,
                "scroll_y": self.viewport.scroll_y,
            },
        }


@dataclass
class Message:
    """A message in the AI conversation.

    Attributes:
        role: The role of the message sender.
        content: The text content of the message.
        tool_calls: List of tool calls made by the assistant.
        tool_call_id: ID of the tool call this message responds to.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list["ToolCall"] | None = None
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    """A tool invocation from the AI.

    Attributes:
        id: Unique identifier for this tool call.
        name: Name of the tool to invoke.
        arguments: Arguments to pass to the tool.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AIResponse:
    """Response from AI client.

    Attributes:
        content: Text content of the response.
        tool_calls: List of tool calls requested by the AI.
        stop_reason: Reason why the AI stopped generating.
    """

    content: str
    tool_calls: list[ToolCall]
    stop_reason: Literal["end_turn", "tool_use", "max_tokens"]


# Type alias for error codes used in tool results
ErrorCode = Literal[
    "ref_invalid",
    "element_disabled",
    "element_obscured",
    "element_not_visible",
    "action_failed",
    "timeout",
    "human_rejected",
    "invalid_params",
]


@dataclass
class ToolResult:
    """Result of a tool execution.

    Attributes:
        success: Whether the tool execution succeeded.
        snapshot: Updated page snapshot after the action.
        error: Error code if the action failed.
        message: Human-readable message with details.
    """

    success: bool
    snapshot: Snapshot | None = None
    error: ErrorCode | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for AI.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        result: dict[str, Any] = {"success": self.success}
        if self.snapshot:
            result["snapshot"] = self.snapshot.to_dict()
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class TaskResult:
    """Final result of a task execution.

    Attributes:
        success: Whether the task completed successfully.
        reason: Explanation of the outcome.
        turns: Number of conversation turns used.
        final_snapshot: Last snapshot before task completion.
    """

    success: bool
    reason: str
    turns: int
    final_snapshot: Snapshot | None = None


@dataclass
class CompletionCriteria:
    """Service-specific completion verification rules.

    Attributes:
        success_indicators: Functions that return True if success conditions are met.
        failure_indicators: Functions that return True if failure conditions are met.
    """

    success_indicators: list[Callable[[Snapshot], bool]] = field(default_factory=list)
    failure_indicators: list[Callable[[Snapshot], bool]] = field(default_factory=list)
