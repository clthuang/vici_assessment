# Tasks: AI Browser Orchestration via MCP Tools

## Summary
- **Total Tasks**: 32
- **Phases**: 5 (P0-P4)
- **Parallel Groups**: 8

---

## Phase 0: Foundation & Validation (POC)

### Group 0A: Data Types (Sequential - same file)

#### T0.1: Create mcp_orchestrator package structure
- **File**: `src/subterminator/mcp_orchestrator/__init__.py`
- **Done**: Package importable, `__all__` exports types and exceptions
- **Steps**:
  1. Create `src/subterminator/mcp_orchestrator/` directory
  2. Create `__init__.py` with version and `__all__`
- **Dependencies**: None
- **Test**: `from subterminator.mcp_orchestrator import *` succeeds

#### T0.2: Implement TaskReason and TaskResult
- **File**: `src/subterminator/mcp_orchestrator/types.py`
- **Done**: `TaskResult` dataclass passes instantiation test
- **Steps**:
  1. Define `TaskReason = Literal["completed", "human_rejected", "max_turns_exceeded", "llm_no_action", "llm_error", "mcp_error", "verification_failed"]`
  2. Create `@dataclass TaskResult` with fields: success, verified, reason, turns, final_url, error
- **Dependencies**: T0.1
- **Test**: `TaskResult(success=True, verified=True, reason="completed", turns=5)` creates valid instance

#### T0.3: Implement ToolCall dataclass
- **File**: `src/subterminator/mcp_orchestrator/types.py`
- **Done**: `ToolCall(id="x", name="click", args={})` succeeds
- **Steps**:
  1. Create `@dataclass ToolCall` with fields: id, name, args (not arguments)
- **Dependencies**: T0.2
- **Test**: ToolCall equality and dict conversion work

#### T0.4: Implement NormalizedSnapshot and type aliases
- **File**: `src/subterminator/mcp_orchestrator/types.py`
- **Done**: `NormalizedSnapshot(url="...", title="...", content="...")` succeeds and type aliases defined
- **Steps**:
  1. Create `@dataclass NormalizedSnapshot` with fields: url, title, content, screenshot_path (optional `str | None = None`)
  2. Add type aliases for predicate functions:
     ```python
     # Snapshot-only predicate (for success/failure indicators)
     SnapshotPredicate = Callable[[NormalizedSnapshot], bool]
     # Tool+Snapshot predicate (for checkpoint conditions)
     CheckpointPredicate = Callable[["ToolCall", NormalizedSnapshot], bool]
     ```
  3. Export in `__all__`: `NormalizedSnapshot`, `SnapshotPredicate`, `CheckpointPredicate`
- **Dependencies**: T0.3 (needs ToolCall for forward reference)
- **Test**: Optional screenshot_path defaults to None; type aliases importable

#### T0.5: Implement OrchestratorError hierarchy
- **File**: `src/subterminator/mcp_orchestrator/exceptions.py`
- **Done**: All 6 exception classes defined and inherit correctly
- **Steps**:
  1. Import base class and existing config error:
     ```python
     from subterminator.utils.exceptions import SubTerminatorError, ConfigurationError
     ```
  2. Create `OrchestratorError(SubTerminatorError)` as base for MCP orchestration errors
  3. Create these exceptions inheriting from `OrchestratorError`:
     - `MCPConnectionError` - MCP server connection failures
     - `MCPToolError` - MCP tool execution failures
     - `LLMError` - LLM API failures
     - `CheckpointRejectedError` - Human rejected checkpoint
     - `SnapshotValidationError` - Snapshot parsing failures
     - `ServiceNotFoundError` - Unknown service requested
  4. Re-export `ConfigurationError` in `__all__` for convenience:
     - Note: This is a re-export only (for import convenience), NOT a recreation
     - The actual class lives in `subterminator.utils.exceptions`
     - Do NOT define a new ConfigurationError class here
- **Dependencies**: T0.1
- **Test**: `isinstance(MCPConnectionError("msg"), OrchestratorError)` and `isinstance(MCPConnectionError("msg"), SubTerminatorError)` both True

---

### Group 0B: MCP Connection (P0.2)

#### T0.6: Implement MCPClient.__init__ and _validate_nodejs
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `MCPClient()` validates Node.js >= 18 or raises ConfigurationError
- **Steps**:
  1. Create MCPClient class with `_profile_dir` attribute
  2. Implement `_validate_nodejs()` using subprocess to check `node --version`
  3. Raise `ConfigurationError` with install instructions if Node.js < 18 or missing
