"""Unit tests for ClaudeInterpreter.

Tests cover:
- Initialization with and without API key
- _parse_response with valid JSON
- _parse_response with markdown code blocks
- _parse_response with invalid JSON raises StateDetectionError
- State enum mapping for valid and invalid states
"""

import pytest

from subterminator.core.ai import ClaudeInterpreter
from subterminator.core.protocols import AIInterpretation, State
from subterminator.utils.exceptions import StateDetectionError


class TestClaudeInterpreterInit:
    """Tests for ClaudeInterpreter initialization."""

    def test_init_without_api_key(self) -> None:
        """ClaudeInterpreter can be initialized without explicit API key."""
        # Will use ANTHROPIC_API_KEY from environment or fail gracefully
        interpreter = ClaudeInterpreter()
        assert interpreter.client is not None

    def test_init_with_api_key(self) -> None:
        """ClaudeInterpreter can be initialized with explicit API key."""
        interpreter = ClaudeInterpreter(api_key="test-api-key")
        assert interpreter.client is not None


class TestParseResponse:
    """Tests for _parse_response method."""

    @pytest.fixture
    def interpreter(self) -> ClaudeInterpreter:
        """Create a ClaudeInterpreter instance for testing."""
        return ClaudeInterpreter(api_key="test-key")

    def test_parse_valid_json(self, interpreter: ClaudeInterpreter) -> None:
        """Valid JSON response should be parsed correctly."""
        response_text = '''{
            "state": "LOGIN_REQUIRED",
            "confidence": 0.95,
            "reasoning": "Login form with email and password fields detected",
            "actions": [{"text": "Sign In", "action": "click"}]
        }'''
        result = interpreter._parse_response(response_text)

        assert isinstance(result, AIInterpretation)
        assert result.state == State.LOGIN_REQUIRED
        assert result.confidence == 0.95
        assert result.reasoning == "Login form with email and password fields detected"
        assert result.actions == [{"text": "Sign In", "action": "click"}]

    def test_parse_json_with_markdown_code_block(
        self, interpreter: ClaudeInterpreter
    ) -> None:
        """JSON wrapped in markdown code block should be parsed correctly."""
        response_text = '''Here's my analysis:

```json
{
    "state": "ACCOUNT_ACTIVE",
    "confidence": 0.85,
    "reasoning": "Account page with cancel button visible",
    "actions": [{"text": "Cancel Membership", "action": "click"}]
}
```

This appears to be an active account page.'''
        result = interpreter._parse_response(response_text)

        assert result.state == State.ACCOUNT_ACTIVE
        assert result.confidence == 0.85
        assert result.reasoning == "Account page with cancel button visible"
        assert result.actions == [{"text": "Cancel Membership", "action": "click"}]

    def test_parse_json_with_generic_code_block(
        self, interpreter: ClaudeInterpreter
    ) -> None:
        """JSON wrapped in generic code block should be parsed correctly."""
        response_text = '''Analysis:

```
{
    "state": "EXIT_SURVEY",
    "confidence": 0.75,
    "reasoning": "Survey form asking why user is leaving",
    "actions": []
}
```'''
        result = interpreter._parse_response(response_text)

        assert result.state == State.EXIT_SURVEY
        assert result.confidence == 0.75
        assert result.reasoning == "Survey form asking why user is leaving"
        assert result.actions == []

    def test_parse_invalid_json_raises_error(
        self, interpreter: ClaudeInterpreter
    ) -> None:
        """Invalid JSON should raise StateDetectionError."""
        response_text = "This is not valid JSON at all"

        with pytest.raises(StateDetectionError) as exc_info:
            interpreter._parse_response(response_text)

        assert "Failed to parse Claude response" in str(exc_info.value)

    def test_parse_json_missing_required_field_raises_error(
        self, interpreter: ClaudeInterpreter
    ) -> None:
        """JSON missing required 'state' field should raise StateDetectionError."""
        response_text = '''{
            "confidence": 0.95,
            "reasoning": "Some reasoning"
        }'''

        with pytest.raises(StateDetectionError) as exc_info:
            interpreter._parse_response(response_text)

        assert "Failed to parse Claude response" in str(exc_info.value)

    def test_parse_unknown_state_maps_to_unknown(
        self, interpreter: ClaudeInterpreter
    ) -> None:
        """Unknown state string should map to State.UNKNOWN."""
        response_text = '''{
            "state": "SOME_INVALID_STATE",
            "confidence": 0.5,
            "reasoning": "Could not determine state"
        }'''
        result = interpreter._parse_response(response_text)

        assert result.state == State.UNKNOWN

    def test_parse_lowercase_state(self, interpreter: ClaudeInterpreter) -> None:
        """Lowercase state string should be normalized to uppercase."""
        response_text = '''{
            "state": "login_required",
            "confidence": 0.90,
            "reasoning": "Login page detected"
        }'''
        result = interpreter._parse_response(response_text)

        assert result.state == State.LOGIN_REQUIRED

    def test_parse_optional_fields_have_defaults(
        self, interpreter: ClaudeInterpreter
    ) -> None:
        """Missing optional fields should use defaults."""
        response_text = '''{
            "state": "COMPLETE"
        }'''
        result = interpreter._parse_response(response_text)

        assert result.state == State.COMPLETE
        assert result.confidence == 0.5  # Default confidence
        assert result.reasoning == ""  # Default reasoning
        assert result.actions == []  # Default actions

    def test_parse_all_valid_states(self, interpreter: ClaudeInterpreter) -> None:
        """All valid State enum values should be correctly mapped."""
        valid_states = [
            "LOGIN_REQUIRED",
            "ACCOUNT_ACTIVE",
            "ACCOUNT_CANCELLED",
            "THIRD_PARTY_BILLING",
            "RETENTION_OFFER",
            "EXIT_SURVEY",
            "FINAL_CONFIRMATION",
            "COMPLETE",
            "FAILED",
            "UNKNOWN",
        ]
        for state_str in valid_states:
            response_text = f'{{"state": "{state_str}", "confidence": 0.8}}'
            result = interpreter._parse_response(response_text)
            assert result.state == State[state_str], f"Failed for state {state_str}"


