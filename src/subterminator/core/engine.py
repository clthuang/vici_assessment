"""Cancellation engine for SubTerminator.

This module provides the main orchestrator that coordinates the subscription
cancellation flow using all the components built so far.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

import anthropic

from subterminator.core.ai import HeuristicInterpreter
from subterminator.core.protocols import (
    AIInterpreterProtocol,
    BrowserProtocol,
    CancellationResult,
    ServiceProtocol,
    State,
)
from subterminator.services.selectors import SelectorConfig
from subterminator.utils.config import AppConfig
from subterminator.utils.exceptions import (
    ElementNotFound,
    HumanInterventionRequired,
    SubTerminatorError,
    TransientError,
    UserAborted,
)
from subterminator.utils.session import SessionLogger

if TYPE_CHECKING:
    from subterminator.core.agent import AIBrowserAgent

# Note: CancellationStateMachine exists in states.py for documentation and potential
# future use for strict transition validation. Currently, the engine manages states
# directly for simplicity. The state machine can be integrated if stricter validation
# is needed (see states.py for valid transitions).

logger = logging.getLogger(__name__)

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
        service: ServiceProtocol,
        browser: BrowserProtocol,
        heuristic: HeuristicInterpreter,
        ai: AIInterpreterProtocol | None,
        session: SessionLogger,
        config: AppConfig,
        output_callback: Callable[[str, str], None] | None = None,
        input_callback: Callable[[str, int], str | None] | None = None,
        use_agent: bool = False,
        agent: AIBrowserAgent | None = None,
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
            use_agent: If True, use AI-first agent mode instead of heuristic-first.
                (Deprecated: prefer using agent parameter)
            agent: Optional AIBrowserAgent for AI-driven state handling.
                If provided, delegates to agent.handle_state() for most states.
        """
        self.service = service
        self.browser = browser
        self.heuristic = heuristic
        self.ai = ai
        self.session = session
        self.config = config
        self.output_callback = output_callback or (lambda state, msg: None)
        self.input_callback = input_callback
        self.use_agent = use_agent
        self.agent = agent

        self.dry_run = False
        self._current_state = State.START
        self._step = 0
        self._action_history_cleared = False

    async def _click_selector(self, selector: SelectorConfig) -> None:
        """Click an element using SelectorConfig with CSS and optional ARIA fallback.

        Args:
            selector: SelectorConfig with css list and optional aria tuple.
        """
        await self.browser.click(
            selector.css,
            fallback_role=selector.aria,
            timeout=self.config.element_timeout,
        )

    async def run(self, dry_run: bool = False) -> CancellationResult:
        """Execute the cancellation flow.

        Args:
            dry_run: If True, stops before actual cancellation.

        Returns:
            CancellationResult indicating success or failure.
        """
        self.dry_run = dry_run

        # Use agent mode if enabled
        if self.use_agent:
            return await self._run_agent_mode(dry_run)

        # Original heuristic-first flow
        return await self._run_heuristic_mode(dry_run)

    async def _run_agent_mode(self, dry_run: bool) -> CancellationResult:
        """Execute cancellation using AI-first agent mode.

        Args:
            dry_run: If True, stops before actual cancellation.

        Returns:
            CancellationResult indicating success or failure.
        """
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.ai import ClaudeActionPlanner

        # Create planner if we have an API key
        planner = None
        if self.config.anthropic_api_key:
            planner = ClaudeActionPlanner(api_key=self.config.anthropic_api_key)

        # Create and run agent
        agent = AIBrowserAgent(
            browser=self.browser,  # type: ignore[arg-type]
            planner=planner,
            heuristic=self.heuristic,
            service=self.service,
            max_steps=self.config.max_transitions,
            input_callback=self.input_callback,
            output_callback=self.output_callback,
        )

        try:
            result = await agent.run(dry_run=dry_run)

            # Convert AgentResult to CancellationResult
            success = result.state in (State.COMPLETE, State.ACCOUNT_CANCELLED)
            self._current_state = result.state

            return self._complete(success, result.state, result.message)

        except HumanInterventionRequired as e:
            return self._complete(False, State.FAILED, str(e))
        except Exception as e:
            return self._complete(False, State.FAILED, f"Agent error: {e}")

    async def _run_heuristic_mode(self, dry_run: bool) -> CancellationResult:
        """Execute cancellation using original heuristic-first flow.

        Args:
            dry_run: If True, stops before actual cancellation.

        Returns:
            CancellationResult indicating success or failure.
        """
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
            # HIL-5: Leave browser open on abort so user can complete manually
            return self._complete(False, State.ABORTED, "User aborted the operation")
        except SubTerminatorError as e:
            # BA-4: Save HTML dump on failure for debugging
            await self._save_html_dump_on_failure()
            return self._complete(False, State.FAILED, str(e))
        finally:
            # Only close browser if not aborted (user may want to continue manually)
            if self._current_state != State.ABORTED:
                await self.browser.close()

    async def _handle_state(self, state: State) -> State:
        """Process current state and determine next state.

        AI-first architecture: Only START uses hardcoded handling (navigation).
        All other states use AI agent to analyze screenshots and decide actions.
        No fallback to hardcoded selectors - AI handles everything.

        Args:
            state: The current state to handle.

        Returns:
            The next state to transition to.
        """
        self.output_callback(state.name, f"Handling state: {state.name}")

        # Only START needs hardcoded (navigation to entry URL)
        if state == State.START:
            return await self._hardcoded_handle_state(state)

        # LOGIN_REQUIRED - still need human checkpoint but then use AI
        if state == State.LOGIN_REQUIRED:
            await self._human_checkpoint("AUTH", self.config.auth_timeout)
            await self.browser.navigate(
                self.service.entry_url, self.config.page_timeout
            )
            return await self._detect_state()

        # ALL other states use AI agent - no fallback to hardcoded
        if self.agent:
            return await self._ai_driven_handle(state)

        # No agent configured - fail gracefully
        self.output_callback(
            state.name,
            "No AI agent configured - cannot proceed with AI-first architecture"
        )
        return State.FAILED

    async def _ai_driven_handle(self, state: State) -> State:
        """Handle state using AI agent with agentic loop.

        Uses the new run_agentic_loop method for intelligent, adaptive handling
        that doesn't rely on hardcoded selectors. AI-first architecture: no
        fallback to hardcoded handlers on failure.

        Args:
            state: The current state to handle.

        Returns:
            The next state after agent handling.
        """
        # Human checkpoint for FINAL_CONFIRMATION (unless dry_run)
        if state == State.FINAL_CONFIRMATION and not self.dry_run:
            await self._human_checkpoint("CONFIRM", self.config.confirm_timeout)

        # Clear action history on first AI-driven call
        if not self._action_history_cleared:
            self.agent.clear_history()  # type: ignore[union-attr]
            self._action_history_cleared = True

        # Use agentic loop with flexible goal based on current state
        goal = self._get_agentic_goal(state)

        try:
            result = await self.agent.run_agentic_loop(goal=goal, max_actions=10)  # type: ignore[union-attr]
            return result.state
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            # AI-first: no fallback to hardcoded, just fail gracefully
            logger.warning(f"AI agent API error: {e}")
            self.output_callback(
                state.name,
                f"AI agent API error - no fallback in AI-first mode: {e}"
            )
            return State.FAILED

    def _get_agentic_goal(self, state: State) -> str:
        """Get a flexible, goal-oriented prompt for the agentic loop.

        Args:
            state: The current state.

        Returns:
            A goal string that encourages intelligent visual analysis.
        """
        goals = {
            State.ACCOUNT_ACTIVE: (
                "Cancel this subscription. Look for 'Cancel', 'Cancel plan', "
                "'Cancel membership' buttons or links. Click whatever leads "
                "to cancellation."
            ),
            State.RETENTION_OFFER: (
                "Continue with cancellation. The page may show offers or "
                "alternatives. Look for buttons to proceed with canceling - "
                "they might say 'Cancel plan', 'Continue to cancel', "
                "'Cancel anyway', or similar. If you see an expandable "
                "section (+ icon), expand it first. If there's a checkbox "
                "to confirm cancellation, check it. "
                "Then click the cancel/confirm button."
            ),
            State.EXIT_SURVEY: (
                "Complete or skip the exit survey to proceed with cancellation. "
                "Look for 'Continue', 'Submit', 'Skip', or 'Cancel' buttons."
            ),
            State.FINAL_CONFIRMATION: (
                "Confirm the cancellation. Look for 'Finish Cancellation', "
                "'Confirm', or 'Cancel plan' button to complete the process."
            ),
            State.UNKNOWN: (
                "Analyze the page and find the next step to cancel this subscription. "
                "Look for any cancel-related buttons, links, or actions."
            ),
        }
        return goals.get(state, "Continue with the subscription cancellation process.")

    async def _hardcoded_handle_state(self, state: State) -> State:
        """Process state using hardcoded logic.

        Args:
            state: The current state to handle.

        Returns:
            The next state to transition to.
        """
        if state == State.START:
            await self.browser.navigate(
                self.service.entry_url, self.config.page_timeout
            )
            return await self._detect_state()

        elif state == State.LOGIN_REQUIRED:
            await self._human_checkpoint("AUTH", self.config.auth_timeout)
            # Navigate to entry URL after login to ensure correct page for detection
            await self.browser.navigate(
                self.service.entry_url, self.config.page_timeout
            )
            return await self._detect_state()

        elif state == State.ACCOUNT_ACTIVE:
            try:
                await self._click_selector(self.service.selectors.cancel_link)
                await asyncio.sleep(1)  # Wait for page transition
                return await self._detect_state()
            except ElementNotFound as e:
                # Graceful degradation: transition to UNKNOWN for human intervention
                self.output_callback(
                    state.name,
                    f"Cancel button not found ({e}). Requesting human assistance.",
                )
                return State.UNKNOWN

        elif state == State.ACCOUNT_CANCELLED:
            return State.COMPLETE  # Already done

        elif state == State.THIRD_PARTY_BILLING:
            self.output_callback(
                state.name, "Third-party billing detected - cannot cancel here"
            )
            return State.FAILED

        elif state == State.RETENTION_OFFER:
            try:
                await self._click_selector(self.service.selectors.decline_offer)
                await asyncio.sleep(1)
                return await self._detect_state()
            except ElementNotFound as e:
                # Graceful degradation: transition to UNKNOWN for human intervention
                self.output_callback(
                    state.name,
                    f"Decline button not found ({e}). Requesting human assistance.",
                )
                return State.UNKNOWN

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
            try:
                await self._click_selector(self.service.selectors.confirm_cancel)
                await asyncio.sleep(2)
                return await self._detect_state()
            except ElementNotFound as e:
                # Graceful degradation: transition to UNKNOWN for human intervention
                self.output_callback(
                    state.name,
                    f"Confirm button not found ({e}). Requesting human assistance.",
                )
                return State.UNKNOWN

        elif state == State.UNKNOWN:
            # Try AI interpretation
            if self.ai:
                screenshot = await self.browser.screenshot()
                ai_result = await self.ai.interpret(screenshot)
                if ai_result.confidence >= 0.7:
                    return ai_result.state
            # Ask human
            await self._human_checkpoint("UNKNOWN", self.config.auth_timeout)
            # Navigate to entry URL after manual intervention for recovery
            await self.browser.navigate(
                self.service.entry_url, self.config.page_timeout
            )
            return await self._detect_state()

        else:
            return State.FAILED

    async def _detect_state(self) -> State:
        """Detect current page state using AI-first approach.

        AI-first architecture: Only trust heuristics for terminal/entry states
        (LOGIN_REQUIRED, COMPLETE, FAILED, ACCOUNT_CANCELLED, THIRD_PARTY_BILLING).
        For flow states, return UNKNOWN to trigger AI-driven handling.

        Returns:
            The detected State.
        """
        url = await self.browser.url()
        text = await self.browser.text_content()
        screenshot_name = f"{self._step:02d}_detection.png"
        screenshot_path = self.session.screenshots_dir / screenshot_name
        await self.browser.screenshot(str(screenshot_path))

        # Only use heuristic for terminal/entry states with high confidence
        if self.heuristic:
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

            # Only trust very high confidence for terminal/entry states
            terminal_entry_states = (
                State.LOGIN_REQUIRED,
                State.COMPLETE,
                State.FAILED,
                State.ACCOUNT_CANCELLED,
                State.THIRD_PARTY_BILLING,
            )
            if result.confidence >= 0.9 and result.state in terminal_entry_states:
                return result.state

        # For all flow states, return UNKNOWN to trigger AI-driven handling
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
                f"Please log in to {self.service.config.name} in the browser, "
                "then press Enter to continue..."
            ),
            "CONFIRM": (
                f"WARNING: This will cancel your {self.service.config.name} "
                "subscription. Type 'confirm' to proceed: "
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
        """Complete the exit survey by selecting first option and submitting.

        Survey completion is optional - if it fails, we log and continue
        since the cancellation can still proceed.
        """
        try:
            await self._click_selector(self.service.selectors.survey_option)
            await asyncio.sleep(0.5)
            await self._click_selector(self.service.selectors.survey_submit)
            await asyncio.sleep(1)
        except (ElementNotFound, TimeoutError) as e:
            # Survey completion is optional, log and continue
            self.output_callback("EXIT_SURVEY", f"Survey skipped: {e}")
        except Exception as e:
            # Log unexpected errors but don't block cancellation
            self.output_callback(
                "EXIT_SURVEY", f"Survey error (continuing): {type(e).__name__}: {e}"
            )

    async def _save_html_dump_on_failure(self) -> None:
        """Save HTML dump on failure for debugging (BA-4)."""
        try:
            html_content = await self.browser.html()
            html_path = self.session.screenshots_dir / f"{self._step:02d}_failure.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.output_callback("FAILED", f"HTML dump saved: {html_path}")
        except Exception:
            # Don't fail the failure handling
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
    operation: Callable[[], Awaitable[T]],
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
