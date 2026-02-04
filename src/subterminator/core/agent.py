"""AI-driven browser control agent for SubTerminator.

This module provides the AIBrowserAgent class which orchestrates AI-first
browser automation for subscription cancellation flows.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from subterminator.core.protocols import (
    ActionPlan,
    ActionRecord,
    AgentContext,
    CancellationResult,
    ErrorRecord,
    ExecutionResult,
    State,
    TargetStrategy,
    ValidationResult,
)
from subterminator.utils.exceptions import HumanInterventionRequired

if TYPE_CHECKING:
    from subterminator.core.ai import ClaudeActionPlanner, HeuristicInterpreter
    from subterminator.core.browser import PlaywrightBrowser
    from subterminator.core.protocols import PlannedAction, ServiceProtocol


# State transitions: state -> (goal description, expected next state)
STATE_TRANSITIONS: dict[State, tuple[str, State | None]] = {
    State.ACCOUNT_ACTIVE: ("Click the cancel membership link", State.RETENTION_OFFER),
    State.RETENTION_OFFER: ("Decline the retention offer", State.EXIT_SURVEY),
    State.EXIT_SURVEY: ("Complete the exit survey", State.FINAL_CONFIRMATION),
    State.FINAL_CONFIRMATION: ("Click finish cancellation", State.COMPLETE),
    State.UNKNOWN: ("Analyze the page and determine next action", None),
}


@dataclass
class AgentResult:
    """Result of an agent run.

    Attributes:
        state: Final state reached.
        message: Human-readable result message.
        steps: Number of steps taken.
    """

    state: State
    message: str
    steps: int = 0


class AIBrowserAgent:
    """AI-driven browser control agent.

    Orchestrates browser automation using AI-first approach with
    heuristic fallback. Coordinates planner, browser, and human
    checkpoints for subscription cancellation flows.

    Example:
        >>> agent = AIBrowserAgent(
        ...     browser=PlaywrightBrowser(),
        ...     planner=ClaudeActionPlanner(),
        ...     heuristic=HeuristicInterpreter(),
        ...     service=NetflixService()
        ... )
        >>> result = await agent.run()
    """

    TERMINAL_STATES = frozenset([State.COMPLETE, State.FAILED, State.ABORTED])
    HUMAN_CHECKPOINT_STATES = frozenset([State.LOGIN_REQUIRED, State.FINAL_CONFIRMATION])

    def __init__(
        self,
        browser: "PlaywrightBrowser",
        planner: "ClaudeActionPlanner | None" = None,
        heuristic: "HeuristicInterpreter | None" = None,
        service: "ServiceProtocol | None" = None,
        max_steps: int = 20,
        max_retries: int = 3,
        heuristic_threshold: float = 0.8,
        input_callback: Callable[[str, int], str | None] | None = None,
        output_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """Initialize the AIBrowserAgent.

        Args:
            browser: Browser automation instance.
            planner: AI action planner (optional).
            heuristic: Heuristic interpreter for fast state detection (optional).
            service: Service configuration (optional).
            max_steps: Maximum number of steps before failing.
            max_retries: Maximum retry attempts per action (default 3).
            heuristic_threshold: Confidence threshold for using heuristic result.
            input_callback: Callback for human input.
            output_callback: Callback for status output.

        Raises:
            ValueError: If max_retries is less than 1.
        """
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        self.browser = browser
        self.planner = planner
        self.heuristic = heuristic
        self.service = service
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.heuristic_threshold = heuristic_threshold
        self.input_callback = input_callback
        self.output_callback = output_callback or (lambda s, m: None)

        self.current_state = State.START
        self._step = 0
        self._dry_run = False
        self._action_history: list[ActionRecord] = []
        self._error_history: list[ErrorRecord] = []

    async def run(self, dry_run: bool = False) -> AgentResult:
        """Execute the AI-driven browser automation flow.

        Args:
            dry_run: If True, skip final confirmation without executing.

        Returns:
            AgentResult with final state and message.
        """
        self._dry_run = dry_run
        self._step = 0

        try:
            await self.browser.launch()

            if self.service:
                await self.browser.navigate(self.service.entry_url)

            while not self._is_terminal():
                if self._step >= self.max_steps:
                    self.current_state = State.FAILED
                    return AgentResult(
                        state=State.FAILED,
                        message="Max steps exceeded",
                        steps=self._step
                    )

                await self._step_once()
                self._step += 1

            return AgentResult(
                state=self.current_state,
                message=self._get_result_message(),
                steps=self._step
            )

        except HumanInterventionRequired:
            raise
        except Exception as e:
            self.current_state = State.FAILED
            return AgentResult(
                state=State.FAILED,
                message=f"Error: {e}",
                steps=self._step
            )
        finally:
            await self.browser.close()

    async def _step_once(self) -> None:
        """Execute one step of the automation flow."""
        # Get current page state
        screenshot = await self.browser.screenshot()
        url = await self.browser.url()
        text = await self.browser.text_content()

        # Try heuristic first
        if self.heuristic:
            heuristic_result = self.heuristic.interpret(url, text)
            if heuristic_result.confidence >= self.heuristic_threshold:
                self.current_state = heuristic_result.state
                self.output_callback(
                    self.current_state.name,
                    f"Heuristic: {heuristic_result.reasoning}"
                )

                # Check for human checkpoint
                if await self._check_human_checkpoint():
                    return

                # For terminal states from heuristic, we're done
                if self._is_terminal():
                    return

        # Fall back to AI planner
        if self.planner:
            accessibility_tree = await self.browser.accessibility_snapshot()
            planned = await self.planner.plan(screenshot, url, accessibility_tree)

            self.current_state = planned.state
            self.output_callback(
                self.current_state.name,
                f"AI: {planned.reasoning}"
            )

            # Check for human checkpoint
            if await self._check_human_checkpoint():
                return

            # Execute the planned action
            if not self._is_terminal():
                await self.browser.execute_action(planned.action)
                await self.browser.wait_for_navigation()
        else:
            # No planner, just use heuristic state
            if self._is_terminal():
                return
            # No action to take without planner
            self.current_state = State.UNKNOWN

    async def _check_human_checkpoint(self) -> bool:
        """Check and handle human checkpoint states.

        Returns:
            True if checkpoint was handled, False otherwise.
        """
        if self.current_state not in self.HUMAN_CHECKPOINT_STATES:
            return False

        # Handle LOGIN_REQUIRED
        if self.current_state == State.LOGIN_REQUIRED:
            if self.input_callback is None:
                raise HumanInterventionRequired("Login required")

            self.output_callback(
                "AUTH",
                "Please log in, then press Enter to continue..."
            )
            self.input_callback("AUTH", 0)
            # After login, we need to re-detect state
            return True

        # Handle FINAL_CONFIRMATION
        if self.current_state == State.FINAL_CONFIRMATION:
            if self._dry_run:
                self.output_callback(
                    "DRY_RUN",
                    "Would confirm cancellation here (dry run)"
                )
                self.current_state = State.COMPLETE
                return True

            if self.input_callback is None:
                raise HumanInterventionRequired("Final confirmation required")

            self.output_callback(
                "CONFIRM",
                "Type 'confirm' to proceed with cancellation..."
            )
            response = self.input_callback("CONFIRM", 0)
            if response != "confirm":
                self.current_state = State.ABORTED
                return True

            # Continue to execute confirmation
            return False

        return False

    def _is_terminal(self) -> bool:
        """Check if current state is terminal."""
        return self.current_state in self.TERMINAL_STATES

    def _get_result_message(self) -> str:
        """Get message for final state."""
        messages = {
            State.COMPLETE: "Cancellation completed successfully",
            State.FAILED: "Cancellation failed",
            State.ABORTED: "Operation aborted",
        }
        return messages.get(self.current_state, "Unknown result")

    # =====================================================================
    # SPEC-REQUIRED METHODS (per design.md Section 4)
    # =====================================================================

    def clear_history(self) -> None:
        """Clear action and error history.

        Should be called when starting a new state handling session.
        """
        self._action_history.clear()
        self._error_history.clear()

    def _record_action(self, record: ActionRecord) -> None:
        """Record a completed action in history.

        Args:
            record: The ActionRecord to add to history.
        """
        self._action_history.append(record)

    def _record_error(self, record: ErrorRecord) -> None:
        """Record an error in history.

        Args:
            record: The ErrorRecord to add to history.
        """
        self._error_history.append(record)

    async def _gather_accessibility_tree(self) -> str:
        """Gather the accessibility tree from the browser.

        Returns:
            JSON string of the accessibility tree.
        """
        try:
            return await self.browser.accessibility_tree()
        except Exception:
            return "{}"

    async def _extract_html_snippet(self) -> str:
        """Extract interactive HTML elements from the current viewport.

        Uses JavaScript to find interactive elements (buttons, links, inputs)
        that are currently visible in the viewport.

        Returns:
            HTML snippet of interactive elements, truncated to 5000 chars.
        """
        script = """() => {
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            const selectors = 'button, a, input, select, [role="button"], [role="link"]';
            const elements = document.querySelectorAll(selectors);
            const results = [];
            for (const el of elements) {
                const rect = el.getBoundingClientRect();
                if (rect.bottom > 0 && rect.top < vh && rect.right > 0 && rect.left < vw) {
                    let html = el.outerHTML;
                    if (html.length > 500) {
                        const tag = el.tagName.toLowerCase();
                        html = '<' + tag + '>...truncated</' + tag + '>';
                    }
                    results.push(html);
                }
            }
            return results.slice(0, 50);
        }"""
        try:
            elements = await self.browser.evaluate(script)
            return "\n".join(elements)[:5000]
        except Exception:
            return ""

    async def perceive(self) -> AgentContext:
        """Gather context from the browser for decision making.

        Collects screenshot, accessibility tree, HTML snippet, URL,
        visible text, viewport size, and scroll position.

        Returns:
            AgentContext with all gathered information.
        """
        screenshot = await self.browser.screenshot()
        a11y_tree = await self._gather_accessibility_tree()
        html_snippet = await self._extract_html_snippet()
        url = await self.browser.url()
        visible_text = await self.browser.text_content()
        viewport = await self.browser.viewport_size()
        scroll = await self.browser.scroll_position()

        return AgentContext(
            screenshot=screenshot,
            accessibility_tree=a11y_tree,
            html_snippet=html_snippet,
            url=url,
            visible_text=visible_text,
            previous_actions=list(self._action_history),
            error_history=list(self._error_history),
            viewport_size=viewport,
            scroll_position=scroll,
        )

    async def plan(self, context: AgentContext, goal: str) -> ActionPlan:
        """Generate an action plan using the AI planner.

        Args:
            context: Current page context.
            goal: Description of what we're trying to achieve.

        Returns:
            ActionPlan with targeting strategies.

        Raises:
            RuntimeError: If no planner is configured.
        """
        if not self.planner:
            raise RuntimeError("No planner configured for AIBrowserAgent")

        return await self.planner.plan_action(context, goal)

    async def _try_target_strategy(
        self,
        strategy: TargetStrategy,
        action_type: str,
        value: str | None,
        use_bbox: bool = True,
    ) -> bool:
        """Attempt to execute an action using a specific targeting strategy.

        Args:
            strategy: The targeting strategy to use.
            action_type: Type of action (click, fill, select).
            value: Value for fill/select actions.
            use_bbox: If True, use bounding box method for clicks (more reliable).

        Returns:
            True if the action succeeded, False otherwise.
        """
        try:
            # For click actions, prefer bounding box method for reliability
            if action_type == "click" and use_bbox:
                result = await self._try_bbox_click(strategy)
                if result:
                    return True
                # Fall through to standard methods if bbox fails

            if strategy.method == "css" and strategy.css_selector:
                if action_type == "click":
                    await self.browser.click(strategy.css_selector)
                elif action_type == "fill" and value:
                    await self.browser.fill(strategy.css_selector, value)
                elif action_type == "select":
                    await self.browser.select_option(strategy.css_selector, value)
                return True

            elif strategy.method == "aria" and strategy.aria_role:
                await self.browser.click_by_role(
                    strategy.aria_role,
                    strategy.aria_name
                )
                return True

            elif strategy.method == "text" and strategy.text_content:
                await self.browser.click_by_text(strategy.text_content)
                return True

            elif strategy.method == "coordinates" and strategy.coordinates:
                x, y = strategy.coordinates
                await self.browser.click_coordinates(x, y)
                return True

            return False

        except Exception:
            return False

    async def _try_bbox_click(self, strategy: TargetStrategy) -> bool:
        """Try to click using bounding box method for reliability.

        Uses JavaScript to find the element and click at its center.
        This is more reliable than Playwright's click() on complex UIs.

        Args:
            strategy: The targeting strategy with element identification.

        Returns:
            True if click succeeded, False otherwise.
        """
        try:
            # Check if browser supports bbox clicking
            if not hasattr(self.browser, "click_by_bbox"):
                return False

            if strategy.method == "css" and strategy.css_selector:
                result = await self.browser.click_by_bbox(
                    selector=strategy.css_selector
                )
                return result.get("clicked", False)

            elif strategy.method == "aria" and strategy.aria_role:
                result = await self.browser.click_by_bbox(
                    aria_role=strategy.aria_role,
                    aria_name=strategy.aria_name
                )
                return result.get("clicked", False)

            elif strategy.method == "text" and strategy.text_content:
                result = await self.browser.click_by_bbox(
                    text=strategy.text_content
                )
                return result.get("clicked", False)

            return False

        except Exception:
            return False

    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute an action plan, trying strategies in order.

        Attempts primary target first, then fallbacks until one succeeds.

        Args:
            plan: The action plan to execute.

        Returns:
            ExecutionResult indicating success/failure and which strategy worked.
        """
        start = time.time()

        for strategy in plan.all_targets():
            success = await self._try_target_strategy(
                strategy, plan.action_type, plan.value
            )
            if success:
                elapsed = int((time.time() - start) * 1000)
                self._record_action(
                    ActionRecord(
                        action_type=plan.action_type,
                        target_description=strategy.describe(),
                        success=True,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    )
                )
                return ExecutionResult(
                    success=True,
                    action_plan=plan,
                    strategy_used=strategy,
                    elapsed_ms=elapsed,
                )

        # All strategies failed
        elapsed = int((time.time() - start) * 1000)
        self._record_error(
            ErrorRecord(
                action_type=plan.action_type,
                error_type="AllStrategiesFailed",
                error_message="All strategies failed",
                strategy_attempted="all",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        )
        return ExecutionResult(
            success=False,
            action_plan=plan,
            error="All strategies failed",
            elapsed_ms=elapsed,
        )

    def _is_valid_state_progression(
        self,
        expected: State,
        actual: State,
    ) -> bool:
        """Check if the actual state represents valid progression.

        Args:
            expected: The expected state after action.
            actual: The actual state detected.

        Returns:
            True if progression is valid, False otherwise.
        """
        # UNKNOWN expected means any forward progress is OK
        if expected == State.UNKNOWN:
            return actual not in (State.FAILED, State.UNKNOWN)

        # Terminal states are always valid if reached
        if actual in (State.COMPLETE, State.ACCOUNT_CANCELLED):
            return True

        # Exact match is always valid
        if actual == expected:
            return True

        # Allow skipping states (e.g., going from ACCOUNT_ACTIVE to EXIT_SURVEY)
        forward_states = [
            State.ACCOUNT_ACTIVE,
            State.RETENTION_OFFER,
            State.EXIT_SURVEY,
            State.FINAL_CONFIRMATION,
            State.COMPLETE,
        ]
        if expected in forward_states and actual in forward_states:
            expected_idx = forward_states.index(expected)
            actual_idx = forward_states.index(actual)
            return actual_idx >= expected_idx

        return False

    async def validate(self, result: ExecutionResult) -> ValidationResult:
        """Validate the page state after executing an action.

        Uses the heuristic interpreter to determine actual state
        and compares against expected state.

        Args:
            result: The execution result to validate.

        Returns:
            ValidationResult indicating success and state comparison.
        """
        url = await self.browser.url()
        text = await self.browser.text_content()

        if self.heuristic:
            interpretation = self.heuristic.interpret(url, text)
            actual = interpretation.state
            confidence = interpretation.confidence
        else:
            actual = State.UNKNOWN
            confidence = 0.0

        expected = result.action_plan.expected_state or State.UNKNOWN
        success = self._is_valid_state_progression(expected, actual)

        return ValidationResult(
            success=success,
            expected_state=expected,
            actual_state=actual,
            confidence=confidence,
            message=f"Expected {expected.name}, got {actual.name}",
        )

    async def self_correct(
        self,
        context: AgentContext,
        failure: ValidationResult,
        attempt: int,
    ) -> ActionPlan:
        """Generate a corrected action plan after a failure.

        Args:
            context: Current page context.
            failure: The validation result showing what went wrong.
            attempt: Current attempt number (1-indexed).

        Returns:
            New ActionPlan with different targeting strategies.

        Raises:
            RuntimeError: If no planner is configured.
        """
        if not self.planner:
            raise RuntimeError("No planner configured for AIBrowserAgent")

        # Build error context for the planner
        error_context = self.planner.SELF_CORRECT_PROMPT.format(
            action_type="unknown",
            target_description="previous target",
            failed_strategy="previous strategy",
            error_message=failure.message,
            strategies_tried="\n".join(
                f"- {e.strategy_attempted}: {e.error_message}"
                for e in self._error_history
            ),
        )

        # Get the goal from state transitions
        goal_info = STATE_TRANSITIONS.get(
            failure.actual_state,
            ("Analyze and take corrective action", None)
        )
        goal = goal_info[0]

        return await self.planner.plan_action(context, goal, error_context)

    async def handle_state(self, state: State) -> State:
        """Handle a single state using the perceive-plan-execute-validate loop.

        This is the main entry point for AI-driven state handling.
        Implements self-correction with retry on failure.

        Args:
            state: The current state to handle.

        Returns:
            The new state after handling (may be the actual detected state).
        """
        # Get goal and expected state for this state
        goal_info = STATE_TRANSITIONS.get(state, ("Analyze and act", None))
        goal, expected = goal_info

        validation: ValidationResult | None = None

        for attempt in range(1, self.max_retries + 1):
            context = await self.perceive()

            # Plan action
            if attempt == 1:
                plan = await self.plan(context, goal)
            else:
                # Self-correct on subsequent attempts
                if validation:
                    plan = await self.self_correct(context, validation, attempt)
                else:
                    plan = await self.plan(context, goal)

            # Update expected state if not set
            if plan.expected_state is None and expected is not None:
                # Create new plan with expected_state set
                plan = ActionPlan(
                    action_type=plan.action_type,
                    primary_target=plan.primary_target,
                    fallback_targets=plan.fallback_targets,
                    value=plan.value,
                    reasoning=plan.reasoning,
                    confidence=plan.confidence,
                    expected_state=expected,
                )

            # Execute the plan
            result = await self.execute(plan)
            if not result.success:
                continue

            # Validate the result
            validation = await self.validate(result)
            if validation.success:
                return validation.actual_state

        # All retries exhausted
        return State.UNKNOWN
