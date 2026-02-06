"""Tests for task runner."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from subterminator.mcp_orchestrator.services.base import ServiceConfig
from subterminator.mcp_orchestrator.services.registry import ServiceRegistry
from subterminator.mcp_orchestrator.task_runner import (
    VIRTUAL_TOOLS,
    TaskRunner,
    get_all_tools,
    is_virtual_tool,
)
from subterminator.mcp_orchestrator.types import NormalizedSnapshot, TaskResult


class TestVirtualTools:
    """Tests for virtual tools."""

    def test_virtual_tools_defined(self):
        """VIRTUAL_TOOLS contains expected tools."""
        assert "complete_task" in VIRTUAL_TOOLS
        assert "request_human_approval" in VIRTUAL_TOOLS

    def test_complete_task_schema(self):
        """complete_task has correct schema."""
        schema = VIRTUAL_TOOLS["complete_task"]
        assert schema["name"] == "complete_task"
        assert "inputSchema" in schema
        assert "status" in schema["inputSchema"]["properties"]
        assert "reason" in schema["inputSchema"]["properties"]

    def test_is_virtual_tool_true(self):
        """is_virtual_tool returns True for virtual tools."""
        assert is_virtual_tool("complete_task") is True
        assert is_virtual_tool("request_human_approval") is True

    def test_is_virtual_tool_false(self):
        """is_virtual_tool returns False for MCP tools."""
        assert is_virtual_tool("browser_click") is False
        assert is_virtual_tool("browser_navigate") is False

    def test_get_all_tools_merges(self):
        """get_all_tools merges MCP and virtual tools."""
        mcp_tools = [{"name": "browser_click"}, {"name": "browser_snapshot"}]
        result = get_all_tools(mcp_tools)

        assert len(result) == 4  # 2 MCP + 2 virtual
        names = [t["name"] for t in result]
        assert "browser_click" in names
        assert "complete_task" in names


class TestTaskRunnerInit:
    """Tests for TaskRunner initialization."""

    def test_init_stores_clients(self):
        """TaskRunner stores MCP and LLM clients."""
        mcp = MagicMock()
        llm = MagicMock()
        runner = TaskRunner(mcp, llm)

        assert runner._mcp is mcp
        assert runner._llm is llm
        assert runner._checkpoint is not None

    def test_init_uses_default_registry(self):
        """TaskRunner uses default registry when not provided."""
        from subterminator.mcp_orchestrator.services.registry import default_registry

        runner = TaskRunner(MagicMock(), MagicMock())
        assert runner._registry is default_registry

    def test_init_accepts_custom_registry(self):
        """TaskRunner accepts custom registry."""
        registry = ServiceRegistry()
        runner = TaskRunner(MagicMock(), MagicMock(), service_registry=registry)
        assert runner._registry is registry


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt method."""

    @pytest.fixture
    def runner(self):
        """Create runner with mocks."""
        return TaskRunner(MagicMock(), MagicMock())

    def test_includes_goal(self, runner):
        """System prompt includes service goal."""
        config = ServiceConfig(
            name="test",
            initial_url="https://test.com",
            goal_template="Cancel the test subscription",
        )
        prompt = runner._build_system_prompt(config)
        assert "Cancel the test subscription" in prompt

    def test_includes_service_addition(self, runner):
        """System prompt includes service-specific addition."""
        config = ServiceConfig(
            name="test",
            initial_url="https://test.com",
            goal_template="Test goal",
            system_prompt_addition="## Test-Specific Rules\nBe careful with X.",
        )
        prompt = runner._build_system_prompt(config)
        assert "Test-Specific Rules" in prompt
        assert "Be careful with X" in prompt


