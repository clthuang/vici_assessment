"""Tests for configuration loading."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from subterminator.utils.config import AppConfig, ConfigLoader
from subterminator.utils.exceptions import ConfigurationError


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_app_config_with_all_values(self) -> None:
        """Test AppConfig with all values specified."""
        config = AppConfig(
            anthropic_api_key="test-key",
            output_dir=Path("/tmp/output"),
            page_timeout=5000,
            element_timeout=2000,
            auth_timeout=60000,
            confirm_timeout=30000,
            max_retries=5,
            max_transitions=20,
        )

        assert config.anthropic_api_key == "test-key"
        assert config.output_dir == Path("/tmp/output")
        assert config.page_timeout == 5000
        assert config.element_timeout == 2000
        assert config.auth_timeout == 60000
        assert config.confirm_timeout == 30000
        assert config.max_retries == 5
        assert config.max_transitions == 20

    def test_app_config_with_defaults(self) -> None:
        """Test AppConfig with default values."""
        config = AppConfig(
            anthropic_api_key=None,
            output_dir=Path("./output"),
        )

        assert config.anthropic_api_key is None
        assert config.output_dir == Path("./output")
        assert config.page_timeout == 30000
        assert config.element_timeout == 10000
        assert config.auth_timeout == 300000
        assert config.confirm_timeout == 120000
        assert config.max_retries == 3
        assert config.max_transitions == 10

    def test_app_config_with_none_api_key(self) -> None:
        """Test AppConfig allows None for API key."""
        config = AppConfig(
            anthropic_api_key=None,
            output_dir=Path("./output"),
        )
        assert config.anthropic_api_key is None


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_with_default_values(self) -> None:
        """Test loading config with default values when env vars not set."""
        with patch("subterminator.utils.config.load_dotenv"):  # Skip .env file
            with patch.dict(os.environ, {}, clear=True):
                config = ConfigLoader.load()

        assert config.anthropic_api_key is None
        assert config.output_dir == Path("./output")
        assert config.page_timeout == 30000
        assert config.element_timeout == 10000
        assert config.auth_timeout == 300000
        assert config.confirm_timeout == 120000
        assert config.max_retries == 3
        assert config.max_transitions == 10

    def test_load_with_anthropic_api_key(self) -> None:
        """Test loading config with ANTHROPIC_API_KEY set."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}, clear=True):
            config = ConfigLoader.load()

        assert config.anthropic_api_key == "sk-test-key"

    def test_load_with_custom_output_dir(self) -> None:
        """Test loading config with custom output directory."""
        with patch.dict(
            os.environ,
            {"SUBTERMINATOR_OUTPUT": "/custom/output/path"},
            clear=True,
        ):
            config = ConfigLoader.load()

        assert config.output_dir == Path("/custom/output/path")

    def test_load_with_custom_timeouts(self) -> None:
        """Test loading config with custom timeout values."""
        env_vars = {
            "SUBTERMINATOR_PAGE_TIMEOUT": "5000",
            "SUBTERMINATOR_ELEMENT_TIMEOUT": "2000",
            "SUBTERMINATOR_AUTH_TIMEOUT": "60000",
            "SUBTERMINATOR_CONFIRM_TIMEOUT": "30000",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ConfigLoader.load()

        assert config.page_timeout == 5000
        assert config.element_timeout == 2000
        assert config.auth_timeout == 60000
        assert config.confirm_timeout == 30000

    def test_load_with_custom_retries_and_transitions(self) -> None:
        """Test loading config with custom retry and transition limits."""
        env_vars = {
            "SUBTERMINATOR_MAX_RETRIES": "5",
            "SUBTERMINATOR_MAX_TRANSITIONS": "20",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ConfigLoader.load()

        assert config.max_retries == 5
        assert config.max_transitions == 20

    def test_load_with_all_env_vars(self) -> None:
        """Test loading config with all environment variables set."""
        env_vars = {
            "ANTHROPIC_API_KEY": "sk-full-test",
            "SUBTERMINATOR_OUTPUT": "/tmp/subterminator",
            "SUBTERMINATOR_PAGE_TIMEOUT": "15000",
            "SUBTERMINATOR_ELEMENT_TIMEOUT": "5000",
            "SUBTERMINATOR_AUTH_TIMEOUT": "120000",
            "SUBTERMINATOR_CONFIRM_TIMEOUT": "60000",
            "SUBTERMINATOR_MAX_RETRIES": "10",
            "SUBTERMINATOR_MAX_TRANSITIONS": "50",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ConfigLoader.load()

        assert config.anthropic_api_key == "sk-full-test"
        assert config.output_dir == Path("/tmp/subterminator")
        assert config.page_timeout == 15000
        assert config.element_timeout == 5000
        assert config.auth_timeout == 120000
        assert config.confirm_timeout == 60000
        assert config.max_retries == 10
        assert config.max_transitions == 50

    def test_load_with_invalid_timeout_raises_error(self) -> None:
        """Test that invalid timeout value raises ConfigurationError."""
        with patch.dict(
            os.environ,
            {"SUBTERMINATOR_PAGE_TIMEOUT": "not-a-number"},
            clear=True,
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigLoader.load()
            assert "SUBTERMINATOR_PAGE_TIMEOUT" in str(exc_info.value)

    def test_load_with_invalid_retries_raises_error(self) -> None:
        """Test that invalid max_retries value raises ConfigurationError."""
        with patch.dict(
            os.environ,
            {"SUBTERMINATOR_MAX_RETRIES": "invalid"},
            clear=True,
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigLoader.load()
            assert "SUBTERMINATOR_MAX_RETRIES" in str(exc_info.value)
