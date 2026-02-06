"""Checkpoint handler for human approval requests.

This module provides the CheckpointHandler class for managing
human checkpoints during browser orchestration.
"""

from __future__ import annotations

import base64
import logging
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mcp_client import MCPClient
    from .services.base import ServiceConfig
    from .types import NormalizedSnapshot, ToolCall

logger = logging.getLogger(__name__)


class CheckpointHandler:
    """Handler for human approval checkpoints.

    Manages checkpoint conditions and approval requests during
    browser orchestration.

    Example:
        handler = CheckpointHandler(mcp_client)
        if handler.should_checkpoint(tool, snapshot, config):
            approved = handler.request_approval(tool, snapshot)
            if not approved:
                # User rejected, abort operation
    """

    def __init__(self, mcp: MCPClient, disabled: bool = False) -> None:
        """Initialize checkpoint handler.

        Args:
            mcp: MCP client for screenshot capture.
            disabled: If True, all checkpoints are skipped (--no-checkpoint flag).
        """
        self._mcp = mcp
        self._disabled = disabled

    def detect_auth_edge_case(
        self,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig,
    ) -> str | None:
        """Detect if current page is an auth edge case requiring user action.

        Args:
            snapshot: Current page snapshot.
            config: Service configuration with auth detectors.

        Returns:
            Auth type string ("login", "captcha", "mfa") or None if not auth page.
        """
        for detector in config.auth_edge_case_detectors:
            try:
                if detector(snapshot):
                    # Extract auth type from function name (is_login_page -> login)
                    name = detector.__name__
                    if "login" in name:
                        return "login"
                    elif "captcha" in name:
                        return "captcha"
                    elif "mfa" in name:
                        return "mfa"
                    return "auth"
            except Exception as e:
                logger.warning(f"Auth detector error: {e}")
        return None

    async def wait_for_auth_completion(
        self,
        snapshot: NormalizedSnapshot,
        auth_type: str,
    ) -> bool:
        """Wait for user to complete authentication manually.

        Args:
            snapshot: Current page state.
            auth_type: Type of auth required (login, captcha, mfa).

        Returns:
            True if user signals completion, False if cancelled.
        """
        messages = {
            "login": (
                "Login required. Please login in the browser, "
                "then press Enter to continue..."
            ),
            "captcha": (
                "CAPTCHA detected. Please solve it in the browser, "
                "then press Enter to continue..."
            ),
            "mfa": (
                "MFA required. Please complete verification in the browser, "
                "then press Enter to continue..."
            ),
            "auth": (
                "Authentication required. Please complete it in the browser, "
                "then press Enter to continue..."
            ),
        }
        print(f"\n{'='*60}")
        print(f"  {messages.get(auth_type, messages['auth'])}")
        print(f"  Current URL: {snapshot.url}")
        print(f"{'='*60}")

        try:
            input("\nPress Enter when done (or Ctrl+C to cancel)...")
            return True
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False

    def should_checkpoint(
        self,
        tool: ToolCall,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig,
    ) -> bool:
        """Check if a checkpoint is needed before executing a tool.

        Note: Auth edge cases (login, CAPTCHA, MFA) are handled separately
        via detect_auth_edge_case() and wait_for_auth_completion().

        Args:
            tool: Tool call about to be executed.
            snapshot: Current page snapshot.
            config: Service configuration with predicates.

        Returns:
            True if human approval is required.
        """
        if self._disabled:
            return False

        # Check checkpoint conditions (tool + snapshot predicates)
        for predicate in config.checkpoint_conditions:
            try:
                if predicate(tool, snapshot):
                    pred_name = predicate.__name__
                    logger.info(f"Checkpoint triggered by condition: {pred_name}")
                    return True
            except Exception as e:
                logger.warning(f"Checkpoint predicate error: {e}")

        return False

    async def request_approval(
        self,
        tool: ToolCall,
        snapshot: NormalizedSnapshot,
    ) -> bool:
        """Request human approval for an action.

        Captures a screenshot and displays checkpoint information,
        then waits for user input.

        Args:
            tool: Tool call requiring approval.
            snapshot: Current page snapshot.

        Returns:
            True if user approved, False if rejected.
        """
        # Capture screenshot for visual context
        screenshot_path = await self._capture_screenshot()

        # Display checkpoint information
        self._display_checkpoint_info(tool, snapshot, screenshot_path)

        # Get user input
        return self._get_user_input()

    async def _capture_screenshot(self) -> str | None:
        """Capture a screenshot of the current page.

        Returns:
            Path to saved screenshot file, or None if capture failed.
        """
        try:
            result = await self._mcp.call_tool("browser_take_screenshot", {})

            if not result:
                logger.warning("Screenshot returned empty result")
                return None

            # Check if result is base64 encoded image data
            # Playwright MCP typically returns base64 encoded PNG
            if result.startswith("data:image"):
                # Extract base64 data after the prefix
                _, data = result.split(",", 1)
                image_data = base64.b64decode(data)
            elif result.startswith("/") or result.startswith("C:"):
                # Already a file path
                return result
            else:
                # Assume raw base64
                try:
                    image_data = base64.b64decode(result)
                except Exception:
                    logger.warning("Could not decode screenshot data")
                    return None

            # Save to temp file
            with tempfile.NamedTemporaryFile(
                prefix="subterminator_checkpoint_",
                suffix=".png",
                delete=False,
            ) as f:
                f.write(image_data)
                return f.name

        except Exception as e:
            logger.warning(f"Screenshot capture failed: {e}")
            return None

    def _display_checkpoint_info(
        self,
        tool: ToolCall,
        snapshot: NormalizedSnapshot,
        screenshot_path: str | None,
    ) -> None:
        """Display checkpoint information to the user.

        Args:
            tool: Tool call requiring approval.
            snapshot: Current page snapshot.
            screenshot_path: Path to screenshot file, if available.
        """
        print("\n" + "=" * 60)
        print("🛑 CHECKPOINT: Human Approval Required")
        print("=" * 60)
        print(f"\n📍 Current URL: {snapshot.url}")
        print(f"📄 Page Title: {snapshot.title}")
        print("\n🔧 Pending Action:")
        print(f"   Tool: {tool.name}")
        if tool.args:
            print(f"   Args: {tool.args}")

        if screenshot_path:
            print(f"\n📸 Screenshot saved to: {screenshot_path}")

        print("\n" + "-" * 60)

    def _get_user_input(self) -> bool:
        """Get user approval input.

        Returns:
            True if user approved (response starts with 'y'),
            False otherwise.
        """
        try:
            response = input("Approve this action? [y/N]: ").strip().lower()
            return response.startswith("y")
        except EOFError:
            # Non-interactive mode or stdin closed
            logger.warning("Could not read user input (non-interactive mode)")
            return False
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            print("\nCancelled.")
            return False
