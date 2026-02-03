"""Unit tests for the CancellationStateMachine.

Tests cover:
- Initial state verification
- Valid state transitions
- Invalid transitions raising TransitionNotAllowed
- Terminal (final) states behavior
- State tracking (step counter, human_confirmed flag)
- State entry callbacks
"""

import pytest
from statemachine.exceptions import TransitionNotAllowed

from subterminator.core.states import CancellationStateMachine


class TestInitialState:
    """Tests for initial state configuration."""

    def test_initial_state_is_start(self) -> None:
        """State machine should start in 'start' state."""
        sm = CancellationStateMachine()
        assert sm.current_state == sm.start

    def test_initial_step_is_zero(self) -> None:
        """Step counter should start at zero."""
        sm = CancellationStateMachine()
        assert sm.step == 0

    def test_initial_human_confirmed_is_false(self) -> None:
        """Human confirmed flag should start as False."""
        sm = CancellationStateMachine()
        assert sm.human_confirmed is False


class TestNavigateTransition:
    """Tests for the 'navigate' transition from start state."""

    def test_navigate_to_login_required(self) -> None:
        """Should transition from start to login_required."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        assert sm.current_state == sm.login_required

    def test_navigate_to_account_active(self) -> None:
        """Should transition from start to account_active."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        assert sm.current_state == sm.account_active

    def test_navigate_to_account_cancelled(self) -> None:
        """Should transition from start to account_cancelled."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_cancelled")
        assert sm.current_state == sm.account_cancelled

    def test_navigate_to_third_party_billing(self) -> None:
        """Should transition from start to third_party_billing."""
        sm = CancellationStateMachine()
        sm.navigate(dest="third_party_billing")
        assert sm.current_state == sm.third_party_billing

    def test_navigate_to_failed(self) -> None:
        """Should transition from start to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="failed")
        assert sm.current_state == sm.failed

    def test_navigate_to_unknown(self) -> None:
        """Should transition from start to unknown."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        assert sm.current_state == sm.unknown


class TestAuthenticateTransition:
    """Tests for the 'authenticate' transition from login_required state."""

    def test_authenticate_to_account_active(self) -> None:
        """Should transition from login_required to account_active."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.authenticate(dest="account_active")
        assert sm.current_state == sm.account_active

    def test_authenticate_to_account_cancelled(self) -> None:
        """Should transition from login_required to account_cancelled."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.authenticate(dest="account_cancelled")
        assert sm.current_state == sm.account_cancelled

    def test_authenticate_to_third_party_billing(self) -> None:
        """Should transition from login_required to third_party_billing."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.authenticate(dest="third_party_billing")
        assert sm.current_state == sm.third_party_billing

    def test_authenticate_to_failed(self) -> None:
        """Should transition from login_required to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.authenticate(dest="failed")
        assert sm.current_state == sm.failed

    def test_authenticate_to_unknown(self) -> None:
        """Should transition from login_required to unknown."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.authenticate(dest="unknown")
        assert sm.current_state == sm.unknown


class TestClickCancelTransition:
    """Tests for the 'click_cancel' transition from account_active state."""

    def test_click_cancel_to_retention_offer(self) -> None:
        """Should transition from account_active to retention_offer."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="retention_offer")
        assert sm.current_state == sm.retention_offer

    def test_click_cancel_to_exit_survey(self) -> None:
        """Should transition from account_active to exit_survey."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="exit_survey")
        assert sm.current_state == sm.exit_survey

    def test_click_cancel_to_final_confirmation(self) -> None:
        """Should transition from account_active to final_confirmation."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="final_confirmation")
        assert sm.current_state == sm.final_confirmation

    def test_click_cancel_to_failed(self) -> None:
        """Should transition from account_active to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="failed")
        assert sm.current_state == sm.failed

    def test_click_cancel_to_unknown(self) -> None:
        """Should transition from account_active to unknown."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="unknown")
        assert sm.current_state == sm.unknown


class TestDeclineOfferTransition:
    """Tests for the 'decline_offer' transition from retention_offer state."""

    def test_decline_offer_to_another_retention_offer(self) -> None:
        """Should handle multiple retention offers."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="retention_offer")
        sm.decline_offer(dest="retention_offer")
        assert sm.current_state == sm.retention_offer

    def test_decline_offer_to_exit_survey(self) -> None:
        """Should transition from retention_offer to exit_survey."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="retention_offer")
        sm.decline_offer(dest="exit_survey")
        assert sm.current_state == sm.exit_survey

    def test_decline_offer_to_final_confirmation(self) -> None:
        """Should transition from retention_offer to final_confirmation."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="retention_offer")
        sm.decline_offer(dest="final_confirmation")
        assert sm.current_state == sm.final_confirmation

    def test_decline_offer_to_failed(self) -> None:
        """Should transition from retention_offer to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="retention_offer")
        sm.decline_offer(dest="failed")
        assert sm.current_state == sm.failed

    def test_decline_offer_to_unknown(self) -> None:
        """Should transition from retention_offer to unknown."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="retention_offer")
        sm.decline_offer(dest="unknown")
        assert sm.current_state == sm.unknown


