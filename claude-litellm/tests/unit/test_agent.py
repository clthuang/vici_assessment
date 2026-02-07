"""Unit tests for Claude-DA Agent SDK integration.

Covers:
- _messages_to_prompt() formatting (T-018)
- AgentResult / AgentResultMetadata dataclasses (T-019)
- DataAnalystAgent construction (T-020)
- DataAnalystAgent._build_options() (T-021a)
- DataAnalystAgent.run() with mocked SDK (T-021b / T-022)
- Timeout mapping to AgentTimeoutError (T-022)
- DataAnalystAgent.run_streaming() (T-024 / T-025)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from claude_da.agent import (
    AgentResult,
    AgentResultMetadata,
    DataAnalystAgent,
    _messages_to_prompt,
)
from claude_da.config import ClaudeDAConfig
from claude_da.exceptions import AgentTimeoutError

# ---------------------------------------------------------------------------
# Helpers: mock SDK message types
# ---------------------------------------------------------------------------


@dataclass
class _MockTextBlock:
    """Simulates claude_agent_sdk.TextBlock."""

    text: str


@dataclass
class _MockToolUseBlock:
    """Simulates claude_agent_sdk.ToolUseBlock."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class _MockToolResultBlock:
    """Simulates claude_agent_sdk.ToolResultBlock."""

    tool_use_id: str
    content: str | list[dict[str, Any]] | None = None
    is_error: bool | None = None


@dataclass
class _MockAssistantMessage:
    """Simulates claude_agent_sdk.AssistantMessage."""

    content: list
    model: str = "claude-sonnet-4-5-20250929"
    parent_tool_use_id: str | None = None
    error: Any = None


@dataclass
class _MockResultMessage:
    """Simulates claude_agent_sdk.ResultMessage."""

    subtype: str = "result"
    duration_ms: int = 1500
    duration_api_ms: int = 1400
    is_error: bool = False
    num_turns: int = 2
    session_id: str = "test-session-id"
    total_cost_usd: float | None = 0.005
    usage: dict[str, Any] | None = field(
        default_factory=lambda: {
            "input_tokens": 100,
            "output_tokens": 50,
        }
    )
    result: str | None = None


@dataclass
class _MockUserMessage:
    """Simulates claude_agent_sdk.UserMessage with tool results."""

    content: str | list = ""
    uuid: str | None = None
    parent_tool_use_id: str | None = None
    tool_use_result: dict[str, Any] | None = None


def _make_config() -> ClaudeDAConfig:
    """Create a test config."""
    return ClaudeDAConfig(
        anthropic_api_key="sk-ant-test-key",
        db_path="/tmp/test.db",
        model="claude-sonnet-4-5-20250929",
        max_turns=10,
        max_budget_usd=0.50,
    )


def _make_agent() -> DataAnalystAgent:
    """Create a test agent."""
    return DataAnalystAgent(
        config=_make_config(),
        system_prompt="You are a test data analyst.",
    )


# ---------------------------------------------------------------------------
# T-018: _messages_to_prompt tests
# ---------------------------------------------------------------------------


class TestMessagesToPrompt:
    """Test _messages_to_prompt() formatting."""

    def test_single_user_message_returns_content_directly(self) -> None:
        messages = [{"role": "user", "content": "How many users?"}]
        result = _messages_to_prompt(messages)
        assert result == "How many users?"

    def test_multi_turn_produces_labeled_format(self) -> None:
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How many orders?"},
        ]
        result = _messages_to_prompt(messages)
        expected = "User: Hello\nAssistant: Hi there\nUser: How many orders?"
        assert result == expected

    def test_system_messages_filtered_out_single_remaining(self) -> None:
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Count customers"},
        ]
        result = _messages_to_prompt(messages)
        # Only one non-system message, so content returned directly
        assert result == "Count customers"

    def test_system_messages_filtered_out_multi_turn(self) -> None:
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Query data"},
        ]
        result = _messages_to_prompt(messages)
        assert "system" not in result.lower()
        assert result == "User: Hello\nAssistant: Hi\nUser: Query data"

    def test_empty_messages_list(self) -> None:
        result = _messages_to_prompt([])
        # No non-system messages; single-element path returns empty content
        # Actually, empty list has 0 non-system, len != 1, so multi-turn
        # path returns empty string from join
        assert result == ""

    def test_missing_content_key_uses_empty_string(self) -> None:
        messages = [{"role": "user"}]
        result = _messages_to_prompt(messages)
        assert result == ""