- **Dependencies**: T0.5
- **Test**: Mock subprocess to test version detection and error paths

#### T0.7: Implement MCPClient.connect
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `await client.connect()` starts Playwright MCP subprocess
- **Steps**:
  1. **First**: Verify mcp SDK imports work:
     ```python
     from mcp import StdioServerParameters, ClientSession
     from mcp.client.stdio import stdio_client
     from contextlib import AsyncExitStack
     ```
     If import fails: raise `ConfigurationError("mcp package not installed. Run: pip install mcp")` - do NOT auto-install
  2. Use `StdioServerParameters` with command `["npx", "@playwright/mcp@latest", "--user-data-dir", self._profile_dir]`
  3. Create `AsyncExitStack` and store in `self._exit_stack` for lifecycle management
  4. Use `await self._exit_stack.enter_async_context(stdio_client(params))` to get (read, write) streams
  5. Create `ClientSession(read, write)` and store in `_session`
  6. Call `await _session.initialize()`
  7. Raise `MCPConnectionError` on any failure
- **Dependencies**: T0.6
- **Test**: Integration test connects to real Playwright MCP within 10 seconds

#### T0.8: Implement MCPClient.list_tools
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `await client.list_tools()` returns list with `browser_snapshot`
- **Steps**:
  1. Call `_session.list_tools()`
  2. Cache result in `_tools`
  3. Convert to list of dicts
- **Dependencies**: T0.7
- **Test**: Result contains at least: browser_snapshot, browser_click, browser_navigate, browser_type

#### T0.9: Implement MCPClient.close
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `await client.close()` terminates subprocess cleanly
- **Steps**:
  1. Call `await self._exit_stack.aclose()` to exit stdio_client context
     - Note: This automatically terminates the subprocess managed by stdio_client
  2. Set `_session = None` and `_tools = None` to clear state
  3. Set `_exit_stack = None` to indicate closed state
- **Dependencies**: T0.7
- **Test**: No zombie processes after close; repeat connect/close 3 times without leak

---

### Group 0C: Snapshot Parsing (P0.3) - Depends on 0B

#### T0.10: Create snapshot format discovery script
- **File**: `scripts/discover_snapshot_format.py` (temporary - delete after T1.1)
- **Done**: Script logs actual browser_snapshot output to console
- **Note**: This script uses internal `_session` access intentionally for format discovery before `call_tool()` is implemented. Script will be deprecated after T1.1 implements proper `call_tool()`.
- **Steps**:
  1. Create script using raw session calls (call_tool not yet implemented):
     ```python
     import asyncio
     from subterminator.mcp_orchestrator.mcp_client import MCPClient

     async def main():
         client = MCPClient()
         await client.connect()
         tools = await client.list_tools()
         print("=== TOOLS ===")
         for t in tools:
             print(f"  - {t['name']}")

         # TEMPORARY: Use raw session calls (call_tool comes in T1.1)
         # This script will be deprecated after T1.1
         session = client._session

         # Navigate to example.com
         await session.call_tool("browser_navigate", {"url": "https://example.com"})

         # Get snapshot
         result = await session.call_tool("browser_snapshot", {})
         snapshot_text = result.content[0].text if result.content else ""
         print("=== SNAPSHOT OUTPUT ===")
         print(snapshot_text)
         print("=== END SNAPSHOT ===")

         # Get screenshot
         result = await session.call_tool("browser_take_screenshot", {})
         print("=== SCREENSHOT OUTPUT TYPE ===")
         print(type(result.content[0]) if result.content else "empty")

         await client.close()

     if __name__ == "__main__":
         asyncio.run(main())
     ```
  2. Run: `python scripts/discover_snapshot_format.py`
  3. Save output to `tests/fixtures/mcp_snapshots/discovery_output.txt`
  4. Also navigate to https://www.netflix.com/login and save that output for login_page fixture
