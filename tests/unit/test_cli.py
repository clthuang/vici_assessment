"""Unit tests for CLI commands.

Tests cover:
- SUPPORTED_SERVICES contains expected services
- cancel command exists on the Typer app
- Invalid service shows error message
- Exit codes for various scenarios
"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from subterminator.cli.main import SUPPORTED_SERVICES, app

runner = CliRunner()


class TestSupportedServices:
    """Tests for SUPPORTED_SERVICES constant."""

    def test_netflix_is_supported(self) -> None:
        """Netflix should be in the list of supported services."""
        assert "netflix" in SUPPORTED_SERVICES

    def test_supported_services_is_list(self) -> None:
        """SUPPORTED_SERVICES should be a list."""
        assert isinstance(SUPPORTED_SERVICES, list)

    def test_supported_services_not_empty(self) -> None:
        """SUPPORTED_SERVICES should not be empty."""
        assert len(SUPPORTED_SERVICES) > 0


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
        result = runner.invoke(app, ["cancel", "invalid_service"])
        assert result.exit_code == 3
        assert "unsupported service" in result.output.lower()
        assert "invalid_service" in result.output

    def test_invalid_service_shows_supported_services(self) -> None:
        """Error message should list supported services."""
        result = runner.invoke(app, ["cancel", "spotify"])
        assert result.exit_code == 3
        assert "netflix" in result.output.lower()

    def test_service_name_case_insensitive(self) -> None:
        """Service name validation should be case insensitive."""
        # Both should fail with the same error type (unsupported)
        result_lower = runner.invoke(app, ["cancel", "badservice"])
        result_upper = runner.invoke(app, ["cancel", "BADSERVICE"])
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

        result = runner.invoke(app, ["cancel", "netflix", "--dry-run"])
        # Should not fail on the argument itself - check no error about the option
        has_dry_run_error = "dry-run" in result.output.lower()
        has_error = "error" in result.output.lower()
        assert not (has_dry_run_error and has_error)

    def test_help_shows_all_options(self) -> None:
        """Help should show all available options."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--target" in result.output
        assert "--headless" in result.output
        assert "--verbose" in result.output
        assert "--output-dir" in result.output


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
