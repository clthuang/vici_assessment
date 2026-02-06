"""Tests for MCP orchestrator types."""


from subterminator.mcp_orchestrator.types import (
    CheckpointPredicate,
    NormalizedSnapshot,
    SnapshotPredicate,
    TaskResult,
    ToolCall,
)


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_create_success_result(self):
        """TaskResult can be created with success state."""
        result = TaskResult(
            success=True,
            verified=True,
            reason="completed",
            turns=5,
        )
        assert result.success is True
        assert result.verified is True
        assert result.reason == "completed"
        assert result.turns == 5
        assert result.final_url is None
        assert result.error is None

    def test_create_failure_result(self):
        """TaskResult can be created with failure state."""
        result = TaskResult(
            success=False,
            verified=False,
            reason="llm_error",
            turns=3,
            error="API timeout",
        )
        assert result.success is False
        assert result.reason == "llm_error"
        assert result.error == "API timeout"

    def test_optional_fields(self):
        """TaskResult optional fields work correctly."""
        result = TaskResult(
            success=True,
            verified=True,
            reason="completed",
            turns=10,
            final_url="https://example.com/done",
        )
        assert result.final_url == "https://example.com/done"


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_tool_call(self):
        """ToolCall can be created with all fields."""
        tc = ToolCall(
            id="call_123",
            name="browser_click",
            args={"element": "button#submit"},
        )
        assert tc.id == "call_123"
        assert tc.name == "browser_click"
        assert tc.args == {"element": "button#submit"}

    def test_tool_call_default_args(self):
        """ToolCall args defaults to empty dict."""
        tc = ToolCall(id="x", name="browser_snapshot")
        assert tc.args == {}

    def test_tool_call_equality(self):
        """ToolCall equality works correctly."""
        tc1 = ToolCall(id="1", name="click", args={"a": 1})
        tc2 = ToolCall(id="1", name="click", args={"a": 1})
        tc3 = ToolCall(id="2", name="click", args={"a": 1})
        assert tc1 == tc2
        assert tc1 != tc3


class TestNormalizedSnapshot:
    """Tests for NormalizedSnapshot dataclass."""

    def test_create_snapshot(self):
        """NormalizedSnapshot can be created with required fields."""
        snap = NormalizedSnapshot(
            url="https://example.com",
            title="Example Domain",
            content="- document [ref=@e0]:",
        )
        assert snap.url == "https://example.com"
        assert snap.title == "Example Domain"
        assert snap.content == "- document [ref=@e0]:"
        assert snap.screenshot_path is None

    def test_screenshot_path_optional(self):
        """NormalizedSnapshot screenshot_path defaults to None."""
        snap = NormalizedSnapshot(url="u", title="t", content="c")
        assert snap.screenshot_path is None

    def test_screenshot_path_can_be_set(self):
        """NormalizedSnapshot screenshot_path can be specified."""
        snap = NormalizedSnapshot(
            url="u",
            title="t",
            content="c",
            screenshot_path="/tmp/screenshot.png",
        )
        assert snap.screenshot_path == "/tmp/screenshot.png"


class TestTypeAliases:
    """Tests for type aliases."""

    def test_snapshot_predicate_signature(self):
        """SnapshotPredicate has correct signature."""
        # Define a function matching the signature
        def has_login(snap: NormalizedSnapshot) -> bool:
            return "login" in snap.content.lower()

        # Type check: this should work without errors
        predicate: SnapshotPredicate = has_login
        snap = NormalizedSnapshot(url="u", title="t", content="Please login")
        assert predicate(snap) is True

    def test_checkpoint_predicate_signature(self):
        """CheckpointPredicate has correct signature."""
        # Define a function matching the signature
        def is_confirm_click(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
            return tool.name == "browser_click" and "confirm" in str(tool.args).lower()

        # Type check: this should work without errors
        predicate: CheckpointPredicate = is_confirm_click
        tool = ToolCall(id="1", name="browser_click", args={"element": "Confirm"})
        snap = NormalizedSnapshot(url="u", title="t", content="c")
        assert predicate(tool, snap) is True
