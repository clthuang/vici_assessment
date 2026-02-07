"""Claude-DA exception hierarchy.

All application-specific exceptions inherit from ClaudeDAError.
Exceptions that map to HTTP-like failures carry status_code and error_code
class attributes for uniform error handling downstream.
"""


class ClaudeDAError(Exception):
    """Base exception for Claude-DA."""


class ConfigurationError(ClaudeDAError):
    """Invalid or missing configuration. Raised at startup."""


class InputValidationError(ClaudeDAError):
    """User input failed validation (e.g., too long)."""

    status_code: int = 400
    error_code: str = "input_too_long"


class AgentTimeoutError(ClaudeDAError):
    """Agent SDK session exceeded timeout."""

    status_code: int = 504
    error_code: str = "agent_timeout"


class RateLimitError(ClaudeDAError):
    """Anthropic API rate limited."""

    status_code: int = 429
    error_code: str = "rate_limited"


class DatabaseUnavailableError(ClaudeDAError):
    """MCP database server unreachable."""

    status_code: int = 503
    error_code: str = "database_unavailable"
