"""MCP Orchestrator - AI-driven browser automation via MCP tools.

This package provides AI-powered browser orchestration using existing
MCP (Model Context Protocol) servers like Playwright MCP.
"""

__version__ = "0.1.0"

from .checkpoint import CheckpointHandler
from .exceptions import (
    CheckpointRejectedError,
    ConfigurationError,
    LLMError,
    MCPConnectionError,
    MCPToolError,
    OrchestratorError,
    ServiceNotFoundError,
    SnapshotValidationError,
)
from .llm_client import LLMClient
from .mcp_client import MCPClient
from .services import ServiceConfig, ServiceRegistry, default_registry
from .snapshot import normalize_snapshot
from .task_runner import TaskRunner
from .types import (
    CheckpointPredicate,
    NormalizedSnapshot,
    SnapshotPredicate,
    TaskReason,
    TaskResult,
    ToolCall,
)

__all__ = [
    # Types
    "TaskReason",
    "TaskResult",
    "ToolCall",
    "NormalizedSnapshot",
    "SnapshotPredicate",
    "CheckpointPredicate",
    # Exceptions
    "OrchestratorError",
    "MCPConnectionError",
    "MCPToolError",
    "LLMError",
    "CheckpointRejectedError",
    "SnapshotValidationError",
    "ServiceNotFoundError",
    "ConfigurationError",
    # Clients
    "MCPClient",
    "LLMClient",
    # Components
    "CheckpointHandler",
    "TaskRunner",
    "normalize_snapshot",
    # Services
    "ServiceConfig",
    "ServiceRegistry",
    "default_registry",
]
