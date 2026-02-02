"""Cancellation engine for SubTerminator.

This module provides the main orchestrator that coordinates the subscription
cancellation flow using all the components built so far.
"""

import asyncio
from collections.abc import Callable
from typing import TypeVar

from subterminator.core.ai import HeuristicInterpreter
from subterminator.core.protocols import (
    AIInterpreterProtocol,
    BrowserProtocol,
    CancellationResult,
    State,
)
from subterminator.core.states import CancellationStateMachine
from subterminator.services.netflix import NetflixService
from subterminator.utils.config import AppConfig
from subterminator.utils.exceptions import (
    HumanInterventionRequired,
    SubTerminatorError,
    TransientError,
    UserAborted,
)
from subterminator.utils.session import SessionLogger

T = TypeVar("T")


class CancellationEngine:
    """Coordinates the subscription cancellation flow.

    This is the main orchestrator that coordinates the cancellation flow
    using browser automation, heuristic detection, AI interpretation,
    and human checkpoints.

    Attributes:
        service: The service-specific implementation (e.g., NetflixService).
        browser: Browser automation interface.
        heuristic: Heuristic-based page state interpreter.
        ai: Optional AI-based page state interpreter.
        session: Session logger for tracking progress.
        config: Application configuration.
        output_callback: Callback for outputting status messages.
        input_callback: Callback for requesting human input.
        state_machine: State machine tracking valid transitions.
        dry_run: Whether to skip actual cancellation.

    Example:
        >>> engine = CancellationEngine(
        ...     service=NetflixService(),
        ...     browser=PlaywrightBrowser(),
        ...     heuristic=HeuristicInterpreter(),
        ...     ai=ClaudeInterpreter(),
        ...     session=session_logger,
        ...     config=config,
        ... )
        >>> result = await engine.run(dry_run=True)
        >>> print(result.message)
    """

    def __init__(
        self,
        service: NetflixService,
        browser: BrowserProtocol,
        heuristic: HeuristicInterpreter,
        ai: AIInterpreterProtocol | None,
        session: SessionLogger,
        config: AppConfig,
        output_callback: Callable[[str, str], None] | None = None,
        input_callback: Callable[[str, int], str | None] | None = None,
    ):
        """Initialize the CancellationEngine.

        Args:
            service: Service-specific implementation.
            browser: Browser automation interface.
            heuristic: Heuristic-based page state interpreter.
            ai: Optional AI-based page state interpreter.
            session: Session logger for tracking progress.
            config: Application configuration.
            output_callback: Optional callback for status messages.
                Signature: (state_name: str, message: str) -> None
            input_callback: Optional callback for human input.
                Signature: (checkpoint_type: str, timeout_ms: int) -> str | None
        """
        self.service = service
        self.browser = browser
        self.heuristic = heuristic
        self.ai = ai
        self.session = session
        self.config = config
        self.output_callback = output_callback or (lambda state, msg: None)
        self.input_callback = input_callback

        self.state_machine = CancellationStateMachine()
        self.dry_run = False
        self._current_state = State.START
        self._step = 0

    async def run(self, dry_run: bool = False) -> CancellationResult:
        """Execute the cancellation flow.

        Args:
            dry_run: If True, stops before actual cancellation.

        Returns:
            CancellationResult indicating success or failure.
        """
        self.dry_run = dry_run

        try:
            await self.browser.launch()

            while not self._is_terminal_state():
                if self._step >= self.config.max_transitions:
                    return self._complete(
                        False, State.FAILED, "Max transitions exceeded"
                    )

                next_state = await self._handle_state(self._current_state)
                self._transition_to(next_state)
                self._step += 1

            # Determine result based on final state
            success = self._current_state in (
                State.COMPLETE, State.ACCOUNT_CANCELLED
            )
            return self._complete(
                success, self._current_state, self._get_result_message()
            )

        except UserAborted:
            return self._complete(False, State.ABORTED, "User aborted the operation")
        except SubTerminatorError as e:
            return self._complete(False, State.FAILED, str(e))
        finally:
            await self.browser.close()

    async def _handle_state(self, state: State) -> State:
        """Process current state and determine next state.

        Args:
            state: The current state to handle.

        Returns:
            The next state to transition to.
        """
        self.output_callback(state.name, f"Handling state: {state.name}")

        if state == State.START:
            await self.browser.navigate(
                self.service.entry_url, self.config.page_timeout
            )
            return await self._detect_state()

        elif state == State.LOGIN_REQUIRED:
            await self._human_checkpoint("AUTH", self.config.auth_timeout)
            return await self._detect_state()

        elif state == State.ACCOUNT_ACTIVE:
            await self.browser.click(self.service.selectors.cancel_link)
            await asyncio.sleep(1)  # Wait for page transition
            return await self._detect_state()

        elif state == State.ACCOUNT_CANCELLED:
            return State.COMPLETE  # Already done

        elif state == State.THIRD_PARTY_BILLING:
            self.output_callback(
                state.name, "Third-party billing detected - cannot cancel here"
            )
            return State.FAILED

        elif state == State.RETENTION_OFFER:
            await self.browser.click(self.service.selectors.decline_offer)
            await asyncio.sleep(1)
            return await self._detect_state()

        elif state == State.EXIT_SURVEY:
            await self._complete_survey()
            return await self._detect_state()

        elif state == State.FINAL_CONFIRMATION:
            if self.dry_run:
                self.output_callback(
                    state.name, "DRY RUN: Would click 'Finish Cancellation' here"
                )
                return State.COMPLETE
            await self._human_checkpoint("CONFIRM", self.config.confirm_timeout)
            await self.browser.click(self.service.selectors.confirm_cancel)
            await asyncio.sleep(2)
            return await self._detect_state()

        elif state == State.UNKNOWN:
            # Try AI interpretation
            if self.ai:
                screenshot = await self.browser.screenshot()
                ai_result = await self.ai.interpret(screenshot)
                if ai_result.confidence >= 0.7:
                    return ai_result.state
            # Ask human
            await self._human_checkpoint("UNKNOWN", self.config.auth_timeout)
            return await self._detect_state()

        else:
            return State.FAILED

    async def _detect_state(self) -> State:
        """Detect current page state using heuristic then AI.

        First tries heuristic detection for speed. If confidence is low,
        falls back to AI-based detection.

        Returns:
            The detected State.
        """
        url = await self.browser.url()
        text = await self.browser.text_content()
        screenshot_name = f"{self._step:02d}_detection.png"
        screenshot_path = self.session.screenshots_dir / screenshot_name
        await self.browser.screenshot(str(screenshot_path))

        # Try heuristic first
        result = self.heuristic.interpret(url, text)

        self.session.log_transition(
            from_state=self._current_state.name,
            to_state=result.state.name,
            trigger="detect",
            url=url,
            screenshot=str(screenshot_path),
            detection_method="heuristic",
            confidence=result.confidence,
        )

        if result.confidence >= 0.7:
            return result.state

        # Fall back to AI
        if self.ai:
            screenshot = await self.browser.screenshot()
            ai_result = await self.ai.interpret(screenshot)

            self.session.log_ai_call(
                screenshot=str(screenshot_path),
                prompt_tokens=0,  # Not tracked
                response_tokens=0,
                state=ai_result.state.name,
                confidence=ai_result.confidence,
            )

            if ai_result.confidence >= 0.5:
                return ai_result.state

        return State.UNKNOWN

    async def _human_checkpoint(self, checkpoint_type: str, timeout: int) -> None:
        """Pause for human input.

        Args:
            checkpoint_type: Type of checkpoint (AUTH, CONFIRM, UNKNOWN).
            timeout: Timeout in milliseconds.

        Raises:
            UserAborted: If user doesn't confirm or times out.
            HumanInterventionRequired: If no input callback is set.
        """
        messages = {
            "AUTH": (
                "Please log in to Netflix in the browser, "
                "then press Enter to continue..."
            ),
            "CONFIRM": (
                "WARNING: This will cancel your subscription. "
                "Type 'confirm' to proceed: "
            ),
            "UNKNOWN": (
                "Could not detect page state. "
                "Please navigate manually, then press Enter..."
            ),
        }

        self.output_callback(
            checkpoint_type, messages.get(checkpoint_type, "Press Enter to continue...")
        )

        if self.input_callback:
            response = self.input_callback(checkpoint_type, timeout)
            if checkpoint_type == "CONFIRM" and response != "confirm":
                raise UserAborted("User did not confirm cancellation")
            if response is None:
                raise UserAborted(f"Timeout waiting for {checkpoint_type}")
        else:
            raise HumanInterventionRequired(f"Need human input for {checkpoint_type}")

    async def _complete_survey(self) -> None:
        """Complete the exit survey by selecting first option and submitting."""
        try:
            await self.browser.click(self.service.selectors.survey_option)
            await asyncio.sleep(0.5)
            await self.browser.click(self.service.selectors.survey_submit)
            await asyncio.sleep(1)
        except Exception:
            # If survey fails, try to continue anyway
            pass

    def _is_terminal_state(self) -> bool:
        """Check if current state is terminal.

        Returns:
            True if current state is a terminal state.
        """
        return self._current_state in (State.COMPLETE, State.ABORTED, State.FAILED)

    def _transition_to(self, new_state: State) -> None:
        """Transition to new state.

        Args:
            new_state: The state to transition to.
        """
        self._current_state = new_state

    def _complete(
        self, success: bool, state: State, message: str
    ) -> CancellationResult:
        """Complete the session and return result.

        Args:
            success: Whether the operation succeeded.
            state: The final state.
            message: Result message.

        Returns:
            CancellationResult with session details.
        """
        self.session.complete(
            result="success" if success else "failed",
            final_state=state.name,
            error=None if success else message,
        )
        return CancellationResult(
            success=success,
            state=state,
            message=message,
            session_dir=self.session.session_dir,
            effective_date=None,
        )

    def _get_result_message(self) -> str:
        """Get message for final state.

        Returns:
            Human-readable message for the final state.
        """
        messages = {
            State.COMPLETE: "Cancellation completed successfully",
            State.ACCOUNT_CANCELLED: "Account was already cancelled",
            State.ABORTED: "Operation aborted by user",
            State.FAILED: "Cancellation failed",
        }
        return messages.get(self._current_state, "Unknown result")


async def with_retry(
    operation: Callable[[], T],
    max_retries: int = 3,
    retry_on: tuple[type[Exception], ...] = (TransientError,),
) -> T:
    """Execute operation with retry for transient failures.

    Implements exponential backoff between retries.

    Args:
        operation: Async callable to execute.
        max_retries: Maximum number of attempts.
        retry_on: Tuple of exception types to retry on.

    Returns:
        The result of the operation.

    Raises:
        The last exception if all retries fail.
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except retry_on as e:
            last_error = e
            await asyncio.sleep(2**attempt)  # Exponential backoff
    if last_error:
        raise last_error
    raise RuntimeError("No retries attempted")
