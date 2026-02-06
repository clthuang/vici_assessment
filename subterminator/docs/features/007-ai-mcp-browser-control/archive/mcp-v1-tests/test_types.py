"""Tests for MCP types.

This module tests the data types defined in subterminator.mcp.types,
focusing on serialization, correctness, and edge cases.
"""

import json

import pytest

from subterminator.mcp.types import (
    AIResponse,
    BoundingBox,
    CompletionCriteria,
    ElementInfo,
    Message,
    PageInfo,
    Snapshot,
    TaskResult,
    ToolCall,
    ToolResult,
    ViewportInfo,
)


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_center_returns_correct_values(self) -> None:
        """Test that center() computes the correct center point."""
        bbox = BoundingBox(x=100, y=200, width=50, height=30)
        center = bbox.center()

        assert center == (125, 215)

    def test_center_with_zero_dimensions(self) -> None:
        """Test center() with zero-sized bounding box."""
        bbox = BoundingBox(x=50, y=50, width=0, height=0)
        center = bbox.center()

        assert center == (50, 50)

    def test_center_with_odd_dimensions(self) -> None:
        """Test center() with odd dimensions uses integer division."""
        bbox = BoundingBox(x=0, y=0, width=11, height=7)
        center = bbox.center()

        # 11 // 2 = 5, 7 // 2 = 3
        assert center == (5, 3)

    def test_center_with_large_values(self) -> None:
        """Test center() with large coordinate values."""
        bbox = BoundingBox(x=10000, y=20000, width=1000, height=2000)
        center = bbox.center()

        assert center == (10500, 21000)


class TestElementInfo:
    """Tests for ElementInfo dataclass."""

    def test_default_values(self) -> None:
        """Test that ElementInfo has sensible defaults."""
        elem = ElementInfo()

        assert elem.ref == ""
        assert elem.role == ""
        assert elem.name == ""
        assert elem.state == []
        assert elem.bbox is None
        assert elem.value is None
        assert elem.level is None
        assert elem.selector is None
        assert elem.children == []

    def test_with_all_fields(self) -> None:
        """Test ElementInfo with all fields populated."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        elem = ElementInfo(
            ref="@e7",
            role="button",
            name="Submit",
            state=["visible", "enabled"],
            bbox=bbox,
            value="Click me",
            level=None,
            selector="button#submit",
            children=["@e8", "@e9"],
        )

        assert elem.ref == "@e7"
        assert elem.role == "button"
        assert elem.name == "Submit"
        assert elem.state == ["visible", "enabled"]
        assert elem.bbox == bbox
        assert elem.value == "Click me"
        assert elem.selector == "button#submit"
        assert elem.children == ["@e8", "@e9"]


class TestPageInfo:
    """Tests for PageInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic PageInfo creation."""
        page = PageInfo(url="https://example.com", title="Example Page")

        assert page.url == "https://example.com"
        assert page.title == "Example Page"


class TestViewportInfo:
    """Tests for ViewportInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic ViewportInfo creation."""
        viewport = ViewportInfo(width=1920, height=1080, scroll_x=0, scroll_y=500)

        assert viewport.width == 1920
        assert viewport.height == 1080
        assert viewport.scroll_x == 0
        assert viewport.scroll_y == 500


class TestSnapshot:
    """Tests for Snapshot dataclass."""

    def test_default_values(self) -> None:
        """Test that Snapshot has sensible defaults."""
        snapshot = Snapshot()

        assert snapshot.snapshot_id  # Should be a UUID string
        assert snapshot.timestamp  # Should be an ISO timestamp
        assert snapshot.elements == []
        assert snapshot.focused is None
        assert snapshot.page.url == ""
        assert snapshot.page.title == ""
        assert snapshot.screenshot == ""
        assert snapshot.viewport.width == 1024
        assert snapshot.viewport.height == 768

    def test_to_dict_produces_valid_json(self) -> None:
        """Test that to_dict() produces JSON-serializable output."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        elem = ElementInfo(
            ref="@e0",
            role="button",
            name="Click me",
            state=["visible", "enabled"],
            bbox=bbox,
            children=["@e1"],
        )
        snapshot = Snapshot(
            snapshot_id="test-id-123",
            timestamp="2024-01-15T10:30:00",
            elements=[elem],
            focused="@e0",
            page=PageInfo(url="https://example.com", title="Test"),
            screenshot="base64data",
            viewport=ViewportInfo(width=1920, height=1080, scroll_x=0, scroll_y=100),
        )

        result = snapshot.to_dict()

        # Verify it's JSON serializable
        json_str = json.dumps(result)
        assert json_str  # Should not raise

        # Verify structure
        assert result["snapshot_id"] == "test-id-123"
        assert result["timestamp"] == "2024-01-15T10:30:00"
        assert len(result["elements"]) == 1
        assert result["elements"][0]["ref"] == "@e0"
        assert result["elements"][0]["role"] == "button"
        assert result["elements"][0]["bbox"]["x"] == 10
        assert result["elements"][0]["children"] == ["@e1"]
        assert result["focused"] == "@e0"
        assert result["page"]["url"] == "https://example.com"
        assert result["screenshot"] == "base64data"
        assert result["viewport"]["scroll_y"] == 100

    def test_to_dict_with_empty_elements(self) -> None:
        """Test to_dict() with no elements."""
        snapshot = Snapshot(
            snapshot_id="empty-snapshot",
            timestamp="2024-01-15T10:30:00",
            page=PageInfo(url="https://empty.com", title="Empty"),
        )

        result = snapshot.to_dict()
        json_str = json.dumps(result)

        assert json_str
        assert result["elements"] == []
        assert result["focused"] is None

    def test_to_dict_with_none_bbox(self) -> None:
        """Test to_dict() when element has no bounding box."""
        elem = ElementInfo(ref="@e0", role="generic", name="Hidden")
        snapshot = Snapshot(elements=[elem])

        result = snapshot.to_dict()

        assert result["elements"][0]["bbox"] is None

    def test_to_dict_with_empty_children(self) -> None:
        """Test to_dict() when element has empty children list."""
        elem = ElementInfo(ref="@e0", role="button", name="Leaf", children=[])
        snapshot = Snapshot(elements=[elem])

        result = snapshot.to_dict()

        # Empty children should be None per design doc
        assert result["elements"][0]["children"] is None


