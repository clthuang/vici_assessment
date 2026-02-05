"""MCP (Model Context Protocol) style AI-led browser control."""

from subterminator.mcp.types import (
    AIResponse,
    BoundingBox,
    CompletionCriteria,
    ElementInfo,
    ErrorCode,
    Message,
    PageInfo,
    Snapshot,
    TaskResult,
    ToolCall,
    ToolResult,
    ViewportInfo,
)
from subterminator.mcp.exceptions import (
    ElementDisabledError,
    ElementObscuredError,
    InvalidParamsError,
    MCPError,
    MCPTimeoutError,
    RefInvalidError,
)

__all__ = [
    # Types
    "AIResponse",
    "BoundingBox",
    "CompletionCriteria",
    "ElementInfo",
    "ErrorCode",
    "Message",
    "PageInfo",
    "Snapshot",
    "TaskResult",
    "ToolCall",
    "ToolResult",
    "ViewportInfo",
    # Exceptions
    "ElementDisabledError",
    "ElementObscuredError",
    "InvalidParamsError",
    "MCPError",
    "MCPTimeoutError",
    "RefInvalidError",
]