# ---------------------------------------------------------------------------
# T-019: AgentResult / AgentResultMetadata dataclass tests
# ---------------------------------------------------------------------------


class TestAgentResultMetadata:
    """Test AgentResultMetadata dataclass."""

    def test_all_fields_set(self) -> None:
        meta = AgentResultMetadata(
            model="claude-sonnet-4-5-20250929",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost_usd=0.005,
            duration_seconds=1.5,
            tool_call_count=2,
        )
        assert meta.model == "claude-sonnet-4-5-20250929"
        assert meta.prompt_tokens == 100
        assert meta.completion_tokens == 50
        assert meta.total_cost_usd == 0.005
        assert meta.duration_seconds == 1.5
        assert meta.tool_call_count == 2

    def test_nullable_fields(self) -> None:
        meta = AgentResultMetadata(
            model="test",
            prompt_tokens=None,
            completion_tokens=None,
            total_cost_usd=None,
            duration_seconds=0.0,
            tool_call_count=0,
        )
        assert meta.prompt_tokens is None
        assert meta.completion_tokens is None
        assert meta.total_cost_usd is None


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_minimal_construction(self) -> None:
        result = AgentResult(response_text="Hello")
        assert result.response_text == "Hello"
        assert result.sql_queries == []
        assert result.query_results == []
        assert result.metadata.model == "unknown"

    def test_full_construction(self) -> None:
        meta = AgentResultMetadata(
            model="claude-sonnet-4-5-20250929",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost_usd=0.005,
            duration_seconds=1.5,
            tool_call_count=1,
        )
        result = AgentResult(
            response_text="There are 42 users.",
            sql_queries=["SELECT COUNT(*) FROM users"],
            query_results=[{"count": 42}],
            metadata=meta,
        )
        assert result.response_text == "There are 42 users."
        assert len(result.sql_queries) == 1
        assert result.query_results == [{"count": 42}]
        assert result.metadata.total_cost_usd == 0.005


# ---------------------------------------------------------------------------
# T-020: DataAnalystAgent construction tests
# ---------------------------------------------------------------------------


class TestDataAnalystAgentInit:
    """Test DataAnalystAgent.__init__."""

    def test_stores_config_and_prompt(self) -> None:
        config = _make_config()
        agent = DataAnalystAgent(config=config, system_prompt="Test prompt")
        assert agent._config is config
        assert agent._system_prompt == "Test prompt"

    def test_different_configs(self) -> None:
        config1 = ClaudeDAConfig(anthropic_api_key="key1", db_path="/a.db")
        config2 = ClaudeDAConfig(anthropic_api_key="key2", db_path="/b.db")
        agent1 = DataAnalystAgent(config=config1, system_prompt="p1")
        agent2 = DataAnalystAgent(config=config2, system_prompt="p2")
        assert agent1._config.db_path != agent2._config.db_path


# ---------------------------------------------------------------------------
# T-021a: _build_options tests
# ---------------------------------------------------------------------------


