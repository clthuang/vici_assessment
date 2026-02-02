"""State machine for subscription cancellation flow.

This module defines the CancellationStateMachine that governs the valid
transitions in a subscription cancellation process. It uses python-statemachine
to enforce state transition rules.

States are organized into logical groups:
- Entry: start (initial)
- Authentication: login_required
- Account: account_active, account_cancelled, third_party_billing
- Cancellation flow: retention_offer, exit_survey, final_confirmation
- Terminal: complete, aborted, failed (final states)
- Recovery: unknown (for unrecognized page states)
"""

from statemachine import State as SMState
from statemachine import StateMachine


class CancellationStateMachine(StateMachine):
    """State machine for subscription cancellation flow.

    This state machine tracks the progress of a subscription cancellation,
    enforcing valid transitions between states.

    Attributes:
        step: Counter that increments on each state transition.
        human_confirmed: Flag indicating whether a human has confirmed the action.

    States:
        start: Initial state before navigation.
        login_required: Authentication is needed.
        account_active: Logged in with active subscription.
        account_cancelled: Subscription already cancelled.
        third_party_billing: Billing through third party (App Store, etc).
        retention_offer: Service is offering retention incentives.
        exit_survey: Exit survey form is displayed.
        final_confirmation: Final confirmation step before cancellation.
        complete: Cancellation successfully completed (final).
        aborted: Process was aborted by user (final).
        failed: Process failed (final).
        unknown: Page state could not be determined.
    """

    # Entry state
    start = SMState(initial=True)

    # Authentication state
    login_required = SMState()

    # Account states
    account_active = SMState()
    account_cancelled = SMState()
    third_party_billing = SMState()

    # Cancellation flow states
    retention_offer = SMState()
    exit_survey = SMState()
    final_confirmation = SMState()

    # Terminal states
    complete = SMState(final=True)
    aborted = SMState(final=True)
    failed = SMState(final=True)

    # Recovery state
    unknown = SMState()

    # Transitions
    # Note: Using 'dest' parameter name because 'target' is reserved by statemachine

    # navigate: start -> various states after initial page load
    navigate = (
        start.to(login_required, cond="dest_is_login_required")
        | start.to(account_active, cond="dest_is_account_active")
        | start.to(account_cancelled, cond="dest_is_account_cancelled")
        | start.to(third_party_billing, cond="dest_is_third_party_billing")
        | start.to(failed, cond="dest_is_failed")
        | start.to(unknown, cond="dest_is_unknown")
    )

    # authenticate: login_required -> various states after login
    authenticate = (
        login_required.to(account_active, cond="dest_is_account_active")
        | login_required.to(account_cancelled, cond="dest_is_account_cancelled")
        | login_required.to(third_party_billing, cond="dest_is_third_party_billing")
        | login_required.to(failed, cond="dest_is_failed")
        | login_required.to(unknown, cond="dest_is_unknown")
    )

    # click_cancel: account_active -> various states after clicking cancel
    click_cancel = (
        account_active.to(retention_offer, cond="dest_is_retention_offer")
        | account_active.to(exit_survey, cond="dest_is_exit_survey")
        | account_active.to(final_confirmation, cond="dest_is_final_confirmation")
        | account_active.to(failed, cond="dest_is_failed")
        | account_active.to(unknown, cond="dest_is_unknown")
    )

    # decline_offer: retention_offer -> various states after declining
    decline_offer = (
        retention_offer.to(retention_offer, cond="dest_is_retention_offer")
        | retention_offer.to(exit_survey, cond="dest_is_exit_survey")
        | retention_offer.to(final_confirmation, cond="dest_is_final_confirmation")
        | retention_offer.to(failed, cond="dest_is_failed")
        | retention_offer.to(unknown, cond="dest_is_unknown")
    )

    # submit_survey: exit_survey -> various states after survey submission
    submit_survey = (
        exit_survey.to(retention_offer, cond="dest_is_retention_offer")
        | exit_survey.to(final_confirmation, cond="dest_is_final_confirmation")
        | exit_survey.to(failed, cond="dest_is_failed")
        | exit_survey.to(unknown, cond="dest_is_unknown")
    )

    # confirm: final_confirmation -> complete or failed
    confirm = (
        final_confirmation.to(complete, cond="dest_is_complete")
        | final_confirmation.to(failed, cond="dest_is_failed")
    )

    # abort: from certain states -> aborted
    abort = (
        login_required.to(aborted)
        | final_confirmation.to(aborted)
        | unknown.to(aborted)
    )

    # resolve_unknown: unknown -> various known states
    resolve_unknown = (
        unknown.to(login_required, cond="dest_is_login_required")
        | unknown.to(account_active, cond="dest_is_account_active")
        | unknown.to(account_cancelled, cond="dest_is_account_cancelled")
        | unknown.to(retention_offer, cond="dest_is_retention_offer")
        | unknown.to(exit_survey, cond="dest_is_exit_survey")
        | unknown.to(final_confirmation, cond="dest_is_final_confirmation")
        | unknown.to(failed, cond="dest_is_failed")
    )

    # mark_already_cancelled: account_cancelled -> complete
    mark_already_cancelled = account_cancelled.to(complete)

    # mark_third_party: third_party_billing -> failed
    mark_third_party = third_party_billing.to(failed)

    def __init__(self) -> None:
        """Initialize the state machine with tracking variables."""
        self.step: int = 0
        self.human_confirmed: bool = False
        super().__init__()

    # Condition methods for dest-based transitions

    def dest_is_login_required(self, dest: str) -> bool:
        """Check if destination state is login_required."""
        return dest == "login_required"

    def dest_is_account_active(self, dest: str) -> bool:
        """Check if destination state is account_active."""
        return dest == "account_active"

    def dest_is_account_cancelled(self, dest: str) -> bool:
        """Check if destination state is account_cancelled."""
        return dest == "account_cancelled"

    def dest_is_third_party_billing(self, dest: str) -> bool:
        """Check if destination state is third_party_billing."""
        return dest == "third_party_billing"

    def dest_is_retention_offer(self, dest: str) -> bool:
        """Check if destination state is retention_offer."""
        return dest == "retention_offer"

    def dest_is_exit_survey(self, dest: str) -> bool:
        """Check if destination state is exit_survey."""
        return dest == "exit_survey"

    def dest_is_final_confirmation(self, dest: str) -> bool:
        """Check if destination state is final_confirmation."""
        return dest == "final_confirmation"

    def dest_is_complete(self, dest: str) -> bool:
        """Check if destination state is complete."""
        return dest == "complete"

    def dest_is_failed(self, dest: str) -> bool:
        """Check if destination state is failed."""
        return dest == "failed"

    def dest_is_unknown(self, dest: str) -> bool:
        """Check if destination state is unknown."""
        return dest == "unknown"

    # State transition callback
    def after_transition(self, event: str, source: SMState, target: SMState) -> None:
        """Callback invoked after any state transition.

        Increments the step counter to track progress through the flow.

        Args:
            event: The event/transition that triggered this state change.
            source: The state we're transitioning from.
            target: The state we're transitioning to.
        """
        self.step += 1
