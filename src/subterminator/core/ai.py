"""Heuristic-based page state interpretation for SubTerminator.

This module provides fast, rule-based page state detection using URL patterns
and text content analysis. It serves as a fallback before more expensive AI
interpretation is invoked.
"""

from subterminator.core.protocols import AIInterpretation, State


class HeuristicInterpreter:
    """Fallback heuristic-based page state detection.

    Uses URL patterns and text content analysis to quickly determine page state
    without requiring AI inference. Returns confidence scores indicating how
    certain the heuristic is about the detected state.

    Example:
        >>> interpreter = HeuristicInterpreter()
        >>> result = interpreter.interpret(
        ...     url="https://example.com/login",
        ...     text="Sign in to your account"
        ... )
        >>> result.state
        <State.LOGIN_REQUIRED: 2>
        >>> result.confidence
        0.95
    """

    def interpret(self, url: str, text: str) -> AIInterpretation:
        """Detect state from URL patterns and text content.

        Analyzes the URL and page text to determine the current state in
        the subscription cancellation flow. Uses a priority order of checks:
        1. URL-based detection (highest confidence)
        2. Text-based detection for various states
        3. UNKNOWN fallback when no patterns match

        Args:
            url: The current page URL.
            text: The visible text content of the page.

        Returns:
            AIInterpretation with detected state, confidence, and reasoning.
            Actions list is always empty for heuristic interpretation.
        """
        text_lower = text.lower()

        # T8.2: URL-based detection (high confidence)
        if "/login" in url or "/signin" in url:
            return AIInterpretation(
                State.LOGIN_REQUIRED, 0.95, "URL contains /login"
            )

        # T8.3: Text detection - login states
        login_phrases = ["sign in", "log in", "email or phone"]
        if any(phrase in text_lower for phrase in login_phrases):
            if "password" in text_lower:
                return AIInterpretation(
                    State.LOGIN_REQUIRED, 0.90, "Login form detected"
                )

        # T8.4: Text detection - account states
        if "cancel membership" in text_lower and "/account" in url:
            return AIInterpretation(
                State.ACCOUNT_ACTIVE, 0.85, "Cancel link found on account page"
            )

        if "restart" in text_lower and "membership" in text_lower:
            return AIInterpretation(
                State.ACCOUNT_CANCELLED, 0.85,
                "Restart link found - already cancelled"
            )

        # T8.5: Text detection - third-party billing
        third_party_indicators = [
            "billed through", "itunes", "google play",
            "t-mobile", "app store", "play store"
        ]
        if any(indicator in text_lower for indicator in third_party_indicators):
            return AIInterpretation(
                State.THIRD_PARTY_BILLING, 0.80, "Third-party billing detected"
            )

        # T8.6: Text detection - cancel flow states
        retention_phrases = [
            "before you go", "special offer", "we'd hate to see you go", "save"
        ]
        if any(phrase in text_lower for phrase in retention_phrases):
            if "discount" in text_lower or "offer" in text_lower:
                return AIInterpretation(
                    State.RETENTION_OFFER, 0.75, "Retention offer detected"
                )

        survey_phrases = [
            "why are you leaving", "reason for cancelling",
            "tell us why", "feedback"
        ]
        if any(phrase in text_lower for phrase in survey_phrases):
            return AIInterpretation(
                State.EXIT_SURVEY, 0.75, "Survey language detected"
            )

        final_confirm_phrases = [
            "finish cancellation", "confirm cancellation", "complete cancellation"
        ]
        if any(phrase in text_lower for phrase in final_confirm_phrases):
            return AIInterpretation(
                State.FINAL_CONFIRMATION, 0.80, "Finish button detected"
            )

        complete_phrases = [
            "cancelled", "cancellation is complete", "membership ends"
        ]
        if any(phrase in text_lower for phrase in complete_phrases):
            if "restart" not in text_lower:  # Avoid false positive
                return AIInterpretation(
                    State.COMPLETE, 0.80, "Cancellation confirmed"
                )

        # T8.7: Text detection - error state
        error_phrases = [
            "something went wrong", "error", "try again", "unexpected"
        ]
        if any(phrase in text_lower for phrase in error_phrases):
            return AIInterpretation(
                State.FAILED, 0.70, "Error page detected"
            )

        # T8.8: Return UNKNOWN as fallback
        return AIInterpretation(State.UNKNOWN, 0.0, "No patterns matched")
