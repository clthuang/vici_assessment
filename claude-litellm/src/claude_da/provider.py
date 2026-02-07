"""Claude-DA LiteLLM custom provider.

Implements the LiteLLM CustomLLM interface to expose the Claude data
analyst agent as a LiteLLM-compatible model. Only async methods
(acompletion, astreaming) are implemented; synchronous methods raise
NotImplementedError since the underlying Agent SDK is async-only.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from litellm import ModelResponse
from litellm.llms.custom_llm import CustomLLMError
from litellm.types.llms.custom_llm import CustomLLM

from claude_da.agent import DataAnalystAgent
from claude_da.audit import AuditEntry, AuditLogger, AuditMetadata
from claude_da.config import ClaudeDAConfig, load_config
from claude_da.exceptions import ClaudeDAError, InputValidationError
from claude_da.prompt import build_system_prompt
from claude_da.schema import discover_schema, verify_read_only

# ---------------------------------------------------------------------------
# Error type mapping
# ---------------------------------------------------------------------------

_ERROR_TYPE_MAP: dict[int, str] = {
    400: "invalid_request_error",
    429: "rate_limit_error",
    503: "server_error",
    504: "server_error",
}


# ---------------------------------------------------------------------------
# ClaudeDAProvider
# ---------------------------------------------------------------------------


class ClaudeDAProvider(CustomLLM):
    """LiteLLM custom provider for Claude-DA data analyst.

    Wraps the DataAnalystAgent behind the LiteLLM CustomLLM interface.
    Only async methods are supported; synchronous completion() and
    streaming() raise NotImplementedError.
    """

    def __init__(self) -> None:
        super().__init__()
        self._initialized: bool = False
        self._init_lock: asyncio.Lock = asyncio.Lock()
        self._init_error: Exception | None = None
        self._config: ClaudeDAConfig | None = None
        self._agent: DataAnalystAgent | None = None
        self._audit: AuditLogger | None = None

    # -- Synchronous stubs (not supported) ----------------------------------

    def completion(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous completion is not supported.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "ClaudeDAProvider only supports async methods. Use acompletion() instead."
        )

    def streaming(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous streaming is not supported.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "ClaudeDAProvider only supports async methods. Use astreaming() instead."
        )

    # -- Error handling -----------------------------------------------------

    def _handle_error(self, exc: ClaudeDAError) -> None:
        """Translate a ClaudeDAError into a CustomLLMError.

        Builds an OpenAI-compatible error JSON body and raises
        CustomLLMError with the appropriate HTTP status code.

        Args:
            exc: The application exception to translate.

        Raises:
            CustomLLMError: Always, with OpenAI-format error JSON.
        """
        status_code = getattr(exc, "status_code", 500)
        error_code = getattr(exc, "error_code", "internal_error")
        error_type = _ERROR_TYPE_MAP.get(status_code, "server_error")

        error_body = json.dumps(
            {
                "error": {
                    "message": str(exc),
                    "type": error_type,
                    "code": error_code,
                }
            }
        )

        raise CustomLLMError(status_code=status_code, message=error_body)

    # -- Initialization -----------------------------------------------------

    async def _ensure_initialized(self) -> None:
        """Initialize the provider on first use (double-check locking).

        Loads config, discovers schema, verifies read-only access,
        builds the system prompt, and creates the agent and audit logger.

        On failure, caches the error so subsequent calls fail
        immediately without retrying.

        Raises:
            The original exception from the failed initialization step.
        """
        if self._initialized:
            return

        if self._init_error is not None:
            raise self._init_error

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized:
                return

            if self._init_error is not None:
                raise self._init_error

            try:
                config = load_config()
                schema = discover_schema(config.db_path)
                verify_read_only(config.db_path)
                system_prompt = build_system_prompt(schema)

                self._agent = DataAnalystAgent(config, system_prompt)
                self._audit = AuditLogger(
                    log_output=config.log_output,
                    log_file=config.log_file,
                    verbose=config.log_verbose,
                )
                self._config = config
                self._initialized = True
            except Exception as exc:
                self._init_error = exc
                raise

    # -- Input validation ---------------------------------------------------

    def _validate_input_length(self, messages: list[dict]) -> None:
        """Validate that total input length does not exceed the limit.

        Args:
            messages: List of chat-style message dicts.

        Raises:
            InputValidationError: If total content length exceeds
                config.input_max_chars.
        """
        assert self._config is not None
        total = sum(len(m.get("content", "")) for m in messages)
        if total > self._config.input_max_chars:
            raise InputValidationError(
                f"Input length {total} exceeds maximum "
                f"{self._config.input_max_chars} characters"
            )

    # -- Audit helpers ------------------------------------------------------

    def _build_audit_entry(
        self,
        messages: list[dict],
        result: Any,
    ) -> AuditEntry:
        """Build an AuditEntry from messages and an AgentResult.

        Args:
            messages: The original chat messages.
            result: The AgentResult from the agent.

        Returns:
            A populated AuditEntry.
        """
        return AuditEntry(
            session_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            user_question=(messages[-1].get("content", "") if messages else ""),
            sql_queries_executed=result.sql_queries,
            query_results_summary=result.query_results,
            final_response=result.response_text,
            metadata=AuditMetadata(
                model=result.metadata.model,
                prompt_tokens=result.metadata.prompt_tokens,
                completion_tokens=result.metadata.completion_tokens,
                cost_estimate_usd=result.metadata.total_cost_usd,
                duration_seconds=result.metadata.duration_seconds,
                tool_call_count=result.metadata.tool_call_count,
            ),
        )

    def _fire_audit(
        self,
        messages: list[dict],
        result: Any,
    ) -> None:
        """Fire-and-forget audit logging.

        Creates an asyncio task to log the audit entry. Exceptions
        are suppressed via a done callback.

        Args:
            messages: The original chat messages.
            result: The AgentResult from the agent.
        """
        assert self._audit is not None
        entry = self._build_audit_entry(messages, result)
        task = asyncio.create_task(self._audit.log(entry))

        def _suppress_exception(t: asyncio.Task) -> None:
            if t.exception() is not None:
                pass  # Audit failures are silently swallowed

        task.add_done_callback(_suppress_exception)

    # -- Async completion ---------------------------------------------------

    async def acompletion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding: Any,
        api_key: Any,
        logging_obj: Any,
        optional_params: dict,
        acompletion: Any = None,
        litellm_params: Any = None,
        logger_fn: Any = None,
        headers: dict = {},
        timeout: float | httpx.Timeout | None = None,
        client: Any = None,
    ) -> ModelResponse:
        """Handle an async completion request.

        Validates input, runs the agent, formats the response as a
        ModelResponse, and fires an audit log task.

        Args:
            model: The model name (e.g., "claude-da/analyst").
            messages: Chat-style message dicts.
            Other args: Standard LiteLLM CustomLLM parameters.

        Returns:
            A populated ModelResponse.

        Raises:
            CustomLLMError: On input validation failure or agent error.
        """
        try:
            await self._ensure_initialized()
            self._validate_input_length(messages)

            assert self._agent is not None
            result = await self._agent.run(messages)

            response = ModelResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                created=int(time.time()),
                model=model,
                choices=[
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.response_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                usage={
                    "prompt_tokens": (result.metadata.prompt_tokens or 0),
                    "completion_tokens": (result.metadata.completion_tokens or 0),
                    "total_tokens": (
                        (result.metadata.prompt_tokens or 0)
                        + (result.metadata.completion_tokens or 0)
                    ),
                },
            )

            self._fire_audit(messages, result)

            return response

        except ClaudeDAError as exc:
            self._handle_error(exc)
            raise  # unreachable, _handle_error always raises

    # -- Async streaming ----------------------------------------------------

    async def astreaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding: Any,
        api_key: Any,
        logging_obj: Any,
        optional_params: dict,
        acompletion: Any = None,
        litellm_params: Any = None,
        logger_fn: Any = None,
        headers: dict = {},
        timeout: float | httpx.Timeout | None = None,
        client: Any = None,
    ) -> AsyncIterator[dict]:
        """Handle an async streaming request.

        Validates input, streams chunks from the agent, and fires
        an audit log task after the stream completes.

        Args:
            model: The model name (e.g., "claude-da/analyst").
            messages: Chat-style message dicts.
            Other args: Standard LiteLLM CustomLLM parameters.

        Yields:
            GenericStreamingChunk-compatible dicts.

        Raises:
            CustomLLMError: On input validation failure or agent error.
        """
        try:
            await self._ensure_initialized()
            self._validate_input_length(messages)

            assert self._agent is not None
            result_holder: list[Any] = [None]

            async for chunk in self._agent.run_streaming(messages, result_holder):
                yield chunk

            if result_holder[0] is not None:
                self._fire_audit(messages, result_holder[0])

        except ClaudeDAError as exc:
            self._handle_error(exc)
            raise  # unreachable, _handle_error always raises


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

claude_da_provider = ClaudeDAProvider()
