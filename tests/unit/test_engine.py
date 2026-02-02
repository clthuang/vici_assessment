"""Unit tests for the CancellationEngine.

Tests cover:
- CancellationEngine initialization
- _is_terminal_state returns True for terminal states
- _complete creates CancellationResult
- with_retry succeeds on first try
- with_retry retries on TransientError
"""

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from subterminator.core.protocols import (
    CancellationResult,
    State,
)
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


class TestModuleExports:
    """Tests for module exports."""

    def test_exports_from_core_init(self) -> None:
        """CancellationEngine and with_retry should be importable."""
        from subterminator.core import CancellationEngine, with_retry

        assert CancellationEngine.__name__ == "CancellationEngine"
        assert with_retry.__name__ == "with_retry"
