"""Unit tests for Claude-DA LiteLLM custom provider.

Covers:
- T-027a: ClaudeDAProvider shell (CustomLLM subclass, completion/streaming raise)
- T-028: _handle_error() produces correct OpenAI error JSON
- T-027b: _ensure_initialized() double-check locking, error caching
- T-029/T-030: acompletion() input validation, ModelResponse, audit
- T-031/T-032: astreaming() chunk sequence, audit, input validation
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm import ModelResponse
from litellm.llms.custom_llm import CustomLLMError
from litellm.types.llms.custom_llm import CustomLLM

from claude_da.agent import AgentResult, AgentResultMetadata
from claude_da.audit import AuditEntry
from claude_da.config import ClaudeDAConfig
from claude_da.exceptions import (
    AgentTimeoutError,
    ClaudeDAError,
    ConfigurationError,
    DatabaseUnavailableError,
    InputValidationError,
    RateLimitError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> ClaudeDAConfig:
    """Create a test config with low input_max_chars for easy testing."""
    return ClaudeDAConfig(
        anthropic_api_key="sk-ant-test-key",
        db_path="/tmp/test.db",
        model="claude-sonnet-4-5-20250929",
        max_turns=10,
        max_budget_usd=0.50,
        input_max_chars=100,
    )


def _make_agent_result(
    response_text: str = "There are 42 users.",
    sql_queries: list[str] | None = None,
    query_results: list[dict] | None = None,
) -> AgentResult:
    """Create a mock AgentResult."""
    return AgentResult(
        response_text=response_text,
        sql_queries=sql_queries or ["SELECT COUNT(*) FROM users"],
        query_results=query_results or [{"count": 42}],
        metadata=AgentResultMetadata(
            model="claude-sonnet-4-5-20250929",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost_usd=0.005,
            duration_seconds=1.5,
            tool_call_count=1,
        ),
    )


# ---------------------------------------------------------------------------
# T-027a / T-028: ClaudeDAProvider shell tests
# ---------------------------------------------------------------------------


class TestProviderShell:
    """Test ClaudeDAProvider is a proper CustomLLM subclass."""

    def test_module_level_instance_is_custom_llm(self) -> None:
        from claude_da.provider import claude_da_provider

        assert isinstance(claude_da_provider, CustomLLM)

    def test_provider_class_inherits_custom_llm(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        assert issubclass(ClaudeDAProvider, CustomLLM)

    def test_init_sets_initialized_false(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        assert provider._initialized is False

    def test_init_sets_init_error_none(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        assert provider._init_error is None

    def test_init_creates_lock(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        assert isinstance(provider._init_lock, asyncio.Lock)

    def test_completion_raises_not_implemented(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        with pytest.raises(NotImplementedError):
            provider.completion(
                model="test",
                messages=[],
                api_base="",
                custom_prompt_dict={},
                model_response=MagicMock(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            )

    def test_streaming_raises_not_implemented(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        with pytest.raises(NotImplementedError):
            provider.streaming(
                model="test",
                messages=[],
                api_base="",
                custom_prompt_dict={},
                model_response=MagicMock(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            )


# ---------------------------------------------------------------------------
# T-028: _handle_error() tests
# ---------------------------------------------------------------------------


class TestHandleError:
    """Test _handle_error() translates ClaudeDAError to CustomLLMError."""

    def test_input_validation_error(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        exc = InputValidationError("Input too long")

        with pytest.raises(CustomLLMError) as exc_info:
            provider._handle_error(exc)

        error_body = json.loads(str(exc_info.value))
        assert error_body["error"]["message"] == "Input too long"
        assert error_body["error"]["type"] == "invalid_request_error"
        assert error_body["error"]["code"] == "input_too_long"
        assert exc_info.value.status_code == 400

    def test_agent_timeout_error(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        exc = AgentTimeoutError("Timed out")

        with pytest.raises(CustomLLMError) as exc_info:
            provider._handle_error(exc)

        error_body = json.loads(str(exc_info.value))
        assert error_body["error"]["message"] == "Timed out"
        assert error_body["error"]["type"] == "server_error"
        assert error_body["error"]["code"] == "agent_timeout"
        assert exc_info.value.status_code == 504

    def test_rate_limit_error(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        exc = RateLimitError("Rate limited")

        with pytest.raises(CustomLLMError) as exc_info:
            provider._handle_error(exc)

        error_body = json.loads(str(exc_info.value))
        assert error_body["error"]["message"] == "Rate limited"
        assert error_body["error"]["type"] == "rate_limit_error"
        assert error_body["error"]["code"] == "rate_limited"
        assert exc_info.value.status_code == 429

    def test_database_unavailable_error(self) -> None:
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        exc = DatabaseUnavailableError("DB down")

        with pytest.raises(CustomLLMError) as exc_info:
            provider._handle_error(exc)

        error_body = json.loads(str(exc_info.value))
        assert error_body["error"]["message"] == "DB down"
        assert error_body["error"]["type"] == "server_error"
        assert error_body["error"]["code"] == "database_unavailable"
        assert exc_info.value.status_code == 503

    def test_generic_claude_da_error_defaults(self) -> None:
        """ClaudeDAError without status_code/error_code uses defaults."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        exc = ClaudeDAError("Something went wrong")

        with pytest.raises(CustomLLMError) as exc_info:
            provider._handle_error(exc)

        error_body = json.loads(str(exc_info.value))
        assert error_body["error"]["message"] == "Something went wrong"
        assert error_body["error"]["type"] == "server_error"
        assert error_body["error"]["code"] == "internal_error"
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# T-027b: _ensure_initialized() tests
# ---------------------------------------------------------------------------


