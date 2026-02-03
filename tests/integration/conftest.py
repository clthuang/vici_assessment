"""Fixtures for integration tests."""

import pytest
from pathlib import Path

from dotenv import load_dotenv

from subterminator.services.mock import MockServer

# Load .env file at test startup
load_dotenv(Path(__file__).parent.parent.parent / ".env")


@pytest.fixture
def mock_pages_dir() -> Path:
    """Path to mock pages directory."""
    return Path(__file__).parent.parent.parent / "mock_pages" / "netflix"


@pytest.fixture
def mock_server(mock_pages_dir: Path):
    """Start mock server for integration tests."""
    import socket

    def get_free_port() -> int:
        """Get a free port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            return s.getsockname()[1]

    port = get_free_port()
    server = MockServer(mock_pages_dir, port=port)
    server.start()
    yield server
    server.stop()


@pytest.fixture
async def playwright_browser():
    """Real Playwright browser for capturing screenshots."""
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    yield page
    await browser.close()
    await playwright.stop()
