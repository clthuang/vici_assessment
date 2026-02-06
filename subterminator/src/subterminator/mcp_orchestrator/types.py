"""Type definitions for the MCP orchestrator.

This module defines the core data types used throughout the orchestration:
- TaskResult: Outcome of an orchestration run
- ToolCall: Represents a single tool invocation
- NormalizedSnapshot: Parsed browser state
- Type aliases for predicate functions
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass

# Task completion reasons
TaskReason = Literal[
    "completed",  # Task completed successfully
    "human_rejected",  # Human rejected a checkpoint
    "max_turns_exceeded",  # Hit maximum turn limit
    "llm_no_action",  # LLM failed to call tools 3 times
    "llm_error",  # LLM API error
    "mcp_error",  # MCP connection or tool error
    "verification_failed",  # Success indicators not found
]


@dataclass
class TaskResult:
    """Result of an orchestration run.

    Attributes:
        success: Whether the task completed successfully
        verified: Whether success was verified via indicators
        reason: Why the task ended
        turns: Number of turns executed
        final_url: Last URL visited (optional)
        error: Error message if failed (optional)
    """

    success: bool
    verified: bool
    reason: TaskReason
    turns: int
    final_url: str | None = None
    error: str | None = None


@dataclass
class ToolCall:
    """Represents a single tool invocation from the LLM.

    Attributes:
        id: Unique identifier for this tool call
        name: Name of the tool to invoke
        args: Arguments to pass to the tool (uses 'args' per LangChain convention)

    Note:
        Uses 'args' instead of 'arguments' to match LangChain's tool_calls format.
    """

    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedSnapshot:
    """Normalized browser snapshot parsed from Playwright MCP output.

    Playwright MCP returns markdown-formatted text. This dataclass
    holds the extracted structured data.

    Attributes:
        url: Current page URL
        title: Current page title
        content: Page content (accessibility tree in YAML format)
        screenshot_path: Path to screenshot file if captured (optional)
    """

    url: str
    title: str
    content: str
    screenshot_path: str | None = None


# Type aliases for predicate functions

# Snapshot-only predicate (for success/failure indicators)
SnapshotPredicate = Callable[[NormalizedSnapshot], bool]

# Tool+Snapshot predicate (for checkpoint conditions - checks both tool AND snapshot)
CheckpointPredicate = Callable[[ToolCall, NormalizedSnapshot], bool]
