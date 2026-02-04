"""Unit tests for the CancellationEngine.

Tests cover:
- CancellationEngine initialization
- _is_terminal_state returns True for terminal states
- _complete creates CancellationResult
- with_retry succeeds on first try
- with_retry retries on TransientError
- Engine accepts ServiceProtocol (service-agnostic)
- _click_selector helper extracts CSS and passes ARIA fallback
- Generic checkpoint messages use service name
"""

import time
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from subterminator.core.protocols import (
    CancellationResult,
    State,
)
from subterminator.services.selectors import SelectorConfig
from subterminator.utils.config import AppConfig
from subterminator.utils.exceptions import TransientError


class TestCancellationEngineInitialization:
    """Tests for CancellationEngine initialization."""

    def test_initialization_with_all_components(self, tmp_path: Path) -> None:
        """Should initialize CancellationEngine with all components."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        service = NetflixService()
        browser = MagicMock()
        heuristic = HeuristicInterpreter()
        ai = MagicMock()
        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test@example.com"
        )
        config = AppConfig(
            anthropic_api_key="test-key",
            output_dir=tmp_path,
        )

        engine = CancellationEngine(
            service=service,
            browser=browser,
            heuristic=heuristic,
            ai=ai,
            session=session,
            config=config,
        )

        assert engine.service == service
        assert engine.browser == browser
        assert engine.heuristic == heuristic
        assert engine.ai == ai
        assert engine.session == session
        assert engine.config == config
        assert engine.dry_run is False
        assert engine._current_state == State.START
        assert engine._step == 0

    def test_initialization_without_ai(self, tmp_path: Path) -> None:
        """Should initialize CancellationEngine without AI interpreter."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        service = NetflixService()
        browser = MagicMock()
        heuristic = HeuristicInterpreter()
        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test@example.com"
        )
        config = AppConfig(
            anthropic_api_key=None,
            output_dir=tmp_path,
        )

        engine = CancellationEngine(
            service=service,
            browser=browser,
            heuristic=heuristic,
            ai=None,
            session=session,
            config=config,
        )

        assert engine.ai is None

    def test_initialization_with_callbacks(self, tmp_path: Path) -> None:
        """Should initialize with output and input callbacks."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        service = NetflixService()
        browser = MagicMock()
        heuristic = HeuristicInterpreter()
        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        output_calls: list[tuple[str, str]] = []
        input_calls: list[tuple[str, int]] = []

        def output_callback(state: str, msg: str) -> None:
            output_calls.append((state, msg))

        def input_callback(checkpoint: str, timeout: int) -> str | None:
            input_calls.append((checkpoint, timeout))
            return "confirm"

        engine = CancellationEngine(
            service=service,
            browser=browser,
            heuristic=heuristic,
            ai=None,
            session=session,
            config=config,
            output_callback=output_callback,
            input_callback=input_callback,
        )

        # Test output callback is set
        engine.output_callback("TEST", "Test message")
        assert len(output_calls) == 1
        assert output_calls[0] == ("TEST", "Test message")


class TestIsTerminalState:
    """Tests for _is_terminal_state method."""

    def test_complete_is_terminal(self, tmp_path: Path) -> None:
        """State.COMPLETE should be a terminal state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.COMPLETE
        assert engine._is_terminal_state() is True

    def test_aborted_is_terminal(self, tmp_path: Path) -> None:
        """State.ABORTED should be a terminal state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.ABORTED
        assert engine._is_terminal_state() is True

    def test_failed_is_terminal(self, tmp_path: Path) -> None:
        """State.FAILED should be a terminal state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.FAILED
        assert engine._is_terminal_state() is True

    def test_start_is_not_terminal(self, tmp_path: Path) -> None:
        """State.START should not be a terminal state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.START
        assert engine._is_terminal_state() is False

    def test_account_active_is_not_terminal(self, tmp_path: Path) -> None:
        """State.ACCOUNT_ACTIVE should not be a terminal state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.ACCOUNT_ACTIVE
        assert engine._is_terminal_state() is False


