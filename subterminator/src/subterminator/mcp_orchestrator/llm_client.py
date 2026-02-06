"""LLM Client for AI model communication.

This module provides the LLMClient class for interacting with LLM APIs
(Claude and OpenAI) via LangChain.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any

from .exceptions import ConfigurationError, LLMError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

# Default model to use
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# LLM timeout in seconds
LLM_TIMEOUT = 60

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds


class LLMClient:
    """Client for LLM communication via LangChain.

    Supports both Anthropic (Claude) and OpenAI models with automatic
    detection based on model name prefix.

    Example:
        client = LLMClient()  # Uses default Claude model
        response = await client.invoke(messages, tools)
    """

    def __init__(self, model_name: str | None = None) -> None:
        """Initialize LLM client.

        Args:
            model_name: Model to use. If None, checks SUBTERMINATOR_MODEL env var,
                       then falls back to default (claude-sonnet-4-20250514).

        Raises:
            ConfigurationError: If API key is missing or model unsupported.
        """
        self._model_name = self._resolve_model_name(model_name)
        self._model = self._create_model()

    def _resolve_model_name(self, model_name: str | None) -> str:
        """Resolve model name from parameter, env var, or default.

        Priority:
        1. Explicit parameter
        2. SUBTERMINATOR_MODEL env var
        3. Default model

        Args:
            model_name: Optional explicit model name.

        Returns:
            Resolved model name.
        """
        if model_name:
            return model_name

        env_model = os.environ.get("SUBTERMINATOR_MODEL")
        if env_model:
            return env_model

        return DEFAULT_MODEL

    def _create_model(self) -> BaseChatModel:
        """Create the appropriate LangChain model.

        Returns:
            LangChain chat model instance.

        Raises:
            ConfigurationError: If API key missing or model unsupported.
        """
        model_name = self._model_name.lower()

        if model_name.startswith("claude"):
            return self._create_anthropic_model()
        elif model_name.startswith("gpt"):
            return self._create_openai_model()
        else:
            raise ConfigurationError(
                f"Unsupported model: {self._model_name}. "
                "Model name must start with 'claude' or 'gpt'."
            )

    def _create_anthropic_model(self) -> BaseChatModel:
        """Create Anthropic (Claude) model.

        Returns:
            ChatAnthropic instance.

        Raises:
            ConfigurationError: If ANTHROPIC_API_KEY not set.
        """
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ConfigurationError(
                "langchain-anthropic not installed. "
                "Run: pip install langchain-anthropic"
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY environment variable not set.")

        return ChatAnthropic(  # type: ignore[call-arg]
            model=self._model_name,
            api_key=api_key,  # type: ignore[arg-type]
        )

    def _create_openai_model(self) -> BaseChatModel:
        """Create OpenAI model.

        Returns:
            ChatOpenAI instance.

        Raises:
            ConfigurationError: If OPENAI_API_KEY not set.
        """
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ConfigurationError(
                "langchain-openai not installed. Run: pip install langchain-openai"
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY environment variable not set.")

        return ChatOpenAI(
            model=self._model_name,
            api_key=api_key,  # type: ignore[arg-type]
        )

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[Any]:
        """Convert dict messages to LangChain message objects.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            List of LangChain message objects.
        """
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        result: list[Any] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                result.append(HumanMessage(content=content))
            elif role == "assistant":
                ai_msg = AIMessage(content=content)
                # Include tool_calls if present
                if "tool_calls" in msg:
                    ai_msg.tool_calls = msg["tool_calls"]
                result.append(ai_msg)
            elif role == "tool":
                result.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=msg.get("tool_call_id", ""),
                    )
                )
            else:
                # Default to human message
                result.append(HumanMessage(content=content))

        return result

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert tools from MCP format to LangChain format.

        MCP tools use 'inputSchema' for the parameter schema, but LangChain's
        bind_tools() expects 'parameters'. This method normalizes the format.

        Args:
            tools: List of tool schemas (may use inputSchema or parameters).

        Returns:
            List of tool schemas with 'parameters' key for LangChain.
        """
        result = []
        for tool in tools:
            converted = {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
            }
            # Use inputSchema if present, otherwise use parameters
            if "inputSchema" in tool:
                converted["parameters"] = tool["inputSchema"]
            elif "parameters" in tool:
                converted["parameters"] = tool["parameters"]
            else:
                # Default empty schema
                converted["parameters"] = {"type": "object", "properties": {}}
            result.append(converted)
        return result

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AIMessage:
        """Invoke the LLM with messages and tools.

        Args:
            messages: Conversation messages.
            tools: Tool schemas for function calling.

        Returns:
            AI response message.

        Raises:
            LLMError: If invocation fails after retries or timeout.
        """
        # Convert messages
        lc_messages = self._convert_messages(messages)

        # Convert tools to LangChain format and bind
        lc_tools = self._convert_tools(tools)
        model_with_tools = self._model.bind_tools(lc_tools)

        # Retry loop with exponential backoff
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                # Call with timeout
                response = await asyncio.wait_for(
                    model_with_tools.ainvoke(lc_messages),
                    timeout=LLM_TIMEOUT,
                )
                return response

            except TimeoutError:
                last_error = LLMError(f"LLM call timed out after {LLM_TIMEOUT} seconds")
                logger.warning(f"LLM timeout (attempt {attempt + 1}/{MAX_RETRIES})")

            except Exception as e:
                last_error = e
                logger.warning(f"LLM error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

            # Wait before retry (except on last attempt)
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF[attempt]
                logger.info(f"Retrying in {backoff}s...")
                await asyncio.sleep(backoff)

        # All retries exhausted
        raise LLMError(f"LLM call failed after {MAX_RETRIES} attempts: {last_error}")

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name
