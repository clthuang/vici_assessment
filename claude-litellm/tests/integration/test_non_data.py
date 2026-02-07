"""Integration test for non-data question handling (T-036).

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
async def test_non_data_question_no_sql() -> None:
    """Send a non-data question and verify no SQL is executed."""
    from claude_da.agent import DataAnalystAgent
    from claude_da.config import load_config
    from claude_da.prompt import build_system_prompt
    from claude_da.schema import discover_schema

    config = load_config()
    schema = discover_schema(config.db_path)
    prompt = build_system_prompt(schema)
    agent = DataAnalystAgent(config, prompt)

    result = await agent.run(
        [{"role": "user", "content": "What's 2+2?"}]
    )

    assert result.response_text, "Should provide a conversational response"
    assert len(result.sql_queries) == 0, "Should not execute SQL for non-data question"