class TestBuildOptions:
    """Test DataAnalystAgent._build_options()."""

    def test_system_prompt_set(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert options.system_prompt == "You are a test data analyst."

    def test_model_set(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert options.model == "claude-sonnet-4-5-20250929"

    def test_max_turns_set(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert options.max_turns == 10

    def test_max_budget_set(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert options.max_budget_usd == 0.50

    def test_mcp_servers_configured(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert "sqlite" in options.mcp_servers
        sqlite_config = options.mcp_servers["sqlite"]
        assert sqlite_config["command"] == "npx"
        assert "@modelcontextprotocol/server-sqlite" in sqlite_config["args"]
        assert "/tmp/test.db" in sqlite_config["args"]

    def test_allowed_tools(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert options.allowed_tools == ["mcp__sqlite__*"]

    def test_disallowed_tools(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert "Bash" in options.disallowed_tools
        assert "Write" in options.disallowed_tools
        assert "Edit" in options.disallowed_tools

    def test_permission_mode(self) -> None:
        agent = _make_agent()
        options = agent._build_options()
        assert options.permission_mode == "bypassPermissions"


# ---------------------------------------------------------------------------
# T-022: run() with mocked SDK
# ---------------------------------------------------------------------------


class TestAgentRun:
    """Test DataAnalystAgent.run() with mocked SDK."""

    @pytest.mark.asyncio
    async def test_run_returns_agent_result(self) -> None:
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="tool-1",
                        name="mcp__sqlite__read_query",
                        input={"sql": "SELECT COUNT(*) FROM users"},
                    ),
                ]
            )
            yield _MockUserMessage(
                content=[
                    _MockToolResultBlock(
                        tool_use_id="tool-1",
                        content='[{"count": 42}]',
                    ),
                ]
            )
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="There are 42 users in the database."),
                ]
            )
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result = await agent.run([{"role": "user", "content": "How many users?"}])

        assert isinstance(result, AgentResult)
        assert "42 users" in result.response_text
        assert "SELECT COUNT(*) FROM users" in result.sql_queries
        assert result.metadata.prompt_tokens == 100
        assert result.metadata.completion_tokens == 50
        assert result.metadata.total_cost_usd == 0.005
        assert result.metadata.tool_call_count == 1

    @pytest.mark.asyncio
    async def test_run_collects_multiple_sql_queries(self) -> None:
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="t1",
                        name="mcp__sqlite__read_query",
                        input={"sql": "SELECT * FROM customers LIMIT 5"},
                    ),
                ]
            )
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="t2",
                        name="mcp__sqlite__read_query",
                        input={"sql": "SELECT COUNT(*) FROM orders"},
                    ),
                ]
            )
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="Here are your results."),
                ]
            )
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result = await agent.run([{"role": "user", "content": "Show me data"}])

        assert len(result.sql_queries) == 2
        assert result.metadata.tool_call_count == 2

    @pytest.mark.asyncio
    async def test_run_timeout_raises_agent_timeout_error(self) -> None:
        agent = _make_agent()

        async def mock_query_slow(prompt: str, options: Any) -> Any:
            await asyncio.sleep(999)
            yield _MockResultMessage()  # Never reached

        with (
            patch("claude_da.agent.query", mock_query_slow),
            patch("claude_da.agent._AGENT_TIMEOUT_SECONDS", 0.01),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            with pytest.raises(AgentTimeoutError, match="timeout"):
                await agent.run([{"role": "user", "content": "Slow query"}])

    @pytest.mark.asyncio
    async def test_run_with_null_usage(self) -> None:
        """ResultMessage with usage=None should not crash."""
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="No data available."),
                ]
            )
            yield _MockResultMessage(usage=None, total_cost_usd=None)

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result = await agent.run([{"role": "user", "content": "Anything?"}])

        assert result.response_text == "No data available."
        assert result.metadata.prompt_tokens is None
        assert result.metadata.completion_tokens is None
        assert result.metadata.total_cost_usd is None

    @pytest.mark.asyncio
    async def test_run_ignores_non_sqlite_tool_use(self) -> None:
        """Tool use blocks not matching mcp__sqlite__* are ignored."""
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="t1",
                        name="some_other_tool",
                        input={"data": "irrelevant"},
                    ),
                ]
            )
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="Done."),
                ]
            )
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result = await agent.run([{"role": "user", "content": "Do something"}])

        assert result.sql_queries == []
        assert result.metadata.tool_call_count == 0

    @pytest.mark.asyncio
    async def test_run_captures_query_results_from_tool_result(
        self,
    ) -> None:
        """Tool result blocks populate query_results."""
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="t1",
                        name="mcp__sqlite__read_query",
                        input={"sql": "SELECT 1"},
                    ),
                ]
            )
            yield _MockUserMessage(
                content=[
                    _MockToolResultBlock(
                        tool_use_id="t1",
                        content='[{"result": 1}]',
                    ),
                ]
            )
            yield _MockAssistantMessage(content=[_MockTextBlock(text="Result is 1.")])
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result = await agent.run([{"role": "user", "content": "Select 1"}])

        assert len(result.query_results) == 1
        assert result.query_results[0]["raw"] == '[{"result": 1}]'


# ---------------------------------------------------------------------------
# T-024 / T-025: run_streaming() tests
# ---------------------------------------------------------------------------


