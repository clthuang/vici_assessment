"""Tests for checkpoint handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.mcp_orchestrator.checkpoint import CheckpointHandler
from subterminator.mcp_orchestrator.services.base import ServiceConfig
from subterminator.mcp_orchestrator.types import NormalizedSnapshot, ToolCall


class TestCheckpointHandlerInit:
    """Tests for CheckpointHandler initialization."""

    def test_init_stores_mcp(self):
        """CheckpointHandler stores MCP client."""
        mcp = MagicMock()
        handler = CheckpointHandler(mcp)
        assert handler._mcp is mcp
        assert handler._disabled is False

    def test_init_accepts_disabled(self):
        """CheckpointHandler can be disabled."""
        mcp = MagicMock()
        handler = CheckpointHandler(mcp, disabled=True)
        assert handler._disabled is True


class TestShouldCheckpoint:
    """Tests for should_checkpoint method."""

    @pytest.fixture
    def handler(self):
        """Create handler with mock MCP."""
        return CheckpointHandler(MagicMock())

    @pytest.fixture
    def snap(self):
        """Create test snapshot."""
        return NormalizedSnapshot(
            url="https://example.com/cancel",
            title="Cancel",
            content="finish your cancellation"
        )

    @pytest.fixture
    def tool(self):
        """Create test tool call."""
        return ToolCall(
            id="1",
            name="browser_click",
            args={"element": "Finish Cancellation"}
        )

    def test_returns_false_when_disabled(self, snap, tool):
        """should_checkpoint returns False when disabled."""
        handler = CheckpointHandler(MagicMock(), disabled=True)
        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            checkpoint_conditions=[lambda t, s: True],  # Would trigger
        )
        assert handler.should_checkpoint(tool, snap, config) is False

    def test_triggers_on_checkpoint_condition(self, handler, snap, tool):
        """should_checkpoint returns True when condition matches."""
        def matches_finish(t: ToolCall, s: NormalizedSnapshot) -> bool:
            return "finish" in t.args.get("element", "").lower()

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            checkpoint_conditions=[matches_finish],
        )
        assert handler.should_checkpoint(tool, snap, config) is True

    def test_no_trigger_when_no_match(self, handler):
        """should_checkpoint returns False when no conditions match."""
        snap = NormalizedSnapshot(url="u", title="t", content="browse movies")
        tool = ToolCall(id="1", name="browser_click", args={"element": "Next"})

        def matches_finish(t: ToolCall, s: NormalizedSnapshot) -> bool:
            return "finish" in t.args.get("element", "").lower()

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            checkpoint_conditions=[matches_finish],
        )
        assert handler.should_checkpoint(tool, snap, config) is False

    def test_auth_edge_case_handled_separately(self, handler):
        """Auth edge cases are NOT handled via should_checkpoint (handled separately)."""
        snap = NormalizedSnapshot(
            url="https://example.com/login",
            title="Sign In",
            content="email and password"
        )
        tool = ToolCall(id="1", name="browser_click", args={})

        def is_login(s: NormalizedSnapshot) -> bool:
            return "/login" in s.url

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            auth_edge_case_detectors=[is_login],
        )
        # Auth edge cases are now handled via detect_auth_edge_case(), not should_checkpoint()
        assert handler.should_checkpoint(tool, snap, config) is False

    def test_handles_predicate_exception(self, handler, snap, tool):
        """should_checkpoint handles exceptions in predicates."""
        def bad_predicate(t: ToolCall, s: NormalizedSnapshot) -> bool:
            raise ValueError("broken")

        def good_predicate(t: ToolCall, s: NormalizedSnapshot) -> bool:
            return True

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            checkpoint_conditions=[bad_predicate, good_predicate],
        )
        # Should continue to good_predicate despite exception
        assert handler.should_checkpoint(tool, snap, config) is True


class TestRequestApproval:
    """Tests for request_approval method."""

    @pytest.fixture
    def handler(self):
        """Create handler with mock MCP."""
        mcp = AsyncMock()
        return CheckpointHandler(mcp)

    @pytest.fixture
    def snap(self):
        """Create test snapshot."""
        return NormalizedSnapshot(
            url="https://example.com/cancel",
            title="Cancel Membership",
            content="Click finish to cancel"
        )

    @pytest.fixture
    def tool(self):
        """Create test tool call."""
        return ToolCall(
            id="1",
            name="browser_click",
            args={"element": "Finish"}
        )

    @pytest.mark.asyncio
    async def test_approval_yes(self, handler, snap, tool):
        """request_approval returns True on 'y' input."""
        handler._mcp.call_tool = AsyncMock(return_value="")

        with patch("builtins.input", return_value="y"):
            result = await handler.request_approval(tool, snap)
        assert result is True

    @pytest.mark.asyncio
    async def test_approval_yes_uppercase(self, handler, snap, tool):
        """request_approval accepts 'Y' as approval."""
        handler._mcp.call_tool = AsyncMock(return_value="")

        with patch("builtins.input", return_value="Y"):
            result = await handler.request_approval(tool, snap)
        assert result is True

    @pytest.mark.asyncio
    async def test_approval_yes_with_extra(self, handler, snap, tool):
        """request_approval accepts 'yes' as approval."""
        handler._mcp.call_tool = AsyncMock(return_value="")

        with patch("builtins.input", return_value="yes"):
            result = await handler.request_approval(tool, snap)
        assert result is True

    @pytest.mark.asyncio
    async def test_approval_no(self, handler, snap, tool):
        """request_approval returns False on 'n' input."""
        handler._mcp.call_tool = AsyncMock(return_value="")

        with patch("builtins.input", return_value="n"):
            result = await handler.request_approval(tool, snap)
        assert result is False

    @pytest.mark.asyncio
    async def test_approval_empty(self, handler, snap, tool):
        """request_approval returns False on empty input (default No)."""
        handler._mcp.call_tool = AsyncMock(return_value="")

        with patch("builtins.input", return_value=""):
            result = await handler.request_approval(tool, snap)
        assert result is False

    @pytest.mark.asyncio
    async def test_approval_eof(self, handler, snap, tool):
        """request_approval returns False on EOFError."""
        handler._mcp.call_tool = AsyncMock(return_value="")

        with patch("builtins.input", side_effect=EOFError):
            result = await handler.request_approval(tool, snap)
        assert result is False


class TestDetectAuthEdgeCase:
    """Tests for detect_auth_edge_case method."""

    @pytest.fixture
    def handler(self):
        """Create handler with mock MCP."""
        return CheckpointHandler(MagicMock())

    def test_detects_login_page(self, handler):
        """detect_auth_edge_case returns 'login' for login pages."""
        snap = NormalizedSnapshot(
            url="https://example.com/login",
            title="Sign In",
            content="Enter your email"
        )

        def is_login_page(s: NormalizedSnapshot) -> bool:
            return "/login" in s.url

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            auth_edge_case_detectors=[is_login_page],
        )
        assert handler.detect_auth_edge_case(snap, config) == "login"

    def test_detects_captcha_page(self, handler):
        """detect_auth_edge_case returns 'captcha' for captcha pages."""
        snap = NormalizedSnapshot(
            url="https://example.com/verify",
            title="Verify",
            content="captcha verification"
        )

        def is_captcha_page(s: NormalizedSnapshot) -> bool:
            return "captcha" in s.content.lower()

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            auth_edge_case_detectors=[is_captcha_page],
        )
        assert handler.detect_auth_edge_case(snap, config) == "captcha"

    def test_detects_mfa_page(self, handler):
        """detect_auth_edge_case returns 'mfa' for MFA pages."""
        snap = NormalizedSnapshot(
            url="https://example.com/verify",
            title="Verify",
            content="Enter your mfa code"
        )

        def is_mfa_page(s: NormalizedSnapshot) -> bool:
            return "mfa" in s.content.lower()

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            auth_edge_case_detectors=[is_mfa_page],
        )
        assert handler.detect_auth_edge_case(snap, config) == "mfa"

    def test_returns_none_when_no_match(self, handler):
        """detect_auth_edge_case returns None when no auth detected."""
        snap = NormalizedSnapshot(
            url="https://example.com/account",
            title="Account",
            content="Your account settings"
        )

        def is_login_page(s: NormalizedSnapshot) -> bool:
            return "/login" in s.url

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            auth_edge_case_detectors=[is_login_page],
        )
        assert handler.detect_auth_edge_case(snap, config) is None

    def test_handles_exception_in_detector(self, handler):
        """detect_auth_edge_case handles exceptions gracefully."""
        snap = NormalizedSnapshot(url="u", title="t", content="c")

        def bad_detector(s: NormalizedSnapshot) -> bool:
            raise ValueError("broken")

        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            auth_edge_case_detectors=[bad_detector],
        )
        # Should return None, not raise
        assert handler.detect_auth_edge_case(snap, config) is None


class TestWaitForAuthCompletion:
    """Tests for wait_for_auth_completion method."""

    @pytest.fixture
    def handler(self):
        """Create handler with mock MCP."""
        return CheckpointHandler(MagicMock())

    @pytest.fixture
    def snap(self):
        """Create test snapshot."""
        return NormalizedSnapshot(
            url="https://example.com/login",
            title="Sign In",
            content="Enter credentials"
        )

    @pytest.mark.asyncio
    async def test_returns_true_on_enter(self, handler, snap):
        """wait_for_auth_completion returns True when user presses Enter."""
        with patch("builtins.input", return_value=""):
            result = await handler.wait_for_auth_completion(snap, "login")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_keyboard_interrupt(self, handler, snap):
        """wait_for_auth_completion returns False on Ctrl+C."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = await handler.wait_for_auth_completion(snap, "login")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_eof(self, handler, snap):
        """wait_for_auth_completion returns False on EOF."""
        with patch("builtins.input", side_effect=EOFError):
            result = await handler.wait_for_auth_completion(snap, "login")
        assert result is False


