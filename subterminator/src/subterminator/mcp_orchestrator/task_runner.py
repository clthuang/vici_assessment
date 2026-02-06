"""Task runner for browser orchestration.

This module provides the TaskRunner class that orchestrates the
LLM-driven browser automation loop.
"""

from __future__ import annotations

import logging
import signal
from typing import TYPE_CHECKING, Any

from .checkpoint import CheckpointHandler
from .exceptions import (
    MCPConnectionError,
    MCPToolError,
    ServiceNotFoundError,
)
from .services.registry import default_registry
from .snapshot import normalize_snapshot
from .types import NormalizedSnapshot, TaskResult, ToolCall

if TYPE_CHECKING:
    from .llm_client import LLMClient
    from .mcp_client import MCPClient
    from .services.base import ServiceConfig
    from .services.registry import ServiceRegistry

logger = logging.getLogger(__name__)


# Virtual tool schemas (spec Section 2.3)
VIRTUAL_TOOLS = {
    "complete_task": {
        "name": "complete_task",
        "description": "Call this when the task is complete or has failed. "
        "status='success' if the goal was achieved, 'failed' if not.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success", "failed"],
                    "description": "Whether the task succeeded or failed",
                },
                "reason": {
                    "type": "string",
                    "description": "Explanation of the outcome",
                },
            },
            "required": ["status", "reason"],
        },
    },
    "request_human_approval": {
        "name": "request_human_approval",
        "description": "Request human approval before proceeding with an action. "
        "Use this for irreversible actions or when unsure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Description of the action requiring approval",
                },
                "reason": {
                    "type": "string",
                    "description": "Why human approval is needed",
                },
            },
            "required": ["action", "reason"],
        },
    },
}

# Maximum consecutive turns without a tool call
MAX_NO_ACTION_COUNT = 3


def is_virtual_tool(name: str) -> bool:
    """Check if a tool name is a virtual tool."""
    return name in VIRTUAL_TOOLS