class TestTaskRunnerRun:
    """Tests for TaskRunner.run method."""

    @pytest.fixture
    def mock_registry(self):
        """Create registry with test config."""
        registry = ServiceRegistry()
        registry.register(
            ServiceConfig(
                name="test",
                initial_url="https://test.com",
                goal_template="Test goal",
            )
        )
        return registry

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        mcp = AsyncMock()
        mcp.connect = AsyncMock()
        mcp.close = AsyncMock()
        mcp.list_tools = AsyncMock(
            return_value=[
                {"name": "browser_click"},
                {"name": "browser_navigate"},
                {"name": "browser_snapshot"},
            ]
        )
        mcp.call_tool = AsyncMock(
            side_effect=[
                # browser_navigate
                "Navigated to test.com",
                # browser_snapshot
                """### Page state
- Page URL: https://test.com
- Page Title: Test Page
- Page Snapshot:
- document [ref=@e0]""",
            ]
        )
        return mcp

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        llm = AsyncMock()
        response = MagicMock()
        response.content = "I will complete the task"
        response.tool_calls = [
            {
                "id": "call_1",
                "name": "complete_task",
                "args": {"status": "success", "reason": "Done"},
            }
        ]
        llm.invoke = AsyncMock(return_value=response)
        return llm

    @pytest.mark.asyncio
    async def test_run_returns_task_result(self, mock_registry, mock_mcp, mock_llm):
        """run() returns TaskResult."""
        runner = TaskRunner(mock_mcp, mock_llm, service_registry=mock_registry)
        result = await runner.run("test")

        assert isinstance(result, TaskResult)

    @pytest.mark.asyncio
    async def test_run_unknown_service(self, mock_mcp, mock_llm):
        """run() returns error for unknown service."""
        registry = ServiceRegistry()  # Empty registry
        runner = TaskRunner(mock_mcp, mock_llm, service_registry=registry)

        result = await runner.run("unknown")

        assert result.success is False
        assert "unknown" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_max_turns_exceeded(self, mock_registry, mock_mcp, mock_llm):
        """run() returns max_turns_exceeded when limit reached."""
        # LLM always returns a non-completion tool
        response = MagicMock()
        response.content = ""
        response.tool_calls = [
            {
                "id": "call_1",
                "name": "browser_snapshot",
                "args": {},
            }
        ]
        mock_llm.invoke = AsyncMock(return_value=response)

        # MCP returns snapshot for each call
        mock_mcp.call_tool = AsyncMock(
            return_value="""### Page state
- Page URL: https://test.com
- Page Title: Test
- Page Snapshot:
content"""
        )

        runner = TaskRunner(mock_mcp, mock_llm, service_registry=mock_registry)
        result = await runner.run("test", max_turns=3)

        assert result.success is False
        assert result.reason == "max_turns_exceeded"
        assert result.turns == 3

    @pytest.mark.asyncio
    async def test_run_no_action_limit(self, mock_registry, mock_mcp, mock_llm):
        """run() returns llm_no_action after 3 empty responses."""
        # LLM returns no tool calls
        response = MagicMock()
        response.content = "I understand but I'm not sure"
        response.tool_calls = []
        mock_llm.invoke = AsyncMock(return_value=response)

        mock_mcp.call_tool = AsyncMock(
            return_value="""### Page state
- Page URL: https://test.com
- Page Title: Test
- Page Snapshot:
content"""
        )

        runner = TaskRunner(mock_mcp, mock_llm, service_registry=mock_registry)
        result = await runner.run("test", max_turns=10)

        assert result.success is False
        assert result.reason == "llm_no_action"

    @pytest.mark.asyncio
    async def test_run_dry_run(self, mock_registry, mock_mcp, mock_llm):
        """run() with dry_run returns proposed action."""
        response = MagicMock()
        response.content = ""
        response.tool_calls = [
            {
                "id": "call_1",
                "name": "browser_click",
                "args": {"element": "button#submit"},
            }
        ]
        mock_llm.invoke = AsyncMock(return_value=response)

        mock_mcp.call_tool = AsyncMock(
            return_value="""### Page state
- Page URL: https://test.com
- Page Title: Test
- Page Snapshot:
content"""
        )

        runner = TaskRunner(mock_mcp, mock_llm, service_registry=mock_registry)
        result = await runner.run("test", dry_run=True)

        assert result.success is True
        assert "browser_click" in result.error  # Contains proposed action


