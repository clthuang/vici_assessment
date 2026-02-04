"""Unit tests for HeuristicInterpreter.

Tests cover:
- URL-based detection for login pages
- Text-based detection for various states:
  - Login states (sign in, log in forms)
  - Account states (active, cancelled)
  - Third-party billing detection
  - Cancel flow states (retention offer, exit survey, final confirmation)
  - Error detection
- Unknown fallback when no patterns match
"""

import pytest

from subterminator.core.ai import HeuristicInterpreter
from subterminator.core.protocols import AIInterpretation, State


class TestHeuristicInterpreter:
    """Tests for the HeuristicInterpreter class."""

    @pytest.fixture
    def interpreter(self) -> HeuristicInterpreter:
        """Create a HeuristicInterpreter instance for testing."""
        return HeuristicInterpreter()

    # URL-based detection tests (T8.2)
    class TestURLDetection:
        """Tests for URL-based state detection."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_login_url_pattern(self, interpreter: HeuristicInterpreter) -> None:
            """URL containing /login should return LOGIN_REQUIRED."""
            result = interpreter.interpret(
                url="https://example.com/login",
                text="Welcome to our site",
            )
            assert result.state == State.LOGIN_REQUIRED
            assert result.confidence == 0.95
            assert "URL" in result.reasoning

        def test_signin_url_pattern(self, interpreter: HeuristicInterpreter) -> None:
            """URL containing /signin should return LOGIN_REQUIRED."""
            result = interpreter.interpret(
                url="https://example.com/signin",
                text="Welcome",
            )
            assert result.state == State.LOGIN_REQUIRED
            assert result.confidence == 0.95

        def test_login_url_with_query_params(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """URL with /login and query params should still detect login."""
            result = interpreter.interpret(
                url="https://example.com/login?redirect=/account",
                text="Please authenticate",
            )
            assert result.state == State.LOGIN_REQUIRED
            assert result.confidence == 0.95

    # Text-based login detection tests (T8.3)
    class TestLoginTextDetection:
        """Tests for text-based login state detection."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_sign_in_with_password(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Text with 'sign in' and 'password' should detect login form."""
            result = interpreter.interpret(
                url="https://example.com/",
                text="Sign in to your account. Enter your email and password.",
            )
            assert result.state == State.LOGIN_REQUIRED
            assert result.confidence == 0.90
            assert "Login form" in result.reasoning

        def test_log_in_with_password(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Text with 'log in' and 'password' should detect login form."""
            result = interpreter.interpret(
                url="https://example.com/",
                text="Log in with your password to continue.",
            )
            assert result.state == State.LOGIN_REQUIRED
            assert result.confidence == 0.90

        def test_email_or_phone_with_password(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Text with 'email or phone' and 'password' should detect login."""
            result = interpreter.interpret(
                url="https://example.com/",
                text="Email or phone. Password. Forgot password?",
            )
            assert result.state == State.LOGIN_REQUIRED
            assert result.confidence == 0.90

        def test_sign_in_without_password_no_match(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Text with 'sign in' but no 'password' should not match login."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Sign in successful. Welcome back!",
            )
            # Should not detect as LOGIN_REQUIRED since no password field
            assert result.state != State.LOGIN_REQUIRED or result.confidence < 0.90

    # Account state detection tests (T8.4)
    class TestAccountStateDetection:
        """Tests for account state detection."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_cancel_membership_on_account_page(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Cancel membership link on account page indicates active account."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Your Plan: Premium. Cancel membership. Update payment.",
            )
            assert result.state == State.ACCOUNT_ACTIVE
            assert result.confidence == 0.85
            assert "Account management" in result.reasoning

        def test_cancel_membership_not_on_account_page(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Cancel membership not on /account URL should not match."""
            result = interpreter.interpret(
                url="https://example.com/help",
                text="To cancel membership, go to your account settings.",
            )
            # Should not match ACCOUNT_ACTIVE since not on /account URL
            assert result.state != State.ACCOUNT_ACTIVE

        def test_restart_membership_indicates_cancelled(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Restart membership link indicates already cancelled account."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Your membership ended on Jan 15. Restart membership.",
            )
            assert result.state == State.ACCOUNT_CANCELLED
            assert result.confidence == 0.85
            assert "Restart" in result.reasoning

    # Third-party billing detection tests (T8.5)
    class TestThirdPartyBillingDetection:
        """Tests for third-party billing detection."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_billed_through_detection(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Billed through' text should detect third-party billing."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="You are billed through your mobile carrier.",
            )
            assert result.state == State.THIRD_PARTY_BILLING
            assert result.confidence == 0.80

        def test_itunes_billing(self, interpreter: HeuristicInterpreter) -> None:
            """iTunes billing should be detected."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Your subscription is managed through iTunes.",
            )
            assert result.state == State.THIRD_PARTY_BILLING
            assert result.confidence == 0.80

        def test_google_play_billing(self, interpreter: HeuristicInterpreter) -> None:
            """Google Play billing should be detected."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Manage your subscription in Google Play.",
            )
            assert result.state == State.THIRD_PARTY_BILLING
            assert result.confidence == 0.80

        def test_t_mobile_billing(self, interpreter: HeuristicInterpreter) -> None:
            """T-Mobile billing should be detected."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Your plan is included with T-Mobile.",
            )
            assert result.state == State.THIRD_PARTY_BILLING
            assert result.confidence == 0.80

        def test_app_store_billing(self, interpreter: HeuristicInterpreter) -> None:
            """App Store billing should be detected."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Cancel through the App Store on your device.",
            )
            assert result.state == State.THIRD_PARTY_BILLING
            assert result.confidence == 0.80

        def test_play_store_billing(self, interpreter: HeuristicInterpreter) -> None:
            """Play Store billing should be detected."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Manage billing in the Play Store.",
            )
            assert result.state == State.THIRD_PARTY_BILLING
            assert result.confidence == 0.80

    # Cancel flow state detection tests (T8.6)
    class TestCancelFlowDetection:
        """Tests for cancel flow state detection."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_retention_offer_before_you_go(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Before you go' with offer should detect retention offer."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Before you go, here's a special offer: 50% discount!",
            )
            assert result.state == State.RETENTION_OFFER
            assert result.confidence == 0.75

        def test_retention_offer_special_offer(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Special offer' with save should detect retention."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Special offer! We'd hate to see you go. Save 30%.",
            )
            assert result.state == State.RETENTION_OFFER
            assert result.confidence == 0.75

        def test_retention_offer_hate_to_see_you_go(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'We'd hate to see you go' with discount should detect retention."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="We'd hate to see you go! Accept this discount to stay.",
            )
            assert result.state == State.RETENTION_OFFER
            assert result.confidence == 0.75

        def test_exit_survey_why_leaving(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Why are you leaving' should detect exit survey."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Why are you leaving? Select a reason below.",
            )
            assert result.state == State.EXIT_SURVEY
            assert result.confidence == 0.75

        def test_exit_survey_reason_for_cancelling(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Reason for cancelling' should detect exit survey."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Please select your reason for cancelling.",
            )
            assert result.state == State.EXIT_SURVEY
            assert result.confidence == 0.75

        def test_exit_survey_tell_us_why(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Tell us why' should detect exit survey."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Tell us why you're cancelling today.",
            )
            assert result.state == State.EXIT_SURVEY
            assert result.confidence == 0.75

        def test_exit_survey_feedback(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Feedback' keyword should detect exit survey."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="We'd appreciate your feedback before you cancel.",
            )
            assert result.state == State.EXIT_SURVEY
            assert result.confidence == 0.75

        def test_final_confirmation_finish(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Finish cancellation' should detect final confirmation."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Click to finish cancellation.",
            )
            assert result.state == State.FINAL_CONFIRMATION
            assert result.confidence == 0.85

        def test_final_confirmation_confirm(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Confirm cancellation' should detect final confirmation."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Please confirm cancellation of your subscription.",
            )
            assert result.state == State.FINAL_CONFIRMATION
            assert result.confidence == 0.85

        def test_final_confirmation_complete(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Complete cancellation' should detect final confirmation."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Complete cancellation now.",
            )
            assert result.state == State.FINAL_CONFIRMATION
            assert result.confidence == 0.85

        def test_cancellation_complete_cancelled(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Cancelled' confirmation should detect COMPLETE state."""
            result = interpreter.interpret(
                url="https://example.com/cancel/done",
                text="Your subscription has been cancelled. Access until Feb 1.",
            )
            assert result.state == State.COMPLETE
            assert result.confidence == 0.80

        def test_cancellation_complete_is_complete(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Cancellation is complete' should detect COMPLETE state."""
            result = interpreter.interpret(
                url="https://example.com/cancel/done",
                text="Your cancellation is complete. Thank you for being a member.",
            )
            assert result.state == State.COMPLETE
            assert result.confidence == 0.80

        def test_cancellation_complete_membership_ends(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Membership ends' should detect COMPLETE state."""
            result = interpreter.interpret(
                url="https://example.com/cancel/done",
                text="Your membership ends on March 15, 2026.",
            )
            assert result.state == State.COMPLETE
            assert result.confidence == 0.80

        def test_cancelled_with_restart_not_complete(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Cancelled with restart detects ACCOUNT_CANCELLED not COMPLETE."""
            result = interpreter.interpret(
                url="https://example.com/account",
                text="Subscription cancelled. Restart your membership anytime.",
            )
            # Should detect as ACCOUNT_CANCELLED because restart is present
            assert result.state == State.ACCOUNT_CANCELLED

    # Error detection tests (T8.7)
    class TestErrorDetection:
        """Tests for error state detection."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_something_went_wrong(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Something went wrong' should detect FAILED state."""
            result = interpreter.interpret(
                url="https://example.com/error",
                text="Something went wrong. Please try again later.",
            )
            assert result.state == State.FAILED
            assert result.confidence == 0.70

        def test_error_page(self, interpreter: HeuristicInterpreter) -> None:
            """'Error' text should detect FAILED state."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="An error occurred while processing your request.",
            )
            assert result.state == State.FAILED
            assert result.confidence == 0.70

        def test_try_again(self, interpreter: HeuristicInterpreter) -> None:
            """'Try again' should detect FAILED state."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Request failed. Please try again.",
            )
            assert result.state == State.FAILED
            assert result.confidence == 0.70

        def test_unexpected_error(self, interpreter: HeuristicInterpreter) -> None:
            """'Unexpected' should detect FAILED state."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="An unexpected problem occurred.",
            )
            assert result.state == State.FAILED
            assert result.confidence == 0.70

    # Unknown fallback tests (T8.8)
    class TestUnknownFallback:
        """Tests for unknown state fallback."""

        @pytest.fixture
        def interpreter(self) -> HeuristicInterpreter:
            """Create a HeuristicInterpreter instance for testing."""
            return HeuristicInterpreter()

        def test_no_patterns_matched(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Unrecognized content should return UNKNOWN state."""
            result = interpreter.interpret(
                url="https://example.com/random",
                text="This is some random page content with no recognizable patterns.",
            )
            assert result.state == State.UNKNOWN
            assert result.confidence == 0.0
            assert "No patterns" in result.reasoning

        def test_empty_text(self, interpreter: HeuristicInterpreter) -> None:
            """Empty text should return UNKNOWN state."""
            result = interpreter.interpret(
                url="https://example.com/page",
                text="",
            )
            assert result.state == State.UNKNOWN
            assert result.confidence == 0.0

        def test_generic_page_content(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """Generic page content should return UNKNOWN state."""
            result = interpreter.interpret(
                url="https://example.com/home",
                text="Welcome to our service. Browse our catalog. Contact support.",
            )
            assert result.state == State.UNKNOWN
            assert result.confidence == 0.0


class TestInterpretationResult:
    """Tests for AIInterpretation result structure."""

    @pytest.fixture
    def interpreter(self) -> HeuristicInterpreter:
        """Create a HeuristicInterpreter instance for testing."""
        return HeuristicInterpreter()

    def test_result_is_ai_interpretation(
        self, interpreter: HeuristicInterpreter
    ) -> None:
        """Result should be an AIInterpretation instance."""
        result = interpreter.interpret(
            url="https://example.com/login",
            text="Sign in",
        )
        assert isinstance(result, AIInterpretation)

    def test_result_has_valid_confidence(
        self, interpreter: HeuristicInterpreter
    ) -> None:
        """Result confidence should be between 0.0 and 1.0."""
        result = interpreter.interpret(
            url="https://example.com/login",
            text="Sign in with password",
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_result_has_reasoning(
        self, interpreter: HeuristicInterpreter
    ) -> None:
        """Result should have non-empty reasoning."""
        result = interpreter.interpret(
            url="https://example.com/login",
            text="Sign in with password",
        )
        assert result.reasoning
        assert len(result.reasoning) > 0

    def test_result_actions_default_empty(
        self, interpreter: HeuristicInterpreter
    ) -> None:
        """HeuristicInterpreter should return empty actions list."""
        result = interpreter.interpret(
            url="https://example.com/login",
            text="Sign in with password",
        )
        assert result.actions == []


class TestModuleExports:
    """Tests for module exports."""

    def test_heuristic_interpreter_importable_from_core(self) -> None:
        """HeuristicInterpreter should be importable from subterminator.core."""
        from subterminator.core import HeuristicInterpreter

        interpreter = HeuristicInterpreter()
        assert interpreter is not None

    def test_heuristic_interpreter_importable_from_ai(self) -> None:
        """HeuristicInterpreter should be importable from subterminator.core.ai."""
        from subterminator.core.ai import HeuristicInterpreter

        interpreter = HeuristicInterpreter()
        assert interpreter is not None


# --- Phase 3: ClaudeActionPlanner Tests ---


class TestClaudeActionPlannerInit:
    """Tests for ClaudeActionPlanner initialization (Task 3.3)."""

    def test_planner_initializes_with_api_key(self) -> None:
        """ClaudeActionPlanner should accept api_key parameter."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        assert planner is not None

    def test_planner_initializes_without_api_key(self) -> None:
        """ClaudeActionPlanner should work without explicit api_key (uses env)."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner()
        assert planner is not None

    def test_planner_stores_client(self) -> None:
        """ClaudeActionPlanner should store Anthropic client."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        assert hasattr(planner, "client")


class TestClaudeActionPlannerPlan:
    """Tests for ClaudeActionPlanner.plan() method (Tasks 3.4-3.5)."""

    @pytest.mark.asyncio
    async def test_plan_returns_planned_action(self) -> None:
        """plan() should return PlannedAction."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import PlannedAction, State

        planner = ClaudeActionPlanner(api_key="test-key")

        # Mock tool_use response
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "selector": "#cancel-btn",
            "reasoning": "Click cancel button"
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(planner.client.messages, "create", return_value=response):
            result = await planner.plan(
                screenshot=b"fake_png",
                url="https://example.com/account",
                accessibility_tree={"role": "WebArea", "children": []}
            )

        assert isinstance(result, PlannedAction)
        assert result.state == State.ACCOUNT_ACTIVE

    @pytest.mark.asyncio
    async def test_plan_extracts_action_type_from_tool_use(self) -> None:
        """plan() should extract action_type from tool_use response."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import ActionType

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "selector": "#cancel-btn",
            "reasoning": "Click cancel"
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(planner.client.messages, "create", return_value=response):
            result = await planner.plan(
                screenshot=b"fake_png",
                url="https://example.com",
                accessibility_tree={}
            )

        assert result.action.action_type == ActionType.CLICK

    @pytest.mark.asyncio
    async def test_plan_extracts_selector_from_tool_use(self) -> None:
        """plan() should extract selector from tool_use response."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "selector": "#my-special-button",
            "reasoning": "Click button"
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(planner.client.messages, "create", return_value=response):
            result = await planner.plan(
                screenshot=b"fake_png",
                url="https://example.com",
                accessibility_tree={}
            )

        assert result.action.selector == "#my-special-button"

    @pytest.mark.asyncio
    async def test_plan_extracts_reasoning_from_tool_use(self) -> None:
        """plan() should extract reasoning from tool_use response."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "selector": "#btn",
            "reasoning": "This button cancels the subscription"
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(planner.client.messages, "create", return_value=response):
            result = await planner.plan(
                screenshot=b"fake_png",
                url="https://example.com",
                accessibility_tree={}
            )

        assert result.reasoning == "This button cancels the subscription"


class TestClaudeActionPlannerToolDefinition:
    """Tests for ClaudeActionPlanner tool definition (Task 3.6)."""

    def test_planner_has_browser_action_tool(self) -> None:
        """ClaudeActionPlanner should define browser_action tool."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        # Check that tool definition exists
        assert hasattr(planner, "TOOLS")
        tool_names = [tool["name"] for tool in planner.TOOLS]
        assert "browser_action" in tool_names

    def test_browser_action_tool_has_state_parameter(self) -> None:
        """browser_action tool should have state parameter."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        browser_action_tool = next(
            tool for tool in planner.TOOLS if tool["name"] == "browser_action"
        )
        properties = browser_action_tool["input_schema"]["properties"]
        assert "state" in properties

    def test_browser_action_tool_has_action_type_parameter(self) -> None:
        """browser_action tool should have action_type parameter."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        browser_action_tool = next(
            tool for tool in planner.TOOLS if tool["name"] == "browser_action"
        )
        properties = browser_action_tool["input_schema"]["properties"]
        assert "action_type" in properties

    def test_browser_action_tool_has_targets_parameter(self) -> None:
        """browser_action tool should have targets array parameter."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        browser_action_tool = next(
            tool for tool in planner.TOOLS if tool["name"] == "browser_action"
        )
        properties = browser_action_tool["input_schema"]["properties"]
        # New schema uses targets array instead of selector
        assert "targets" in properties
        assert properties["targets"]["type"] == "array"


class TestClaudeActionPlannerErrorHandling:
    """Tests for ClaudeActionPlanner error handling (Task 3.7)."""

    @pytest.mark.asyncio
    async def test_plan_raises_on_api_error(self) -> None:
        """plan() should raise StateDetectionError on API error."""
        from unittest.mock import patch

        import anthropic

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.utils.exceptions import StateDetectionError

        planner = ClaudeActionPlanner(api_key="test-key")

        # Create a proper APIStatusError
        mock_response = anthropic._base_client.httpx.Response(
            status_code=500,
            request=anthropic._base_client.httpx.Request("POST", "https://api.anthropic.com")
        )

        with patch.object(
            planner.client.messages,
            "create",
            side_effect=anthropic.APIStatusError(
                message="Server Error",
                response=mock_response,
                body=None,
            )
        ):
            with pytest.raises(StateDetectionError, match="API error"):
                await planner.plan(
                    screenshot=b"fake_png",
                    url="https://example.com",
                    accessibility_tree={}
                )

    @pytest.mark.asyncio
    async def test_plan_returns_unknown_on_no_tool_use(self) -> None:
        """plan() should return UNKNOWN state when no tool_use in response."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import State

        planner = ClaudeActionPlanner(api_key="test-key")

        # Mock text response (no tool_use)
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "I'm not sure what to do"

        response = MagicMock()
        response.content = [text_block]

        with patch.object(planner.client.messages, "create", return_value=response):
            result = await planner.plan(
                screenshot=b"fake_png",
                url="https://example.com",
                accessibility_tree={}
            )

        assert result.state == State.UNKNOWN

    @pytest.mark.asyncio
    async def test_plan_handles_invalid_state_string(self) -> None:
        """plan() should handle invalid state strings gracefully."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import State

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "INVALID_STATE",
            "action_type": "click",
            "selector": "#btn",
            "reasoning": "Test"
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(planner.client.messages, "create", return_value=response):
            result = await planner.plan(
                screenshot=b"fake_png",
                url="https://example.com",
                accessibility_tree={}
            )

        assert result.state == State.UNKNOWN


class TestClaudeActionPlannerExports:
    """Tests for ClaudeActionPlanner module exports."""

    def test_planner_importable_from_ai(self) -> None:
        """ClaudeActionPlanner should be importable from ai module."""
        from subterminator.core.ai import ClaudeActionPlanner

        assert ClaudeActionPlanner is not None

    def test_planner_importable_from_core(self) -> None:
        """ClaudeActionPlanner should be importable from core."""
        from subterminator.core import ClaudeActionPlanner

        assert ClaudeActionPlanner is not None


# --- Phase 3 New Tests: targets array format and plan_action method ---


class TestClaudeActionPlannerTargetsArraySchema:
    """Tests for new TOOL_SCHEMA with targets array (Task 3.8-3.9)."""

    def test_tool_schema_has_targets_array(self) -> None:
        """TOOL_SCHEMA should have targets as array type."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        schema = planner.TOOL_SCHEMA["input_schema"]["properties"]["targets"]

        assert schema["type"] == "array"
        assert schema["minItems"] == 1
        assert schema["maxItems"] == 4

    def test_targets_items_has_method_enum(self) -> None:
        """targets.items should have method enum with css, aria, text, coordinates."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        items = planner.TOOL_SCHEMA["input_schema"]["properties"]["targets"]["items"]
        method_enum = items["properties"]["method"]["enum"]

        assert "css" in method_enum
        assert "aria" in method_enum
        assert "text" in method_enum
        assert "coordinates" in method_enum

    def test_tool_schema_has_expected_next_state(self) -> None:
        """TOOL_SCHEMA should have expected_next_state field."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        props = planner.TOOL_SCHEMA["input_schema"]["properties"]

        assert "expected_next_state" in props
        assert "enum" in props["expected_next_state"]


class TestClaudeActionPlannerParseTargets:
    """Tests for _parse_targets method (Task 3.10-3.11)."""

    def test_parse_targets_css_method(self) -> None:
        """_parse_targets should parse CSS method correctly."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import TargetStrategy

        planner = ClaudeActionPlanner(api_key="test-key")
        targets_data = [{"method": "css", "css": "#cancel-btn"}]

        result = planner._parse_targets(targets_data)

        assert len(result) == 1
        assert isinstance(result[0], TargetStrategy)
        assert result[0].method == "css"
        assert result[0].css_selector == "#cancel-btn"

    def test_parse_targets_aria_method(self) -> None:
        """_parse_targets should parse ARIA method correctly."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        targets_data = [
            {"method": "aria", "aria_role": "button", "aria_name": "Cancel"}
        ]

        result = planner._parse_targets(targets_data)

        assert len(result) == 1
        assert result[0].method == "aria"
        assert result[0].aria_role == "button"
        assert result[0].aria_name == "Cancel"

    def test_parse_targets_text_method(self) -> None:
        """_parse_targets should parse text method correctly."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        targets_data = [{"method": "text", "text": "Cancel Membership"}]

        result = planner._parse_targets(targets_data)

        assert len(result) == 1
        assert result[0].method == "text"
        assert result[0].text_content == "Cancel Membership"

    def test_parse_targets_coordinates_method(self) -> None:
        """_parse_targets should parse coordinates method correctly."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        targets_data = [{"method": "coordinates", "coordinates": [100, 200]}]

        result = planner._parse_targets(targets_data)

        assert len(result) == 1
        assert result[0].method == "coordinates"
        assert result[0].coordinates == (100, 200)

    def test_parse_targets_multiple(self) -> None:
        """_parse_targets should parse multiple targets."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        targets_data = [
            {"method": "css", "css": "#btn"},
            {"method": "aria", "aria_role": "button", "aria_name": "Click"},
            {"method": "text", "text": "Click Here"},
        ]

        result = planner._parse_targets(targets_data)

        assert len(result) == 3

    def test_parse_targets_skips_invalid(self) -> None:
        """_parse_targets should skip invalid targets without failing."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")
        # Missing required css field for css method
        targets_data = [
            {"method": "css"},  # Invalid - missing css selector
            {"method": "text", "text": "Valid"},  # Valid
        ]

        result = planner._parse_targets(targets_data)

        # Should only have the valid target
        assert len(result) == 1
        assert result[0].method == "text"


class TestClaudeActionPlannerTargetToSelector:
    """Tests for _target_to_selector method (Task 3.12)."""

    def test_target_to_selector_css(self) -> None:
        """_target_to_selector should return CSS selector."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import TargetStrategy

        planner = ClaudeActionPlanner(api_key="test-key")
        target = TargetStrategy(method="css", css_selector="#my-button")

        result = planner._target_to_selector(target)

        assert result == "#my-button"

    def test_target_to_selector_aria(self) -> None:
        """_target_to_selector should return ARIA pseudo-selector."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import TargetStrategy

        planner = ClaudeActionPlanner(api_key="test-key")
        target = TargetStrategy(
            method="aria", aria_role="button", aria_name="Submit"
        )

        result = planner._target_to_selector(target)

        assert "[role='button']" in result
        assert "[name='Submit']" in result

    def test_target_to_selector_text(self) -> None:
        """_target_to_selector should return text pseudo-selector."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import TargetStrategy

        planner = ClaudeActionPlanner(api_key="test-key")
        target = TargetStrategy(method="text", text_content="Click here")

        result = planner._target_to_selector(target)

        assert ":text('Click here')" == result

    def test_target_to_selector_coordinates(self) -> None:
        """_target_to_selector should return coordinates pseudo-selector."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import TargetStrategy

        planner = ClaudeActionPlanner(api_key="test-key")
        target = TargetStrategy(method="coordinates", coordinates=(150, 300))

        result = planner._target_to_selector(target)

        assert "@(150,300)" == result


class TestClaudeActionPlannerParseToolResponseTargets:
    """Tests for _parse_tool_response with new targets format (Task 3.13-3.14)."""

    def test_parse_tool_response_with_targets(self) -> None:
        """_parse_tool_response should parse new targets array format."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import ActionType, State

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "targets": [{"method": "css", "css": "#cancel-btn"}],
            "reasoning": "Click cancel button",
            "confidence": 0.9,
        }

        result = planner._parse_tool_response(tool_input)

        assert result.state == State.ACCOUNT_ACTIVE
        assert result.action.action_type == ActionType.CLICK
        assert "#cancel-btn" in result.action.selector
        assert result.reasoning == "Click cancel button"
        assert result.confidence == 0.9

    def test_parse_tool_response_with_aria_fallback_role(self) -> None:
        """_parse_tool_response should set fallback_role for ARIA targets."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "targets": [
                {"method": "aria", "aria_role": "button", "aria_name": "Cancel"}
            ],
            "reasoning": "Click cancel button",
            "confidence": 0.85,
        }

        result = planner._parse_tool_response(tool_input)

        assert result.action.fallback_role == ("button", "Cancel")

    def test_parse_tool_response_legacy_selector_fallback(self) -> None:
        """_parse_tool_response should fallback to legacy selector format."""
        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import State

        planner = ClaudeActionPlanner(api_key="test-key")

        tool_input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "selector": "#old-style-selector",
            "reasoning": "Legacy format",
        }

        result = planner._parse_tool_response(tool_input)

        assert result.state == State.ACCOUNT_ACTIVE
        assert result.action.selector == "#old-style-selector"


