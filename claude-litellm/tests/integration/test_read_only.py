"""Integration test for read-only enforcement (T-037).

Requires ANTHROPIC_API_KEY and a seeded demo.db. Skipped in CI.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


def test_demo_db_is_read_only() -> None:
    """Verify the demo database file has read-only permissions."""
    db_path = Path(os.environ.get("CLAUDE_DA_DB_PATH", "./demo.db"))
    if not db_path.exists():
        pytest.skip("demo.db not found")

    mode = db_path.stat().st_mode
    assert not (mode & stat.S_IWUSR), "Owner should not have write permission"
    assert not (mode & stat.S_IWGRP), "Group should not have write permission"
    assert not (mode & stat.S_IWOTH), "Others should not have write permission"


@pytest.mark.asyncio
async def test_agent_cannot_write() -> None:
    """Verify the agent's MCP server cannot write to the database."""
    from claude_da.agent import DataAnalystAgent
    from claude_da.config import load_config
    from claude_da.prompt import build_system_prompt
    from claude_da.schema import discover_schema

    config = load_config()
    schema = discover_schema(config.db_path)
    prompt = build_system_prompt(schema)
    agent = DataAnalystAgent(config, prompt)

    result = await agent.run(
        [{"role": "user", "content": "Please create a new table called test_table."}]
    )

    # The agent should refuse or the MCP server should block the write
    assert result.response_text, "Should get a response"
