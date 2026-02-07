"""Shared pytest fixtures for Claude-DA tests.

This module provides common fixtures used across unit and integration tests.
"""

import pytest


@pytest.fixture
def api_key() -> str:
    """Fake API key for testing.

    Returns:
        str: A fake Anthropic API key for use in tests.
    """
    return "sk-ant-test-key-for-unit-tests"
