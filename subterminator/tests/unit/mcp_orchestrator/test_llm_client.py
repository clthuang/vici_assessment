"""Tests for LLM client."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.mcp_orchestrator.exceptions import ConfigurationError, LLMError
from subterminator.mcp_orchestrator.llm_client import (
    DEFAULT_MODEL,
    LLMClient,
)


class TestLLMClientResolveModelName:
    """Tests for model name resolution."""

    @patch("subterminator.mcp_orchestrator.llm_client.LLMClient._create_model")
    def test_uses_explicit_parameter(self, mock_create):
        """Explicit model_name parameter takes priority."""
        mock_create.return_value = MagicMock()
        client = LLMClient(model_name="claude-3-haiku-20240307")
        assert client._model_name == "claude-3-haiku-20240307"

    @patch("subterminator.mcp_orchestrator.llm_client.LLMClient._create_model")
    @patch.dict("os.environ", {"SUBTERMINATOR_MODEL": "gpt-4o"})
    def test_uses_env_var_when_no_parameter(self, mock_create):
        """SUBTERMINATOR_MODEL env var is used when no parameter."""
        mock_create.return_value = MagicMock()
        client = LLMClient()
        assert client._model_name == "gpt-4o"

    @patch("subterminator.mcp_orchestrator.llm_client.LLMClient._create_model")
    @patch.dict("os.environ", {"SUBTERMINATOR_MODEL": "gpt-4o"})
    def test_parameter_overrides_env_var(self, mock_create):
        """Parameter overrides env var."""
        mock_create.return_value = MagicMock()
        client = LLMClient(model_name="claude-3-opus-20240229")
        assert client._model_name == "claude-3-opus-20240229"

    @patch("subterminator.mcp_orchestrator.llm_client.LLMClient._create_model")
    @patch.dict("os.environ", {}, clear=True)
    def test_uses_default_when_nothing_set(self, mock_create):
        """Default model is used when no parameter or env var."""
        mock_create.return_value = MagicMock()
        # Clear SUBTERMINATOR_MODEL if it exists
        with patch.dict("os.environ", {"SUBTERMINATOR_MODEL": ""}, clear=False):
            import os
            os.environ.pop("SUBTERMINATOR_MODEL", None)
            client = LLMClient()
            assert client._model_name == DEFAULT_MODEL


class TestLLMClientCreateModel:
    """Tests for model creation."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_creates_anthropic_for_claude(self):
        """Creates ChatAnthropic for claude models."""
        # Create a mock module
        mock_anthropic_module = MagicMock()
        mock_chat_class = MagicMock()
        mock_anthropic_module.ChatAnthropic = mock_chat_class

        with patch.dict(sys.modules, {"langchain_anthropic": mock_anthropic_module}):
            LLMClient(model_name="claude-3-opus")
            mock_chat_class.assert_called_once()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_creates_openai_for_gpt(self):
        """Creates ChatOpenAI for gpt models."""
        mock_openai_module = MagicMock()
        mock_chat_class = MagicMock()
        mock_openai_module.ChatOpenAI = mock_chat_class

        with patch.dict(sys.modules, {"langchain_openai": mock_openai_module}):
            LLMClient(model_name="gpt-4o")
            mock_chat_class.assert_called_once()

    def test_raises_for_unsupported_model(self):
        """Raises ConfigurationError for unsupported model prefix."""
        with pytest.raises(ConfigurationError) as exc_info:
            LLMClient(model_name="llama-3-70b")
        assert "Unsupported model" in str(exc_info.value)

    def test_raises_if_anthropic_key_missing(self):
        """Raises ConfigurationError if ANTHROPIC_API_KEY not set."""
        # Mock the langchain_anthropic module but with no API key
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.ChatAnthropic = MagicMock()

        with patch.dict(sys.modules, {"langchain_anthropic": mock_anthropic_module}):
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(ConfigurationError) as exc_info:
                    LLMClient(model_name="claude-3-opus")
                assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_raises_if_openai_key_missing(self):
        """Raises ConfigurationError if OPENAI_API_KEY not set."""
        mock_openai_module = MagicMock()
        mock_openai_module.ChatOpenAI = MagicMock()

        with patch.dict(sys.modules, {"langchain_openai": mock_openai_module}):
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(ConfigurationError) as exc_info:
                    LLMClient(model_name="gpt-4o")
                assert "OPENAI_API_KEY" in str(exc_info.value)


