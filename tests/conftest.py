"""Shared pytest fixtures for SubTerminator tests.

This module provides common fixtures used across unit, integration, and e2e tests.
Fixtures include mocks for browser, AI interpreter, heuristic interpreter,
session logger, config, services, and state machine.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from subterminator.core.protocols import AIInterpretation, BrowserProtocol, State
from subterminator.core.states import CancellationStateMachine
from subterminator.services.netflix import NetflixService
from subterminator.utils.config import AppConfig
from subterminator.utils.session import SessionLogger


@pytest.fixture
def mock_browser() -> MagicMock:
    """Mock browser for unit tests.

    Creates a MagicMock that conforms to BrowserProtocol with all
    async methods properly configured as AsyncMock.

    Returns:
        MagicMock: A mock browser instance with async method support.
    """
    browser = MagicMock(spec=BrowserProtocol)
    # Make async methods return coroutines
    browser.launch = AsyncMock()
    browser.navigate = AsyncMock()
    browser.click = AsyncMock()
    browser.fill = AsyncMock()
    browser.select_option = AsyncMock()
    browser.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    browser.html = AsyncMock(return_value="<html></html>")
    browser.url = AsyncMock(return_value="https://example.com")
    browser.text_content = AsyncMock(return_value="Sample text content")
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_ai() -> MagicMock:
    """Mock AI interpreter for unit tests.

    Creates a mock that returns a default AIInterpretation with
    ACCOUNT_ACTIVE state and high confidence.

    Returns:
        MagicMock: A mock AI interpreter with interpret method.
    """
    ai = MagicMock()
    ai.interpret = AsyncMock(return_value=AIInterpretation(
        state=State.ACCOUNT_ACTIVE,
        confidence=0.9,
        reasoning="Test mock interpretation"
    ))
    return ai


@pytest.fixture
def mock_heuristic() -> MagicMock:
    """Mock heuristic interpreter for unit tests.

    Creates a mock that returns a default AIInterpretation with
    ACCOUNT_ACTIVE state detected via heuristic rules.

    Returns:
        MagicMock: A mock heuristic interpreter with interpret method.
    """
    heuristic = MagicMock()
    heuristic.interpret = MagicMock(return_value=AIInterpretation(
        state=State.ACCOUNT_ACTIVE,
        confidence=0.85,
        reasoning="Heuristic detection"
    ))
    return heuristic


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
def state_machine() -> CancellationStateMachine:
    """Fresh state machine instance.

    Creates a new CancellationStateMachine in its initial state.

    Returns:
        CancellationStateMachine: A fresh state machine instance.
    """
    return CancellationStateMachine()


@pytest.fixture
def mock_pages_dir() -> Path:
    """Path to mock pages directory.

    Returns the path to the Netflix mock pages directory containing
    HTML files for testing page state detection.

    Returns:
        Path: Path to the mock_pages/netflix directory.
    """
    return Path(__file__).parent.parent / "mock_pages" / "netflix"
