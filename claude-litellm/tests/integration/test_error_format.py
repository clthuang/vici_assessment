"""Integration test for error response format.

T-038: Verify that oversized input returns a properly formatted OpenAI-compatible
error. This test does NOT require an API key — it tests the provider directly
with mocked initialization.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from litellm.llms.custom_llm import CustomLLMError

from claude_da.config import ClaudeDAConfig
from claude_da.provider import ClaudeDAProvider


@pytest.mark.asyncio
async def test_oversized_input_error_format() -> None:
    """Test that input exceeding input_max_chars returns proper error format.

    Validates:
    - CustomLLMError is raised with status_code=400
    - Error body is valid JSON with error.message, error.type, error.code
    - error.type is "invalid_request_error"
    - error.code is "input_too_long"
    """
    provider = ClaudeDAProvider()

    # Mock the config and initialization to avoid needing API key or database
    test_config = ClaudeDAConfig(
        anthropic_api_key="sk-ant-test-key",
        db_path="/tmp/test.db",
        model="claude-sonnet-4-5-20250929",
        max_turns=10,
        max_budget_usd=0.50,
        input_max_chars=100,  # Low limit for easy testing
        log_output="stdout",
        log_file="./test-audit.jsonl",
        log_verbose=False,
    )

    # Mock the initialization process
    provider._config = test_config
    provider._agent = AsyncMock()
    provider._audit = AsyncMock()
    provider._initialized = True

    # Create oversized input
    messages = [
        {
            "role": "user",
            "content": "x" * 150,  # Exceeds the 100-char limit
        }
    ]

    # Attempt acompletion with oversized input
    with pytest.raises(CustomLLMError) as exc_info:
        await provider.acompletion(
            model="claude-da/analyst",
            messages=messages,
            api_base="",
            custom_prompt_dict={},
            model_response=AsyncMock(),
            print_verbose=MagicMock(),
            encoding=None,
            api_key=None,
            logging_obj=AsyncMock(),
            optional_params={},
        )

    # Verify status code
    assert exc_info.value.status_code == 400

    # Verify error body structure
    error_body = json.loads(str(exc_info.value))
    assert "error" in error_body
    assert "message" in error_body["error"]
    assert "type" in error_body["error"]
    assert "code" in error_body["error"]

    # Verify error content
    expected_msg = "Input length 150 exceeds maximum 100 characters"
    assert expected_msg in error_body["error"]["message"]
    assert error_body["error"]["type"] == "invalid_request_error"
    assert error_body["error"]["code"] == "input_too_long"
