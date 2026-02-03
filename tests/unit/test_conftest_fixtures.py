"""Tests for conftest.py fixtures.

These tests verify that the fixtures defined in conftest.py work correctly
and return expected types with proper defaults.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from subterminator.core.protocols import AIInterpretation, BrowserProtocol, State
from subterminator.core.states import CancellationStateMachine
from subterminator.services.netflix import NetflixService
from subterminator.utils.config import AppConfig
from subterminator.utils.session import SessionLogger


class TestMockBrowserFixture:
    """Tests for mock_browser fixture."""

    def test_mock_browser_has_spec(self, mock_browser: MagicMock) -> None:
        """mock_browser should have BrowserProtocol spec."""
        assert mock_browser._spec_class == BrowserProtocol

    def test_mock_browser_launch_is_async(self, mock_browser: MagicMock) -> None:
        """mock_browser.launch should be an AsyncMock."""
        assert isinstance(mock_browser.launch, AsyncMock)

    def test_mock_browser_navigate_is_async(self, mock_browser: MagicMock) -> None:
        """mock_browser.navigate should be an AsyncMock."""
        assert isinstance(mock_browser.navigate, AsyncMock)

    def test_mock_browser_click_is_async(self, mock_browser: MagicMock) -> None:
        """mock_browser.click should be an AsyncMock."""
        assert isinstance(mock_browser.click, AsyncMock)

    def test_mock_browser_fill_is_async(self, mock_browser: MagicMock) -> None:
        """mock_browser.fill should be an AsyncMock."""
        assert isinstance(mock_browser.fill, AsyncMock)

    def test_mock_browser_select_option_is_async(self, mock_browser: MagicMock) -> None:
        """mock_browser.select_option should be an AsyncMock."""
        assert isinstance(mock_browser.select_option, AsyncMock)

    def test_mock_browser_screenshot_returns_bytes(
        self, mock_browser: MagicMock
    ) -> None:
        """mock_browser.screenshot should return fake screenshot data."""
        assert mock_browser.screenshot.return_value == b"fake_screenshot_data"

    def test_mock_browser_html_returns_string(self, mock_browser: MagicMock) -> None:
        """mock_browser.html should return HTML string."""
        assert mock_browser.html.return_value == "<html></html>"

    def test_mock_browser_url_returns_string(self, mock_browser: MagicMock) -> None:
        """mock_browser.url should return URL string."""
        assert mock_browser.url.return_value == "https://example.com"

    def test_mock_browser_text_content_returns_string(
        self, mock_browser: MagicMock
    ) -> None:
        """mock_browser.text_content should return text string."""
        assert mock_browser.text_content.return_value == "Sample text content"

    def test_mock_browser_close_is_async(self, mock_browser: MagicMock) -> None:
        """mock_browser.close should be an AsyncMock."""
        assert isinstance(mock_browser.close, AsyncMock)


class TestMockAiFixture:
    """Tests for mock_ai fixture."""

    def test_mock_ai_interpret_is_async(self, mock_ai: MagicMock) -> None:
        """mock_ai.interpret should be an AsyncMock."""
        assert isinstance(mock_ai.interpret, AsyncMock)

    def test_mock_ai_interpret_returns_ai_interpretation(
        self, mock_ai: MagicMock
    ) -> None:
        """mock_ai.interpret should return AIInterpretation."""
        result = mock_ai.interpret.return_value
        assert isinstance(result, AIInterpretation)

    def test_mock_ai_interpret_returns_account_active(
        self, mock_ai: MagicMock
    ) -> None:
        """mock_ai.interpret should return ACCOUNT_ACTIVE state by default."""
        result = mock_ai.interpret.return_value
        assert result.state == State.ACCOUNT_ACTIVE

    def test_mock_ai_interpret_has_high_confidence(self, mock_ai: MagicMock) -> None:
        """mock_ai.interpret should return high confidence."""
        result = mock_ai.interpret.return_value
        assert result.confidence == 0.9

    def test_mock_ai_interpret_has_reasoning(self, mock_ai: MagicMock) -> None:
        """mock_ai.interpret should have reasoning string."""
        result = mock_ai.interpret.return_value
        assert result.reasoning == "Test mock interpretation"


class TestMockHeuristicFixture:
    """Tests for mock_heuristic fixture."""

    def test_mock_heuristic_interpret_is_sync(self, mock_heuristic: MagicMock) -> None:
        """mock_heuristic.interpret should be a MagicMock (sync)."""
        # AsyncMock is a subclass of MagicMock, so check it's not AsyncMock
        assert not isinstance(mock_heuristic.interpret, AsyncMock)
        assert isinstance(mock_heuristic.interpret, MagicMock)

    def test_mock_heuristic_interpret_returns_ai_interpretation(
        self, mock_heuristic: MagicMock
    ) -> None:
        """mock_heuristic.interpret should return AIInterpretation."""
        result = mock_heuristic.interpret.return_value
        assert isinstance(result, AIInterpretation)

    def test_mock_heuristic_interpret_returns_account_active(
        self, mock_heuristic: MagicMock
    ) -> None:
        """mock_heuristic.interpret should return ACCOUNT_ACTIVE state."""
        result = mock_heuristic.interpret.return_value
        assert result.state == State.ACCOUNT_ACTIVE

    def test_mock_heuristic_interpret_has_confidence(
        self, mock_heuristic: MagicMock
    ) -> None:
        """mock_heuristic.interpret should return 0.85 confidence."""
        result = mock_heuristic.interpret.return_value
        assert result.confidence == 0.85

    def test_mock_heuristic_interpret_has_reasoning(
        self, mock_heuristic: MagicMock
    ) -> None:
        """mock_heuristic.interpret should have reasoning string."""
        result = mock_heuristic.interpret.return_value
        assert result.reasoning == "Heuristic detection"


class TestMockSessionFixture:
    """Tests for mock_session fixture."""

    def test_mock_session_is_session_logger(
        self, mock_session: SessionLogger
    ) -> None:
        """mock_session should be a SessionLogger instance."""
        assert isinstance(mock_session, SessionLogger)

    def test_mock_session_has_session_dir(self, mock_session: SessionLogger) -> None:
        """mock_session should have a session directory."""
        assert mock_session.session_dir.exists()

    def test_mock_session_service_is_netflix(
        self, mock_session: SessionLogger
    ) -> None:
        """mock_session should be configured for netflix service."""
        assert mock_session.data["service"] == "netflix"

    def test_mock_session_target_is_mock(self, mock_session: SessionLogger) -> None:
        """mock_session should be configured with mock target."""
        assert mock_session.data["target"] == "mock"


class TestAppConfigFixture:
    """Tests for app_config fixture."""

    def test_app_config_is_app_config(self, app_config: AppConfig) -> None:
        """app_config should be an AppConfig instance."""
        assert isinstance(app_config, AppConfig)

    def test_app_config_has_test_api_key(self, app_config: AppConfig) -> None:
        """app_config should have test API key."""
        assert app_config.anthropic_api_key == "test-key"

    def test_app_config_has_output_dir(self, app_config: AppConfig) -> None:
        """app_config should have output directory in tmp_path."""
        assert "output" in str(app_config.output_dir)

    def test_app_config_has_short_timeouts(self, app_config: AppConfig) -> None:
        """app_config should have shorter timeouts for testing."""
        assert app_config.page_timeout == 5000
        assert app_config.element_timeout == 2000
        assert app_config.auth_timeout == 10000
        assert app_config.confirm_timeout == 5000

    def test_app_config_has_reduced_retries(self, app_config: AppConfig) -> None:
        """app_config should have reduced max_retries."""
        assert app_config.max_retries == 2

    def test_app_config_has_reduced_transitions(self, app_config: AppConfig) -> None:
        """app_config should have reduced max_transitions."""
        assert app_config.max_transitions == 5


class TestNetflixServiceFixture:
    """Tests for netflix_service fixture."""

    def test_netflix_service_is_netflix_service(
        self, netflix_service: NetflixService
    ) -> None:
        """netflix_service should be a NetflixService instance."""
        assert isinstance(netflix_service, NetflixService)

    def test_netflix_service_target_is_mock(
        self, netflix_service: NetflixService
    ) -> None:
        """netflix_service should be configured for mock target."""
        assert netflix_service.target == "mock"

    def test_netflix_service_entry_url_is_mock(
        self, netflix_service: NetflixService
    ) -> None:
        """netflix_service entry_url should be mock URL."""
        assert netflix_service.entry_url == "http://localhost:8000/account"


class TestStateMachineFixture:
    """Tests for state_machine fixture."""

    def test_state_machine_is_cancellation_state_machine(
        self, state_machine: CancellationStateMachine
    ) -> None:
        """state_machine should be a CancellationStateMachine instance."""
        assert isinstance(state_machine, CancellationStateMachine)

    def test_state_machine_initial_state_is_start(
        self, state_machine: CancellationStateMachine
    ) -> None:
        """state_machine should start in 'start' state."""
        assert state_machine.current_state == state_machine.start

    def test_state_machine_step_is_zero(
        self, state_machine: CancellationStateMachine
    ) -> None:
        """state_machine step should be zero."""
        assert state_machine.step == 0


class TestMockPagesDirFixture:
    """Tests for mock_pages_dir fixture."""

    def test_mock_pages_dir_is_path(self, mock_pages_dir: Path) -> None:
        """mock_pages_dir should be a Path instance."""
        assert isinstance(mock_pages_dir, Path)

    def test_mock_pages_dir_ends_with_netflix(self, mock_pages_dir: Path) -> None:
        """mock_pages_dir should point to netflix directory."""
        assert mock_pages_dir.name == "netflix"

    def test_mock_pages_dir_parent_is_mock_pages(self, mock_pages_dir: Path) -> None:
        """mock_pages_dir parent should be mock_pages."""
        assert mock_pages_dir.parent.name == "mock_pages"

    def test_mock_pages_dir_exists(self, mock_pages_dir: Path) -> None:
        """mock_pages_dir should exist on disk."""
        assert mock_pages_dir.exists()

    def test_mock_pages_dir_contains_html_files(self, mock_pages_dir: Path) -> None:
        """mock_pages_dir should contain HTML files."""
        html_files = list(mock_pages_dir.glob("*.html"))
        assert len(html_files) > 0