class TestMessage:
    """Tests for Message dataclass."""

    def test_system_message(self) -> None:
        """Test creating a system message."""
        msg = Message(role="system", content="You are a browser assistant.")

        assert msg.role == "system"
        assert msg.content == "You are a browser assistant."
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_assistant_message_with_tool_calls(self) -> None:
        """Test creating an assistant message with tool calls."""
        tool_call = ToolCall(
            id="call_123", name="browser_click", arguments={"ref": "@e7"}
        )
        msg = Message(
            role="assistant",
            content="Clicking the submit button.",
            tool_calls=[tool_call],
        )

        assert msg.role == "assistant"
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "browser_click"

    def test_tool_message(self) -> None:
        """Test creating a tool result message."""
        msg = Message(
            role="tool",
            content='{"success": true}',
            tool_call_id="call_123",
        )

        assert msg.role == "tool"
        assert msg.tool_call_id == "call_123"


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic ToolCall creation."""
        call = ToolCall(
            id="call_abc123",
            name="browser_fill",
            arguments={"ref": "@e5", "value": "test@example.com"},
        )

        assert call.id == "call_abc123"
        assert call.name == "browser_fill"
        assert call.arguments["ref"] == "@e5"
        assert call.arguments["value"] == "test@example.com"


class TestAIResponse:
    """Tests for AIResponse dataclass."""

    def test_response_with_tool_use(self) -> None:
        """Test AIResponse with tool calls."""
        tool_call = ToolCall(
            id="call_123", name="get_snapshot", arguments={"viewport_only": True}
        )
        response = AIResponse(
            content="Let me check the page state.",
            tool_calls=[tool_call],
            stop_reason="tool_use",
        )

        assert response.content == "Let me check the page state."
        assert len(response.tool_calls) == 1
        assert response.stop_reason == "tool_use"

    def test_response_end_turn(self) -> None:
        """Test AIResponse that ends the turn."""
        response = AIResponse(
            content="Task completed.",
            tool_calls=[],
            stop_reason="end_turn",
        )

        assert response.stop_reason == "end_turn"
        assert response.tool_calls == []


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful ToolResult."""
        snapshot = Snapshot(snapshot_id="snap-123")
        result = ToolResult(success=True, snapshot=snapshot)

        assert result.success is True
        assert result.snapshot == snapshot
        assert result.error is None
        assert result.message is None

    def test_failed_result(self) -> None:
        """Test creating a failed ToolResult."""
        result = ToolResult(
            success=False,
            error="ref_invalid",
            message="Element @e99 not found",
        )

        assert result.success is False
        assert result.error == "ref_invalid"
        assert result.message == "Element @e99 not found"

    def test_to_dict_includes_all_fields(self) -> None:
        """Test that to_dict() includes all present fields."""
        snapshot = Snapshot(
            snapshot_id="snap-456",
            page=PageInfo(url="https://test.com", title="Test"),
        )
        result = ToolResult(
            success=False,
            snapshot=snapshot,
            error="element_disabled",
            message="Cannot click disabled button",
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert "snapshot" in result_dict
        assert result_dict["snapshot"]["snapshot_id"] == "snap-456"
        assert result_dict["error"] == "element_disabled"
        assert result_dict["message"] == "Cannot click disabled button"

    def test_to_dict_json_serializable(self) -> None:
        """Test that to_dict() output is JSON serializable."""
        snapshot = Snapshot(
            elements=[
                ElementInfo(
                    ref="@e0",
                    role="button",
                    name="Submit",
                    state=["visible"],
                    bbox=BoundingBox(x=0, y=0, width=100, height=30),
                )
            ]
        )
        result = ToolResult(success=True, snapshot=snapshot, message="Clicked")

        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)

        assert json_str  # Should not raise

    def test_to_dict_omits_none_fields(self) -> None:
        """Test that to_dict() omits fields that are None."""
        result = ToolResult(success=True)

        result_dict = result.to_dict()

        assert "success" in result_dict
        assert "snapshot" not in result_dict
        assert "error" not in result_dict
        assert "message" not in result_dict


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_successful_task(self) -> None:
        """Test creating a successful TaskResult."""
        snapshot = Snapshot(snapshot_id="final-snap")
        result = TaskResult(
            success=True,
            reason="Subscription cancelled successfully",
            turns=5,
            final_snapshot=snapshot,
        )

        assert result.success is True
        assert result.reason == "Subscription cancelled successfully"
        assert result.turns == 5
        assert result.final_snapshot == snapshot

    def test_failed_task(self) -> None:
        """Test creating a failed TaskResult."""
        result = TaskResult(
            success=False,
            reason="max_turns_exceeded",
            turns=20,
            final_snapshot=None,
        )

        assert result.success is False
        assert result.reason == "max_turns_exceeded"
        assert result.turns == 20
        assert result.final_snapshot is None


class TestCompletionCriteria:
    """Tests for CompletionCriteria dataclass."""

    def test_default_values(self) -> None:
        """Test that CompletionCriteria has empty lists by default."""
        criteria = CompletionCriteria()

        assert criteria.success_indicators == []
        assert criteria.failure_indicators == []

    def test_with_indicators(self) -> None:
        """Test CompletionCriteria with indicator functions."""

        def check_title(s: Snapshot) -> bool:
            return "cancelled" in s.page.title.lower()

        def check_error(s: Snapshot) -> bool:
            return "error" in s.page.url.lower()

        criteria = CompletionCriteria(
            success_indicators=[check_title],
            failure_indicators=[check_error],
        )

        # Test success indicator
        success_snapshot = Snapshot(page=PageInfo(url="https://test.com", title="Subscription Cancelled"))
        assert criteria.success_indicators[0](success_snapshot) is True

        # Test failure indicator
        failure_snapshot = Snapshot(page=PageInfo(url="https://test.com/error", title="Error"))
        assert criteria.failure_indicators[0](failure_snapshot) is True
