"""Unit tests for Claude-DA configuration loading.

Covers defaults, env var overrides, missing required keys,
invalid numerics, and invalid enum values.
"""

import pytest

from claude_da.config import ClaudeDAConfig, load_config
from claude_da.exceptions import ConfigurationError


class TestDefaults:
    """When only ANTHROPIC_API_KEY is set, all other fields use defaults."""

    def test_defaults_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        # Clear any other env vars that could interfere
        for key in [
            "CLAUDE_DA_DB_PATH",
            "CLAUDE_DA_MODEL",
            "CLAUDE_DA_MAX_TURNS",
            "CLAUDE_DA_MAX_BUDGET_USD",
            "CLAUDE_DA_INPUT_MAX_CHARS",
            "CLAUDE_DA_LOG_OUTPUT",
            "CLAUDE_DA_LOG_FILE",
            "CLAUDE_DA_LOG_VERBOSE",
        ]:
            monkeypatch.delenv(key, raising=False)

        cfg = load_config()

        assert cfg.anthropic_api_key == "sk-test"
        assert cfg.db_path == "./demo.db"
        assert cfg.model == "claude-sonnet-4-5-20250929"
        assert cfg.max_turns == 10
        assert cfg.max_budget_usd == 0.50
        assert cfg.input_max_chars == 10000
        assert cfg.log_output == "stdout"
        assert cfg.log_file == "./claude-da-audit.jsonl"
        assert cfg.log_verbose is False

    def test_config_is_frozen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        cfg = load_config()
        with pytest.raises(AttributeError):
            cfg.model = "other-model"  # type: ignore[misc]


class TestEnvVarOverrides:
    """Each config field can be overridden via its environment variable."""

    def test_db_path_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_DB_PATH", "/tmp/custom.db")
        cfg = load_config()
        assert cfg.db_path == "/tmp/custom.db"

    def test_model_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_MODEL", "claude-haiku-4-5-20250929")
        cfg = load_config()
        assert cfg.model == "claude-haiku-4-5-20250929"

    def test_max_turns_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_MAX_TURNS", "25")
        cfg = load_config()
        assert cfg.max_turns == 25

    def test_max_budget_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_MAX_BUDGET_USD", "1.25")
        cfg = load_config()
        assert cfg.max_budget_usd == 1.25

    def test_input_max_chars_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_INPUT_MAX_CHARS", "5000")
        cfg = load_config()
        assert cfg.input_max_chars == 5000

    def test_log_output_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_LOG_OUTPUT", "file")
        cfg = load_config()
        assert cfg.log_output == "file"

    def test_log_output_both(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_LOG_OUTPUT", "both")
        cfg = load_config()
        assert cfg.log_output == "both"

    def test_log_file_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_LOG_FILE", "/var/log/audit.jsonl")
        cfg = load_config()
        assert cfg.log_file == "/var/log/audit.jsonl"

    def test_log_verbose_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_LOG_VERBOSE", "true")
        cfg = load_config()
        assert cfg.log_verbose is True

    def test_log_verbose_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_LOG_VERBOSE", "1")
        cfg = load_config()
        assert cfg.log_verbose is True


class TestValidationErrors:
    """Invalid or missing values raise ConfigurationError."""

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
            load_config()

    def test_invalid_max_turns_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_MAX_TURNS", "abc")
        with pytest.raises(ConfigurationError, match="CLAUDE_DA_MAX_TURNS"):
            load_config()

    def test_invalid_max_budget_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_MAX_BUDGET_USD", "not-a-number")
        with pytest.raises(ConfigurationError, match="CLAUDE_DA_MAX_BUDGET_USD"):
            load_config()

    def test_invalid_log_output_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_LOG_OUTPUT", "syslog")
        with pytest.raises(ConfigurationError, match="log_output"):
            load_config()

    def test_invalid_input_max_chars_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("CLAUDE_DA_INPUT_MAX_CHARS", "3.5")
        with pytest.raises(ConfigurationError, match="CLAUDE_DA_INPUT_MAX_CHARS"):
            load_config()


class TestConfigDataclass:
    """ClaudeDAConfig is a proper frozen dataclass."""

    def test_equality(self) -> None:
        a = ClaudeDAConfig(anthropic_api_key="k1")
        b = ClaudeDAConfig(anthropic_api_key="k1")
        assert a == b

    def test_inequality(self) -> None:
        a = ClaudeDAConfig(anthropic_api_key="k1")
        b = ClaudeDAConfig(anthropic_api_key="k2")
        assert a != b
