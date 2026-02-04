"""Page state interpretation for SubTerminator.

This module provides both heuristic-based and AI-based page state detection:
- HeuristicInterpreter: Fast, rule-based detection using URL patterns and text
- ClaudeInterpreter: Claude Vision-based detection for when heuristics fail
- ClaudeActionPlanner: Tool-use based action planning for AI-driven control
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

import anthropic

from subterminator.core.protocols import AIInterpretation, State
from subterminator.utils.exceptions import StateDetectionError

if TYPE_CHECKING:
    from subterminator.core.protocols import (
        ActionPlan,
        AgentContext,
        PlannedAction,
        TargetStrategy,
    )


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
        has_account_indicator = (
            "cancel membership" in text_lower or "manage membership" in text_lower
        )
        if has_account_indicator and "/account" in url:
            return AIInterpretation(
                State.ACCOUNT_ACTIVE, 0.85, "Account management page detected"
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
        # IMPORTANT: Check FINAL_CONFIRMATION first - higher priority than
        # RETENTION_OFFER - misclassifying would skip human safety checkpoint

        # FINAL_CONFIRMATION - check these FIRST (higher priority)
        final_confirm_phrases = [
            "finish cancellation",
            "confirm cancellation",
            "complete cancellation",
            "finalize cancellation",
            "this action is final",
            "this is final",
            "cannot be undone",
        ]
        if any(phrase in text_lower for phrase in final_confirm_phrases):
            return AIInterpretation(
                State.FINAL_CONFIRMATION, 0.85, "Final confirmation page detected"
            )

        survey_phrases = [
            "why are you leaving",
            "reason for cancelling",
            "tell us why",
            "feedback",
        ]
        if any(phrase in text_lower for phrase in survey_phrases):
            return AIInterpretation(State.EXIT_SURVEY, 0.75, "Survey language detected")

        # RETENTION_OFFER - only check AFTER ruling out FINAL_CONFIRMATION
        # Netflix uses pause/downgrade options rather than discounts
        retention_phrases = [
            "before you go",
            "pause your membership",
            "pause for 1 month",
            "change your plan",
            "downgrade",
            "special offer",
            "stay with us",
            "we'd hate to see you go",
        ]
        if any(phrase in text_lower for phrase in retention_phrases):
            # Only classify as retention if no final confirmation indicators present
            if not any(p in text_lower for p in final_confirm_phrases):
                return AIInterpretation(
                    State.RETENTION_OFFER, 0.75, "Retention offer detected"
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
- RETENTION_OFFER: Page offering ALTERNATIVES to cancellation (pause subscription,
  downgrade plan, special discounts). Look for: "pause", "change plan", "downgrade",
  "special offer", "before you go". User has NOT yet finalized cancellation.
- EXIT_SURVEY: "Why are you leaving?" survey
- FINAL_CONFIRMATION: The LAST step before cancellation is executed. Look for:
  "Finish Cancellation" button, "Confirm Cancellation" heading, explicit
  "this is final" messaging. No alternative offers - just confirm or go back.
- COMPLETE: Cancellation confirmed
- FAILED: Error message displayed
- UNKNOWN: Cannot determine

KEY DISTINCTION for RETENTION_OFFER vs FINAL_CONFIRMATION:
- RETENTION_OFFER presents alternatives to keep user subscribed (pause, downgrade).
- FINAL_CONFIRMATION is point-of-no-return with only "confirm" or "go back".
If page has "Finish Cancellation" and NO pause/downgrade, it's FINAL_CONFIRMATION.

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


class ClaudeActionPlanner:
    """Claude-based action planner using tool use for browser automation.

    Uses Claude's tool-use capability to analyze page state and decide
    the next browser action to take. Returns structured PlannedAction
    objects that can be executed by the browser.

    Example:
        >>> planner = ClaudeActionPlanner()
        >>> action = await planner.plan(screenshot, url, accessibility_tree)
        >>> await browser.execute_action(action.action)
    """

    SYSTEM_PROMPT = (
        "You are an AI assistant helping to automate subscription "
        "cancellation flows.\n"
        "Analyze the screenshot and accessibility tree to determine "
        "the current page state and the best action to take.\n\n"
        "States:\n"
        "- LOGIN_REQUIRED: Login form visible, need user to authenticate\n"
        "- ACCOUNT_ACTIVE: Account page with active subscription\n"
        "- ACCOUNT_CANCELLED: Account already cancelled\n"
        "- THIRD_PARTY_BILLING: Billing managed by Apple/Google/carrier\n"
        "- RETENTION_OFFER: Offers to keep user (pause, discount)\n"
        "- EXIT_SURVEY: Survey asking why cancelling\n"
        "- FINAL_CONFIRMATION: Final 'confirm cancellation' step\n"
        "- COMPLETE: Cancellation successful\n"
        "- FAILED: Error state\n"
        "- UNKNOWN: Cannot determine state\n\n"
        "Use the browser_action tool to specify what action to take next."
    )

    # Updated TOOL_SCHEMA with targets array format per design.md Section 4.4
    TOOL_SCHEMA = {
        "name": "browser_action",
        "description": "Execute a browser action to progress toward the goal",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Detected current page state",
                    "enum": [
                        "LOGIN_REQUIRED", "ACCOUNT_ACTIVE", "ACCOUNT_CANCELLED",
                        "THIRD_PARTY_BILLING", "RETENTION_OFFER", "EXIT_SURVEY",
                        "FINAL_CONFIRMATION", "COMPLETE", "FAILED", "UNKNOWN"
                    ]
                },
                "expected_next_state": {
                    "type": "string",
                    "description": "Expected state after this action succeeds",
                    "enum": [
                        "LOGIN_REQUIRED", "ACCOUNT_ACTIVE", "ACCOUNT_CANCELLED",
                        "THIRD_PARTY_BILLING", "RETENTION_OFFER", "EXIT_SURVEY",
                        "FINAL_CONFIRMATION", "COMPLETE", "FAILED", "UNKNOWN"
                    ]
                },
                "action_type": {
                    "type": "string",
                    "enum": ["click", "fill", "select", "scroll", "wait", "navigate"]
                },
                "targets": {
                    "type": "array",
                    "description": (
                        "Element targeting strategies in priority order (provide 2-4)"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "enum": ["css", "aria", "text", "coordinates"]
                            },
                            "css": {"type": "string"},
                            "aria_role": {"type": "string"},
                            "aria_name": {"type": "string"},
                            "text": {"type": "string"},
                            "coordinates": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2
                            }
                        },
                        "required": ["method"]
                    },
                    "minItems": 1,
                    "maxItems": 4
                },
                "value": {"type": "string"},
                "reasoning": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["state", "action_type", "targets", "reasoning", "confidence"]
        }
    }

    # Legacy TOOLS list for backward compatibility
    TOOLS = [TOOL_SCHEMA]

    # Enhanced system prompt for agent mode
    AGENT_SYSTEM_PROMPT = (
        "You are an AI agent controlling a browser to cancel a subscription.\n\n"
        "Your task: Analyze the page and decide what action to take next.\n\n"
        "ELEMENT IDENTIFICATION PRIORITY:\n"
        "1. CSS selector - Use when element has unique id or class\n"
        "2. ARIA role + name - Use for buttons, links with clear labels\n"
        "3. Text content - Use when text is visible and unique\n"
        "4. Coordinates - ONLY as last resort when semantic methods fail\n\n"
        "RULES:\n"
        "- Always provide at least 2 targeting methods when possible\n"
        "- Confidence should reflect how certain you are about the target\n"
        "- If page state is unclear, set state to UNKNOWN\n"
        "- For fill/select actions, you MUST provide a value\n\n"
        "IMPORTANT: After clicking, the page will change. Your "
        "expected_next_state in the response should predict what state "
        "the page will be in AFTER the action completes."
    )

    SELF_CORRECT_PROMPT = (
        "Your previous action FAILED. You must try a DIFFERENT approach.\n\n"
        "FAILED ACTION:\n"
        "- Action: {action_type}\n"
        "- Target: {target_description}\n"
        "- Strategy: {failed_strategy}\n"
        "- Error: {error_message}\n\n"
        "STRATEGIES ALREADY TRIED:\n"
        "{strategies_tried}\n\n"
        "REQUIREMENT: Use a DIFFERENT targeting strategy than the ones "
        "listed above.\n"
        "- If CSS failed, try ARIA role/name\n"
        "- If ARIA failed, try text content\n"
        "- If text failed, try coordinates (analyze screenshot for position)\n\n"
        "Analyze the current screenshot and accessibility tree to find "
        "an alternative."
    )

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the ClaudeActionPlanner.

        Args:
            api_key: Optional Anthropic API key. If not provided, will use
                the ANTHROPIC_API_KEY environment variable.
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def _compress_screenshot(
        self, screenshot: bytes, max_size_bytes: int = 4_500_000
    ) -> bytes:
        """Compress screenshot if it exceeds max size for Claude API.

        Uses PIL to resize the image while maintaining aspect ratio.

        Args:
            screenshot: PNG screenshot bytes.
            max_size_bytes: Maximum allowed size in bytes (default 4.5MB for 5MB limit).

        Returns:
            Compressed screenshot bytes (JPEG for smaller size).
        """
        if len(screenshot) <= max_size_bytes:
            return screenshot

        try:
            from io import BytesIO

            from PIL import Image

            # Open the PNG image
            img = Image.open(BytesIO(screenshot))

            # Convert to RGB if necessary (JPEG doesn't support alpha)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Start with original size and reduce until under limit
            quality = 85
            scale = 1.0

            while True:
                # Resize if needed
                if scale < 1.0:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    resized = img.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    resized = img

                # Compress to JPEG
                output = BytesIO()
                resized.save(output, format="JPEG", quality=quality, optimize=True)
                compressed = output.getvalue()

                if len(compressed) <= max_size_bytes:
                    return compressed

                # Reduce quality or scale
                if quality > 50:
                    quality -= 10
                elif scale > 0.5:
                    scale -= 0.1
                    quality = 85  # Reset quality when scaling down
                else:
                    # Return best effort
                    return compressed

        except ImportError:
            # PIL not available, return original (will fail on API call)
            return screenshot
        except Exception:
            # Any other error, return original
            return screenshot

    async def plan_action(
        self,
        context: AgentContext,
        goal: str,
        error_context: str | None = None,
    ) -> ActionPlan:
        """Generate an action plan using Claude with AgentContext.

        Uses the new targets array format per design.md Section 4.4.

        Args:
            context: Current page context including screenshot.
            goal: What we're trying to achieve.
            error_context: Formatted error info for self-correction.

        Returns:
            ActionPlan parsed from Claude's tool_use response.

        Raises:
            StateDetectionError: If Claude returns invalid response.
            anthropic.APIError: If API call fails.
        """
        import asyncio

        return await asyncio.to_thread(
            self._plan_action_sync, context, goal, error_context
        )

    def _plan_action_sync(
        self,
        context: AgentContext,
        goal: str,
        error_context: str | None = None,
    ) -> ActionPlan:
        """Synchronous implementation of plan_action.

        Args:
            context: Current page context including screenshot.
            goal: What we're trying to achieve.
            error_context: Formatted error info for self-correction.

        Returns:
            ActionPlan with targeting strategies.
        """
        from subterminator.core.protocols import (
            ActionPlan,
            TargetStrategy,
        )

        # Compress screenshot if too large for Claude API (max 5MB)
        screenshot = self._compress_screenshot(context.screenshot, max_size_bytes=4_500_000)
        image_data = base64.b64encode(screenshot).decode("utf-8")

        # Detect media type (JPEG if compressed, PNG otherwise)
        media_type = "image/jpeg" if screenshot[:2] == b'\xff\xd8' else "image/png"

        # Build the prompt text
        prompt_text = f"""Goal: {goal}