class TestSubmitSurveyTransition:
    """Tests for the 'submit_survey' transition from exit_survey state."""

    def test_submit_survey_to_retention_offer(self) -> None:
        """Should transition from exit_survey to retention_offer."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="exit_survey")
        sm.submit_survey(dest="retention_offer")
        assert sm.current_state == sm.retention_offer

    def test_submit_survey_to_final_confirmation(self) -> None:
        """Should transition from exit_survey to final_confirmation."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="exit_survey")
        sm.submit_survey(dest="final_confirmation")
        assert sm.current_state == sm.final_confirmation

    def test_submit_survey_to_failed(self) -> None:
        """Should transition from exit_survey to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="exit_survey")
        sm.submit_survey(dest="failed")
        assert sm.current_state == sm.failed

    def test_submit_survey_to_unknown(self) -> None:
        """Should transition from exit_survey to unknown."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="exit_survey")
        sm.submit_survey(dest="unknown")
        assert sm.current_state == sm.unknown


class TestConfirmTransition:
    """Tests for the 'confirm' transition from final_confirmation state."""

    def test_confirm_to_complete(self) -> None:
        """Should transition from final_confirmation to complete."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="final_confirmation")
        sm.confirm(dest="complete")
        assert sm.current_state == sm.complete

    def test_confirm_to_failed(self) -> None:
        """Should transition from final_confirmation to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="final_confirmation")
        sm.confirm(dest="failed")
        assert sm.current_state == sm.failed


class TestAbortTransition:
    """Tests for the 'abort' transition."""

    def test_abort_from_login_required(self) -> None:
        """Should transition from login_required to aborted."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.abort()
        assert sm.current_state == sm.aborted

    def test_abort_from_final_confirmation(self) -> None:
        """Should transition from final_confirmation to aborted."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="final_confirmation")
        sm.abort()
        assert sm.current_state == sm.aborted

    def test_abort_from_unknown(self) -> None:
        """Should transition from unknown to aborted."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.abort()
        assert sm.current_state == sm.aborted


class TestResolveUnknownTransition:
    """Tests for the 'resolve_unknown' transition from unknown state."""

    def test_resolve_unknown_to_login_required(self) -> None:
        """Should transition from unknown to login_required."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="login_required")
        assert sm.current_state == sm.login_required

    def test_resolve_unknown_to_account_active(self) -> None:
        """Should transition from unknown to account_active."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="account_active")
        assert sm.current_state == sm.account_active

    def test_resolve_unknown_to_account_cancelled(self) -> None:
        """Should transition from unknown to account_cancelled."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="account_cancelled")
        assert sm.current_state == sm.account_cancelled

    def test_resolve_unknown_to_retention_offer(self) -> None:
        """Should transition from unknown to retention_offer."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="retention_offer")
        assert sm.current_state == sm.retention_offer

    def test_resolve_unknown_to_exit_survey(self) -> None:
        """Should transition from unknown to exit_survey."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="exit_survey")
        assert sm.current_state == sm.exit_survey

    def test_resolve_unknown_to_final_confirmation(self) -> None:
        """Should transition from unknown to final_confirmation."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="final_confirmation")
        assert sm.current_state == sm.final_confirmation

    def test_resolve_unknown_to_failed(self) -> None:
        """Should transition from unknown to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="unknown")
        sm.resolve_unknown(dest="failed")
        assert sm.current_state == sm.failed


class TestMarkAlreadyCancelledTransition:
    """Tests for the 'mark_already_cancelled' transition."""

    def test_mark_already_cancelled_to_complete(self) -> None:
        """Should transition from account_cancelled to complete."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_cancelled")
        sm.mark_already_cancelled()
        assert sm.current_state == sm.complete


class TestMarkThirdPartyTransition:
    """Tests for the 'mark_third_party' transition."""

    def test_mark_third_party_to_failed(self) -> None:
        """Should transition from third_party_billing to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="third_party_billing")
        sm.mark_third_party()
        assert sm.current_state == sm.failed


