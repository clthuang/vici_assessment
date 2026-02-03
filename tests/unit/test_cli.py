"""Unit tests for CLI commands.

Tests cover:
- Service registry contains expected services
- cancel command exists on the Typer app
- Invalid service shows error message
- Exit codes for various scenarios
"""

import re
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from subterminator.cli.main import app
from subterminator.services.registry import get_available_services, get_service_by_id

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


class TestSupportedServices:
    """Tests for service registry."""

    def test_netflix_is_supported(self) -> None:
        """Netflix should be available in the registry."""
        service = get_service_by_id("netflix")
        assert service is not None
        assert service.available is True

    def test_available_services_returns_list(self) -> None:
        """get_available_services should return a list."""
        services = get_available_services()
        assert isinstance(services, list)

    def test_available_services_not_empty(self) -> None:
        """There should be at least one available service."""
        services = get_available_services()
        assert len(services) > 0


class TestCancelCommandExists:
    """Tests for verifying the cancel command exists."""

    def test_cancel_command_available_in_help(self) -> None:
        """The cancel command should be listed in the app help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # The cancel command should appear in the help output
        assert "cancel" in result.output.lower()

    def test_cancel_command_help_shows_description(self) -> None:
        """The cancel command should have a help description."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "cancel" in result.output.lower()

    def test_app_has_help(self) -> None:
        """App should have help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "cancel" in result.output.lower()


class TestCancelCommandValidation:
    """Tests for cancel command argument validation."""

    def test_invalid_service_shows_error(self) -> None:
        """Invalid service name should show error and exit with code 3."""
        result = runner.invoke(app, ["cancel", "--service", "invalid_service"])
        assert result.exit_code == 3
        assert "unknown service" in result.output.lower()
        assert "invalid_service" in result.output

    def test_invalid_service_shows_available_services(self) -> None:
        """Error message should list available services."""
        result = runner.invoke(app, ["cancel", "--service", "badservice"])
        assert result.exit_code == 3
        assert "available services" in result.output.lower()
        assert "netflix" in result.output.lower()

    def test_service_name_case_insensitive(self) -> None:
        """Service name validation should be case insensitive."""
        # Both should fail with the same error type (unknown)
        result_lower = runner.invoke(app, ["cancel", "--service", "badservice"])
        result_upper = runner.invoke(app, ["cancel", "--service", "BADSERVICE"])
        assert result_lower.exit_code == result_upper.exit_code


class TestCancelCommandOptions:
    """Tests for cancel command options."""

    @patch("subterminator.cli.main.ConfigLoader")
    @patch("subterminator.cli.main.CancellationEngine")
    @patch("subterminator.cli.main.PlaywrightBrowser")
    @patch("subterminator.cli.main.NetflixService")
    @patch("subterminator.cli.main.SessionLogger")
    @patch("subterminator.cli.main.HeuristicInterpreter")
    def test_dry_run_option_accepted(
        self,
        mock_heuristic: MagicMock,
        mock_session: MagicMock,
        mock_netflix: MagicMock,
        mock_browser: MagicMock,
        mock_engine: MagicMock,
        mock_config_loader: MagicMock,
    ) -> None:
        """--dry-run option should be accepted."""
        # Mock the config
        mock_config = MagicMock()
        mock_config.anthropic_api_key = None
        mock_config.output_dir = MagicMock()
        mock_config_loader.load.return_value = mock_config

        # Mock session to have screenshots_dir attribute
        mock_session_instance = MagicMock()
        mock_session_instance.session_dir = MagicMock()
        mock_session.return_value = mock_session_instance

        # Mock engine run to return successful result
        from subterminator.core.protocols import CancellationResult, State
        mock_result = CancellationResult(
            success=True,
            state=State.COMPLETE,
            message="Test completed",
        )
        mock_engine_instance = MagicMock()
        mock_engine_instance.run = MagicMock(return_value=mock_result)
        mock_engine.return_value = mock_engine_instance

        result = runner.invoke(app, ["cancel", "--service", "netflix", "--dry-run"])
        # Should not fail on the argument itself - check no error about the option
        has_dry_run_error = "dry-run" in result.output.lower()
        has_error = "error" in result.output.lower()
        assert not (has_dry_run_error and has_error)

    def test_help_shows_all_options(self) -> None:
        """Help should show all available options."""
        result = runner.invoke(app, ["cancel", "--help"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "--dry-run" in output
        assert "--target" in output
        assert "--headless" in output
        assert "--verbose" in output
        assert "--output-dir" in output
        assert "--service" in output
        assert "--no-input" in output
        assert "--plain" in output


class TestVersionFlag:
    """Tests for version flag."""

    def test_version_flag_shows_version(self) -> None:
        """--version should show the version number."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "SubTerminator" in result.output

    def test_short_version_flag(self) -> None:
        """-v should also show the version number."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "SubTerminator" in result.output


class TestNoArgs:
    """Tests for behavior with no arguments."""

    def test_no_args_shows_help(self) -> None:
        """Running with no arguments should show help text."""
        result = runner.invoke(app, [])
        # Typer with no_args_is_help=True exits with code 0 or 2 depending on version
        # The important thing is that help is shown
        assert "Usage" in result.output or "usage" in result.output
        assert "cancel" in result.output.lower()