{context.to_prompt_context()}"""

        if error_context:
            prompt_text = f"{error_context}\n\n{prompt_text}"

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.AGENT_SYSTEM_PROMPT,
                tools=[self.TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "browser_action"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt_text},
                        ],
                    }
                ],
            )

            # Find tool_use block in response
            for block in response.content:
                if block.type == "tool_use" and block.name == "browser_action":
                    return self._parse_action_plan(block.input)

            # No tool_use found, return default ActionPlan
            return ActionPlan(
                action_type="wait",
                primary_target=TargetStrategy(method="css", css_selector="body"),
                fallback_targets=[],
                value=None,
                reasoning="No action could be determined",
                confidence=0.0,
                expected_state=State.UNKNOWN,
            )

        except anthropic.APIError as e:
            raise StateDetectionError(f"Claude API error: {e}") from e

    def _parse_action_plan(self, tool_input: dict) -> ActionPlan:
        """Parse tool_use response into ActionPlan with targets array.

        Args:
            tool_input: The input dict from the tool_use block.

        Returns:
            ActionPlan with targeting strategies.
        """
        from subterminator.core.protocols import (
            ActionPlan,
            TargetStrategy,
        )

        # Parse state for expected_state
        expected_state = None
        expected_state_str = tool_input.get("expected_next_state", "")
        if expected_state_str:
            try:
                expected_state = State[expected_state_str.upper()]
            except KeyError:
                pass

        # Parse action type
        action_type = tool_input.get("action_type", "wait").lower()

        # Parse confidence
        confidence = tool_input.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        # Parse targets array
        targets_data = tool_input.get("targets", [])
        targets = self._parse_targets(targets_data)

        # Ensure we have at least one target
        if not targets:
            targets = [TargetStrategy(method="css", css_selector="body")]

        primary_target = targets[0]
        fallback_targets = targets[1:4] if len(targets) > 1 else []

        return ActionPlan(
            action_type=action_type,
            primary_target=primary_target,
            fallback_targets=fallback_targets,
            value=tool_input.get("value"),
            reasoning=tool_input.get("reasoning", ""),
            confidence=confidence,
            expected_state=expected_state,
        )

    async def plan(
        self,
        screenshot: bytes,
        url: str,
        accessibility_tree: dict,
    ) -> PlannedAction:
        """Plan the next browser action based on page state.

        Args:
            screenshot: PNG image bytes of the page screenshot.
            url: Current page URL.
            accessibility_tree: Accessibility tree snapshot of the page.

        Returns:
            PlannedAction with state, action, and reasoning.

        Raises:
            StateDetectionError: If the Claude API call fails.
        """
        import asyncio

        return await asyncio.to_thread(
            self._plan_sync, screenshot, url, accessibility_tree
        )

    def _plan_sync(
        self,
        screenshot: bytes,
        url: str,
        accessibility_tree: dict,
    ) -> PlannedAction:
        """Synchronous implementation of plan.

        Args:
            screenshot: PNG image bytes of the page screenshot.
            url: Current page URL.
            accessibility_tree: Accessibility tree snapshot of the page.

        Returns:
            PlannedAction with state, action, and reasoning.

        Raises:
            StateDetectionError: If the Claude API call fails.
        """
        from subterminator.core.protocols import (
            ActionType,
            BrowserAction,
            PlannedAction,
        )

        image_data = base64.b64encode(screenshot).decode("utf-8")

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                tools=self.TOOLS,
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
                            {
                                "type": "text",
                                "text": (
                                    f"URL: {url}\n\n"
                                    f"Accessibility tree: "
                                    f"{json.dumps(accessibility_tree, indent=2)}\n\n"
                                    "Analyze this page and decide the next action."
                                ),
                            },
                        ],
                    }
                ],
            )

            # Find tool_use block in response
            for block in response.content:
                if block.type == "tool_use" and block.name == "browser_action":
                    return self._parse_tool_response(block.input)

            # No tool_use found, return UNKNOWN state
            return PlannedAction(
                state=State.UNKNOWN,
                action=BrowserAction(
                    action_type=ActionType.WAIT,
                    selector="",
                    timeout=1000
                ),
                reasoning="No action could be determined",
                confidence=0.0
            )

        except anthropic.APIError as e:
            raise StateDetectionError(f"Claude API error: {e}") from e

    def _parse_tool_response(self, tool_input: dict) -> PlannedAction:
        """Parse tool_use response into PlannedAction.

        Supports both new targets array format and legacy selector format.

        Args:
            tool_input: The input dict from the tool_use block.

        Returns:
            PlannedAction with parsed state, action, and reasoning.
        """
        from subterminator.core.protocols import (
            ActionType,
            BrowserAction,
            PlannedAction,
        )

        # Parse state
        state_str = tool_input.get("state", "UNKNOWN").upper()
        try:
            state = State[state_str]
        except KeyError:
            state = State.UNKNOWN

        # Parse action type
        action_type_str = tool_input.get("action_type", "wait").upper()
        try:
            action_type = ActionType[action_type_str]
        except KeyError:
            action_type = ActionType.WAIT

        # Parse confidence
        confidence = tool_input.get("confidence", 1.0)
        if not isinstance(confidence, (int, float)):
            confidence = 1.0
        confidence = max(0.0, min(1.0, confidence))

        # Check for new targets array format
        targets_data = tool_input.get("targets", [])
        if targets_data:
            # Parse targets array into TargetStrategy objects
            targets = self._parse_targets(targets_data)
            primary_target = targets[0] if targets else None

            # If we have targets, convert to PlannedAction
            if primary_target:
                # Convert primary target to selector for BrowserAction
                selector = self._target_to_selector(primary_target)
                fallback_role = None
                if primary_target.method == "aria" and primary_target.aria_role:
                    fallback_role = (
                        primary_target.aria_role,
                        primary_target.aria_name or ""
                    )

                action = BrowserAction(
                    action_type=action_type,
                    selector=selector,
                    value=tool_input.get("value"),
                    timeout=None,
                    fallback_role=fallback_role
                )

                return PlannedAction(
                    state=state,
                    action=action,
                    reasoning=tool_input.get("reasoning", ""),
                    confidence=confidence
                )

        # Legacy selector format fallback
        action = BrowserAction(
            action_type=action_type,
            selector=tool_input.get("selector", ""),
            value=tool_input.get("value"),
            timeout=None,
            fallback_role=None
        )

        return PlannedAction(
            state=state,
            action=action,
            reasoning=tool_input.get("reasoning", ""),
            confidence=confidence
        )

    def _parse_targets(self, targets_data: list[dict]) -> list[TargetStrategy]:
        """Parse targets array into TargetStrategy objects.

        Args:
            targets_data: List of target dicts from tool response.

        Returns:
            List of TargetStrategy objects.
        """
        from subterminator.core.protocols import TargetStrategy

        targets = []
        for t in targets_data:
            method = t.get("method", "css")
            try:
                target = TargetStrategy(
                    method=method,
                    css_selector=t.get("css"),
                    aria_role=t.get("aria_role"),
                    aria_name=t.get("aria_name"),
                    text_content=t.get("text"),
                    coordinates=(
                        tuple(t["coordinates"]) if t.get("coordinates") else None
                    ),
                )
                targets.append(target)
            except ValueError:
                # Skip invalid targets but continue parsing
                continue
        return targets

    def _target_to_selector(self, target: TargetStrategy) -> str:
        """Convert TargetStrategy to CSS selector string.

        Args:
            target: TargetStrategy to convert.

        Returns:
            CSS selector string or empty string for non-CSS methods.
        """
        if target.method == "css" and target.css_selector:
            return target.css_selector
        elif target.method == "aria":
            # Return ARIA as a pseudo-selector for logging
            name_part = f"[name='{target.aria_name}']" if target.aria_name else ""
            return f"[role='{target.aria_role}']{name_part}"
        elif target.method == "text":
            return f":text('{target.text_content}')"
        elif target.method == "coordinates" and target.coordinates:
            return f"@({target.coordinates[0]},{target.coordinates[1]})"
        return ""
