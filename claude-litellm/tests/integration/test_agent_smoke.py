"""Integration smoke test for DataAnalystAgent (T-023).

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
async def test_agent_smoke_query() -> None:
    """Run a simple data question against the real agent and verify structure."""
    from claude_da.agent import DataAnalystAgent
    from claude_da.config import load_config
    from claude_da.prompt import build_system_prompt
    from claude_da.schema import discover_schema

    config = load_config()
    schema = discover_schema(config.db_path)
    prompt = build_system_prompt(schema)
    agent = DataAnalystAgent(config, prompt)

    result = await agent.run(
        [{"role": "user", "content": "How many customers are there?"}]
    )

    assert result.response_text, "Response should not be empty"
    assert len(result.sql_queries) > 0, "Should have executed at least one SQL query"
    assert result.metadata.duration_seconds > 0