- **Fallback**: If live capture fails (network issues, site changes), manually create minimal fixtures with this format:
  ```
  ### Page state
  - Page URL: https://example.com
  - Page Title: Example Domain
  - Page Snapshot:
  ```yaml
  - document [ref=@e0]:
    - heading "Example Domain" [ref=@e1]
  ```
- **Dependencies**: T0.8
- **Test**: Script runs without error, output saved to fixture (or fallback created)

#### T0.11: Implement normalize_snapshot parser
- **File**: `src/subterminator/mcp_orchestrator/snapshot.py`
- **Done**: `normalize_snapshot(text)` extracts url, title, content
- **Steps**:
  1. Parse "- Page URL: ..." line with regex: `r"- Page URL: (.+)"`
     - If not found: raise `SnapshotValidationError(f"Could not find Page URL line. Input starts with: {text[:200]}")`
  2. Parse "- Page Title: ..." line with regex: `r"- Page Title: (.+)"`
     - If not found: raise `SnapshotValidationError(f"Could not find Page Title line. Input starts with: {text[:200]}")`
  3. Extract content after "- Page Snapshot:" line
     - If not found: raise `SnapshotValidationError(f"Could not find Page Snapshot section. Input starts with: {text[:200]}")`
  4. Return `NormalizedSnapshot(url=url, title=title, content=content)`
- **Dependencies**: T0.10 (to know actual format)
- **Test**: Unit test with sample markdown text from T0.10; test each error path

#### T0.12: Create snapshot test fixtures
- **File**: `tests/fixtures/mcp_snapshots/example_com.txt`
- **Done**: Fixture files contain real browser_snapshot output from MCP
- **Steps**:
  1. Save example.com output from T0.10 to `example_com.txt`
  2. Update T0.10 script to also navigate to Netflix login page:
     - Navigate to `https://www.netflix.com/login`
     - Capture and save to `netflix_login.txt`
  3. For empty_page fixture, navigate to `about:blank` and save (minimal structure)
  4. All fixtures must come from real MCP output to ensure format consistency
- **Dependencies**: T0.10
- **Test**: `normalize_snapshot()` successfully parses all 3 fixtures

---

### Group 0D: LLM Validation (P0.4) - Parallel with 0B/0C

#### T0.13: Implement LLMClient._resolve_model_name
- **File**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Done**: Model selection follows priority: param > env > default
- **Steps**:
  1. Check `model_name` parameter first
  2. Check `SUBTERMINATOR_MODEL` env var
  3. Default to `claude-sonnet-4-20250514`
- **Dependencies**: T0.5
- **Test**: Unit test with mocked env var

#### T0.14: Implement LLMClient._create_model
- **File**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Done**: Creates ChatAnthropic or ChatOpenAI based on model name
- **Steps**:
  1. If starts with "claude" → ChatAnthropic
  2. If starts with "gpt" → ChatOpenAI
  3. Check for API key, raise ConfigurationError if missing
  4. Else raise ConfigurationError("Unsupported model")
- **Dependencies**: T0.13
- **Test**: Correct model class instantiated

#### T0.15: Implement LLMClient.invoke (basic)
- **File**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Done**: `await client.invoke(messages, tools)` returns AIMessage
- **Steps**:
  1. Bind tools to model
  2. Convert messages with `_convert_messages()`
  3. Call `ainvoke()` with timeout
- **Dependencies**: T0.14
- **Test**: Integration test with Claude API returns tool_calls

#### T0.16: Validate LLM tool_calls format
- **File**: `tests/integration/test_llm_format.py`
- **Done**: Verified Claude and OpenAI tool_calls have name, args, id
- **Steps**:
  1. Send simple tool schema to Claude
  2. Assert response.tool_calls[0] has "name", "args", "id" keys
  3. Repeat for OpenAI
- **Dependencies**: T0.15
- **Test**: Both providers return expected format

---

### Validation Gate Checkpoint
After T0.16, all 6 validation criteria must pass before proceeding to Phase 1.

---

## Phase 1: Core Components

### Group 1A: MCPClient Completion (Parallel with 1B)

#### T1.1: Implement MCPClient.call_tool
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `await client.call_tool("browser_click", {...})` executes tool
- **Steps**:
  1. Call `_session.call_tool(name, arguments)`
  2. Extract text from result.content[0].text
  3. Raise `MCPToolError` on failure
- **Dependencies**: T0.8
- **Test**: Unit test with mocked session

#### T1.2: Implement MCPClient.reconnect
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `await client.reconnect()` recovers from connection loss
- **Steps**:
  1. Call `close()`
  2. Clear `_tools` cache
  3. Call `connect()`
- **Dependencies**: T1.1
- **Test**: Reconnect after simulated connection drop

#### T1.3: Implement MCPClient context manager
- **File**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Done**: `async with MCPClient() as client:` works
- **Steps**:
  1. `__aenter__` calls `connect()`, returns self
  2. `__aexit__` calls `close()`
- **Dependencies**: T1.1
- **Test**: Context manager cleans up on exception

---

### Group 1B: LLMClient Completion (Parallel with 1A)

