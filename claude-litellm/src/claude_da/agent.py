"""Claude Agent SDK integration for the data analyst agent.

Provides the DataAnalystAgent class that wraps the Claude Agent SDK
to execute natural-language data analysis queries against a SQLite
database via the MCP sqlite server. Includes both synchronous (run)
and streaming (run_streaming) interfaces.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

from claude_da.config import ClaudeDAConfig
from claude_da.exceptions import AgentTimeoutError

# ---------------------------------------------------------------------------
# Helper: convert message dicts to a flat prompt string
# ---------------------------------------------------------------------------

_AGENT_TIMEOUT_SECONDS = 240


def _messages_to_prompt(messages: list[dict]) -> str:
    """Convert a list of chat-style message dicts to a flat prompt string.

    Rules:
    - System messages are skipped (handled separately by ClaudeAgentOptions).
    - If only a single user message remains after filtering, return its
      content directly (no label prefix).
    - For multi-turn conversations, format as labeled turns:
        User: {content}
        Assistant: {content}
        User: {content}

    Args:
        messages: List of dicts with "role" and "content" keys.

    Returns:
        A single prompt string for the Claude Agent SDK query() call.
    """
    non_system = [m for m in messages if m.get("role") != "system"]

    if len(non_system) == 1:
        return non_system[0].get("content", "")

    lines: list[str] = []
    for msg in non_system:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role.capitalize()}: {content}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AgentResultMetadata:
    """Metadata from a completed agent run.

    Attributes:
        model: The Claude model identifier used.
        prompt_tokens: Number of prompt tokens (None if unavailable).
        completion_tokens: Number of completion tokens (None if unavailable).
        total_cost_usd: Total cost in USD (None if unavailable).
        duration_seconds: Wall-clock seconds for the agent turn.
        tool_call_count: Number of tool calls made during the turn.
    """

    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_cost_usd: float | None
    duration_seconds: float
    tool_call_count: int


@dataclass
class AgentResult:
    """Complete result from a data analyst agent run.

    Attributes:
        response_text: The agent's final natural-language response.
        sql_queries: SQL queries the agent executed.
        query_results: Raw query result dicts (for verbose audit logging).
        metadata: Token/cost/timing metadata.
    """

    response_text: str
    sql_queries: list[str] = field(default_factory=list)
    query_results: list[dict] = field(default_factory=list)
    metadata: AgentResultMetadata = field(
        default_factory=lambda: AgentResultMetadata(
            model="unknown",
            prompt_tokens=None,
            completion_tokens=None,
            total_cost_usd=None,
            duration_seconds=0.0,
            tool_call_count=0,
        )
    )


# ---------------------------------------------------------------------------
# Message processing helpers
# ---------------------------------------------------------------------------


def _extract_sql_from_tool_use(block: Any) -> str | None:
    """Extract SQL string from a ToolUseBlock if it's an MCP sqlite call."""
    if not block.name.startswith("mcp__sqlite__"):
        return None
    return block.input.get("sql", block.input.get("query", "")) or None


def _extract_tool_results(message: Any) -> list[dict]:
    """Extract query result dicts from a message with ToolResultBlocks."""
    results: list[dict] = []
    if not hasattr(message, "content"):
        return results
    content = message.content
    if not isinstance(content, list):
        return results
    for block in content:
        if isinstance(block, ToolResultBlock):
            result_content = block.content
            if isinstance(result_content, str):
                results.append({"raw": result_content})
            elif isinstance(result_content, list):
                for item in result_content:
                    if isinstance(item, dict):
                        results.append(item)
    return results


def _build_result_metadata(message: Any, model: str) -> AgentResultMetadata:
    """Build metadata from a ResultMessage."""
    usage = message.usage or {}
    return AgentResultMetadata(
        model=model,
        prompt_tokens=usage.get("input_tokens"),
        completion_tokens=usage.get("output_tokens"),
        total_cost_usd=message.total_cost_usd,
        duration_seconds=getattr(message, "duration_ms", 0) / 1000.0,
        tool_call_count=0,  # overwritten by caller
    )


# ---------------------------------------------------------------------------
# DataAnalystAgent
# ---------------------------------------------------------------------------


