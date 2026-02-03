"""Integration tests for Claude Vision state detection.

These tests validate that the ClaudeInterpreter correctly identifies page states
from actual screenshots of mock pages. This ensures Claude Vision works as a
reliable fallback when heuristic detection fails.

Tests require ANTHROPIC_API_KEY to be set (via .env file or environment).
"""

import os
import time

import pytest
from playwright.async_api import Page

from subterminator.core.ai import ClaudeInterpreter
from subterminator.core.protocols import State
from subterminator.services.mock import MockServer
from subterminator.utils.exceptions import StateDetectionError

# Skip all tests in this module if API key is not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping Claude Vision tests"
)


class TestClaudeVisionStateDetection:
    """Test Claude Vision detection against mock page screenshots."""

    @pytest.fixture
    def interpreter(self) -> ClaudeInterpreter:
        """Create a ClaudeInterpreter instance."""
        return ClaudeInterpreter()

    async def _capture_screenshot(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        page_path: str,
    ) -> bytes:
        """Navigate to page and capture screenshot.

        Args:
            playwright_browser: Playwright page instance.
            mock_server: Running mock server.
            page_path: Path to navigate to (e.g., "/account?variant=login").

        Returns:
            Screenshot as PNG bytes.
        """
        url = f"{mock_server.base_url}{page_path}"
        await playwright_browser.goto(url)
        # Small delay to ensure page is fully rendered
        await playwright_browser.wait_for_load_state("networkidle")
        return await playwright_browser.screenshot(type="png")

    async def test_detects_login_page(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects LOGIN_REQUIRED from login page screenshot."""
        # Give server time to start
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/login.html"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.LOGIN_REQUIRED, (
            f"Expected LOGIN_REQUIRED, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.7, (
            f"Expected confidence >= 0.7, got {result.confidence}"
        )

    async def test_detects_account_active(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects ACCOUNT_ACTIVE from account page screenshot."""
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/account.html"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.ACCOUNT_ACTIVE, (
            f"Expected ACCOUNT_ACTIVE, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.7, (
            f"Expected confidence >= 0.7, got {result.confidence}"
        )

    async def test_detects_account_cancelled(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects ACCOUNT_CANCELLED from cancelled account page."""
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/account?variant=cancelled"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.ACCOUNT_CANCELLED, (
            f"Expected ACCOUNT_CANCELLED, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.6, (
            f"Expected confidence >= 0.6, got {result.confidence}"
        )

    async def test_detects_retention_offer(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects RETENTION_OFFER from retention page screenshot."""
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/cancelplan?variant=retention"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.RETENTION_OFFER, (
            f"Expected RETENTION_OFFER, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.6, (
            f"Expected confidence >= 0.6, got {result.confidence}"
        )

    async def test_detects_exit_survey(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects EXIT_SURVEY from survey page screenshot."""
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/cancelplan?variant=survey"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.EXIT_SURVEY, (
            f"Expected EXIT_SURVEY, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.6, (
            f"Expected confidence >= 0.6, got {result.confidence}"
        )

    async def test_detects_final_confirmation(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects FINAL_CONFIRMATION from confirm page screenshot."""
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/cancelplan?variant=confirm"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.FINAL_CONFIRMATION, (
            f"Expected FINAL_CONFIRMATION, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.7, (
            f"Expected confidence >= 0.7, got {result.confidence}"
        )

    async def test_detects_complete(
        self,
        playwright_browser: Page,
        mock_server: MockServer,
        interpreter: ClaudeInterpreter,
    ):
        """Test Claude detects COMPLETE from completion page screenshot."""
        time.sleep(0.1)

        screenshot = await self._capture_screenshot(
            playwright_browser, mock_server, "/cancelplan?variant=complete"
        )

        result = await interpreter.interpret(screenshot)

        assert result.state == State.COMPLETE, (
            f"Expected COMPLETE, got {result.state} "
            f"(confidence: {result.confidence}, reasoning: {result.reasoning})"
        )
        assert result.confidence >= 0.7, (
            f"Expected confidence >= 0.7, got {result.confidence}"
        )


class TestClaudeVisionErrorHandling:
    """Test Claude Vision error handling."""

    @pytest.fixture
    def interpreter(self) -> ClaudeInterpreter:
        """Create a ClaudeInterpreter instance."""
        return ClaudeInterpreter()

    async def test_handles_empty_screenshot(self, interpreter: ClaudeInterpreter):
        """Test that empty/invalid screenshot returns low confidence or error.

        When given an empty or invalid screenshot, Claude should either:
        1. Return UNKNOWN/FAILED with low confidence, or
        2. Raise StateDetectionError
        """
        # Create minimal PNG (1x1 transparent pixel)
        minimal_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        try:
            result = await interpreter.interpret(minimal_png)
            # If it doesn't raise, should return low confidence
            assert result.confidence < 0.7 or result.state in (
                State.UNKNOWN, State.FAILED
            ), (
                f"Expected low confidence or UNKNOWN/FAILED state for empty image, "
                f"got {result.state} with confidence {result.confidence}"
            )
        except StateDetectionError:
            # This is also acceptable - raising an error for invalid input
            pass

    async def test_handles_corrupted_image_data(self, interpreter: ClaudeInterpreter):
        """Test that corrupted image data is handled gracefully."""
        corrupted_data = b"not a valid image at all"

        with pytest.raises(StateDetectionError):
            await interpreter.interpret(corrupted_data)
