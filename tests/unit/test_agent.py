"""Unit tests for AIBrowserAgent.

Tests cover:
- AIBrowserAgent initialization
- run() method orchestration
- State transitions and action execution
- Error handling and recovery
- Human checkpoint integration
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from subterminator.core.protocols import (
    ActionType,
    AIInterpretation,
    BrowserAction,
    PlannedAction,
    State,
)


# --- Test Fixtures and Helpers ---


def create_mock_browser() -> AsyncMock:
    """Create a mock browser with common async methods."""
    mock_browser = AsyncMock()
    mock_browser.launch = AsyncMock()
    mock_browser.close = AsyncMock()
    mock_browser.navigate = AsyncMock()
    mock_browser.screenshot = AsyncMock(return_value=b"fake_screenshot")
    mock_browser.url = AsyncMock(return_value="https://example.com/account")
    mock_browser.text_content = AsyncMock(return_value="Account page")
    mock_browser.accessibility_snapshot = AsyncMock(return_value={"role": "WebArea", "children": []})
    mock_browser.execute_action = AsyncMock()
    mock_browser.wait_for_navigation = AsyncMock()
    return mock_browser


def create_mock_planner(state: State = State.ACCOUNT_ACTIVE) -> Mock:
    """Create a mock planner that returns a specific state."""
    action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
    planned_action = PlannedAction(
        state=state,
        action=action,
        reasoning="Test action"
    )
    mock_planner = Mock()
    mock_planner.plan = AsyncMock(return_value=planned_action)
    return mock_planner


def create_mock_heuristic(state: State = State.ACCOUNT_ACTIVE, confidence: float = 0.9) -> Mock:
    """Create a mock heuristic interpreter."""
    interpretation = AIInterpretation(
        state=state,
        confidence=confidence,
        reasoning="Heuristic test",
        actions=[]
    )
    mock_heuristic = Mock()
    mock_heuristic.interpret = Mock(return_value=interpretation)
    return mock_heuristic


# --- Tests ---


class TestAIBrowserAgentInit:
    """Tests for AIBrowserAgent initialization (Task 4.2)."""

    def test_agent_initializes_with_browser(self) -> None:
        """Agent should accept browser parameter."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        agent = AIBrowserAgent(browser=mock_browser)
        assert agent.browser is mock_browser

    def test_agent_initializes_with_planner(self) -> None:
        """Agent should accept planner parameter."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner()
        agent = AIBrowserAgent(browser=mock_browser, planner=mock_planner)
        assert agent.planner is mock_planner

    def test_agent_initializes_with_heuristic(self) -> None:
        """Agent should accept heuristic parameter."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_heuristic = create_mock_heuristic()
        agent = AIBrowserAgent(browser=mock_browser, heuristic=mock_heuristic)
        assert agent.heuristic is mock_heuristic

    def test_agent_initializes_with_service(self) -> None:
        """Agent should accept service parameter."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"
        agent = AIBrowserAgent(browser=mock_browser, service=mock_service)
        assert agent.service is mock_service

    def test_agent_tracks_current_state(self) -> None:
        """Agent should track current state, starting at START."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        agent = AIBrowserAgent(browser=mock_browser)
        assert agent.current_state == State.START


