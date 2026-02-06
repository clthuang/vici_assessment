"""Fixtures for integration tests."""

import atexit
from pathlib import Path

import pytest
from dotenv import load_dotenv

from subterminator.services.mock import MockServer

# Load .env file at test startup
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


@pytest.fixture(scope="session", autouse=True)
def cleanup_browsers_on_exit():
    """Ensure all browsers are killed when pytest exits, even on interruption.

    This is a safety net for cases where the try/finally in playwright_browser
    doesn't run (e.g., process killed with SIGKILL). Only kills headless
    chromium processes started by tests.
    """
    import subprocess

    def kill_test_browsers():
        """Kill any headless chromium processes started by tests."""
        try:
            subprocess.run(
                ["pkill", "-f", "chromium.*--headless"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass

    atexit.register(kill_test_browsers)
    yield
    # Normal cleanup - atexit handles interrupted cases


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
    """Real Playwright browser for capturing screenshots.

    Uses try/finally to ensure browser cleanup even if setup fails.
    Only closes the browser instance launched by this fixture -
    any existing browser windows remain unaffected.
    """
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    browser = None
    try:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        yield page
    finally:
        if browser:
            await browser.close()
        await playwright.stop()