class TestEnsureInitialized:
    """Test _ensure_initialized() double-check locking and error caching."""

    @pytest.mark.asyncio
    async def test_successful_init(self) -> None:
        """After successful init, provider is marked initialized."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        config = _make_config()

        with (
            patch("claude_da.provider.load_config", return_value=config),
            patch(
                "claude_da.provider.discover_schema",
                return_value=MagicMock(),
            ),
            patch("claude_da.provider.verify_read_only"),
            patch(
                "claude_da.provider.build_system_prompt",
                return_value="system prompt",
            ),
            patch("claude_da.provider.DataAnalystAgent"),
            patch("claude_da.provider.AuditLogger"),
        ):
            await provider._ensure_initialized()

        assert provider._initialized is True
        assert provider._init_error is None

    @pytest.mark.asyncio
    async def test_init_failure_caches_error(self) -> None:
        """If init fails, error is cached and re-raised on subsequent calls."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()

        with patch(
            "claude_da.provider.load_config",
            side_effect=ConfigurationError("Missing key"),
        ):
            with pytest.raises(ConfigurationError, match="Missing key"):
                await provider._ensure_initialized()

        assert provider._init_error is not None
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_cached_error_returned_without_retry(self) -> None:
        """Second call returns cached error without retrying init."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        mock_load = MagicMock(side_effect=ConfigurationError("Missing key"))

        with patch("claude_da.provider.load_config", mock_load):
            with pytest.raises(ConfigurationError):
                await provider._ensure_initialized()

        # Second call should raise same error without calling load_config again
        with pytest.raises(ConfigurationError, match="Missing key"):
            await provider._ensure_initialized()

        # load_config should only have been called once
        assert mock_load.call_count == 1

    @pytest.mark.asyncio
    async def test_already_initialized_skips_init(self) -> None:
        """If already initialized, _ensure_initialized is a no-op."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._agent = MagicMock()
        provider._audit = MagicMock()
        provider._config = _make_config()

        mock_load = MagicMock()
        with patch("claude_da.provider.load_config", mock_load):
            await provider._ensure_initialized()

        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# T-029 / T-030: acompletion() tests
# ---------------------------------------------------------------------------


