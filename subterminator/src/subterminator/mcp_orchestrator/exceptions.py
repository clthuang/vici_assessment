"""Exception hierarchy for MCP orchestrator.

All orchestrator exceptions inherit from OrchestratorError, which itself
inherits from SubTerminatorError for consistent exception handling.
"""

from subterminator.utils.exceptions import ConfigurationError, SubTerminatorError

# Re-export ConfigurationError for convenience
__all__ = [
    "ConfigurationError",
    "OrchestratorError",
    "MCPConnectionError",
    "MCPToolError",
    "LLMError",
    "CheckpointRejectedError",
    "SnapshotValidationError",
    "ServiceNotFoundError",
]


class OrchestratorError(SubTerminatorError):
    """Base exception for all MCP orchestration errors."""


class MCPConnectionError(OrchestratorError):
    """MCP server connection failure.

    Raised when:
    - Cannot start MCP subprocess
    - Connection to MCP server lost
    - MCP server crashes
    """


class MCPToolError(OrchestratorError):
    """MCP tool execution failure.

    Raised when an MCP tool returns an error. This is different from
    MCPConnectionError - the connection is fine, but the tool failed.
    """


class LLMError(OrchestratorError):
    """LLM API failure.

    Raised when:
    - API call fails after retries
    - Timeout exceeded
    - Invalid response format
    """


class CheckpointRejectedError(OrchestratorError):
    """Human rejected a checkpoint approval request.

    This is not necessarily an error condition - it means the human
    chose to stop the operation at a checkpoint.
    """


class SnapshotValidationError(OrchestratorError):
    """Snapshot parsing failure.

    Raised when normalize_snapshot() cannot parse the MCP output.
    Usually indicates unexpected output format from Playwright MCP.
    """


class ServiceNotFoundError(OrchestratorError):
    """Unknown service requested.

    Raised when ServiceRegistry.get() is called with an unregistered
    service name.
    """
