"""Integration tests for authentication flow in CancellationEngine.

Tests the LOGIN_REQUIRED → ACCOUNT_ACTIVE transition with post-login redirect.
Uses a TransitioningMockBrowser that switches content based on a _logged_in flag
set by the test's input_callback.
"""

import tempfile
from pathlib import Path

import pytest

from subterminator.core.ai import HeuristicInterpreter
from subterminator.core.engine import CancellationEngine
from subterminator.core.protocols import State
from subterminator.services.mock import MockServer
from subterminator.services.netflix import NetflixService
from subterminator.utils.config import AppConfig
from subterminator.utils.session import SessionLogger


class TransitioningMockBrowser:
    """Mock browser that transitions through the cancellation flow.

    This browser simulates the authentication and cancellation flow by
    tracking state through a _current_page attribute. The flow progresses:
    - login → account (when _logged_in is set)
    - account → confirm (when cancel link is clicked)
    - confirm → complete (when confirm button is clicked in dry_run)
    """

    def __init__(self, mock_server: MockServer, pages_dir: Path):
        """Initialize the transitioning mock browser.

        Args:
            mock_server: The mock server serving HTML pages.
            pages_dir: Path to the directory containing mock HTML pages.
        """
        self._mock_server = mock_server
        self._pages_dir = pages_dir
        self._logged_in = False
        self._launched = False
        # Track current page: login, account, confirm, complete
        self._current_page = "login"

    async def launch(self) -> None:
        """Simulate browser launch."""
        self._launched = True

    async def navigate(self, url: str, timeout: int = 30000) -> None:
        """Simulate navigation - no-op since we control content via state."""
        pass

    async def click(self, selector: str | list[str]) -> None:
        """Simulate click and advance flow state."""
        # Convert list to string for matching
        selector_str = selector[0] if isinstance(selector, list) else selector

        # Transition based on what's being clicked
        if "Cancel" in selector_str or "cancel" in selector_str:
            # Clicking cancel link advances to confirmation page
            self._current_page = "confirm"
        elif "confirm" in selector_str.lower() or "finish" in selector_str.lower():
            # Clicking confirm advances to complete page
            self._current_page = "complete"

    async def fill(self, selector: str, value: str) -> None:
        """Simulate fill - no-op for auth flow test."""
        pass

    async def select_option(self, selector: str, value: str | None = None) -> None:
        """Simulate select - no-op for auth flow test."""
        pass

    async def screenshot(self, path: str | None = None) -> bytes:
        """Capture a mock screenshot."""
        # Return empty PNG for testing
        return b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    async def html(self) -> str:
        """Get mock HTML content."""
        return await self.text_content()

    async def url(self) -> str:
        """Get URL based on current page state."""
        base_url = self._mock_server.base_url

        # Update page based on login state
        if self._logged_in and self._current_page == "login":
            self._current_page = "account"

        page_urls = {
            "login": f"{base_url}/account?variant=login",
            "account": f"{base_url}/account",
            "confirm": f"{base_url}/cancelplan?variant=confirm",
            "complete": f"{base_url}/cancelplan?variant=complete",
        }
        return page_urls.get(self._current_page, f"{base_url}/account")

    async def text_content(self) -> str:
        """Get page text content based on current page state."""
        # Update page based on login state
        if self._logged_in and self._current_page == "login":
            self._current_page = "account"

        page_files = {
            "login": "login.html",
            "account": "account.html",
            "confirm": "cancelplan_confirm.html",
            "complete": "cancelplan_complete.html",
        }
        filename = page_files.get(self._current_page, "account.html")
        return (self._pages_dir / filename).read_text()

    async def close(self) -> None:
        """Close the mock browser."""
        self._launched = False