class TestAcompletion:
    """Test acompletion() input validation, response format, and audit."""

    @pytest.mark.asyncio
    async def test_oversized_input_raises_error(self) -> None:
        """Input exceeding max_chars triggers _handle_error."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()  # input_max_chars=100
        provider._agent = MagicMock()
        provider._audit = MagicMock()

        messages = [{"role": "user", "content": "x" * 101}]

        with pytest.raises(CustomLLMError) as exc_info:
            await provider.acompletion(
                model="claude-da/analyst",
                messages=messages,
                api_base="",
                custom_prompt_dict={},
                model_response=ModelResponse(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            )

        error_body = json.loads(str(exc_info.value))
        assert error_body["error"]["code"] == "input_too_long"
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_input_returns_model_response(self) -> None:
        """Successful agent.run() returns a ModelResponse."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()
        provider._audit = MagicMock()
        provider._audit.log = AsyncMock()

        result = _make_agent_result()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=result)
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "How many users?"}]

        response = await provider.acompletion(
            model="claude-da/analyst",
            messages=messages,
            api_base="",
            custom_prompt_dict={},
            model_response=ModelResponse(),
            print_verbose=lambda *a: None,
            encoding=None,
            api_key=None,
            logging_obj=MagicMock(),
            optional_params={},
        )

        assert isinstance(response, ModelResponse)
        assert response.choices[0].message.content == "There are 42 users."
        assert response.usage.prompt_tokens == 100
        assert response.usage.completion_tokens == 50
        assert response.usage.total_tokens == 150

    @pytest.mark.asyncio
    async def test_acompletion_calls_agent_run(self) -> None:
        """acompletion delegates to agent.run() with the messages."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()
        provider._audit = MagicMock()
        provider._audit.log = AsyncMock()

        result = _make_agent_result()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=result)
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "Hello"}]

        await provider.acompletion(
            model="claude-da/analyst",
            messages=messages,
            api_base="",
            custom_prompt_dict={},
            model_response=ModelResponse(),
            print_verbose=lambda *a: None,
            encoding=None,
            api_key=None,
            logging_obj=MagicMock(),
            optional_params={},
        )

        mock_agent.run.assert_called_once_with(messages)

    @pytest.mark.asyncio
    async def test_acompletion_creates_audit_task(self) -> None:
        """acompletion fires an audit log task."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()

        mock_audit = MagicMock()
        mock_audit.log = AsyncMock()
        provider._audit = mock_audit

        result = _make_agent_result()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=result)
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "Hello"}]

        await provider.acompletion(
            model="claude-da/analyst",
            messages=messages,
            api_base="",
            custom_prompt_dict={},
            model_response=ModelResponse(),
            print_verbose=lambda *a: None,
            encoding=None,
            api_key=None,
            logging_obj=MagicMock(),
            optional_params={},
        )

        # Give the fire-and-forget task a chance to run
        await asyncio.sleep(0.05)

        mock_audit.log.assert_called_once()
        audit_entry = mock_audit.log.call_args[0][0]
        assert isinstance(audit_entry, AuditEntry)
        assert audit_entry.user_question == "Hello"
        assert audit_entry.final_response == "There are 42 users."

    @pytest.mark.asyncio
    async def test_acompletion_agent_error_becomes_custom_llm_error(
        self,
    ) -> None:
        """ClaudeDAError from agent.run() is translated via _handle_error."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()
        provider._audit = MagicMock()

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(side_effect=AgentTimeoutError("Agent timed out"))
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(CustomLLMError) as exc_info:
            await provider.acompletion(
                model="claude-da/analyst",
                messages=messages,
                api_base="",
                custom_prompt_dict={},
                model_response=ModelResponse(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_acompletion_multi_message_input_length(self) -> None:
        """Input length sums all message content lengths."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()  # input_max_chars=100
        provider._agent = MagicMock()
        provider._audit = MagicMock()

        # Two messages, each 60 chars = 120 total > 100 limit
        messages = [
            {"role": "user", "content": "a" * 60},
            {"role": "user", "content": "b" * 60},
        ]

        with pytest.raises(CustomLLMError) as exc_info:
            await provider.acompletion(
                model="claude-da/analyst",
                messages=messages,
                api_base="",
                custom_prompt_dict={},
                model_response=ModelResponse(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# T-031 / T-032: astreaming() tests
# ---------------------------------------------------------------------------


class TestAstreaming:
    """Test astreaming() chunk sequence, audit, and input validation."""

    @pytest.mark.asyncio
    async def test_oversized_input_raises_error(self) -> None:
        """Input exceeding max_chars triggers _handle_error in streaming."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()  # input_max_chars=100
        provider._agent = MagicMock()
        provider._audit = MagicMock()

        messages = [{"role": "user", "content": "x" * 101}]

        with pytest.raises(CustomLLMError) as exc_info:
            async for _ in provider.astreaming(
                model="claude-da/analyst",
                messages=messages,
                api_base="",
                custom_prompt_dict={},
                model_response=ModelResponse(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            ):
                pass

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_streaming_yields_chunks(self) -> None:
        """Streaming returns chunks from agent.run_streaming()."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()

        mock_audit = MagicMock()
        mock_audit.log = AsyncMock()
        provider._audit = mock_audit

        result = _make_agent_result()
        chunk1 = {
            "text": "Part 1. ",
            "is_finished": False,
            "finish_reason": "",
            "index": 0,
            "tool_use": None,
        }
        chunk2 = {
            "text": "",
            "is_finished": True,
            "finish_reason": "stop",
            "index": 0,
            "tool_use": None,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        async def mock_run_streaming(
            messages: list[dict],
            result_holder: list,
        ) -> AsyncIterator[dict]:
            yield chunk1
            yield chunk2
            result_holder[0] = result

        mock_agent = MagicMock()
        mock_agent.run_streaming = mock_run_streaming
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "Hello"}]
        chunks: list[dict] = []

        async for chunk in provider.astreaming(
            model="claude-da/analyst",
            messages=messages,
            api_base="",
            custom_prompt_dict={},
            model_response=ModelResponse(),
            print_verbose=lambda *a: None,
            encoding=None,
            api_key=None,
            logging_obj=MagicMock(),
            optional_params={},
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["text"] == "Part 1. "
        assert chunks[0]["is_finished"] is False
        assert chunks[1]["is_finished"] is True
        assert chunks[1]["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_streaming_fires_audit_after_completion(self) -> None:
        """Audit is fired after streaming completes with result_holder."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()

        mock_audit = MagicMock()
        mock_audit.log = AsyncMock()
        provider._audit = mock_audit

        result = _make_agent_result()

        async def mock_run_streaming(
            messages: list[dict],
            result_holder: list,
        ) -> AsyncIterator[dict]:
            yield {
                "text": "",
                "is_finished": True,
                "finish_reason": "stop",
                "index": 0,
                "tool_use": None,
            }
            result_holder[0] = result

        mock_agent = MagicMock()
        mock_agent.run_streaming = mock_run_streaming
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "Hello"}]

        async for _ in provider.astreaming(
            model="claude-da/analyst",
            messages=messages,
            api_base="",
            custom_prompt_dict={},
            model_response=ModelResponse(),
            print_verbose=lambda *a: None,
            encoding=None,
            api_key=None,
            logging_obj=MagicMock(),
            optional_params={},
        ):
            pass

        # Give the fire-and-forget task a chance to run
        await asyncio.sleep(0.05)

        mock_audit.log.assert_called_once()
        audit_entry = mock_audit.log.call_args[0][0]
        assert isinstance(audit_entry, AuditEntry)
        assert audit_entry.final_response == "There are 42 users."

    @pytest.mark.asyncio
    async def test_streaming_agent_error_becomes_custom_llm_error(
        self,
    ) -> None:
        """ClaudeDAError from agent.run_streaming() is translated."""
        from claude_da.provider import ClaudeDAProvider

        provider = ClaudeDAProvider()
        provider._initialized = True
        provider._config = _make_config()
        provider._audit = MagicMock()

        async def mock_run_streaming(
            messages: list[dict],
            result_holder: list,
        ) -> AsyncIterator[dict]:
            raise DatabaseUnavailableError("DB down")
            yield  # noqa: F841 -- unreachable; makes this an async generator

        mock_agent = MagicMock()
        mock_agent.run_streaming = mock_run_streaming
        provider._agent = mock_agent

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(CustomLLMError) as exc_info:
            async for _ in provider.astreaming(
                model="claude-da/analyst",
                messages=messages,
                api_base="",
                custom_prompt_dict={},
                model_response=ModelResponse(),
                print_verbose=lambda *a: None,
                encoding=None,
                api_key=None,
                logging_obj=MagicMock(),
                optional_params={},
            ):
                pass

        assert exc_info.value.status_code == 503