#### T1.4: Implement LLMClient._convert_messages
- **File**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Done**: Converts dict messages to LangChain message objects
- **Steps**:
  1. Map "system" → SystemMessage
  2. Map "user" → HumanMessage
  3. Map "assistant" → AIMessage with tool_calls
  4. Map "tool" → ToolMessage with tool_call_id
- **Dependencies**: T0.15
- **Test**: Round-trip conversion preserves data

#### T1.5: Implement LLMClient retry logic
- **File**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Done**: Retries 3 times with exponential backoff on failure
- **Steps**:
  1. Wrap invoke in retry loop
  2. Backoff: 1s, 2s, 4s
  3. Raise `LLMError` after all retries exhausted
- **Dependencies**: T1.4
- **Test**: Mock transient failure, verify retry count

#### T1.6: Implement LLMClient 60s timeout
- **File**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Done**: Raises LLMError if call exceeds 60 seconds
- **Steps**:
  1. Use `asyncio.wait_for(ainvoke(), timeout=60)`
  2. Catch `TimeoutError`, raise `LLMError` with message
- **Dependencies**: T1.5
- **Test**: Mock slow response, verify timeout

---

### Group 1C: ServiceConfig (Depends on 0C fixtures)

#### T1.7: Implement ServiceConfig dataclass
- **File**: `src/subterminator/mcp_orchestrator/services/base.py`
- **Done**: ServiceConfig with all fields from design
- **Steps**:
  1. Create services/ subpackage with __init__.py
  2. Define `@dataclass ServiceConfig` with: name, initial_url, goal_template, checkpoint_conditions, success_indicators, failure_indicators, system_prompt_addition, auth_edge_case_detectors
- **Dependencies**: T0.4
- **Test**: ServiceConfig instantiation works

#### T1.8: Implement ServiceRegistry
- **File**: `src/subterminator/mcp_orchestrator/services/registry.py`
- **Done**: `ServiceRegistry.get("netflix")` returns config
- **Steps**:
  1. Class with `_configs: dict[str, ServiceConfig]`
  2. `get(name)` raises `ServiceNotFoundError` if not found
  3. `register(config)` adds to registry
  4. `list_services()` returns names
- **Dependencies**: T1.7
- **Test**: Get unknown service raises ServiceNotFoundError