class DataAnalystAgent:
    """Wraps the Claude Agent SDK for database analysis tasks.

    Uses MCP sqlite server for read-only database access and restricts
    the agent to safe tool usage (no Bash, Write, or Edit).

    Args:
        config: Application configuration (model, db_path, budget, etc.).
        system_prompt: Pre-built system prompt with schema and rules.
    """

    def __init__(self, config: ClaudeDAConfig, system_prompt: str) -> None:
        self._config = config
        self._system_prompt = system_prompt

    def _build_options(self) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions for the agent query.

        Returns:
            Configured ClaudeAgentOptions with MCP sqlite server,
            tool restrictions, and model/budget settings.
        """
        return ClaudeAgentOptions(
            system_prompt=self._system_prompt,
            model=self._config.model,
            max_turns=self._config.max_turns,
            max_budget_usd=self._config.max_budget_usd,
            mcp_servers={
                "sqlite": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-sqlite",
                        self._config.db_path,
                    ],
                }
            },
            allowed_tools=["mcp__sqlite__*"],
            disallowed_tools=["Bash", "Write", "Edit"],
            permission_mode="bypassPermissions",
        )

    async def run(self, messages: list[dict]) -> AgentResult:
        """Execute a data analysis query and return the complete result.

        Converts messages to a prompt, sends to the Claude Agent SDK,
        iterates over response messages to collect text, SQL queries,
        query results, and metadata.

        Args:
            messages: Chat-style message dicts with "role" and "content".

        Returns:
            AgentResult with response text, SQL queries, and metadata.

        Raises:
            AgentTimeoutError: If the agent session exceeds the timeout.
        """
        prompt = _messages_to_prompt(messages)
        options = self._build_options()

        start_time = time.monotonic()

        try:
            collected = await asyncio.wait_for(
                self._collect_messages(prompt, options),
                timeout=_AGENT_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            raise AgentTimeoutError(
                f"Agent session exceeded {_AGENT_TIMEOUT_SECONDS}s timeout"
            ) from None

        elapsed = time.monotonic() - start_time
        response_parts, sql_queries, query_results, tool_call_count, result_metadata = (
            collected
        )

        if result_metadata is None:
            result_metadata = AgentResultMetadata(
                model=self._config.model,
                prompt_tokens=None,
                completion_tokens=None,
                total_cost_usd=None,
                duration_seconds=elapsed,
                tool_call_count=tool_call_count,
            )
        else:
            result_metadata.duration_seconds = elapsed
            result_metadata.tool_call_count = tool_call_count

        return AgentResult(
            response_text="".join(response_parts),
            sql_queries=sql_queries,
            query_results=query_results,
            metadata=result_metadata,
        )

    async def _collect_messages(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
    ) -> tuple[
        list[str],
        list[str],
        list[dict],
        int,
        AgentResultMetadata | None,
    ]:
        """Iterate over SDK messages and collect all results.

        Returns:
            Tuple of (response_parts, sql_queries, query_results,
            tool_call_count, result_metadata).
        """
        response_parts: list[str] = []
        sql_queries: list[str] = []
        query_results: list[dict] = []
        tool_call_count = 0
        result_metadata: AgentResultMetadata | None = None

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        sql = _extract_sql_from_tool_use(block)
                        if sql:
                            sql_queries.append(sql)
                        if block.name.startswith("mcp__sqlite__"):
                            tool_call_count += 1

            elif isinstance(message, ResultMessage):
                result_metadata = _build_result_metadata(
                    message, self._config.model
                )

            else:
                query_results.extend(_extract_tool_results(message))

        return (
            response_parts,
            sql_queries,
            query_results,
            tool_call_count,
            result_metadata,
        )

    async def run_streaming(
        self,
        messages: list[dict],
        result_holder: list[AgentResult | None],
    ) -> AsyncIterator[dict]:
        """Execute a data analysis query with streaming output.

        Yields GenericStreamingChunk-compatible dicts as the agent
        generates text. After iteration completes, populates
        result_holder[0] with the final AgentResult.

        Args:
            messages: Chat-style message dicts with "role" and "content".
            result_holder: Single-element list; [0] is set to AgentResult
                after the stream completes.

        Yields:
            Dicts with keys: text, is_finished, finish_reason, index,
            tool_use, and optionally usage.
        """
        prompt = _messages_to_prompt(messages)
        options = self._build_options()

        response_parts: list[str] = []
        sql_queries: list[str] = []
        query_results: list[dict] = []
        tool_call_count = 0
        result_metadata: AgentResultMetadata | None = None

        start_time = time.monotonic()

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_parts.append(block.text)
                        yield {
                            "text": block.text,
                            "is_finished": False,
                            "finish_reason": "",
                            "index": 0,
                            "tool_use": None,
                        }
                    elif isinstance(block, ToolUseBlock):
                        sql = _extract_sql_from_tool_use(block)
                        if sql:
                            sql_queries.append(sql)
                        if block.name.startswith("mcp__sqlite__"):
                            tool_call_count += 1

            elif isinstance(message, ResultMessage):
                result_metadata = _build_result_metadata(
                    message, self._config.model
                )
                result_metadata.tool_call_count = tool_call_count

            else:
                query_results.extend(_extract_tool_results(message))

        elapsed = time.monotonic() - start_time

        if result_metadata is None:
            result_metadata = AgentResultMetadata(
                model=self._config.model,
                prompt_tokens=None,
                completion_tokens=None,
                total_cost_usd=None,
                duration_seconds=elapsed,
                tool_call_count=tool_call_count,
            )
        else:
            result_metadata.duration_seconds = elapsed

        # Build usage dict for final chunk
        usage_dict: dict = {}
        if result_metadata.prompt_tokens is not None:
            usage_dict["prompt_tokens"] = result_metadata.prompt_tokens
        if result_metadata.completion_tokens is not None:
            usage_dict["completion_tokens"] = result_metadata.completion_tokens
        if result_metadata.total_cost_usd is not None:
            usage_dict["total_cost_usd"] = result_metadata.total_cost_usd

        # Final chunk signals end of stream
        yield {
            "text": "",
            "is_finished": True,
            "finish_reason": "stop",
            "index": 0,
            "tool_use": None,
            "usage": usage_dict,
        }

        # Populate result holder
        result_holder[0] = AgentResult(
            response_text="".join(response_parts),
            sql_queries=sql_queries,
            query_results=query_results,
            metadata=result_metadata,
        )
