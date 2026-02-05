"""Integration tests for cancel command with interactive service selection."""

import re
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from subterminator.cli.main import app

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestCancelInteractiveMode:
    """Tests for interactive mode behavior."""

    @patch("subterminator.cli.main.is_interactive")
    @patch("subterminator.cli.main.select_service")
    def test_cancel_interactive_mode(
        self, mock_select: MagicMock, mock_interactive: MagicMock
    ) -> None:
        """Shows menu when no --service flag and TTY."""
        mock_interactive.return_value = True
        mock_select.return_value = "netflix"
        runner.invoke(app, ["cancel"])
        mock_select.assert_called_once()

    @patch("subterminator.cli.main.is_interactive")
    @patch("subterminator.cli.main.select_service")
    def test_cancel_user_cancels(
        self, mock_select: MagicMock, mock_interactive: MagicMock
    ) -> None:
        """Exit code 2 when user presses Ctrl+C."""
        mock_interactive.return_value = True
        mock_select.return_value = None
        result = runner.invoke(app, ["cancel"])
        assert result.exit_code == 2
        assert "cancelled" in result.output.lower()


class TestCancelNonInteractiveMode:
    """Tests for non-interactive mode behavior."""

    @patch("subterminator.cli.main.is_interactive")
    def test_cancel_non_interactive_with_service(
        self, mock_interactive: MagicMock
    ) -> None:
        """Bypasses menu with --service flag."""
        mock_interactive.return_value = False
        result = runner.invoke(app, ["cancel", "--service", "netflix"])
        assert "--service required" not in result.output

    @patch("subterminator.cli.main.is_interactive")
    def test_cancel_non_interactive_missing_service(
        self, mock_interactive: MagicMock
    ) -> None:
        """Errors with exit 3 when no --service in non-TTY."""
        mock_interactive.return_value = False
        result = runner.invoke(app, ["cancel"])
        assert result.exit_code == 3
        assert "--service required" in result.output.lower()


class TestCancelServiceValidation:
    """Tests for service name validation."""

    def test_cancel_unknown_service(self) -> None:
        """Shows error with suggestion for typo."""
        result = runner.invoke(app, ["cancel", "--service", "netflixx"])
        assert result.exit_code == 3
        assert "unknown service" in result.output.lower()
        assert "did you mean" in result.output.lower()
        assert "netflix" in result.output.lower()

    def test_cancel_unavailable_service(self) -> None:
        """Shows error for 'coming soon' services."""
        result = runner.invoke(app, ["cancel", "--service", "spotify"])
        assert result.exit_code == 3
        assert "not yet available" in result.output.lower()


class TestCancelFlags:
    """Tests for command flags."""

    @patch("subterminator.cli.main.is_interactive")
    @patch("subterminator.cli.main.select_service")
    def test_cancel_plain_flag(
        self, mock_select: MagicMock, mock_interactive: MagicMock
    ) -> None:
        """Passes --plain to select_service."""
        mock_interactive.return_value = True
        mock_select.return_value = "netflix"
        runner.invoke(app, ["cancel", "--plain"])
        mock_select.assert_called_once_with(plain=True)

    @patch("subterminator.cli.main.is_interactive")
    def test_cancel_no_input_flag(self, mock_interactive: MagicMock) -> None:
        """Forces non-interactive with --no-input."""
        mock_interactive.return_value = False
        result = runner.invoke(app, ["cancel", "--no-input"])
        assert result.exit_code == 3
        assert "--service required" in result.output.lower()


class TestCLIBrowserFlags:
    """Tests for CLI browser connection flags (--profile-dir)."""

    def test_help_shows_profile_dir_flag(self) -> None:
        """--help should show --profile-dir flag."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--profile-dir" in strip_ansi(result.output)

    def test_help_shows_model_flag(self) -> None:
        """--help should show --model flag."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--model" in strip_ansi(result.output)

    def test_help_shows_max_turns_flag(self) -> None:
        """--help should show --max-turns flag."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--max-turns" in strip_ansi(result.output)

    def test_help_shows_no_checkpoint_flag(self) -> None:
        """--help should show --no-checkpoint flag."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--no-checkpoint" in strip_ansi(result.output)