class TestPromptTemplate:
    """Tests for the PROMPT_TEMPLATE."""

    def test_prompt_template_exists(self) -> None:
        """PROMPT_TEMPLATE class attribute should exist."""
        assert hasattr(ClaudeInterpreter, "PROMPT_TEMPLATE")
        assert isinstance(ClaudeInterpreter.PROMPT_TEMPLATE, str)

    def test_prompt_template_contains_states(self) -> None:
        """PROMPT_TEMPLATE should mention all relevant states."""
        prompt = ClaudeInterpreter.PROMPT_TEMPLATE
        expected_states = [
            "LOGIN_REQUIRED",
            "ACCOUNT_ACTIVE",
            "ACCOUNT_CANCELLED",
            "THIRD_PARTY_BILLING",
            "RETENTION_OFFER",
            "EXIT_SURVEY",
            "FINAL_CONFIRMATION",
            "COMPLETE",
            "FAILED",
            "UNKNOWN",
        ]
        for state in expected_states:
            assert state in prompt, f"State {state} not in prompt template"

    def test_prompt_template_requests_json_format(self) -> None:
        """PROMPT_TEMPLATE should request JSON response format."""
        prompt = ClaudeInterpreter.PROMPT_TEMPLATE
        assert "JSON" in prompt or "json" in prompt


class TestModuleExports:
    """Tests for module exports."""

    def test_claude_interpreter_importable_from_core(self) -> None:
        """ClaudeInterpreter should be importable from subterminator.core."""
        from subterminator.core import ClaudeInterpreter

        interpreter = ClaudeInterpreter(api_key="test-key")
        assert interpreter is not None

    def test_claude_interpreter_importable_from_ai(self) -> None:
        """ClaudeInterpreter should be importable from subterminator.core.ai."""
        from subterminator.core.ai import ClaudeInterpreter

        interpreter = ClaudeInterpreter(api_key="test-key")
        assert interpreter is not None
