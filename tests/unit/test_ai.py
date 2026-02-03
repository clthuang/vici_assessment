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
            assert "Cancel link" in result.reasoning

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
            assert result.confidence == 0.80

        def test_final_confirmation_confirm(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Confirm cancellation' should detect final confirmation."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Please confirm cancellation of your subscription.",
            )
            assert result.state == State.FINAL_CONFIRMATION
            assert result.confidence == 0.80

        def test_final_confirmation_complete(
            self, interpreter: HeuristicInterpreter
        ) -> None:
            """'Complete cancellation' should detect final confirmation."""
            result = interpreter.interpret(
                url="https://example.com/cancel",
                text="Complete cancellation now.",
            )
            assert result.state == State.FINAL_CONFIRMATION
            assert result.confidence == 0.80

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