class TestAIBrowserAgentRun:
    """Tests for AIBrowserAgent.run() method (Tasks 4.3-4.5)."""

    @pytest.mark.asyncio
    async def test_run_launches_browser(self) -> None:
        """run() should launch browser."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.COMPLETE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service
        )

        await agent.run()

        mock_browser.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_navigates_to_entry_url(self) -> None:
        """run() should navigate to service entry URL."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.COMPLETE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com/cancel"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service
        )

        await agent.run()

        mock_browser.navigate.assert_called_with("https://example.com/cancel")

    @pytest.mark.asyncio
    async def test_run_calls_planner(self) -> None:
        """run() should call planner to get next action."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.COMPLETE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service
        )

        await agent.run()

        mock_planner.plan.assert_called()

    @pytest.mark.asyncio
    async def test_run_executes_action(self) -> None:
        """run() should execute the planned action."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()

        # First call returns ACCOUNT_ACTIVE with click action
        # Second call returns COMPLETE
        action1 = BrowserAction(action_type=ActionType.CLICK, selector="#cancel")
        planned1 = PlannedAction(state=State.ACCOUNT_ACTIVE, action=action1, reasoning="Click")
        action2 = BrowserAction(action_type=ActionType.WAIT, selector="")
        planned2 = PlannedAction(state=State.COMPLETE, action=action2, reasoning="Done")

        mock_planner = Mock()
        mock_planner.plan = AsyncMock(side_effect=[planned1, planned2])

        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service,
            max_steps=5
        )

        await agent.run()

        # Should have executed the click action
        assert mock_browser.execute_action.call_count >= 1

    @pytest.mark.asyncio
    async def test_run_stops_at_terminal_state(self) -> None:
        """run() should stop when reaching terminal state."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.COMPLETE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service
        )

        result = await agent.run()

        assert result.state in (State.COMPLETE, State.FAILED, State.ABORTED)


class TestAIBrowserAgentHeuristicFallback:
    """Tests for heuristic fallback behavior (Tasks 4.6-4.7)."""

    @pytest.mark.asyncio
    async def test_uses_heuristic_when_confidence_high(self) -> None:
        """Agent should use heuristic when confidence is high."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_heuristic = create_mock_heuristic(state=State.COMPLETE, confidence=0.95)
        mock_planner = create_mock_planner(state=State.ACCOUNT_ACTIVE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            heuristic=mock_heuristic,
            service=mock_service,
            heuristic_threshold=0.8
        )

        await agent.run()

        # Heuristic should be called
        mock_heuristic.interpret.assert_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_planner_when_heuristic_low_confidence(self) -> None:
        """Agent should use planner when heuristic confidence is low."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_heuristic = create_mock_heuristic(state=State.UNKNOWN, confidence=0.3)
        mock_planner = create_mock_planner(state=State.COMPLETE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            heuristic=mock_heuristic,
            service=mock_service,
            heuristic_threshold=0.8
        )

        await agent.run()

        # Both should be called
        mock_heuristic.interpret.assert_called()
        mock_planner.plan.assert_called()


class TestAIBrowserAgentMaxSteps:
    """Tests for max steps limit (Task 4.8)."""

    @pytest.mark.asyncio
    async def test_stops_at_max_steps(self) -> None:
        """Agent should stop after max_steps iterations."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        # Planner always returns non-terminal state
        mock_planner = create_mock_planner(state=State.ACCOUNT_ACTIVE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service,
            max_steps=3
        )

        result = await agent.run()

        # Should have stopped due to max steps
        assert result.state == State.FAILED
        assert "max" in result.message.lower() or "step" in result.message.lower()


class TestAIBrowserAgentHumanCheckpoints:
    """Tests for human checkpoint integration (Tasks 4.9-4.10)."""

    @pytest.mark.asyncio
    async def test_pauses_at_login_required(self) -> None:
        """Agent should pause for human at LOGIN_REQUIRED state."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.utils.exceptions import HumanInterventionRequired

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.LOGIN_REQUIRED)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service,
            input_callback=None  # No callback means intervention required
        )

        with pytest.raises(HumanInterventionRequired):
            await agent.run()

    @pytest.mark.asyncio
    async def test_pauses_at_final_confirmation(self) -> None:
        """Agent should pause for human at FINAL_CONFIRMATION state."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.utils.exceptions import HumanInterventionRequired

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.FINAL_CONFIRMATION)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service,
            input_callback=None
        )

        with pytest.raises(HumanInterventionRequired):
            await agent.run()

    @pytest.mark.asyncio
    async def test_continues_after_login_callback(self) -> None:
        """Agent should continue after human completes login."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()

        # First returns LOGIN_REQUIRED, second returns COMPLETE
        action1 = BrowserAction(action_type=ActionType.WAIT, selector="")
        planned1 = PlannedAction(state=State.LOGIN_REQUIRED, action=action1, reasoning="Login")
        action2 = BrowserAction(action_type=ActionType.WAIT, selector="")
        planned2 = PlannedAction(state=State.COMPLETE, action=action2, reasoning="Done")

        mock_planner = Mock()
        mock_planner.plan = AsyncMock(side_effect=[planned1, planned2])

        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        # Input callback that allows proceeding
        input_callback = Mock(return_value="")

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service,
            input_callback=input_callback
        )

        result = await agent.run()

        assert result.state == State.COMPLETE


class TestAIBrowserAgentDryRun:
    """Tests for dry run mode (Task 4.11)."""

    @pytest.mark.asyncio
    async def test_dry_run_skips_final_confirmation(self) -> None:
        """Dry run should skip FINAL_CONFIRMATION without executing."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_planner = create_mock_planner(state=State.FINAL_CONFIRMATION)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service
        )

        result = await agent.run(dry_run=True)

        # Should complete without human checkpoint
        assert result.state == State.COMPLETE


