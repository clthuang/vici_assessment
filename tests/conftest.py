"""Shared pytest fixtures for SubTerminator tests.

This module provides common fixtures used across unit, integration, and e2e tests.
Fixtures include mocks for session logger, config, and services.
"""

from pathlib import Path

import pytest

from subterminator.services.netflix import NetflixService
from subterminator.utils.config import AppConfig
from subterminator.utils.session import SessionLogger


@pytest.fixture
def mock_session(tmp_path: Path) -> SessionLogger:
    """Session logger with temp directory.

    Creates a real SessionLogger instance that writes to a temporary
    directory, useful for testing session-related functionality.

    Args:
        tmp_path: Pytest fixture providing a temporary directory.

    Returns:
        SessionLogger: A session logger configured for testing.
    """
    return SessionLogger(
        output_dir=tmp_path,
        service="netflix",
        target="mock"
    )


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    """Test configuration.

    Creates an AppConfig with test-appropriate settings including
    shorter timeouts and reduced retry counts.

    Args:
        tmp_path: Pytest fixture providing a temporary directory.

    Returns:
        AppConfig: A configuration object for testing.
    """
    return AppConfig(
        anthropic_api_key="test-key",
        output_dir=tmp_path / "output",
        page_timeout=5000,
        element_timeout=2000,
        auth_timeout=10000,
        confirm_timeout=5000,
        max_retries=2,
        max_transitions=5,
    )


@pytest.fixture
def netflix_service() -> NetflixService:
    """Netflix service for mock target.

    Creates a NetflixService configured to use mock URLs
    for testing without real network calls.

    Returns:
        NetflixService: A Netflix service configured for mock target.
    """
    return NetflixService(target="mock")


@pytest.fixture
def mock_pages_dir() -> Path:
    """Path to mock pages directory.

    Returns the path to the Netflix mock pages directory containing
    HTML files for testing page state detection.

    Returns:
        Path: Path to the mock_pages/netflix directory.
    """
    return Path(__file__).parent.parent / "mock_pages" / "netflix"
