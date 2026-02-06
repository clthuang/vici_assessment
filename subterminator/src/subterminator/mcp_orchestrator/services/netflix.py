"""Netflix service configuration for MCP orchestrator.

This module defines the Netflix-specific configuration including
checkpoint conditions, success/failure indicators, and system prompts.
"""

from __future__ import annotations

from ..types import (
    CheckpointPredicate,
    NormalizedSnapshot,
    SnapshotPredicate,
    ToolCall,
)
from .base import ServiceConfig
from .registry import default_registry

# =============================================================================
# Checkpoint Predicates (CheckpointPredicate: tool + snapshot -> bool)
# =============================================================================


def is_destructive_click(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
    """Triggers on clicks with finish/confirm/complete keywords (spec 2.5.3).

    These are potentially irreversible actions that require human approval.
    """
    if tool.name != "browser_click":
        return False
    element = tool.args.get("element", "").lower()
    finality_keywords = [
        "finish",
        "confirm",
        "complete",
        "cancel membership",
        "end membership",
    ]
    return any(kw in element for kw in finality_keywords)


def is_final_cancel_page(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
    """Final cancel page has both 'finish' and 'cancel' in content (spec 2.5.3).

    This catches the final confirmation page before actually cancelling.
    """
    content_lower = snap.content.lower()
    return "finish" in content_lower and "cancel" in content_lower


def is_payment_page(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
    """Design addition: protect against accidental payment changes.

    This is an extra safety measure not in the original spec (2.5.3)
    but added during design phase to prevent billing modifications.
    """
    return "payment" in snap.url.lower() or "billing" in snap.content.lower()


# Checkpoint conditions disabled for cancel flow - cancellation is reversible (user can resubscribe)
# Only payment page protection is kept as a safety measure
NETFLIX_CHECKPOINT_CONDITIONS: list[CheckpointPredicate] = [
    is_payment_page,  # Only block on payment pages to prevent accidental billing changes
]


# =============================================================================
# Success Indicators (SnapshotPredicate: snapshot -> bool)
# =============================================================================


def has_cancellation_confirmed(snap: NormalizedSnapshot) -> bool:
    """Check for cancellation confirmation message."""
    content_lower = snap.content.lower()
    return (
        "cancellation confirmed" in content_lower
        or "membership cancelled" in content_lower
        or "your membership has been cancelled" in content_lower
    )


def has_membership_ended(snap: NormalizedSnapshot) -> bool:
    """Check for membership ended message."""
    content_lower = snap.content.lower()
    return (
        "membership ended" in content_lower
        or "membership will end" in content_lower
        or "your membership ends" in content_lower
    )


def has_restart_option(snap: NormalizedSnapshot) -> bool:
    """Check for restart membership option (indicates successful cancellation)."""
    content_lower = snap.content.lower()
    return (
        "restart membership" in content_lower
        or "restart your membership" in content_lower
        or "rejoin" in content_lower
    )


def has_billing_stopped(snap: NormalizedSnapshot) -> bool:
    """Check for billing stopped message."""
    content_lower = snap.content.lower()
    return (
        "no longer be billed" in content_lower
        or "billing has stopped" in content_lower
        or "you will not be charged" in content_lower
    )


def has_already_cancelled(snap: NormalizedSnapshot) -> bool:
    """Detect account already cancelled state (for return visits)."""
    content_lower = snap.content.lower()
    indicators = [
        "your membership has already been cancelled",
        "membership is cancelled",
        "you cancelled your membership",
        "your account is cancelled",
        "membership was cancelled",
        "plan is cancelled",
    ]
    return any(ind in content_lower for ind in indicators)


NETFLIX_SUCCESS_INDICATORS: list[SnapshotPredicate] = [
    has_cancellation_confirmed,
    has_membership_ended,
    has_restart_option,
    has_billing_stopped,
    has_already_cancelled,
]


# =============================================================================
# Failure Indicators (SnapshotPredicate: snapshot -> bool)
# =============================================================================


def has_error_message(snap: NormalizedSnapshot) -> bool:
    """Check for error messages."""
    content_lower = snap.content.lower()
    return (
        "something went wrong" in content_lower
        or "error occurred" in content_lower
        or "unable to process" in content_lower
    )


def has_try_again(snap: NormalizedSnapshot) -> bool:
    """Check for try again prompts."""
    content_lower = snap.content.lower()
    return "please try again" in content_lower or "try again later" in content_lower


def has_login_required(snap: NormalizedSnapshot) -> bool:
    """Check for login required messages on non-login pages."""
    if "/login" in snap.url.lower():
        return False  # Expected on login page
    content_lower = snap.content.lower()
    return "please sign in" in content_lower or "login required" in content_lower


def has_session_expired(snap: NormalizedSnapshot) -> bool:
    """Check for session expired messages."""
    content_lower = snap.content.lower()
    return (
        "session expired" in content_lower
        or "session has expired" in content_lower
        or "signed out" in content_lower
    )


NETFLIX_FAILURE_INDICATORS: list[SnapshotPredicate] = [
    has_error_message,
    has_try_again,
    has_login_required,
    has_session_expired,
]


# =============================================================================
# Auth Edge Case Detectors (SnapshotPredicate: snapshot -> bool)
# =============================================================================


def is_login_page(snap: NormalizedSnapshot) -> bool:
    """Detect login page."""
    return "/login" in snap.url.lower() or "sign in" in snap.title.lower()


def is_captcha_page(snap: NormalizedSnapshot) -> bool:
    """Detect CAPTCHA page."""
    content_lower = snap.content.lower()
    return (
        "captcha" in content_lower
        or "verify you're human" in content_lower
        or "i'm not a robot" in content_lower
    )


def is_mfa_page(snap: NormalizedSnapshot) -> bool:
    """Detect multi-factor authentication page."""
    content_lower = snap.content.lower()
    return (
        "verification code" in content_lower
        or "two-factor" in content_lower
        or "2fa" in content_lower
        or "enter the code" in content_lower
    )


NETFLIX_AUTH_EDGE_CASES: list[SnapshotPredicate] = [
    is_login_page,
    is_captcha_page,
    is_mfa_page,
]


# =============================================================================
# Netflix Service Configuration
# =============================================================================

NETFLIX_SYSTEM_PROMPT_ADDITION = """
## Netflix-Specific Instructions

You are cancelling a Netflix subscription. Key points:

1. **Navigation**: Start from account settings, find "Cancel Membership" option
2. **Confirmation Pages**: Netflix may show multiple confirmation pages - proceed through them
3. **Success Detection**: Look for "cancellation confirmed", "membership ended", "restart membership" option
4. **Already Cancelled**: If you see the account is already cancelled, call complete_task immediately
5. **Avoid Payment Changes**: Do not modify payment methods or billing info

## IMPORTANT - Termination Rules

When you detect ANY of these conditions, call complete_task(status="success", reason="...") IMMEDIATELY:
- "cancellation confirmed" or "membership cancelled" message
- "membership ended" or "membership will end" message
- "restart membership" or "rejoin" option visible
- Account shows as already cancelled

Do NOT continue browsing after successful cancellation. Terminate immediately.

If you encounter a login page, CAPTCHA, or MFA prompt, wait for the user to complete it.
"""

NETFLIX_CONFIG = ServiceConfig(
    name="netflix",
    initial_url="https://www.netflix.com/YourAccount",
    goal_template="Cancel the Netflix subscription for the logged-in account.",
    checkpoint_conditions=NETFLIX_CHECKPOINT_CONDITIONS,
    success_indicators=NETFLIX_SUCCESS_INDICATORS,
    failure_indicators=NETFLIX_FAILURE_INDICATORS,
    system_prompt_addition=NETFLIX_SYSTEM_PROMPT_ADDITION,
    auth_edge_case_detectors=NETFLIX_AUTH_EDGE_CASES,
)

# Register Netflix config in default registry
default_registry.register(NETFLIX_CONFIG)