class TestAIBrowserAgentErrorHandling:
    """Tests for error handling (Task 4.12)."""

    @pytest.mark.asyncio
    async def test_handles_browser_error(self) -> None:
        """Agent should handle browser errors gracefully."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_browser.execute_action = AsyncMock(side_effect=Exception("Browser error"))

        mock_planner = create_mock_planner(state=State.ACCOUNT_ACTIVE)
        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            service=mock_service
        )

        result = await agent.run()

        assert result.state == State.FAILED

    @pytest.mark.asyncio
    async def test_closes_browser_on_error(self) -> None:
        """Agent should close browser even on error."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        mock_browser.navigate = AsyncMock(side_effect=Exception("Navigation error"))

        mock_service = Mock()
        mock_service.entry_url = "https://example.com"

        agent = AIBrowserAgent(
            browser=mock_browser,
            service=mock_service
        )

        try:
            await agent.run()
        except Exception:
            pass

        mock_browser.close.assert_called()


class TestAIBrowserAgentModuleExports:
    """Tests for module exports."""

    def test_agent_importable_from_agent(self) -> None:
        """AIBrowserAgent should be importable from agent module."""
        from subterminator.core.agent import AIBrowserAgent

        assert AIBrowserAgent is not None

    def test_agent_importable_from_core(self) -> None:
        """AIBrowserAgent should be importable from core."""
        from subterminator.core import AIBrowserAgent

        assert AIBrowserAgent is not None


# --- Spec-required method tests ---


class TestAIBrowserAgentMaxRetries:
    """Tests for max_retries parameter validation."""

    def test_max_retries_defaults_to_three(self) -> None:
        """Agent should have max_retries default of 3."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        agent = AIBrowserAgent(browser=mock_browser)
        assert agent.max_retries == 3

    def test_max_retries_can_be_set(self) -> None:
        """Agent should accept custom max_retries value."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        agent = AIBrowserAgent(browser=mock_browser, max_retries=5)
        assert agent.max_retries == 5

    def test_max_retries_validation_rejects_zero(self) -> None:
        """Agent should reject max_retries < 1."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        with pytest.raises(ValueError, match="max_retries must be at least 1"):
            AIBrowserAgent(browser=mock_browser, max_retries=0)

    def test_max_retries_validation_rejects_negative(self) -> None:
        """Agent should reject negative max_retries."""
        from subterminator.core.agent import AIBrowserAgent

        mock_browser = create_mock_browser()
        with pytest.raises(ValueError, match="max_retries must be at least 1"):
            AIBrowserAgent(browser=mock_browser, max_retries=-1)


class TestAIBrowserAgentPerceive:
    """Tests for perceive() method."""

    @pytest.mark.asyncio
    async def test_perceive_returns_agent_context(self) -> None:
        """perceive() should return AgentContext with all fields."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import AgentContext

        mock_browser = create_mock_browser()
        mock_browser.accessibility_tree = AsyncMock(return_value='{"role": "WebArea"}')
        mock_browser.evaluate = AsyncMock(return_value=["<button>Click</button>"])
        mock_browser.viewport_size = AsyncMock(return_value=(1280, 720))
        mock_browser.scroll_position = AsyncMock(return_value=(0, 100))

        agent = AIBrowserAgent(browser=mock_browser)

        context = await agent.perceive()

        assert isinstance(context, AgentContext)
        assert context.screenshot == b"fake_screenshot"
        assert context.url == "https://example.com/account"
        assert context.viewport_size == (1280, 720)
        assert context.scroll_position == (0, 100)

    @pytest.mark.asyncio
    async def test_perceive_includes_action_history(self) -> None:
        """perceive() should include previous actions in context."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionRecord

        mock_browser = create_mock_browser()
        mock_browser.accessibility_tree = AsyncMock(return_value='{}')
        mock_browser.evaluate = AsyncMock(return_value=[])
        mock_browser.viewport_size = AsyncMock(return_value=(1280, 720))
        mock_browser.scroll_position = AsyncMock(return_value=(0, 0))

        agent = AIBrowserAgent(browser=mock_browser)

        # Add some action history
        record = ActionRecord(
            action_type="click",
            target_description="CSS: #btn",
            success=True,
            timestamp="2024-01-01T00:00:00Z"
        )
        agent._record_action(record)

        context = await agent.perceive()

        assert len(context.previous_actions) == 1
        assert context.previous_actions[0].action_type == "click"


class TestAIBrowserAgentExecute:
    """Tests for execute() method with fallback chain."""

    @pytest.mark.asyncio
    async def test_execute_tries_fallback_chain(self) -> None:
        """execute() should try fallback targets when primary fails."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        mock_browser = create_mock_browser()
        # Bbox click fails, so it falls through to standard click
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": False})
        # First click fails, second succeeds
        mock_browser.click = AsyncMock(side_effect=[Exception("not found"), None])

        agent = AIBrowserAgent(browser=mock_browser)

        plan = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#primary"),
            fallback_targets=[
                TargetStrategy(method="css", css_selector="#fallback")
            ],
            reasoning="Test",
            confidence=0.9,
        )

        result = await agent.execute(plan)

        assert result.success is True
        assert result.strategy_used.css_selector == "#fallback"

    @pytest.mark.asyncio
    async def test_execute_returns_failure_when_all_fail(self) -> None:
        """execute() should return failure when all strategies fail."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        mock_browser = create_mock_browser()
        # Bbox click fails, so it falls through to standard click
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": False})
        mock_browser.click = AsyncMock(side_effect=Exception("not found"))

        agent = AIBrowserAgent(browser=mock_browser)

        plan = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#primary"),
            reasoning="Test",
            confidence=0.9,
        )

        result = await agent.execute(plan)

        assert result.success is False
        assert result.error == "All strategies failed"

    @pytest.mark.asyncio
    async def test_execute_tries_aria_strategy(self) -> None:
        """execute() should try ARIA targeting strategy."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        mock_browser = create_mock_browser()
        # Bbox click fails, so it falls through to standard click_by_role
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": False})
        mock_browser.click_by_role = AsyncMock(return_value=None)

        agent = AIBrowserAgent(browser=mock_browser)

        plan = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(
                method="aria", aria_role="button", aria_name="Submit"
            ),
            reasoning="Test",
            confidence=0.9,
        )

        result = await agent.execute(plan)

        assert result.success is True
        mock_browser.click_by_role.assert_called_once_with("button", "Submit")