class TestInvalidTransitions:
    """Tests for invalid transitions that should raise TransitionNotAllowed."""

    def test_cannot_navigate_from_non_start_state(self) -> None:
        """Navigate should only work from start state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        with pytest.raises(TransitionNotAllowed):
            sm.navigate(dest="login_required")

    def test_cannot_authenticate_from_start(self) -> None:
        """Authenticate should not work from start state."""
        sm = CancellationStateMachine()
        with pytest.raises(TransitionNotAllowed):
            sm.authenticate(dest="account_active")

    def test_cannot_click_cancel_from_start(self) -> None:
        """Click cancel should not work from start state."""
        sm = CancellationStateMachine()
        with pytest.raises(TransitionNotAllowed):
            sm.click_cancel(dest="retention_offer")

    def test_cannot_confirm_from_start(self) -> None:
        """Confirm should not work from start state."""
        sm = CancellationStateMachine()
        with pytest.raises(TransitionNotAllowed):
            sm.confirm(dest="complete")

    def test_cannot_abort_from_start(self) -> None:
        """Abort should not work from start state."""
        sm = CancellationStateMachine()
        with pytest.raises(TransitionNotAllowed):
            sm.abort()

    def test_cannot_abort_from_account_active(self) -> None:
        """Abort should not work from account_active state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        with pytest.raises(TransitionNotAllowed):
            sm.abort()

    def test_cannot_decline_offer_from_exit_survey(self) -> None:
        """Decline offer should not work from exit_survey state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="exit_survey")
        with pytest.raises(TransitionNotAllowed):
            sm.decline_offer(dest="final_confirmation")

    def test_cannot_resolve_unknown_from_account_active(self) -> None:
        """Resolve unknown should not work from account_active state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        with pytest.raises(TransitionNotAllowed):
            sm.resolve_unknown(dest="final_confirmation")


class TestFinalStates:
    """Tests for terminal (final) states."""

    def test_complete_is_final(self) -> None:
        """Complete state should be terminal."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="final_confirmation")
        sm.confirm(dest="complete")
        assert sm.current_state == sm.complete
        assert sm.complete.final is True

    def test_aborted_is_final(self) -> None:
        """Aborted state should be terminal."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.abort()
        assert sm.current_state == sm.aborted
        assert sm.aborted.final is True

    def test_failed_is_final(self) -> None:
        """Failed state should be terminal."""
        sm = CancellationStateMachine()
        sm.navigate(dest="failed")
        assert sm.current_state == sm.failed
        assert sm.failed.final is True

    def test_cannot_transition_from_complete(self) -> None:
        """Should not be able to transition from complete state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="account_active")
        sm.click_cancel(dest="final_confirmation")
        sm.confirm(dest="complete")
        with pytest.raises(TransitionNotAllowed):
            sm.navigate(dest="login_required")

    def test_cannot_transition_from_aborted(self) -> None:
        """Should not be able to transition from aborted state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="login_required")
        sm.abort()
        with pytest.raises(TransitionNotAllowed):
            sm.navigate(dest="account_active")

    def test_cannot_transition_from_failed(self) -> None:
        """Should not be able to transition from failed state."""
        sm = CancellationStateMachine()
        sm.navigate(dest="failed")
        with pytest.raises(TransitionNotAllowed):
            sm.navigate(dest="account_active")


class TestStepCounter:
    """Tests for step counter tracking."""

    def test_step_increments_on_transition(self) -> None:
        """Step counter should increment on each transition."""
        sm = CancellationStateMachine()
        assert sm.step == 0
        sm.navigate(dest="login_required")
        assert sm.step == 1
        sm.authenticate(dest="account_active")
        assert sm.step == 2
        sm.click_cancel(dest="final_confirmation")
        assert sm.step == 3

    def test_step_increments_on_navigate_to_failed(self) -> None:
        """Step counter should increment even when navigating to failed."""
        sm = CancellationStateMachine()
        sm.navigate(dest="failed")
        assert sm.step == 1


class TestHumanConfirmedFlag:
    """Tests for human_confirmed flag."""

    def test_human_confirmed_can_be_set(self) -> None:
        """Human confirmed flag should be settable."""
        sm = CancellationStateMachine()
        assert sm.human_confirmed is False
        sm.human_confirmed = True
        assert sm.human_confirmed is True


class TestModuleExports:
    """Tests for module exports."""

    def test_exports_from_core_init(self) -> None:
        """CancellationStateMachine should be importable from subterminator.core."""
        from subterminator.core import CancellationStateMachine

        sm = CancellationStateMachine()
        assert sm.current_state == sm.start