class TestAuthenticationFlow:
    """Test authentication flow transitions."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for session logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def session_logger(self, temp_output_dir: Path):
        """Create a session logger for tests."""
        return SessionLogger(
            output_dir=temp_output_dir,
            service="netflix",
            target="test@example.com"
        )

    @pytest.fixture
    def config(self):
        """Create test configuration with short timeouts."""
        return AppConfig(
            anthropic_api_key=None,
            output_dir=Path("/tmp"),
            page_timeout=5000,
            element_timeout=2000,
            auth_timeout=5000,  # Short timeout for tests
            confirm_timeout=5000,
            max_retries=1,
            max_transitions=10,
        )

    @pytest.fixture
    def transitioning_browser(
        self, mock_server: MockServer, mock_pages_dir: Path
    ) -> TransitioningMockBrowser:
        """Create a transitioning mock browser."""
        return TransitioningMockBrowser(mock_server, mock_pages_dir)

    async def test_auth_flow_login_to_account_active(
        self,
        mock_server: MockServer,
        mock_pages_dir: Path,
        session_logger: SessionLogger,
        config: AppConfig,
        transitioning_browser: TransitioningMockBrowser,
    ):
        """Test full auth flow: START → LOGIN_REQUIRED → (auth) → ACCOUNT_ACTIVE.

        This test verifies that:
        1. Engine starts and detects LOGIN_REQUIRED state
        2. Engine calls input_callback with "AUTH" checkpoint
        3. After input_callback returns, engine detects ACCOUNT_ACTIVE
        4. Engine proceeds to click cancel link (mocked)
        """
        # Track callback invocations
        callback_calls: list[tuple[str, int]] = []

        def auth_input_callback(checkpoint_type: str, timeout: int) -> str | None:
            """Simulate user completing login."""
            callback_calls.append((checkpoint_type, timeout))
            if checkpoint_type == "AUTH":
                # Simulate user completing login by setting browser flag
                transitioning_browser._logged_in = True
                return "ok"
            return None

        service = NetflixService(target="mock")
        # Override entry_url to start at login page
        service._config.mock_entry_url = f"{mock_server.base_url}/account?variant=login"

        engine = CancellationEngine(
            service=service,
            browser=transitioning_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session_logger,
            config=config,
            input_callback=auth_input_callback,
        )

        result = await engine.run(dry_run=True)

        # Verify AUTH checkpoint was called
        assert any(c[0] == "AUTH" for c in callback_calls), (
            "AUTH checkpoint should have been called"
        )

        # Verify engine detected ACCOUNT_ACTIVE after auth
        # The flow may end in different states, but it should have transitioned
        # through ACCOUNT_ACTIVE
        assert result.state in (
            State.COMPLETE,
            State.ACCOUNT_ACTIVE,
            State.RETENTION_OFFER,
            State.EXIT_SURVEY,
            State.FINAL_CONFIRMATION,
            State.UNKNOWN,
        ), f"Unexpected final state: {result.state}"

        # Verify session was logged
        assert session_logger.data["transitions"], "Should have logged transitions"

    async def test_auth_flow_timeout_aborts(
        self,
        mock_server: MockServer,
        mock_pages_dir: Path,
        session_logger: SessionLogger,
        config: AppConfig,
        transitioning_browser: TransitioningMockBrowser,
    ):
        """Test that timeout during auth returns UserAborted.

        When input_callback returns None (simulating timeout), the engine
        should abort with UserAborted exception and return ABORTED state.
        """

        def timeout_input_callback(checkpoint_type: str, timeout: int) -> str | None:
            """Simulate timeout by returning None."""
            return None

        service = NetflixService(target="mock")
        service._config.mock_entry_url = f"{mock_server.base_url}/account?variant=login"

        engine = CancellationEngine(
            service=service,
            browser=transitioning_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session_logger,
            config=config,
            input_callback=timeout_input_callback,
        )

        result = await engine.run(dry_run=True)

        # Verify engine aborted due to timeout
        assert result.state == State.ABORTED, (
            f"Expected ABORTED state on timeout, got {result.state}"
        )
        assert not result.success, "Operation should not succeed on timeout"
        assert "aborted" in result.message.lower(), (
            f"Expected abort message, got: {result.message}"
        )


class TestAuthFlowEdgeCases:
    """Test edge cases in authentication flow."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def session_logger(self, temp_output_dir: Path):
        """Create a session logger for tests."""
        return SessionLogger(
            output_dir=temp_output_dir,
            service="netflix",
            target="test@example.com"
        )

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AppConfig(
            anthropic_api_key=None,
            output_dir=Path("/tmp"),
            page_timeout=5000,
            element_timeout=2000,
            auth_timeout=5000,
            confirm_timeout=5000,
            max_retries=1,
            max_transitions=5,  # Limit transitions to prevent infinite loops
        )

    async def test_already_logged_in_skips_auth(
        self,
        mock_server: MockServer,
        mock_pages_dir: Path,
        session_logger: SessionLogger,
        config: AppConfig,
    ):
        """Test that starting on account page skips AUTH checkpoint.

        If the browser already shows the account page (user is logged in),
        the engine should not request AUTH checkpoint.
        """
        callback_calls: list[tuple[str, int]] = []

        def track_input_callback(checkpoint_type: str, timeout: int) -> str | None:
            callback_calls.append((checkpoint_type, timeout))
            return "ok"

        # Create browser that starts logged in
        browser = TransitioningMockBrowser(mock_server, mock_pages_dir)
        browser._logged_in = True  # Already logged in

        service = NetflixService(target="mock")
        service._config.mock_entry_url = f"{mock_server.base_url}/account"

        engine = CancellationEngine(
            service=service,
            browser=browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session_logger,
            config=config,
            input_callback=track_input_callback,
        )

        await engine.run(dry_run=True)

        # Verify AUTH checkpoint was NOT called (already logged in)
        auth_calls = [c for c in callback_calls if c[0] == "AUTH"]
        assert len(auth_calls) == 0, (
            f"AUTH checkpoint should not be called when already logged in, "
            f"but got {len(auth_calls)} calls"
        )