class TestHandleCompleteTask:
    """Tests for _handle_complete_task method."""

    @pytest.fixture
    def runner(self):
        """Create runner with mocks."""
        return TaskRunner(MagicMock(), MagicMock())

    @pytest.fixture
    def snap(self):
        """Create test snapshot."""
        return NormalizedSnapshot(
            url="https://test.com/done", title="Done", content="cancellation confirmed"
        )

    @pytest.fixture
    def config(self):
        """Create test config with indicators."""
        return ServiceConfig(
            name="test",
            initial_url="https://test.com",
            goal_template="Test",
            success_indicators=[lambda s: "confirmed" in s.content.lower()],
            failure_indicators=[lambda s: "error" in s.content.lower()],
        )

    @pytest.mark.asyncio
    async def test_complete_failed_returns_immediately(self, runner, snap, config):
        """complete_task with status=failed returns TaskResult."""
        from subterminator.mcp_orchestrator.types import ToolCall

        tc = ToolCall(
            id="1",
            name="complete_task",
            args={"status": "failed", "reason": "Could not find button"},
        )

        result = await runner._handle_complete_task(tc, snap, config, turn=5)

        assert isinstance(result, TaskResult)
        assert result.success is False
        assert result.turns == 5
        assert "Could not find button" in result.error

    @pytest.mark.asyncio
    async def test_complete_success_verified(self, runner, snap, config):
        """complete_task with status=success verifies and returns."""
        from subterminator.mcp_orchestrator.types import ToolCall

        tc = ToolCall(
            id="1",
            name="complete_task",
            args={"status": "success", "reason": "Task completed"},
        )

        result = await runner._handle_complete_task(tc, snap, config, turn=5)

        assert isinstance(result, TaskResult)
        assert result.success is True
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_complete_success_not_verified(self, runner, config):
        """complete_task with status=success returns error if not verified."""
        from subterminator.mcp_orchestrator.types import ToolCall

        snap = NormalizedSnapshot(
            url="https://test.com",
            title="Page",
            content="some other content",  # No success indicator
        )
        tc = ToolCall(
            id="1",
            name="complete_task",
            args={"status": "success", "reason": "Done"},
        )

        result = await runner._handle_complete_task(tc, snap, config, turn=5)

        assert isinstance(result, str)  # Error string, not TaskResult
        assert "not verified" in result.lower()


class TestVerifyCompletion:
    """Tests for _verify_completion method."""

    @pytest.fixture
    def runner(self):
        """Create runner with mocks."""
        return TaskRunner(MagicMock(), MagicMock())

    def test_returns_true_on_success_indicator(self, runner):
        """Verification passes when success indicator matches."""
        snap = NormalizedSnapshot(
            url="https://test.com",
            title="Done",
            content="Your membership has been cancelled",
        )
        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            success_indicators=[lambda s: "cancelled" in s.content.lower()],
        )

        assert runner._verify_completion(snap, config) is True

    def test_returns_false_on_failure_indicator(self, runner):
        """Verification fails when failure indicator matches."""
        snap = NormalizedSnapshot(
            url="https://test.com", title="Error", content="Something went wrong"
        )
        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            success_indicators=[
                lambda s: True  # Would pass
            ],
            failure_indicators=[lambda s: "went wrong" in s.content.lower()],
        )

        # Failure takes precedence
        assert runner._verify_completion(snap, config) is False

    def test_returns_false_on_no_match(self, runner):
        """Verification fails when no indicators match."""
        snap = NormalizedSnapshot(
            url="https://test.com", title="Page", content="Some random content"
        )
        config = ServiceConfig(
            name="test",
            initial_url="u",
            goal_template="g",
            success_indicators=[lambda s: "cancelled" in s.content.lower()],
        )

        assert runner._verify_completion(snap, config) is False
