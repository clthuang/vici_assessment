"""Page state interpretation for SubTerminator.

This module provides both heuristic-based and AI-based page state detection:
- HeuristicInterpreter: Fast, rule-based detection using URL patterns and text
- ClaudeInterpreter: Claude Vision-based detection for when heuristics fail
"""

import base64
import json

import anthropic

from subterminator.core.protocols import AIInterpretation, State
from subterminator.utils.exceptions import StateDetectionError


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
            return AIInterpretation(State.LOGIN_REQUIRED, 0.95, "URL contains /login")

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

        # T8.5: Text detection - third-party billing
        third_party_indicators = [
            "billed through",
            "itunes",
            "google play",
            "t-mobile",
            "app store",
            "play store",
        ]
        if any(indicator in text_lower for indicator in third_party_indicators):
            return AIInterpretation(
                State.THIRD_PARTY_BILLING, 0.80, "Third-party billing detected"
            )

        # T8.6: Text detection - cancel flow states (check before ACCOUNT_CANCELLED)
        # These are more specific and should take priority
        retention_phrases = [
            "before you go",
            "special offer",
            "we'd hate to see you go",
            "save",
        ]
        if any(phrase in text_lower for phrase in retention_phrases):
            if "discount" in text_lower or "offer" in text_lower:
                return AIInterpretation(
                    State.RETENTION_OFFER, 0.75, "Retention offer detected"
                )

        survey_phrases = [
            "why are you leaving",
            "reason for cancelling",
            "tell us why",
            "feedback",
        ]
        if any(phrase in text_lower for phrase in survey_phrases):
            return AIInterpretation(State.EXIT_SURVEY, 0.75, "Survey language detected")

        final_confirm_phrases = [
            "finish cancellation",
            "confirm cancellation",
            "complete cancellation",
        ]
        if any(phrase in text_lower for phrase in final_confirm_phrases):
            return AIInterpretation(
                State.FINAL_CONFIRMATION, 0.80, "Finish button detected"
            )

        # Strong COMPLETE indicators take priority (explicit completion message)
        strong_complete_phrases = [
            "cancellation is complete",
            "your cancellation is complete",
        ]
        if any(phrase in text_lower for phrase in strong_complete_phrases):
            return AIInterpretation(State.COMPLETE, 0.80, "Cancellation confirmed")

        # Weaker COMPLETE indicators (only if no restart membership option present)
        weak_complete_phrases = ["cancelled", "membership ends"]
        if any(phrase in text_lower for phrase in weak_complete_phrases):
            # Only consider COMPLETE if there's no "restart membership" (which indicates
            # ACCOUNT_CANCELLED state instead)
            if not ("restart" in text_lower and "membership" in text_lower):
                return AIInterpretation(State.COMPLETE, 0.80, "Cancellation confirmed")

        # Check ACCOUNT_CANCELLED after flow states (restart with membership but
        # not in cancellation flow context)
        if "restart" in text_lower and "membership" in text_lower:
            # Make sure this isn't a "restart anytime" on a confirmation page
            if "finish cancellation" not in text_lower:
                return AIInterpretation(
                    State.ACCOUNT_CANCELLED,
                    0.85,
                    "Restart link found - already cancelled",
                )

        # T8.7: Text detection - error state
        error_phrases = ["something went wrong", "error", "try again", "unexpected"]
        if any(phrase in text_lower for phrase in error_phrases):
            return AIInterpretation(State.FAILED, 0.70, "Error page detected")

        # T8.8: Return UNKNOWN as fallback
        return AIInterpretation(State.UNKNOWN, 0.0, "No patterns matched")


class ClaudeInterpreter:
    """Claude Vision-based page state interpreter.

    Uses Claude's vision capabilities to analyze screenshots and determine
    the current state in a subscription cancellation flow. This is used
    when heuristic-based detection fails or returns low confidence.

    Note: This interpreter uses the synchronous Anthropic client wrapped in
    asyncio.to_thread() to avoid blocking the event loop while maintaining
    the async interface expected by the engine.

    Example:
        >>> interpreter = ClaudeInterpreter()
        >>> result = await interpreter.interpret(screenshot_bytes)
        >>> result.state
        <State.LOGIN_REQUIRED: 2>
        >>> result.confidence
        0.95
    """

    PROMPT_TEMPLATE = """Analyze this screenshot of a subscription cancellation flow.

Determine which state this page represents:
- LOGIN_REQUIRED: Login form is shown
- ACCOUNT_ACTIVE: Account page with active subscription, cancel option visible
- ACCOUNT_CANCELLED: Account page showing cancelled/inactive subscription
- THIRD_PARTY_BILLING: Shows billing through Apple/Google/carrier
- RETENTION_OFFER: Discount or "stay with us" offer
- EXIT_SURVEY: "Why are you leaving?" survey
- FINAL_CONFIRMATION: Final "Finish Cancellation" button
- COMPLETE: Cancellation confirmed
- FAILED: Error message displayed
- UNKNOWN: Cannot determine

Also identify any actionable buttons/links with their approximate text.

Respond in JSON format:
{
  "state": "<STATE>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>",
  "actions": [{"text": "<button text>", "action": "<click|skip>"}]
}"""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the ClaudeInterpreter.

        Args:
            api_key: Optional Anthropic API key. If not provided, will use
                the ANTHROPIC_API_KEY environment variable.
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    async def interpret(self, screenshot: bytes) -> AIInterpretation:
        """Interpret page state from screenshot using Claude Vision.

        Args:
            screenshot: PNG image bytes of the page screenshot.

        Returns:
            AIInterpretation with detected state, confidence, reasoning,
            and suggested actions.

        Raises:
            StateDetectionError: If the Claude API call fails or response
                cannot be parsed.
        """
        import asyncio

        # Run the synchronous API call in a thread to avoid blocking event loop
        return await asyncio.to_thread(self._interpret_sync, screenshot)

    def _interpret_sync(self, screenshot: bytes) -> AIInterpretation:
        """Synchronous implementation of interpret.

        Args:
            screenshot: PNG image bytes of the page screenshot.

        Returns:
            AIInterpretation with detected state, confidence, reasoning,
            and suggested actions.

        Raises:
            StateDetectionError: If the Claude API call fails or response
                cannot be parsed.
        """
        image_data = base64.b64encode(screenshot).decode("utf-8")

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": self.PROMPT_TEMPLATE},
                        ],
                    }
                ],
            )
            # Extract text from the first content block
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                raise StateDetectionError(
                    "Claude response did not contain expected text content"
                )
            return self._parse_response(content_block.text)
        except anthropic.APIError as e:
            raise StateDetectionError(f"Claude API error: {e}") from e

    def _parse_response(self, text: str) -> AIInterpretation:
        """Parse Claude's JSON response.

        Args:
            text: The raw text response from Claude, which may contain
                JSON directly or wrapped in markdown code blocks.

        Returns:
            AIInterpretation with parsed state, confidence, reasoning,
            and actions.

        Raises:
            StateDetectionError: If the response cannot be parsed as valid
                JSON or is missing required fields.
        """
        try:
            # Handle markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            state_str = data["state"].upper()

            # Map state string to enum
            try:
                state = State[state_str]
            except KeyError:
                state = State.UNKNOWN

            return AIInterpretation(
                state=state,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                actions=data.get("actions", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise StateDetectionError(f"Failed to parse Claude response: {e}") from e