class TestCompleteMethod:
    """Tests for _complete method."""

    def test_complete_creates_success_result(self, tmp_path: Path) -> None:
        """_complete should create successful CancellationResult."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test"
        )
        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        result = engine._complete(True, State.COMPLETE, "Cancellation completed")

        assert isinstance(result, CancellationResult)
        assert result.success is True
        assert result.state == State.COMPLETE
        assert result.message == "Cancellation completed"
        assert result.session_dir == session.session_dir

    def test_complete_creates_failure_result(self, tmp_path: Path) -> None:
        """_complete should create failed CancellationResult."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test"
        )
        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        result = engine._complete(False, State.FAILED, "Operation failed")

        assert isinstance(result, CancellationResult)
        assert result.success is False
        assert result.state == State.FAILED
        assert result.message == "Operation failed"

    def test_complete_calls_session_complete(self, tmp_path: Path) -> None:
        """_complete should call session.complete with correct values."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test"
        )
        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._complete(True, State.COMPLETE, "Done")

        assert session.data["result"] == "success"
        assert session.data["final_state"] == "COMPLETE"
        assert session.data["error"] is None

    def test_complete_records_error_on_failure(self, tmp_path: Path) -> None:
        """_complete should record error message on failure."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test"
        )
        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._complete(False, State.FAILED, "Network timeout")

        assert session.data["result"] == "failed"
        assert session.data["final_state"] == "FAILED"
        assert session.data["error"] == "Network timeout"


class TestWithRetry:
    """Tests for the with_retry utility function."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        """with_retry should return result on first successful try."""
        from subterminator.core.engine import with_retry

        call_count = 0

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(operation)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self) -> None:
        """with_retry should retry on TransientError and eventually succeed."""
        from subterminator.core.engine import with_retry

        call_count = 0

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientError("Temporary failure")
            return "success after retries"

        result = await with_retry(operation, max_retries=3)

        assert result == "success after retries"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        """with_retry should raise error after max retries exceeded."""
        from subterminator.core.engine import with_retry

        call_count = 0

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            raise TransientError("Always fails")

        with pytest.raises(TransientError, match="Always fails"):
            await with_retry(operation, max_retries=3)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_on_non_transient_error(self) -> None:
        """with_retry should not retry on non-TransientError exceptions."""
        from subterminator.core.engine import with_retry

        call_count = 0

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-transient error")

        with pytest.raises(ValueError, match="Non-transient error"):
            await with_retry(operation, max_retries=3)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_custom_retry_exceptions(self) -> None:
        """with_retry should retry on custom exception types."""
        from subterminator.core.engine import with_retry

        call_count = 0

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Custom error")
            return "success"

        result = await with_retry(operation, max_retries=3, retry_on=(ValueError,))

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self) -> None:
        """with_retry should use exponential backoff between retries."""
        from subterminator.core.engine import with_retry

        call_count = 0
        timestamps: list[float] = []

        async def operation() -> str:
            nonlocal call_count
            call_count += 1
            timestamps.append(time.time())
            if call_count < 3:
                raise TransientError("Retry me")
            return "done"

        await with_retry(operation, max_retries=3)

        # Check that delays increase (exponential backoff)
        # First retry: 2^0 = 1 second, second retry: 2^1 = 2 seconds
        if len(timestamps) >= 3:
            delay1 = timestamps[1] - timestamps[0]
            delay2 = timestamps[2] - timestamps[1]
            # Allow some tolerance for timing
            assert delay1 >= 0.9  # ~1 second
            assert delay2 >= 1.8  # ~2 seconds


class TestTransitionTo:
    """Tests for _transition_to method."""

    def test_transition_to_updates_state(self, tmp_path: Path) -> None:
        """_transition_to should update current state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        assert engine._current_state == State.START
        engine._transition_to(State.LOGIN_REQUIRED)
        assert engine._current_state == State.LOGIN_REQUIRED


class TestGetResultMessage:
    """Tests for _get_result_message method."""

    def test_complete_message(self, tmp_path: Path) -> None:
        """Should return success message for COMPLETE state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.COMPLETE
        assert engine._get_result_message() == "Cancellation completed successfully"

    def test_failed_message(self, tmp_path: Path) -> None:
        """Should return failure message for FAILED state."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        engine = CancellationEngine(
            service=NetflixService(),
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=SessionLogger(
                output_dir=tmp_path, service="netflix", target="test"
            ),
            config=AppConfig(anthropic_api_key=None, output_dir=tmp_path),
        )

        engine._current_state = State.FAILED
        assert engine._get_result_message() == "Cancellation failed"