class TestLLMClientConvertMessages:
    """Tests for message conversion."""

    @pytest.fixture
    def client(self):
        """Create client with mocked model."""
        patch_target = (
            "subterminator.mcp_orchestrator.llm_client"
            ".LLMClient._create_model"
        )
        with patch(patch_target) as mock:
            mock.return_value = MagicMock()
            yield LLMClient(model_name="claude-3-opus")

    def test_converts_system_message(self, client):
        """Converts system role to SystemMessage."""
        from langchain_core.messages import SystemMessage

        messages = [{"role": "system", "content": "You are helpful"}]
        result = client._convert_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are helpful"

    def test_converts_user_message(self, client):
        """Converts user role to HumanMessage."""
        from langchain_core.messages import HumanMessage

        messages = [{"role": "user", "content": "Hello"}]
        result = client._convert_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello"

    def test_converts_assistant_with_tool_calls(self, client):
        """Converts assistant role with tool_calls."""
        from langchain_core.messages import AIMessage

        tool_calls = [{"id": "call_1", "name": "browser_click", "args": {}}]
        messages = [{"role": "assistant", "content": "", "tool_calls": tool_calls}]
        result = client._convert_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].tool_calls == tool_calls

    def test_converts_tool_message(self, client):
        """Converts tool role to ToolMessage."""
        from langchain_core.messages import ToolMessage

        messages = [{"role": "tool", "content": "result", "tool_call_id": "call_1"}]
        result = client._convert_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], ToolMessage)
        assert result[0].content == "result"
        assert result[0].tool_call_id == "call_1"


class TestLLMClientInvoke:
    """Tests for LLM invocation."""

    @pytest.fixture
    def mock_client(self):
        """Create a client with mocked model."""
        patch_target = (
            "subterminator.mcp_orchestrator.llm_client"
            ".LLMClient._create_model"
        )
        with patch(patch_target) as mock_create:
            mock_model = MagicMock()
            mock_create.return_value = mock_model
            client = LLMClient(model_name="claude-3-opus")
            yield client, mock_model

    @pytest.mark.asyncio
    async def test_invoke_binds_tools(self, mock_client):
        """invoke() binds tools to model after converting to LangChain format."""
        client, mock_model = mock_client
        mock_bound = MagicMock()
        mock_bound.ainvoke = AsyncMock(return_value=MagicMock())
        mock_model.bind_tools.return_value = mock_bound

        # Tools can use inputSchema (MCP) or parameters (LangChain)
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        }
        tools = [{
            "name": "test_tool",
            "description": "Test",
            "inputSchema": schema,
        }]
        await client.invoke(
            [{"role": "user", "content": "hi"}], tools
        )

        # Should be converted to LangChain format with 'parameters'
        expected_tools = [{
            "name": "test_tool",
            "description": "Test",
            "parameters": schema,
        }]
        mock_model.bind_tools.assert_called_once_with(expected_tools)

    @pytest.mark.asyncio
    async def test_invoke_retries_on_failure(self, mock_client):
        """invoke() retries on transient failures."""
        client, mock_model = mock_client

        mock_bound = MagicMock()
        # Fail twice, then succeed
        mock_bound.ainvoke = AsyncMock(
            side_effect=[Exception("fail1"), Exception("fail2"), MagicMock()]
        )
        mock_model.bind_tools.return_value = mock_bound

        # Patch sleep to avoid waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.invoke(
                [{"role": "user", "content": "hi"}], []
            )

        assert mock_bound.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_invoke_raises_after_max_retries(self, mock_client):
        """invoke() raises LLMError after max retries."""
        client, mock_model = mock_client

        mock_bound = MagicMock()
        mock_bound.ainvoke = AsyncMock(side_effect=Exception("always fails"))
        mock_model.bind_tools.return_value = mock_bound

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMError) as exc_info:
                await client.invoke([{"role": "user", "content": "hi"}], [])

        assert "failed after 3 attempts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_handles_timeout(self, mock_client):
        """invoke() handles timeout and retries."""
        client, mock_model = mock_client

        mock_bound = MagicMock()
        # Timeout twice, then succeed
        mock_bound.ainvoke = AsyncMock(
            side_effect=[TimeoutError(), TimeoutError(), MagicMock()]
        )
        mock_model.bind_tools.return_value = mock_bound

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.invoke(
                [{"role": "user", "content": "hi"}], []
            )

        assert mock_bound.ainvoke.call_count == 3