class TestClaudeActionPlannerPlanAction:
    """Tests for plan_action method with AgentContext (Task 3.15-3.16)."""

    @pytest.mark.asyncio
    async def test_plan_action_returns_action_plan(self) -> None:
        """plan_action should return ActionPlan."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import (
            ActionPlan,
            AgentContext,
        )

        planner = ClaudeActionPlanner(api_key="test-key")

        # Create mock AgentContext
        context = AgentContext(
            screenshot=b"fake_png",
            accessibility_tree='{"role": "WebArea"}',
            html_snippet="<button>Cancel</button>",
            url="https://example.com/account",
            visible_text="Cancel membership",
            previous_actions=[],
            error_history=[],
            viewport_size=(1280, 720),
            scroll_position=(0, 0),
        )

        # Mock tool_use response
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "targets": [{"method": "css", "css": "#cancel-btn"}],
            "reasoning": "Click cancel",
            "confidence": 0.85,
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(
            planner.client.messages, "create", return_value=response
        ):
            result = await planner.plan_action(
                context, "Click cancel button"
            )

        assert isinstance(result, ActionPlan)
        assert result.action_type == "click"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_plan_action_with_error_context(self) -> None:
        """plan_action should accept error_context for self-correction."""
        from unittest.mock import MagicMock, patch

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import AgentContext

        planner = ClaudeActionPlanner(api_key="test-key")

        context = AgentContext(
            screenshot=b"fake_png",
            accessibility_tree='{"role": "WebArea"}',
            html_snippet="<button>Cancel</button>",
            url="https://example.com/account",
            visible_text="Cancel",
            previous_actions=[],
            error_history=[],
            viewport_size=(1280, 720),
            scroll_position=(0, 0),
        )

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "browser_action"
        tool_block.input = {
            "state": "ACCOUNT_ACTIVE",
            "action_type": "click",
            "targets": [{"method": "text", "text": "Cancel"}],
            "reasoning": "Try text instead",
            "confidence": 0.7,
        }

        response = MagicMock()
        response.content = [tool_block]

        with patch.object(
            planner.client.messages, "create", return_value=response
        ):
            result = await planner.plan_action(
                context,
                "Click cancel button",
                error_context="CSS selector #btn failed",
            )

        assert result.primary_target.method == "text"

    @pytest.mark.asyncio
    async def test_plan_action_raises_on_api_error(self) -> None:
        """plan_action should raise StateDetectionError on API error."""
        from unittest.mock import patch

        import anthropic

        from subterminator.core.ai import ClaudeActionPlanner
        from subterminator.core.protocols import AgentContext
        from subterminator.utils.exceptions import StateDetectionError

        planner = ClaudeActionPlanner(api_key="test-key")

        context = AgentContext(
            screenshot=b"fake_png",
            accessibility_tree='{"role": "WebArea"}',
            html_snippet="<button>Cancel</button>",
            url="https://example.com",
            visible_text="Cancel",
            previous_actions=[],
            error_history=[],
            viewport_size=(1280, 720),
            scroll_position=(0, 0),
        )

        # Create a proper APIStatusError
        mock_response = anthropic._base_client.httpx.Response(
            status_code=500,
            request=anthropic._base_client.httpx.Request(
                "POST", "https://api.anthropic.com"
            ),
        )

        with patch.object(
            planner.client.messages,
            "create",
            side_effect=anthropic.APIStatusError(
                message="Server Error",
                response=mock_response,
                body=None,
            ),
        ):
            with pytest.raises(StateDetectionError, match="API error"):
                await planner.plan_action(context, "Click cancel")


class TestClaudeActionPlannerPrompts:
    """Tests for AGENT_SYSTEM_PROMPT and SELF_CORRECT_PROMPT (Task 3.8)."""

    def test_agent_system_prompt_exists(self) -> None:
        """ClaudeActionPlanner should have AGENT_SYSTEM_PROMPT."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        assert hasattr(planner, "AGENT_SYSTEM_PROMPT")
        assert "browser" in planner.AGENT_SYSTEM_PROMPT.lower()

    def test_self_correct_prompt_exists(self) -> None:
        """ClaudeActionPlanner should have SELF_CORRECT_PROMPT."""
        from subterminator.core.ai import ClaudeActionPlanner

        planner = ClaudeActionPlanner(api_key="test-key")

        assert hasattr(planner, "SELF_CORRECT_PROMPT")
        assert "{action_type}" in planner.SELF_CORRECT_PROMPT
        assert "{strategies_tried}" in planner.SELF_CORRECT_PROMPT