class TestHandleStateLoginRequired:
    """Tests for LOGIN_REQUIRED state handling."""

    @pytest.mark.asyncio
    async def test_login_required_navigates_to_entry_url_after_auth(
        self, tmp_path: Path
    ) -> None:
        """After LOGIN_REQUIRED auth, engine should navigate to entry_url."""
        from unittest.mock import AsyncMock

        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        # Setup
        service = NetflixService()
        mock_browser = AsyncMock()
        mock_browser.url = AsyncMock(return_value="https://www.netflix.com/account")
        mock_browser.text_content = AsyncMock(return_value="Account Cancel membership")
        mock_browser.screenshot = AsyncMock(return_value=b"fake_screenshot")

        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        # Create engine with mocked input callback to simulate user completing login
        engine = CancellationEngine(
            service=service,
            browser=mock_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
            input_callback=lambda checkpoint, timeout: "",  # Simulate Enter press
        )

        # Call _handle_state for LOGIN_REQUIRED
        await engine._handle_state(State.LOGIN_REQUIRED)

        # Verify navigation was called with entry_url after auth checkpoint
        mock_browser.navigate.assert_called_once_with(
            service.entry_url, config.page_timeout
        )


class TestHandleStateUnknown:
    """Tests for UNKNOWN state handling."""

    @pytest.mark.asyncio
    async def test_unknown_state_navigates_to_entry_url_for_recovery(
        self, tmp_path: Path
    ) -> None:
        """UNKNOWN state should navigate to entry_url before re-detection."""
        from unittest.mock import AsyncMock

        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        # Setup
        service = NetflixService()
        mock_browser = AsyncMock()
        mock_browser.url = AsyncMock(return_value="https://www.netflix.com/account")
        mock_browser.text_content = AsyncMock(return_value="Account Cancel membership")
        mock_browser.screenshot = AsyncMock(return_value=b"fake_screenshot")

        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        # Create engine with mocked input callback
        engine = CancellationEngine(
            service=service,
            browser=mock_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
            input_callback=lambda checkpoint, timeout: "",  # Simulate Enter press
        )

        # Call _handle_state for UNKNOWN
        await engine._handle_state(State.UNKNOWN)

        # Verify navigation was called with entry_url after human checkpoint
        mock_browser.navigate.assert_called_once_with(
            service.entry_url, config.page_timeout
        )


class TestModuleExports:
    """Tests for module exports."""

    def test_exports_from_core_init(self) -> None:
        """CancellationEngine and with_retry should be importable."""
        from subterminator.core import CancellationEngine, with_retry

        assert CancellationEngine.__name__ == "CancellationEngine"
        assert with_retry.__name__ == "with_retry"


# --- Phase 4: Service-Agnostic Engine Tests ---


@dataclass
class MockServiceConfig:
    """Mock service configuration for testing."""

    name: str = "TestService"


