"""Configuration management for SubTerminator."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from subterminator.utils.exceptions import ConfigurationError


@dataclass
class AppConfig:
    """Application configuration."""

    anthropic_api_key: str | None
    output_dir: Path
    page_timeout: int = 30000  # ms
    element_timeout: int = 10000  # ms
    auth_timeout: int = 300000  # 5 minutes for human auth
    confirm_timeout: int = 120000  # 2 minutes for confirmation
    max_retries: int = 3
    max_transitions: int = 10  # Prevent infinite loops


class ConfigLoader:
    """Loads configuration from environment variables."""

    @staticmethod
    def load() -> AppConfig:
        """Load configuration from environment.

        Raises:
            ConfigurationError: If required configuration is missing or invalid.
        """
        load_dotenv()  # Load .env file if present

        output_dir = Path(os.environ.get("SUBTERMINATOR_OUTPUT", "./output"))

        return AppConfig(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            output_dir=output_dir,
            page_timeout=ConfigLoader._get_int_env(
                "SUBTERMINATOR_PAGE_TIMEOUT", 30000
            ),
            element_timeout=ConfigLoader._get_int_env(
                "SUBTERMINATOR_ELEMENT_TIMEOUT", 10000
            ),
            auth_timeout=ConfigLoader._get_int_env(
                "SUBTERMINATOR_AUTH_TIMEOUT", 300000
            ),
            confirm_timeout=ConfigLoader._get_int_env(
                "SUBTERMINATOR_CONFIRM_TIMEOUT", 120000
            ),
            max_retries=ConfigLoader._get_int_env("SUBTERMINATOR_MAX_RETRIES", 3),
            max_transitions=ConfigLoader._get_int_env(
                "SUBTERMINATOR_MAX_TRANSITIONS", 10
            ),
        )

    @staticmethod
    def _get_int_env(name: str, default: int) -> int:
        """Get an integer environment variable.

        Args:
            name: The environment variable name.
            default: The default value if not set.

        Returns:
            The integer value.

        Raises:
            ConfigurationError: If the value is not a valid integer.
        """
        value = os.environ.get(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid value for {name}: '{value}' is not a valid integer"
            ) from e