class TestAIBrowserAgentValidate:
    """Tests for validate() method."""

    @pytest.mark.asyncio
    async def test_validate_uses_heuristic(self) -> None:
        """validate() should use heuristic interpreter."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        mock_browser = create_mock_browser()
        mock_heuristic = create_mock_heuristic(state=State.RETENTION_OFFER, confidence=0.9)

        agent = AIBrowserAgent(browser=mock_browser, heuristic=mock_heuristic)

        plan = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#btn"),
            reasoning="Test",
            confidence=0.9,
            expected_state=State.RETENTION_OFFER,
        )
        # Create a mock ExecutionResult
        from subterminator.core.protocols import ExecutionResult

        exec_result = ExecutionResult(
            success=True,
            action_plan=plan,
            strategy_used=plan.primary_target,
        )

        validation = await agent.validate(exec_result)

        assert validation.success is True
        assert validation.actual_state == State.RETENTION_OFFER
        mock_heuristic.interpret.assert_called()

    @pytest.mark.asyncio
    async def test_validate_detects_state_mismatch(self) -> None:
        """validate() should detect when actual state differs from expected."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, ExecutionResult, TargetStrategy

        mock_browser = create_mock_browser()
        mock_heuristic = create_mock_heuristic(state=State.FAILED, confidence=0.9)

        agent = AIBrowserAgent(browser=mock_browser, heuristic=mock_heuristic)

        plan = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#btn"),
            reasoning="Test",
            confidence=0.9,
            expected_state=State.RETENTION_OFFER,
        )
        exec_result = ExecutionResult(
            success=True,
            action_plan=plan,
            strategy_used=plan.primary_target,
        )

        validation = await agent.validate(exec_result)

        assert validation.success is False
        assert validation.expected_state == State.RETENTION_OFFER
        assert validation.actual_state == State.FAILED