@dataclass
class MockServiceSelectors:
    """Mock selectors for testing."""

    cancel_link: SelectorConfig = None  # type: ignore[assignment]
    decline_offer: SelectorConfig = None  # type: ignore[assignment]
    survey_option: SelectorConfig = None  # type: ignore[assignment]
    survey_submit: SelectorConfig = None  # type: ignore[assignment]
    confirm_cancel: SelectorConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Initialize with default SelectorConfig values."""
        self.cancel_link = SelectorConfig(css=["#cancel"])
        self.decline_offer = SelectorConfig(css=["#decline"])
        self.survey_option = SelectorConfig(css=["#survey-option"])
        self.survey_submit = SelectorConfig(css=["#survey-submit"])
        self.confirm_cancel = SelectorConfig(css=["#confirm"])


class MockService:
    """Mock service implementing ServiceProtocol for testing."""

    def __init__(self, name: str = "TestService") -> None:
        self._config = MockServiceConfig(name=name)
        self._selectors = MockServiceSelectors()

    @property
    def config(self) -> MockServiceConfig:
        return self._config

    @property
    def service_id(self) -> str:
        return "test_service"

    @property
    def entry_url(self) -> str:
        return "https://test.example.com/account"

    @property
    def selectors(self) -> MockServiceSelectors:
        return self._selectors


class TestEngineServiceProtocol:
    """Test engine works with ServiceProtocol (Step 4.1)."""

    def test_engine_accepts_mock_service_protocol(self, tmp_path: Path) -> None:
        """Engine should accept any ServiceProtocol implementation (4.1.1)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService(name="MockTestService")
        browser = MagicMock()
        heuristic = HeuristicInterpreter()
        session = SessionLogger(
            output_dir=tmp_path, service="test_service", target="test@example.com"
        )
        config = AppConfig(
            anthropic_api_key="test-key",
            output_dir=tmp_path,
        )

        engine = CancellationEngine(
            service=mock_service,
            browser=browser,
            heuristic=heuristic,
            ai=None,
            session=session,
            config=config,
        )

        assert engine.service == mock_service
        assert engine.service.config.name == "MockTestService"

    def test_engine_works_with_netflix_service(self, tmp_path: Path) -> None:
        """Engine should work with NetflixService (4.1.2)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.services.netflix import NetflixService
        from subterminator.utils.session import SessionLogger

        service = NetflixService()
        browser = MagicMock()
        heuristic = HeuristicInterpreter()
        session = SessionLogger(
            output_dir=tmp_path, service="netflix", target="test@example.com"
        )
        config = AppConfig(
            anthropic_api_key="test-key",
            output_dir=tmp_path,
        )

        engine = CancellationEngine(
            service=service,
            browser=browser,
            heuristic=heuristic,
            ai=None,
            session=session,
            config=config,
        )

        assert engine.service == service
        assert engine.service.config.name == "Netflix"

    def test_engine_type_annotation_is_service_protocol(self) -> None:
        """Engine __init__ should accept ServiceProtocol type (4.1.3)."""
        import inspect

        from subterminator.core.engine import CancellationEngine

        sig = inspect.signature(CancellationEngine.__init__)
        service_param = sig.parameters["service"]
        # Check annotation string contains ServiceProtocol
        annotation_str = str(service_param.annotation)
        assert "ServiceProtocol" in annotation_str or "Protocol" in annotation_str


class TestClickSelector:
    """Test _click_selector helper (Step 4.2)."""

    @pytest.mark.asyncio
    async def test_click_selector_extracts_css(self, tmp_path: Path) -> None:
        """_click_selector should extract .css from SelectorConfig (4.2.1)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService()
        mock_browser = AsyncMock()
        session = SessionLogger(
            output_dir=tmp_path, service="test", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        engine = CancellationEngine(
            service=mock_service,
            browser=mock_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
        )

        selector = SelectorConfig(css=["#test-element", ".fallback-class"], aria=None)
        await engine._click_selector(selector)

        mock_browser.click.assert_called_once_with(
            ["#test-element", ".fallback-class"],
            fallback_role=None,
            timeout=config.element_timeout,
        )

    @pytest.mark.asyncio
    async def test_click_selector_passes_aria(self, tmp_path: Path) -> None:
        """_click_selector should pass .aria as fallback_role (4.2.2)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService()
        mock_browser = AsyncMock()
        session = SessionLogger(
            output_dir=tmp_path, service="test", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        engine = CancellationEngine(
            service=mock_service,
            browser=mock_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
        )

        selector = SelectorConfig(
            css=["#test-button"],
            aria=("button", "Click me"),
        )
        await engine._click_selector(selector)

        mock_browser.click.assert_called_once_with(
            ["#test-button"],
            fallback_role=("button", "Click me"),
            timeout=config.element_timeout,
        )

    @pytest.mark.asyncio
    async def test_click_selector_handles_aria_none(self, tmp_path: Path) -> None:
        """_click_selector should handle aria=None correctly (4.2.3)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService()
        mock_browser = AsyncMock()
        session = SessionLogger(
            output_dir=tmp_path, service="test", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        engine = CancellationEngine(
            service=mock_service,
            browser=mock_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
        )

        selector = SelectorConfig(css=["input[type='radio']"], aria=None)
        await engine._click_selector(selector)

        # Verify fallback_role is None
        call_args = mock_browser.click.call_args
        assert call_args.kwargs["fallback_role"] is None

    @pytest.mark.asyncio
    async def test_click_selector_helper_works_correctly(self, tmp_path: Path) -> None:
        """_click_selector helper should work with various inputs (4.2.4)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService()
        mock_browser = AsyncMock()
        session = SessionLogger(
            output_dir=tmp_path, service="test", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        engine = CancellationEngine(
            service=mock_service,
            browser=mock_browser,
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
        )

        # Test with multiple CSS selectors and ARIA
        selector = SelectorConfig(
            css=["#primary", ".secondary", "[data-test='fallback']"],
            aria=("link", "Cancel Membership"),
        )
        await engine._click_selector(selector)

        mock_browser.click.assert_called_once_with(
            ["#primary", ".secondary", "[data-test='fallback']"],
            fallback_role=("link", "Cancel Membership"),
            timeout=config.element_timeout,
        )


class TestGenericMessages:
    """Test checkpoint messages use service name (Step 4.3)."""

    @pytest.mark.asyncio
    async def test_auth_prompt_includes_service_name(self, tmp_path: Path) -> None:
        """AUTH prompt should include service.config.name (4.3.1)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService(name="CustomService")
        session = SessionLogger(
            output_dir=tmp_path, service="custom", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        # Capture output messages
        captured_messages: list[tuple[str, str]] = []

        def capture_output(state: str, msg: str) -> None:
            captured_messages.append((state, msg))

        engine = CancellationEngine(
            service=mock_service,
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
            output_callback=capture_output,
            input_callback=lambda checkpoint, timeout: "",
        )

        # Trigger AUTH checkpoint
        try:
            await engine._human_checkpoint("AUTH", 5000)
        except Exception:
            pass  # We're just testing the message content

        # Check that the message includes "CustomService"
        auth_messages = [msg for state, msg in captured_messages if state == "AUTH"]
        assert len(auth_messages) == 1
        assert "CustomService" in auth_messages[0]
        assert "Please log in to CustomService" in auth_messages[0]

    @pytest.mark.asyncio
    async def test_confirm_prompt_includes_service_name(self, tmp_path: Path) -> None:
        """CONFIRM prompt structure should be verified (4.3.2)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        mock_service = MockService(name="MyService")
        session = SessionLogger(
            output_dir=tmp_path, service="myservice", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        captured_messages: list[tuple[str, str]] = []

        def capture_output(state: str, msg: str) -> None:
            captured_messages.append((state, msg))

        engine = CancellationEngine(
            service=mock_service,
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
            output_callback=capture_output,
            input_callback=lambda checkpoint, timeout: "confirm",
        )

        # Trigger CONFIRM checkpoint
        try:
            await engine._human_checkpoint("CONFIRM", 5000)
        except Exception:
            pass

        # CONFIRM message should include service name
        confirm_messages = [
            msg for state, msg in captured_messages if state == "CONFIRM"
        ]
        assert len(confirm_messages) == 1
        assert "MyService" in confirm_messages[0]
        assert "subscription" in confirm_messages[0]

    @pytest.mark.asyncio
    async def test_no_hardcoded_netflix_in_auth_prompt(self, tmp_path: Path) -> None:
        """No hardcoded 'Netflix' should appear in AUTH prompts (4.3.3)."""
        from subterminator.core.ai import HeuristicInterpreter
        from subterminator.core.engine import CancellationEngine
        from subterminator.utils.session import SessionLogger

        # Use a service with a different name
        mock_service = MockService(name="Spotify")
        session = SessionLogger(
            output_dir=tmp_path, service="spotify", target="test@example.com"
        )
        config = AppConfig(anthropic_api_key=None, output_dir=tmp_path)

        captured_messages: list[tuple[str, str]] = []

        def capture_output(state: str, msg: str) -> None:
            captured_messages.append((state, msg))

        engine = CancellationEngine(
            service=mock_service,
            browser=MagicMock(),
            heuristic=HeuristicInterpreter(),
            ai=None,
            session=session,
            config=config,
            output_callback=capture_output,
            input_callback=lambda checkpoint, timeout: "",
        )

        # Trigger AUTH checkpoint
        try:
            await engine._human_checkpoint("AUTH", 5000)
        except Exception:
            pass

        # Verify "Netflix" does NOT appear in the message
        auth_messages = [msg for state, msg in captured_messages if state == "AUTH"]
        assert len(auth_messages) == 1
        assert "Netflix" not in auth_messages[0]
        assert "Spotify" in auth_messages[0]


class TestEngineAllTestsPass:
    """Verify all engine tests pass with updated click pattern (4.2.7)."""

    def test_engine_module_imports_service_protocol(self) -> None:
        """Engine module should import ServiceProtocol, not NetflixService."""
        from subterminator.core import engine

        # Check that ServiceProtocol is imported
        assert hasattr(engine, "ServiceProtocol") or "ServiceProtocol" in dir(engine)

        # Verify NetflixService is not directly imported in engine module
        import inspect

        source = inspect.getsource(engine)
        assert "from subterminator.services.netflix import NetflixService" not in source
