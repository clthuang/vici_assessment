"""Integration streaming test for DataAnalystAgent (T-026).

Requires ANTHROPIC_API_KEY and a seeded demo.db. Skipped in CI.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@pytest.mark.asyncio
async def test_streaming_chunks_arrive() -> None:
    """Stream a data question and verify chunk format."""
    from claude_da.agent import AgentResult, DataAnalystAgent
    from claude_da.config import load_config
    from claude_da.prompt import build_system_prompt
    from claude_da.schema import discover_schema

    config = load_config()
    schema = discover_schema(config.db_path)
    prompt = build_system_prompt(schema)
    agent = DataAnalystAgent(config, prompt)

    result_holder: list[AgentResult | None] = [None]
    chunks: list[dict] = []

    async for chunk in agent.run_streaming(
        [{"role": "user", "content": "What are the top 5 products by revenue?"}],
        result_holder=result_holder,
    ):
        chunks.append(chunk)

    assert len(chunks) >= 1, "Should yield at least the final chunk"

    final = chunks[-1]
    assert final["is_finished"] is True
    assert final["finish_reason"] == "stop"

    assert result_holder[0] is not None
