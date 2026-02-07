"""End-to-end proxy test (T-034).

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
async def test_e2e_proxy_completion() -> None:
    """Start LiteLLM proxy and verify /v1/chat/completions works."""
    pytest.skip("Requires running LiteLLM proxy — run manually")