class TestCaptureScreenshot:
    """Tests for _capture_screenshot method."""

    @pytest.mark.asyncio
    async def test_handles_empty_result(self):
        """_capture_screenshot handles empty result."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value="")
        handler = CheckpointHandler(mcp)

        result = await handler._capture_screenshot()
        assert result is None

    @pytest.mark.asyncio
    async def test_handles_base64_data(self):
        """_capture_screenshot decodes base64 and saves to file."""
        import base64

        mcp = AsyncMock()
        # Small PNG-like data
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00"
        base64_data = "data:image/png;base64," + base64.b64encode(png_data).decode()
        mcp.call_tool = AsyncMock(return_value=base64_data)
        handler = CheckpointHandler(mcp)

        result = await handler._capture_screenshot()

        assert result is not None
        assert "subterminator_checkpoint_" in result
        assert result.endswith(".png")

    @pytest.mark.asyncio
    async def test_handles_file_path(self):
        """_capture_screenshot returns file path directly."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value="/tmp/screenshot.png")
        handler = CheckpointHandler(mcp)

        result = await handler._capture_screenshot()
        assert result == "/tmp/screenshot.png"

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """_capture_screenshot returns None on exception."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(side_effect=Exception("failed"))
        handler = CheckpointHandler(mcp)

        result = await handler._capture_screenshot()
        assert result is None