def get_all_tools(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge MCP tools with virtual tools."""
    return mcp_tools + list(VIRTUAL_TOOLS.values())


class TaskRunner:
    """Orchestrates LLM-driven browser automation.

    Manages the main loop of:
    1. Getting page snapshot
    2. Asking LLM for next action
    3. Executing tool (with checkpoint if needed)
    4. Repeat until complete or limit reached

    Example:
        async with MCPClient() as mcp:
            llm = LLMClient()
            runner = TaskRunner(mcp, llm)
            result = await runner.run("netflix", max_turns=20)
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        llm_client: LLMClient,
        service_registry: ServiceRegistry | None = None,
        disable_checkpoints: bool = False,
    ) -> None:
        """Initialize task runner.

        Args:
            mcp_client: MCP client for browser control.
            llm_client: LLM client for AI decisions.
            service_registry: Service registry (defaults to global).
            disable_checkpoints: If True, skip all checkpoints.
        """
        self._mcp = mcp_client
        self._llm = llm_client
        self._registry = service_registry or default_registry
        self._checkpoint = CheckpointHandler(mcp_client, disabled=disable_checkpoints)
        self._messages: list[dict[str, Any]] = []
        self._shutdown_requested = False

    def _build_system_prompt(self, config: ServiceConfig) -> str:
        """Build system prompt with service-specific additions.

        Args:
            config: Service configuration.

        Returns:
            Complete system prompt.
        """
        base_prompt = f"""You are a browser automation agent. Your goal is: {config.goal_template}

## Rules
1. Call exactly ONE tool per turn
2. After each action, wait for the result before proceeding
3. Use browser_snapshot to see the current page state
4. Call complete_task when done (success or failure)
5. Call request_human_approval if you need human input

## Available Actions
- browser_navigate: Go to a URL
- browser_click: Click an element (use ref from snapshot)
- browser_type: Type text into an input field
- browser_snapshot: Get current page state
- browser_take_screenshot: Capture screenshot
- complete_task: Signal task completion
- request_human_approval: Request human approval
"""
        if config.system_prompt_addition:
            base_prompt += "\n" + config.system_prompt_addition

        return base_prompt

    async def run(
        self,
        service: str,
        max_turns: int = 20,
        dry_run: bool = False,
    ) -> TaskResult:
        """Run the orchestration loop.

        Args:
            service: Service name (e.g., "netflix").
            max_turns: Maximum number of turns before stopping.
            dry_run: If True, return after first action without executing.

        Returns:
            TaskResult with outcome.
        """
        # Setup SIGINT handler
        original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_sigint)

        try:
            return await self._run_loop(service, max_turns, dry_run)
        finally:
            # Restore original handler
            signal.signal(signal.SIGINT, original_handler)

    async def _run_loop(
        self,
        service: str,
        max_turns: int,
        dry_run: bool,
    ) -> TaskResult:
        """Internal loop implementation."""
        # Get service config
        try:
            config = self._registry.get(service)
        except ServiceNotFoundError as e:
            return TaskResult(
                success=False,
                verified=False,
                reason="mcp_error",
                turns=0,
                error=str(e),
            )

        # Connect to MCP
        try:
            await self._mcp.connect()
        except MCPConnectionError as e:
            return TaskResult(
                success=False,
                verified=False,
                reason="mcp_error",
                turns=0,
                error=f"Failed to connect to MCP: {e}",
            )

        try:
            # Get available tools
            mcp_tools = await self._mcp.list_tools()
            all_tools = get_all_tools(mcp_tools)

            # Navigate to initial URL
            await self._mcp.call_tool("browser_navigate", {"url": config.initial_url})

            # Get initial snapshot
            snapshot_text = await self._mcp.call_tool("browser_snapshot", {})
            snapshot = normalize_snapshot(snapshot_text)

            # Build initial messages
            self._messages = [
                {"role": "system", "content": self._build_system_prompt(config)},
                {"role": "user", "content": f"Current page:\n{snapshot_text}"},
            ]

            # Main loop
            turn = 0
            no_action_count = 0

            while turn < max_turns:
                # Check for shutdown
                if self._shutdown_requested:
                    return TaskResult(
                        success=False,
                        verified=False,
                        reason="human_rejected",
                        turns=turn,
                        final_url=snapshot.url,
                        error="Cancelled by user (SIGINT)",
                    )

                turn += 1
                logger.info(f"Turn {turn}/{max_turns}")

                # Get LLM response
                try:
                    response = await self._llm.invoke(self._messages, all_tools)
                except Exception as e:
                    return TaskResult(
                        success=False,
                        verified=False,
                        reason="llm_error",
                        turns=turn,
                        final_url=snapshot.url,
                        error=str(e),
                    )

                # Extract tool call
                tool_calls = getattr(response, "tool_calls", []) or []

                if not tool_calls:
                    # No tool call - prompt LLM
                    no_action_count += 1
                    logger.warning(f"No tool call (count: {no_action_count})")

                    if no_action_count >= MAX_NO_ACTION_COUNT:
                        return TaskResult(
                            success=False,
                            verified=False,
                            reason="llm_no_action",
                            turns=turn,
                            final_url=snapshot.url,
                            error="LLM failed to call tools after 3 prompts",
                        )

                    # Prompt for action (exact match to spec Section 2.4.2)
                    self._messages.append(
                        {
                            "role": "assistant",
                            "content": response.content or "",
                        }
                    )
                    self._messages.append(
                        {
                            "role": "user",
                            "content": "Call a tool or complete_task.",
                        }
                    )
                    continue

                # Reset no_action counter
                no_action_count = 0

                # Take first tool call only (single-tool-per-turn)
                tc_data = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.warning("Multiple tool_calls ignored, using first only")

                tc = ToolCall(
                    id=tc_data.get("id", f"call_{turn}"),
                    name=tc_data.get("name", ""),
                    args=tc_data.get("args", {}),
                )

                logger.info(f"Tool: {tc.name}")

                # Dry run - return proposed action
                if dry_run:
                    return TaskResult(
                        success=True,
                        verified=False,
                        reason="completed",
                        turns=turn,
                        final_url=snapshot.url,
                        error=f"Dry run - would execute: {tc.name}({tc.args})",
                    )

                # Handle virtual tools
                if is_virtual_tool(tc.name):
                    result = await self._handle_virtual_tool(tc, snapshot, config, turn)
                    if isinstance(result, TaskResult):
                        return result
                    tool_result = result
                else:
                    # Check for auth edge case (login, CAPTCHA, MFA) - wait for user
                    auth_type = self._checkpoint.detect_auth_edge_case(snapshot, config)
                    if auth_type:
                        logger.info(f"Auth edge case detected: {auth_type}")
                        completed = await self._checkpoint.wait_for_auth_completion(
                            snapshot, auth_type
                        )
                        if not completed:
                            return TaskResult(
                                success=False,
                                verified=False,
                                reason="human_rejected",
                                turns=turn,
                                final_url=snapshot.url,
                                error=f"User cancelled during {auth_type}",
                            )
                        # Refresh snapshot after auth and skip this tool call
                        try:
                            snapshot_text = await self._mcp.call_tool(
                                "browser_snapshot", {}
                            )
                            snapshot = normalize_snapshot(snapshot_text)
                            # Add snapshot to messages so LLM sees updated state
                            self._messages.append(
                                {
                                    "role": "user",
                                    "content": f"Authentication completed. Current page:\n{snapshot_text}",
                                }
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to refresh snapshot after auth: {e}"
                            )
                        continue  # Skip executing the tool, let LLM decide next action

                    # Check for checkpoint
                    if self._checkpoint.should_checkpoint(tc, snapshot, config):
                        approved = await self._checkpoint.request_approval(tc, snapshot)
                        if not approved:
                            return TaskResult(
                                success=False,
                                verified=False,
                                reason="human_rejected",
                                turns=turn,
                                final_url=snapshot.url,
                            )

                    # Execute MCP tool
                    try:
                        tool_result = await self._execute_mcp_tool(tc)
                    except MCPConnectionError:
                        # Try reconnect once
                        try:
                            await self._mcp.reconnect()
                            tool_result = await self._execute_mcp_tool(tc)
                        except MCPConnectionError:
                            return TaskResult(
                                success=False,
                                verified=False,
                                reason="mcp_error",
                                turns=turn,
                                final_url=snapshot.url,
                                error="MCP connection lost and reconnect failed",
                            )

                # Update messages with tool result
                self._messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [{"id": tc.id, "name": tc.name, "args": tc.args}],
                    }
                )
                self._messages.append(
                    {
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tc.id,
                    }
                )

                # Update snapshot if we called a navigation/action tool
                if tc.name in ["browser_navigate", "browser_click", "browser_type"]:
                    try:
                        snapshot_text = await self._mcp.call_tool(
                            "browser_snapshot", {}
                        )
                        snapshot = normalize_snapshot(snapshot_text)
                    except Exception as e:
                        logger.warning(f"Failed to update snapshot: {e}")

            # Max turns exceeded
            return TaskResult(
                success=False,
                verified=False,
                reason="max_turns_exceeded",
                turns=turn,
                final_url=snapshot.url,
            )

        finally:
            await self._mcp.close()

    async def _execute_mcp_tool(self, tc: ToolCall) -> str:
        """Execute an MCP tool with error handling.

        Args:
            tc: Tool call to execute.

        Returns:
            Tool result string.

        Raises:
            MCPConnectionError: If connection lost.
        """
        try:
            return await self._mcp.call_tool(tc.name, tc.args)
        except MCPToolError as e:
            # Tool error - return formatted error to LLM
            return f'{{"error": true, "message": "{str(e)}"}}'

    async def _handle_virtual_tool(
        self,
        tc: ToolCall,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig,
        turn: int,
    ) -> TaskResult | str:
        """Handle virtual tool execution.

        Args:
            tc: Tool call.
            snapshot: Current snapshot.
            config: Service config.
            turn: Current turn number.

        Returns:
            TaskResult if task complete, or tool result string.
        """
        if tc.name == "complete_task":
            return await self._handle_complete_task(tc, snapshot, config, turn)
        elif tc.name == "request_human_approval":
            return await self._handle_human_approval(tc, snapshot, turn)
        else:
            return f'{{"error": true, "message": "Unknown virtual tool: {tc.name}"}}'

    async def _handle_complete_task(
        self,
        tc: ToolCall,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig,
        turn: int,
    ) -> TaskResult | str:
        """Handle complete_task virtual tool.

        Args:
            tc: Tool call with status and reason.
            snapshot: Current snapshot.
            config: Service config.
            turn: Current turn number.

        Returns:
            TaskResult if accepted, or error string for retry.
        """
        status = tc.args.get("status", "")
        reason = tc.args.get("reason", "")

        if status == "failed":
            return TaskResult(
                success=False,
                verified=False,
                reason="completed",
                turns=turn,
                final_url=snapshot.url,
                error=reason,
            )

        # status == "success" - verify completion
        verified = self._verify_completion(snapshot, config)

        if verified:
            return TaskResult(
                success=True,
                verified=True,
                reason="completed",
                turns=turn,
                final_url=snapshot.url,
            )
        else:
            # Not verified - return error to retry
            return (
                '{"error": true, "message": "Completion not verified. '
                'Success indicators not found. Please verify the action completed."}'
            )

    async def _handle_human_approval(
        self,
        tc: ToolCall,
        snapshot: NormalizedSnapshot,
        turn: int,
    ) -> TaskResult | str:
        """Handle request_human_approval virtual tool.

        Args:
            tc: Tool call with action and reason.
            snapshot: Current snapshot.
            turn: Current turn number.

        Returns:
            TaskResult if rejected, or approval confirmation string.
        """
        approved = await self._checkpoint.request_approval(tc, snapshot)

        if not approved:
            return TaskResult(
                success=False,
                verified=False,
                reason="human_rejected",
                turns=turn,
                final_url=snapshot.url,
            )

        return '{"approved": true, "message": "Human approved the action. Proceed."}'

    def _verify_completion(
        self,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig,
    ) -> bool:
        """Verify task completion using success/failure indicators.

        Args:
            snapshot: Current snapshot.
            config: Service config.

        Returns:
            True if success indicators found and no failure indicators.
        """
        # Check failure indicators first
        for indicator in config.failure_indicators:
            try:
                if indicator(snapshot):
                    logger.info(f"Failure indicator matched: {indicator.__name__}")
                    return False
            except Exception as e:
                logger.warning(f"Failure indicator error: {e}")

        # Check success indicators
        for indicator in config.success_indicators:
            try:
                if indicator(snapshot):
                    logger.info(f"Success indicator matched: {indicator.__name__}")
                    return True
            except Exception as e:
                logger.warning(f"Success indicator error: {e}")

        return False

    def _handle_sigint(self, signum: int, frame: object) -> None:
        """Handle SIGINT (Ctrl+C)."""
        logger.info("SIGINT received, requesting shutdown...")
        self._shutdown_requested = True