class TestAgentRunStreaming:
    """Test DataAnalystAgent.run_streaming() with mocked SDK."""

    @pytest.mark.asyncio
    async def test_streaming_yields_intermediate_and_final_chunks(
        self,
    ) -> None:
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="Part 1. "),
                ]
            )
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="Part 2."),
                ]
            )
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result_holder: list[AgentResult | None] = [None]
            chunks: list[dict] = []

            async for chunk in agent.run_streaming(
                [{"role": "user", "content": "Hello"}],
                result_holder=result_holder,
            ):
                chunks.append(chunk)

        # Should have 2 intermediate + 1 final
        assert len(chunks) == 3

        # Intermediate chunks
        assert chunks[0]["text"] == "Part 1. "
        assert chunks[0]["is_finished"] is False
        assert chunks[0]["finish_reason"] == ""
        assert chunks[0]["tool_use"] is None

        assert chunks[1]["text"] == "Part 2."
        assert chunks[1]["is_finished"] is False

        # Final chunk
        assert chunks[2]["text"] == ""
        assert chunks[2]["is_finished"] is True
        assert chunks[2]["finish_reason"] == "stop"
        assert "usage" in chunks[2]

    @pytest.mark.asyncio
    async def test_streaming_populates_result_holder(self) -> None:
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="t1",
                        name="mcp__sqlite__read_query",
                        input={"sql": "SELECT 1"},
                    ),
                ]
            )
            yield _MockAssistantMessage(
                content=[
                    _MockTextBlock(text="The answer is 1."),
                ]
            )
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result_holder: list[AgentResult | None] = [None]

            async for _ in agent.run_streaming(
                [{"role": "user", "content": "Query"}],
                result_holder=result_holder,
            ):
                pass

        assert result_holder[0] is not None
        result = result_holder[0]
        assert result.response_text == "The answer is 1."
        assert "SELECT 1" in result.sql_queries
        assert result.metadata.tool_call_count == 1

    @pytest.mark.asyncio
    async def test_streaming_final_chunk_has_usage(self) -> None:
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(content=[_MockTextBlock(text="Hi")])
            yield _MockResultMessage(
                usage={"input_tokens": 200, "output_tokens": 75},
                total_cost_usd=0.01,
            )

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result_holder: list[AgentResult | None] = [None]
            chunks: list[dict] = []

            async for chunk in agent.run_streaming(
                [{"role": "user", "content": "Hello"}],
                result_holder=result_holder,
            ):
                chunks.append(chunk)

        final = chunks[-1]
        assert final["is_finished"] is True
        assert final["usage"]["prompt_tokens"] == 200
        assert final["usage"]["completion_tokens"] == 75
        assert final["usage"]["total_cost_usd"] == 0.01

    @pytest.mark.asyncio
    async def test_streaming_with_null_usage(self) -> None:
        """ResultMessage with None usage produces empty usage dict."""
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(content=[_MockTextBlock(text="Done")])
            yield _MockResultMessage(usage=None, total_cost_usd=None)

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result_holder: list[AgentResult | None] = [None]
            chunks: list[dict] = []

            async for chunk in agent.run_streaming(
                [{"role": "user", "content": "Test"}],
                result_holder=result_holder,
            ):
                chunks.append(chunk)

        final = chunks[-1]
        assert final["is_finished"] is True
        assert final["usage"] == {}

    @pytest.mark.asyncio
    async def test_streaming_no_text_yields_only_final_chunk(self) -> None:
        """When the agent uses tools but produces no text blocks,
        only the final chunk is yielded."""
        agent = _make_agent()

        async def mock_query(prompt: str, options: Any) -> Any:
            yield _MockAssistantMessage(
                content=[
                    _MockToolUseBlock(
                        id="t1",
                        name="mcp__sqlite__read_query",
                        input={"sql": "SELECT 1"},
                    ),
                ]
            )
            yield _MockResultMessage()

        with (
            patch("claude_da.agent.query", mock_query),
            patch("claude_da.agent.AssistantMessage", _MockAssistantMessage),
            patch("claude_da.agent.ResultMessage", _MockResultMessage),
            patch("claude_da.agent.TextBlock", _MockTextBlock),
            patch("claude_da.agent.ToolUseBlock", _MockToolUseBlock),
            patch("claude_da.agent.ToolResultBlock", _MockToolResultBlock),
        ):
            result_holder: list[AgentResult | None] = [None]
            chunks: list[dict] = []

            async for chunk in agent.run_streaming(
                [{"role": "user", "content": "Query"}],
                result_holder=result_holder,
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["is_finished"] is True