#### T1.9: Implement NETFLIX_CONFIG
- **File**: `src/subterminator/mcp_orchestrator/services/netflix.py`
- **Done**: Netflix config with all predicates from spec plus design additions
- **Steps**:
  1. Import `CheckpointPredicate`, `SnapshotPredicate` from `..types` (don't redefine)
  2. Define checkpoint predicates that check BOTH tool AND snapshot (per spec Section 2.5.3):
     ```python
     from ..types import ToolCall, NormalizedSnapshot, CheckpointPredicate, SnapshotPredicate

     def is_destructive_click(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
         """Triggers on clicks with finish/confirm/complete keywords (spec 2.5.3)"""
         if tool.name != "browser_click":
             return False
         element = tool.args.get("element", "").lower()
         return any(kw in element for kw in ["finish", "confirm", "complete"])

     def is_final_cancel_page(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
         """Final cancel page has both 'finish' and 'cancel' in content (spec 2.5.3)"""
         return "finish" in snap.content.lower() and "cancel" in snap.content.lower()

     def is_payment_page(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
         """Design addition: protect against accidental payment changes"""
         return "payment" in snap.url.lower() or "billing" in snap.content.lower()

     NETFLIX_CHECKPOINT_CONDITIONS: list[CheckpointPredicate] = [
         is_destructive_click, is_final_cancel_page, is_payment_page
     ]
     ```
     Note: `is_payment_page` is a design addition (not in spec 2.5.3) for extra safety on billing pages.
  3. Define `NETFLIX_SUCCESS_INDICATORS` (snapshot-only predicates):
     - `has_cancellation_confirmed`, `has_membership_ended`, `has_restart_option`, `has_billing_stopped`
  4. Define `NETFLIX_FAILURE_INDICATORS` (snapshot-only predicates):
     - `has_error_message`, `has_try_again`, `has_login_required`, `has_session_expired`
  5. Define `AUTH_EDGE_CASE_DETECTORS` (snapshot-only predicates):
     - `is_login_page`, `is_captcha_page`, `is_mfa_page`
  6. Create `NETFLIX_CONFIG = ServiceConfig(...)`
  7. Register in default registry
- **Dependencies**: T1.8, T0.12 (fixtures)
- **Test**: Predicates match expected text patterns from fixtures

---

### Group 1D: CheckpointHandler (Depends on 1A, 1C)

#### T1.10: Implement CheckpointHandler.should_checkpoint
- **File**: `src/subterminator/mcp_orchestrator/checkpoint.py`
- **Done**: Returns True if any condition matches
- **Steps**:
  1. Create CheckpointHandler class with constructor:
     ```python
     def __init__(self, mcp: MCPClient, disabled: bool = False):
         self._mcp = mcp  # for _capture_screenshot() in T1.11
         self._disabled = disabled  # --no-checkpoint flag
     ```
  2. Implement `should_checkpoint(tool: ToolCall, snapshot: NormalizedSnapshot, config: ServiceConfig) -> bool`:
     - If `self._disabled`, return False immediately
     - Iterate `config.checkpoint_conditions`, return True if any predicate(tool, snapshot) returns True
     - Iterate `config.auth_edge_case_detectors`, return True if any predicate(snapshot) returns True
     - Return False otherwise
- **Dependencies**: T1.9
- **Test**: Test with Netflix conditions against fixture snapshots

#### T1.11: Implement CheckpointHandler._capture_screenshot
- **File**: `src/subterminator/mcp_orchestrator/checkpoint.py`
- **Done**: Calls browser_take_screenshot, saves to temp file
- **Steps**:
  1. Call `_mcp.call_tool("browser_take_screenshot", {})`
  2. Decode base64 data if present
  3. Save to temp file with subterminator_checkpoint_ prefix
  4. Return path or None on error
- **Dependencies**: T1.1
- **Test**: Mock MCP returns base64, verify file created

#### T1.12: Implement CheckpointHandler.request_approval
- **File**: `src/subterminator/mcp_orchestrator/checkpoint.py`
- **Done**: Displays info and returns True/False based on input
- **Steps**:
  1. Call `_capture_screenshot()`
  2. Call `_display_checkpoint_info(tool_call, snapshot, screenshot_path)`
  3. Implement `_get_user_input()` using `input()` builtin - return True if response starts with 'y'
- **Dependencies**: T1.11
- **Test**: Use `unittest.mock.patch('builtins.input')` to mock stdin:
  ```python
  from unittest.mock import patch

  @patch('builtins.input', return_value='y')
  def test_approval_yes(mock_input):
      assert handler.request_approval(tool, snap) == True

  @patch('builtins.input', return_value='n')
  def test_approval_no(mock_input):
      assert handler.request_approval(tool, snap) == False
  ```

---

## Phase 2: Orchestration Loop

### Group 2A: Virtual Tools (Can start early)

#### T2.1: Define VIRTUAL_TOOLS schemas
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: complete_task and request_human_approval schemas defined
- **Steps**:
  1. Create `VIRTUAL_TOOLS` dict with schemas matching spec Section 2.3
  2. complete_task: status (enum success/failed), reason
  3. request_human_approval: action, reason
- **Dependencies**: T0.2
- **Test**: Schemas validate against spec

#### T2.2: Implement tool merging
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: `get_all_tools(mcp_tools)` returns merged list
- **Steps**:
  1. Concatenate MCP tools + VIRTUAL_TOOLS values
  2. Implement `is_virtual_tool(name)` check
- **Dependencies**: T2.1
- **Test**: Merged list contains both MCP and virtual tools

---

### Group 2B: TaskRunner Core (Depends on all P1)

#### T2.3: Implement TaskRunner.__init__
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: TaskRunner initializes with all dependencies
- **Steps**:
  1. Accept mcp_client, llm_client, service_registry, disable_checkpoints
  2. Create CheckpointHandler with mcp_client
- **Dependencies**: T1.3, T1.6, T1.8, T1.12
- **Test**: Constructor succeeds with mock dependencies

#### T2.4: Implement TaskRunner._build_system_prompt
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Generates system prompt with service-specific addition
- **Steps**:
  1. Build base prompt with tool descriptions and rules
  2. Append `config.system_prompt_addition`
- **Dependencies**: T2.3
- **Test**: Prompt contains Netflix-specific instructions

#### T2.5: Implement TaskRunner.run (skeleton)
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Run method with initial setup and loop structure
- **Steps**:
  1. Get service config
  2. Connect MCP, list tools
  3. Navigate to initial_url, get snapshot
  4. Build initial messages
  5. Loop structure: Initialize `turn = 0`, increment at loop start, exit when `turn >= max_turns`
- **Dependencies**: T2.4
- **Test**: Mock run reaches loop, returns max_turns_exceeded

#### T2.6: Implement message history management
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Messages append correctly after each turn
- **Steps**:
  1. Append assistant message with tool_calls
  2. Append tool result message
  3. Enforce single-tool-per-turn (extract first only)
- **Dependencies**: T2.5
- **Test**: History grows by 2 messages per turn

#### T2.7: Implement no-action counter
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Returns llm_no_action after 3 empty responses
- **Steps**:
  1. Track `no_action_count` (initialize to 0)
  2. Increment if `response.tool_calls` is empty or None
  3. Append user message: "Call a tool or complete_task." (exact match to spec Section 2.4.2)
  4. Return `TaskResult(success=False, verified=False, reason="llm_no_action", turns=turn)` after count reaches 3
- **Dependencies**: T2.6
- **Test**:
  ```python
  # Mock LLM to return no tool_calls 3 times
  mock_llm.invoke.return_value = AIMessage(content="I understand the task", tool_calls=[])

  result = await runner.run("netflix", max_turns=10)

  # Verify prompt messages were added
  user_messages = [m for m in runner._messages if m.get("role") == "user"]
  prompt_messages = [m for m in user_messages if "Call a tool or complete_task" in m.get("content", "")]
  assert len(prompt_messages) == 3

  # Verify final result
  assert result.reason == "llm_no_action"
  assert result.success == False
  ```

---

### Group 2C: Virtual Tool Handlers (Depends on 2B)

#### T2.8: Implement _handle_complete_task
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Handles success/failed status with verification
- **Steps**:
  1. If status="failed", return TaskResult immediately
  2. If status="success", call `_verify_completion()`
  3. If verified, return TaskResult(success=True)
  4. If not verified, return error dict for retry
- **Dependencies**: T2.5
- **Test**: Verification failure returns error dict, not TaskResult

#### T2.9: Implement _verify_completion
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Checks success/failure indicators
- **Steps**:
  1. Check failure_indicators first, return False if any match
  2. Check success_indicators, return True if any match
  3. Return False otherwise
- **Dependencies**: T2.8
- **Test**: Netflix indicators match expected patterns

#### T2.10: Implement checkpoint triggering
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Checkpoint requested before MCP tool execution
- **Steps**:
  1. Before executing MCP tool, call `_checkpoint.should_checkpoint(tc, snapshot, config)`
  2. If True, call `request_approval(tc, snapshot)`
  3. If rejected (returns False), return `TaskResult(success=False, verified=False, reason="human_rejected", turns=turn)`
  4. If approved, continue with tool execution
- **Dependencies**: T2.5, T1.12
- **Test**: Use inline mock snapshots (not file fixtures) for test clarity:
  ```python
  # Test 1: Checkpoint triggers on finality keywords
  snap_cancel = NormalizedSnapshot(url="/cancel", title="Cancel", content="finish your cancellation")
  tool_click = ToolCall(id="1", name="browser_click", args={"element": "Finish Cancellation"})
  assert checkpoint.should_checkpoint(tool_click, snap_cancel, NETFLIX_CONFIG) == True

  # Test 2: No trigger when tool is not browser_click
  tool_snapshot = ToolCall(id="2", name="browser_snapshot", args={})
  assert checkpoint.should_checkpoint(tool_snapshot, snap_cancel, NETFLIX_CONFIG) == False

  # Test 3: No trigger when element lacks finality keywords
  snap_browse = NormalizedSnapshot(url="/browse", title="Browse", content="movies")
  tool_next = ToolCall(id="3", name="browser_click", args={"element": "Next"})
  assert checkpoint.should_checkpoint(tool_next, snap_browse, NETFLIX_CONFIG) == False

  # Test 4: Human rejection returns correct TaskResult
  # Mock _get_user_input() to return 'n', verify reason="human_rejected"
  ```

---

### Group 2D: Error Recovery (Depends on 2B)

#### T2.11: Implement MCPToolError recovery
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Tool errors formatted and returned to LLM
- **Steps**:
  1. Catch MCPToolError in tool execution
  2. Format as `{"error": True, "message": str(e)}`
  3. Continue loop
- **Dependencies**: T2.5
- **Test**: Mock tool failure, verify loop continues

#### T2.12: Implement MCPConnectionError recovery
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Reconnect attempted once on connection loss
- **Steps**:
  1. Catch MCPConnectionError
  2. Try `reconnect()` once
  3. If reconnect fails, return TaskResult(reason="mcp_error")
- **Dependencies**: T2.11, T1.2
- **Test**: Simulated connection drop, verify reconnect attempt

#### T2.13: Implement SIGINT handling
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Ctrl+C terminates gracefully
- **Steps**:
  1. Register SIGINT handler at run() start
  2. Set `shutdown_requested` flag
  3. Check flag in loop, return TaskResult if set
  4. Restore original handler in finally block
- **Dependencies**: T2.5
- **Test**: Send SIGINT, verify cleanup

#### T2.14: Implement dry-run mode
- **File**: `src/subterminator/mcp_orchestrator/task_runner.py`
- **Done**: Returns after first action without executing
- **Steps**:
  1. Add `dry_run` parameter to run()
  2. If dry_run and tool_call received, return TaskResult with action info
  3. Don't execute the tool
- **Dependencies**: T2.5
- **Test**: Dry run returns proposed action string

---

## Phase 3: CLI Integration

### Group 3A: CLI Command

#### T3.1: Add --auto flag to cancel command
- **File**: `src/subterminator/cli/main.py`
- **Done**: `subterminator cancel --service netflix --auto` works
- **Steps**:
  1. **First**: Review existing cancel command in `src/subterminator/cli/main.py`:
     - Verify `--auto` doesn't conflict with existing options
     - Note: Existing CLI uses `-v/--version` at app level and `-V/--verbose` for verbose output
     - Check if `--dry-run` and `--verbose` exist (reuse if available)
     - Note return type and error handling patterns
  2. Add `auto: bool = typer.Option(False, "--auto", help="Use AI-driven MCP orchestration")`
     - Note: No short form for --auto to avoid conflicts with existing flags
  3. If auto is True:
     - Import TaskRunner from mcp_orchestrator
     - Create and run TaskRunner with asyncio.run()
  4. Else, use existing manual flow unchanged
- **Dependencies**: T2.14
- **Test**: `--auto` flag parsed correctly; without `--auto`, existing behavior preserved

#### T3.2: Add MCP orchestration options
- **File**: `src/subterminator/cli/main.py`
- **Done**: --model, --max-turns, --no-checkpoint options work when --auto is used
- **Steps**:
  1. Add new options (only relevant when --auto is used):
     - `model: str = typer.Option(None, "--model", help="LLM model override")`
     - `max_turns: int = typer.Option(20, "--max-turns", help="Maximum orchestration turns")`
     - `no_checkpoint: bool = typer.Option(False, "--no-checkpoint", help="Disable human checkpoints")`
  2. **Note**: Existing `-V/--verbose` and `--dry-run/-n` should be reused if already present
  3. Pass options to TaskRunner when --auto is active
- **Dependencies**: T3.1
- **Test**: Options passed through to TaskRunner

---

### Group 3B: Exit Codes (Parallel with 3C after 3A)

#### T3.3: Implement exit codes
- **File**: `src/subterminator/cli/main.py`
- **Done**: Correct exit codes for all scenarios when --auto is used
- **Note**: Existing CLI uses: 1=failure, 2=aborted, 3=unknown service, 4=config error. The --auto mode uses its own exit codes that are active ONLY when --auto flag is set:
- **Steps**:
  1. Exit 0 on TaskResult.success=True
  2. Exit 1 on TaskResult.success=False (task failure)
  3. Exit 2 on ConfigurationError (e.g., missing API key, bad model name)
  4. Exit 5 on MCPConnectionError (use 5 to avoid conflict with existing code 3)
  5. Exit 130 on SIGINT (standard Unix convention)
- **Dependencies**: T3.2
- **Test**: Each exit code verified with --auto flag

---

### Group 3C: Output (Parallel with 3B)

#### T3.4: Implement turn-by-turn output
- **File**: `src/subterminator/cli/main.py`
- **Done**: Shows `[Turn N] tool_name` for each turn
- **Steps**:
  1. Create progress callback or async generator
  2. Print turn info as orchestration progresses
- **Dependencies**: T3.2
- **Test**: Output format matches spec

#### T3.5: Implement verbose mode
- **File**: `src/subterminator/cli/main.py`
- **Done**: Verbose output (-V/--verbose) shows full snapshot and arguments
- **Steps**:
  1. Reuse existing `-V/--verbose` flag from CLI
  2. If verbose, print snapshot content and tool arguments each turn
- **Dependencies**: T3.4
- **Test**: Verbose output contains snapshot content

---

## Phase 4: Integration Testing

#### T4.1: MCP + Mock LLM integration test
- **File**: `tests/integration/test_mcp_orchestration.py`
- **Done**: Full loop with real MCP, mock LLM responses
- **Steps**:
  1. Start real Playwright MCP (use pytest fixture with `scope="function"` for test isolation)
  2. Mock LLM with predefined tool_calls sequences:
     ```python
     # Create mock responses inline in each test
     mock_responses = [
         AIMessage(content="", tool_calls=[{"id": "1", "name": "browser_navigate", "args": {"url": "..."}}]),
         AIMessage(content="", tool_calls=[{"id": "2", "name": "browser_snapshot", "args": {}}]),
         AIMessage(content="", tool_calls=[{"id": "3", "name": "complete_task", "args": {"status": "success"}}]),
     ]
     mock_llm = Mock()
     mock_llm.invoke.side_effect = mock_responses
     ```
  3. Run TaskRunner with mock LLM
  4. Verify checkpoints trigger correctly
- **Dependencies**: T2.14
- **Test**: Must test these scenarios (each with fresh MCP connection):
  - Happy path: Navigate → snapshot → complete_task(success) → verified
  - Checkpoint trigger: Navigate to page with finality keywords → checkpoint fires
  - Error recovery: MCPToolError → error returned to LLM → continues
  - Max turns: Loop until max_turns → returns max_turns_exceeded

#### T4.2: LLM Provider integration test (P4.2)
- **File**: `tests/integration/test_llm_integration.py`
- **Done**: Real Claude and OpenAI API calls return parseable tool_calls
- **Note**: Mark with `@pytest.mark.slow` - requires `--run-slow` flag to execute
- **Steps**:
  1. Test real Claude API with tool schema:
     ```python
     @pytest.mark.slow
     def test_claude_tool_calls():
         client = LLMClient(model_name="claude-sonnet-4-20250514")
         tools = [{"name": "test_tool", "description": "...", "parameters": {...}}]
         response = await client.invoke(messages, tools)
         assert response.tool_calls is not None
         assert "name" in response.tool_calls[0]
         assert "args" in response.tool_calls[0]
         assert "id" in response.tool_calls[0]
     ```
  2. Test real OpenAI API with same schema (if OPENAI_API_KEY set)
  3. Verify tool_calls format matches expected: `{name: str, args: dict, id: str}`
- **Dependencies**: T0.16
- **Test**: Both providers return tool_calls with correct structure

#### T4.3: CLI integration test
- **File**: `tests/integration/test_cli_integration.py`
- **Done**: CLI runs with mock LLM, correct exit codes
- **Steps**:
  1. Use subprocess to run CLI with `--auto` flag
  2. Set environment variables to control mock behavior (e.g., `SUBTERMINATOR_TEST_MODE=1`)
  3. Verify exit codes and output format
- **Dependencies**: T3.5
- **Test**: Must test these exit codes (use pytest fixture with `scope="function"`):
  - Exit 0: TaskResult.success=True
  - Exit 1: TaskResult.success=False
  - Exit 2: ConfigurationError (unset ANTHROPIC_API_KEY)
  - Exit 5: MCPConnectionError (mock Node.js not found)
  - Exit 130: SIGINT (send signal during execution)
- **Note**: Exit codes for --auto mode differ from non-auto. Document in CLI help: "Exit codes with --auto: 0=success, 1=failure, 2=config error, 5=MCP connection error, 130=interrupted"

---

## Parallel Groups Summary

| Group | Tasks | Can Start After |
|-------|-------|-----------------|
| 0A | T0.1-T0.5 | Immediately |
| 0B | T0.6-T0.9 | T0.5 |
| 0C | T0.10-T0.12 | T0.8 |
| 0D | T0.13-T0.16 | T0.5 (parallel with 0B/0C) |
| 1A | T1.1-T1.3 | T0.8 |
| 1B | T1.4-T1.6 | T0.15 (T1.4 can run parallel with T1.5-T1.6) |
| 1C | T1.7-T1.9 | T0.4 (T1.7-T1.8), T0.12 (T1.9 only) |
| 1D | T1.10-T1.12 | T1.1, T1.9 |
| 2A | T2.1-T2.2 | T0.2 |
| 2B | T2.3-T2.7 | T1.3, T1.6, T1.8, T1.12 |
| 2C | T2.8-T2.10 | T2.5 |
| 2D | T2.11-T2.14 | T2.5 |
| 3A | T3.1-T3.2 | T2.14 |
| 3B | T3.3 | T3.2 |
| 3C | T3.4-T3.5 | T3.2 |
| 4A | T4.1 | T2.14 |
| 4B | T4.2 | T0.16 (can run parallel with T4.1) |
| 4C | T4.3 | T3.5 |
