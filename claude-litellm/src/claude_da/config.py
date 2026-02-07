"""Claude-DA configuration.

Loads configuration from environment variables with sensible defaults.
A .env file in the working directory is loaded automatically if present.
All validation happens eagerly at startup so misconfigurations fail fast.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from claude_da.exceptions import ConfigurationError

load_dotenv()

_VALID_LOG_OUTPUTS = frozenset({"stdout", "file", "both"})


@dataclass(frozen=True)
class ClaudeDAConfig:
    """Immutable application configuration.

    Attributes:
        anthropic_api_key: Anthropic API key (required).
        db_path: Path to the SQLite demo database.
        model: Claude model identifier.
        max_turns: Maximum agent conversation turns.
        max_budget_usd: Maximum spend per session in USD.
        input_max_chars: Maximum user input length.
        log_output: Where to write audit logs ("stdout", "file", or "both").
        log_file: Path for JSONL audit log file.
        log_verbose: Include full query results in audit output.
    """

    anthropic_api_key: str
    db_path: str = "./demo.db"
    model: str = "claude-sonnet-4-5-20250929"
    max_turns: int = 10
    max_budget_usd: float = 0.50
    input_max_chars: int = 10000
    log_output: str = "stdout"
    log_file: str = "./claude-da-audit.jsonl"
    log_verbose: bool = False


def _get_int_env(name: str, default: int) -> int:
    """Read an integer from an environment variable.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset.

    Returns:
        The parsed integer value.

    Raises:
        ConfigurationError: If the value is set but not a valid integer.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from None


def _get_float_env(name: str, default: float) -> float:
    """Read a float from an environment variable.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset.

    Returns:
        The parsed float value.

    Raises:
        ConfigurationError: If the value is set but not a valid float.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be a number, got {raw!r}") from None


def _get_bool_env(name: str, default: bool) -> bool:
    """Read a boolean from an environment variable.

    Truthy values: "true", "1", "yes" (case-insensitive).
    Everything else is treated as False.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset.

    Returns:
        The parsed boolean value.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in {"true", "1", "yes"}


def load_config() -> ClaudeDAConfig:
    """Build a ClaudeDAConfig from environment variables.

    Environment variables:
        ANTHROPIC_API_KEY (required)
        CLAUDE_DA_DB_PATH
        CLAUDE_DA_MODEL
        CLAUDE_DA_MAX_TURNS
        CLAUDE_DA_MAX_BUDGET_USD
        CLAUDE_DA_INPUT_MAX_CHARS
        CLAUDE_DA_LOG_OUTPUT
        CLAUDE_DA_LOG_FILE
        CLAUDE_DA_LOG_VERBOSE

    Returns:
        A validated, frozen ClaudeDAConfig instance.

    Raises:
        ConfigurationError: On missing required keys, bad numeric values,
            or invalid enum values.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ConfigurationError("ANTHROPIC_API_KEY environment variable is required")

    log_output = os.environ.get("CLAUDE_DA_LOG_OUTPUT", "stdout")
    if log_output not in _VALID_LOG_OUTPUTS:
        raise ConfigurationError(
            f"log_output must be one of {sorted(_VALID_LOG_OUTPUTS)}, "
            f"got {log_output!r}"
        )

    return ClaudeDAConfig(
        anthropic_api_key=api_key,
        db_path=os.environ.get("CLAUDE_DA_DB_PATH", "./demo.db"),
        model=os.environ.get("CLAUDE_DA_MODEL", "claude-sonnet-4-5-20250929"),
        max_turns=_get_int_env("CLAUDE_DA_MAX_TURNS", 10),
        max_budget_usd=_get_float_env("CLAUDE_DA_MAX_BUDGET_USD", 0.50),
        input_max_chars=_get_int_env("CLAUDE_DA_INPUT_MAX_CHARS", 10000),
        log_output=log_output,
        log_file=os.environ.get("CLAUDE_DA_LOG_FILE", "./claude-da-audit.jsonl"),
        log_verbose=_get_bool_env("CLAUDE_DA_LOG_VERBOSE", False),
    )