class TestAIBrowserAgentHandleState:
    """Tests for handle_state() method."""

    @pytest.mark.asyncio
    async def test_handle_state_loops_with_self_correction(self) -> None:
        """handle_state() should retry with self-correction on failure."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        mock_browser = create_mock_browser()
        mock_browser.accessibility_tree = AsyncMock(return_value='{}')
        mock_browser.evaluate = AsyncMock(return_value=[])
        mock_browser.viewport_size = AsyncMock(return_value=(1280, 720))
        mock_browser.scroll_position = AsyncMock(return_value=(0, 0))
        # Bbox click fails, so it falls through to standard click
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": False})
        # First click fails, second succeeds
        mock_browser.click = AsyncMock(side_effect=[Exception("fail"), None])

        # Heuristic returns RETENTION_OFFER after success
        mock_heuristic = create_mock_heuristic(state=State.RETENTION_OFFER, confidence=0.9)

        # Planner returns action plans
        plan1 = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#wrong"),
            reasoning="First try",
            confidence=0.9,
            expected_state=State.RETENTION_OFFER,
        )
        plan2 = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#correct"),
            reasoning="Second try",
            confidence=0.9,
            expected_state=State.RETENTION_OFFER,
        )
        mock_planner = Mock()
        mock_planner.plan_action = AsyncMock(side_effect=[plan1, plan2])
        mock_planner.SELF_CORRECT_PROMPT = "Self-correct: {action_type} {target_description} {failed_strategy} {error_message} {strategies_tried}"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            heuristic=mock_heuristic,
            max_retries=3
        )

        result = await agent.handle_state(State.ACCOUNT_ACTIVE)

        assert result == State.RETENTION_OFFER
        # Planner should be called twice (first plan + self-correct)
        assert mock_planner.plan_action.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_state_returns_unknown_after_max_retries(self) -> None:
        """handle_state() should return UNKNOWN after max retries exhausted."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        mock_browser = create_mock_browser()
        mock_browser.accessibility_tree = AsyncMock(return_value='{}')
        mock_browser.evaluate = AsyncMock(return_value=[])
        mock_browser.viewport_size = AsyncMock(return_value=(1280, 720))
        mock_browser.scroll_position = AsyncMock(return_value=(0, 0))
        # Bbox click fails, so it falls through to standard click
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": False})
        # All clicks fail
        mock_browser.click = AsyncMock(side_effect=Exception("always fail"))

        mock_heuristic = create_mock_heuristic(state=State.UNKNOWN, confidence=0.0)

        plan = ActionPlan(
            action_type="click",
            primary_target=TargetStrategy(method="css", css_selector="#btn"),
            reasoning="Test",
            confidence=0.9,
        )
        mock_planner = Mock()
        mock_planner.plan_action = AsyncMock(return_value=plan)
        mock_planner.SELF_CORRECT_PROMPT = "Self-correct: {action_type} {target_description} {failed_strategy} {error_message} {strategies_tried}"

        agent = AIBrowserAgent(
            browser=mock_browser,
            planner=mock_planner,
            heuristic=mock_heuristic,
            max_retries=2
        )

        result = await agent.handle_state(State.ACCOUNT_ACTIVE)

        assert result == State.UNKNOWN
        # Planner called for each retry
        assert mock_planner.plan_action.call_count == 2


class TestAIBrowserAgentClearHistory:
    """Tests for clear_history() method."""

    def test_clear_history_resets_action_history(self) -> None:
        """clear_history() should reset action and error history."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import ActionRecord, ErrorRecord

        mock_browser = create_mock_browser()
        agent = AIBrowserAgent(browser=mock_browser)

        # Add some history
        agent._record_action(ActionRecord(
            action_type="click",
            target_description="CSS: #btn",
            success=True,
            timestamp="2024-01-01T00:00:00Z"
        ))
        agent._record_error(ErrorRecord(
            action_type="click",
            error_type="NotFound",
            error_message="Element not found",
            strategy_attempted="CSS",
            timestamp="2024-01-01T00:00:00Z"
        ))

        assert len(agent._action_history) == 1
        assert len(agent._error_history) == 1

        agent.clear_history()

        assert len(agent._action_history) == 0
        assert len(agent._error_history) == 0


class TestTryBboxClick:
    """Tests for _try_bbox_click method."""

    @pytest.mark.asyncio
    async def test_bbox_click_with_css_strategy(self) -> None:
        """Should use click_by_bbox for CSS selector strategy."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import TargetStrategy

        mock_browser = AsyncMock()
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": True})

        agent = AIBrowserAgent(browser=mock_browser, max_retries=1)
        strategy = TargetStrategy(method="css", css_selector="#btn")

        result = await agent._try_bbox_click(strategy)

        assert result is True
        mock_browser.click_by_bbox.assert_called_once_with(selector="#btn")

    @pytest.mark.asyncio
    async def test_bbox_click_falls_back_on_failure(self) -> None:
        """Should return False if bbox click fails."""
        from subterminator.core.agent import AIBrowserAgent
        from subterminator.core.protocols import TargetStrategy

        mock_browser = AsyncMock()
        mock_browser.click_by_bbox = AsyncMock(return_value={"clicked": False})

        agent = AIBrowserAgent(browser=mock_browser, max_retries=1)
        strategy = TargetStrategy(method="css", css_selector="#btn")

        result = await agent._try_bbox_click(strategy)

        assert result is False
