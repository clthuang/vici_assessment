"""Integration tests for cancel command with interactive service selection."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from subterminator.cli.main import app

runner = CliRunner()


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
    """Tests for CLI browser connection flags (--cdp-url, --profile-dir)."""

    def test_help_shows_cdp_url_flag(self) -> None:
        """--help should show --cdp-url flag."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--cdp-url" in result.output

    def test_help_shows_profile_dir_flag(self) -> None:
        """--help should show --profile-dir flag."""
        result = runner.invoke(app, ["cancel", "--help"])
        assert result.exit_code == 0
        assert "--profile-dir" in result.output

    def test_mutual_exclusivity_error(self) -> None:
        """Should error when both --cdp-url and --profile-dir provided."""
        result = runner.invoke(
            app,
            [
                "cancel",
                "--service",
                "netflix",
                "--cdp-url",
                "http://localhost:9222",
                "--profile-dir",
                "/tmp/profile",
            ],
        )
        assert result.exit_code != 0
        assert "cannot be used together" in result.output.lower()

    @patch("subterminator.cli.main.CancellationEngine")
    @patch("subterminator.cli.main.SessionLogger")
    @patch("subterminator.cli.main.HeuristicInterpreter")
    @patch("subterminator.cli.main.create_service")
    @patch("subterminator.cli.main.PlaywrightBrowser")
    @patch("subterminator.cli.main.ConfigLoader")
    def test_cdp_url_parsed_and_passed_to_browser(
        self,
        mock_config_loader: MagicMock,
        mock_browser_class: MagicMock,
        mock_create_service: MagicMock,
        mock_heuristic: MagicMock,
        mock_session: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """--cdp-url should be parsed and passed to PlaywrightBrowser."""
        from pathlib import Path

        # Setup mock config
        mock_config = MagicMock()
        mock_config.anthropic_api_key = None
        mock_config.output_dir = Path("/tmp")
        mock_config_loader.load.return_value = mock_config

        # Make browser mock return a mock that has the methods we need
        mock_browser_instance = MagicMock()
        mock_browser_class.return_value = mock_browser_instance

        # Run the command (it will fail somewhere but we just need to verify args)
        runner.invoke(
            app,
            ["cancel", "--service", "netflix", "--cdp-url", "http://localhost:9222"],
        )

        # Verify PlaywrightBrowser was called with cdp_url
        mock_browser_class.assert_called_once()
        call_kwargs = mock_browser_class.call_args.kwargs
        assert call_kwargs.get("cdp_url") == "http://localhost:9222"
        assert call_kwargs.get("user_data_dir") is None

    @patch("subterminator.cli.main.CancellationEngine")
    @patch("subterminator.cli.main.SessionLogger")
    @patch("subterminator.cli.main.HeuristicInterpreter")
    @patch("subterminator.cli.main.create_service")
    @patch("subterminator.cli.main.PlaywrightBrowser")
    @patch("subterminator.cli.main.ConfigLoader")
    def test_profile_dir_parsed_and_passed_to_browser(
        self,
        mock_config_loader: MagicMock,
        mock_browser_class: MagicMock,
        mock_create_service: MagicMock,
        mock_heuristic: MagicMock,
        mock_session: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """--profile-dir should be parsed and passed to PlaywrightBrowser."""
        from pathlib import Path

        # Setup mock config
        mock_config = MagicMock()
        mock_config.anthropic_api_key = None
        mock_config.output_dir = Path("/tmp")
        mock_config_loader.load.return_value = mock_config

        # Make browser mock return a mock that has the methods we need
        mock_browser_instance = MagicMock()
        mock_browser_class.return_value = mock_browser_instance

        # Run the command
        runner.invoke(
            app,
            ["cancel", "--service", "netflix", "--profile-dir", "/tmp/my-profile"],
        )

        # Verify PlaywrightBrowser was called with user_data_dir
        mock_browser_class.assert_called_once()
        call_kwargs = mock_browser_class.call_args.kwargs
        assert call_kwargs.get("user_data_dir") == "/tmp/my-profile"
        assert call_kwargs.get("cdp_url") is None


class TestCLIServiceFactory:
    """Tests for CLI using service factory instead of direct instantiation."""

    @patch("subterminator.cli.main.CancellationEngine")
    @patch("subterminator.cli.main.SessionLogger")
    @patch("subterminator.cli.main.HeuristicInterpreter")
    @patch("subterminator.cli.main.create_service")
    @patch("subterminator.cli.main.PlaywrightBrowser")
    @patch("subterminator.cli.main.ConfigLoader")
    def test_cli_uses_create_service(
        self,
        mock_config_loader: MagicMock,
        mock_browser_class: MagicMock,
        mock_create_service: MagicMock,
        mock_heuristic: MagicMock,
        mock_session: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """CLI should use create_service instead of NetflixService directly."""
        from pathlib import Path

        # Setup mock config
        mock_config = MagicMock()
        mock_config.anthropic_api_key = None
        mock_config.output_dir = Path("/tmp")
        mock_config_loader.load.return_value = mock_config

        # Setup mock service
        mock_service = MagicMock()
        mock_create_service.return_value = mock_service

        # Run the command
        runner.invoke(
            app,
            ["cancel", "--service", "netflix"],
        )

        # Verify create_service was called with correct args
        mock_create_service.assert_called_once_with("netflix", "live")

    @patch("subterminator.cli.main.CancellationEngine")
    @patch("subterminator.cli.main.SessionLogger")
    @patch("subterminator.cli.main.HeuristicInterpreter")
    @patch("subterminator.cli.main.get_mock_pages_dir")
    @patch("subterminator.cli.main.MockServer")
    @patch("subterminator.cli.main.create_service")
    @patch("subterminator.cli.main.PlaywrightBrowser")
    @patch("subterminator.cli.main.ConfigLoader")
    def test_mock_target_uses_get_mock_pages_dir(
        self,
        mock_config_loader: MagicMock,
        mock_browser_class: MagicMock,
        mock_create_service: MagicMock,
        mock_mock_server: MagicMock,
        mock_get_mock_pages_dir: MagicMock,
        mock_heuristic: MagicMock,
        mock_session: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """Mock target should use get_mock_pages_dir for path derivation."""
        from pathlib import Path

        # Setup mock config
        mock_config = MagicMock()
        mock_config.anthropic_api_key = None
        mock_config.output_dir = Path("/tmp")
        mock_config_loader.load.return_value = mock_config

        # Setup mock service
        mock_service = MagicMock()
        mock_create_service.return_value = mock_service

        # Setup get_mock_pages_dir to return a valid path that exists
        mock_get_mock_pages_dir.return_value = "mock_pages/netflix"

        # Mock Path to make mock_pages_dir.exists() return True
        with patch("subterminator.cli.main.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
            mock_path_instance.exists.return_value = True
            mock_path_instance.parent = mock_path_instance
            mock_path_class.return_value = mock_path_instance
            mock_path_class.__call__ = MagicMock(return_value=mock_path_instance)

            # Run the command with --target mock
            runner.invoke(
                app,
                ["cancel", "--service", "netflix", "--target", "mock"],
            )

        # Verify get_mock_pages_dir was called with service id
        mock_get_mock_pages_dir.assert_called_once_with("netflix")

    @patch("subterminator.cli.main.create_service")
    @patch("subterminator.cli.main.ConfigLoader")
    def test_unknown_service_error_from_create_service(
        self,
        mock_config_loader: MagicMock,
        mock_create_service: MagicMock,
    ) -> None:
        """Unknown service error from create_service should be helpful."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.anthropic_api_key = None
        mock_config.output_dir = "/tmp"
        mock_config_loader.load.return_value = mock_config

        # Make create_service raise ValueError with suggestion
        mock_create_service.side_effect = ValueError(
            "Unknown service 'netflixx'. Did you mean 'netflix'?"
        )

        # Run the command - note: service validation happens before create_service
        # so this tests the error handling path if create_service were to raise
        result = runner.invoke(
            app,
            ["cancel", "--service", "netflixx"],
        )

        # The service validation happens before create_service is called,
        # so we should see the exit code 3 from service validation
        assert result.exit_code == 3
        assert "unknown service" in result.output.lower()
