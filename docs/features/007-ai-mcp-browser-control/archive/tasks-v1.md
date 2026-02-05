# Tasks: AI-Led MCP Browser Control Redesign

## Overview

Tasks for Feature 007, broken down from plan.md. Each task is 5-15 minutes of focused work.

**Total**: 52 tasks across 7 phases, 12 parallel groups

---

## Phase 0: Validation Infrastructure & Hypothesis Testing

### Group 0A: Foundation Types (sequential within types.py)

**Note**: T0.1-T0.5 all modify types.py. Execute sequentially: T0.1 creates file, T0.2-T0.4 append to it.

#### T0.1: Create types.py with BoundingBox and ElementInfo
**File**: `src/subterminator/mcp/types.py`
**Do**:
- Create `BoundingBox` dataclass with x, y, width, height fields
- Add `center()` method returning (x + width//2, y + height//2)
- Create `ElementInfo` dataclass with ref, role, name, state, bbox, value, level, selector, children fields
**Done when**: Both classes exist with type hints; center() returns correct tuple

#### T0.2: Create types.py with PageInfo, ViewportInfo, Snapshot
**File**: `src/subterminator/mcp/types.py`
**Do**:
- Add `PageInfo` dataclass with url, title
- Add `ViewportInfo` dataclass with width, height, scroll_x, scroll_y
- Add `Snapshot` dataclass with snapshot_id, timestamp, elements, focused, page, screenshot, viewport
- Add `to_dict()` method to Snapshot
**Done when**: All classes exist; to_dict() produces JSON-serializable dict

#### T0.3: Create types.py with Message, ToolCall, AIResponse
**File**: `src/subterminator/mcp/types.py`
**Do**:
- Add `Message` dataclass with role (Literal), content, tool_calls, tool_call_id
- Add `ToolCall` dataclass with id, name, arguments
- Add `AIResponse` dataclass with content, tool_calls, stop_reason
**Done when**: All classes exist with proper Literal types

#### T0.4: Create types.py with ToolResult, TaskResult, ErrorCode
**File**: `src/subterminator/mcp/types.py`
**Do**:
- Add `ErrorCode` type alias for Literal of all error codes
- Add `ToolResult` dataclass with success, snapshot, error, message, to_dict()
- Add `TaskResult` dataclass with success, reason, turns, final_snapshot
- Add `CompletionCriteria` dataclass with success_indicators, failure_indicators
**Done when**: All types exist; ToolResult.to_dict() works

#### T0.5: Create exceptions.py with all MCP exceptions
**File**: `src/subterminator/mcp/exceptions.py`
**Do**:
- Create `MCPError` base exception
- Create `RefInvalidError(ref)` with message
- Create `ElementDisabledError(ref)` with message
- Create `ElementObscuredError(ref, obscuring_element)` with message
- Create `TimeoutError(operation, timeout_ms)` with message
- Create `InvalidParamsError(tool, message)` with message
**Done when**: All exceptions exist with proper __init__ and messages

#### T0.6: Create test_types.py with serialization tests
**File**: `tests/unit/mcp/test_types.py`
**Do**:
- Test BoundingBox.center() returns correct values
- Test Snapshot.to_dict() produces valid JSON
- Test ToolResult.to_dict() includes all fields
**Done when**: All tests pass

### Group 0B: Protocols and Schemas (depends on 0A)

#### T0.7: Create protocols.py with AIClientProtocol
**File**: `src/subterminator/mcp/protocols.py`
**Do**:
- Import Protocol from typing
- Define `AIClientProtocol` with chat() method signature
- Type hints use Message, ToolCall, AIResponse from types.py
**Done when**: Protocol is importable and type-checkable

#### T0.8: Create protocols.py with HumanApprovalHandler
**File**: `src/subterminator/mcp/protocols.py`
**Do**:
- Add `HumanApprovalHandler` protocol
- Define request_approval(action, reason, screenshot) -> tuple[bool, str|None]
**Done when**: Protocol exists with correct signature

#### T0.9: Create tool_schemas.py with TOOL_SCHEMAS
**File**: `src/subterminator/mcp/tool_schemas.py`
**Do**:
- Create TOOL_SCHEMAS list with all 7 tool definitions
- Each tool has name, description, input_schema
- Include WHEN TO USE, COMMON PATTERNS, ERROR CONDITIONS in descriptions
**Done when**: TOOL_SCHEMAS has 7 entries; each has required fields

#### T0.10: Create test_tool_schemas.py
**File**: `tests/unit/mcp/test_tool_schemas.py`
**Do**:
- Test each schema has name, description, input_schema
- Test required fields are specified
- Test ref pattern is ^@e\d+$
**Done when**: All schema validations pass

### Group 0C: Mock Browser (depends on 0A)

#### T0.11: Create mock_browser.py with MockPlaywrightBrowser class
**File**: `src/subterminator/mcp/testing/mock_browser.py`
**Do**:
- Create `MockPlaywrightBrowser` class
- Add __init__ taking list of snapshots to return
- Add snapshot_index to track position
**Done when**: Class is instantiable with snapshot list

#### T0.12: Add accessibility_tree() and screenshot() to mock
**File**: `src/subterminator/mcp/testing/mock_browser.py`
**Do**:
- Add `accessibility_tree()` returning current snapshot's a11y data
- Add `screenshot()` returning bytes
- Add `viewport_size()` returning ViewportInfo
**Done when**: Methods return appropriate mock data

#### T0.13: Add url(), title() to mock
**File**: `src/subterminator/mcp/testing/mock_browser.py`
**Do**:
- Add `url()` returning current snapshot's URL
- Add `title()` returning current snapshot's title
**Done when**: Methods return correct values from snapshot

#### T0.14: Add action methods to mock (click, fill, select, scroll)
**File**: `src/subterminator/mcp/testing/mock_browser.py`
**Do**:
- Add `click(selector, timeout)` that advances snapshot_index
- Add `fill(selector, value, timeout)`
- Add `select_option(selector, value, timeout)`
- Add `scroll(direction, amount)` or `scroll_into_view(selector)`
- Add action_log list to record calls
**Done when**: All action methods exist and log calls

#### T0.15: Add error scripting to mock
**File**: `src/subterminator/mcp/testing/mock_browser.py`
**Do**:
- Add `script_error(action_index, error)` method
- When scripted, action at index raises the error
- Otherwise returns normally
**Done when**: Can script mock to raise errors at specific actions

#### T0.16: Create test_mock_browser.py
**File**: `tests/unit/mcp/test_mock_browser.py`
**Do**:
- Test snapshots are returned in order
- Test actions advance snapshot index
- Test action_log records calls
- Test scripted errors are raised
**Done when**: All mock behavior tests pass

### Group 0D: Fixtures (depends on 0A)

#### T0.17: Create snapshot_schema.json
**File**: `tests/fixtures/mcp/snapshot_schema.json`
**Do**:
- JSON Schema for Snapshot validation
- Include all required fields: snapshot_id, timestamp, elements, page, screenshot, viewport
- Element array with ref pattern ^@e\d+$
- State enum values per spec 1.3.4: "visible", "hidden", "offscreen", "enabled", "disabled", "readonly", "checked", "unchecked", "mixed", "expanded", "collapsed", "focused", "busy"
**Done when**: Schema validates example snapshots; jsonschema library can validate against it

#### T0.18: Create netflix_account_active.json fixture
**File**: `tests/fixtures/mcp/snapshots/netflix_account_active.json`
**Do**:
- Snapshot of Netflix account page before cancellation
- Include "Cancel Membership" button as interactive element
- ~20 realistic elements
**Done when**: Valid JSON matching schema

#### T0.19: Create netflix_cancel_page.json fixture
**File**: `tests/fixtures/mcp/snapshots/netflix_cancel_page.json`
**Do**:
- Snapshot of cancellation start page
- Include checkbox and continue button
- Elements in expanded section
**Done when**: Valid JSON matching schema

#### T0.20: Create netflix_retention_offer.json fixture
**File**: `tests/fixtures/mcp/snapshots/netflix_retention_offer.json`
**Do**:
- Snapshot with retention offer
- "No thanks" and "Accept offer" buttons
**Done when**: Valid JSON matching schema

#### T0.21: Create netflix_confirmation.json fixture
**File**: `tests/fixtures/mcp/snapshots/netflix_confirmation.json`
**Do**:
- Final confirmation page
- "Finish Cancellation" button triggering checkpoint
**Done when**: Valid JSON matching schema

#### T0.22: Create netflix_cancelled.json fixture
**File**: `tests/fixtures/mcp/snapshots/netflix_cancelled.json`
**Do**:
- Success page after cancellation
- Heading with "cancelled" text
**Done when**: Valid JSON matching schema

#### T0.23: Create test_fixtures.py
**File**: `tests/unit/mcp/test_fixtures.py`
**Do**:
- Load each fixture
- Validate against snapshot_schema.json
**Done when**: All fixtures pass schema validation

### Group 0E: Minimal Validation Components (depends on 0A-0D)

#### T0.24: Create minimal ElementRegistry for validation
**File**: `src/subterminator/mcp/validation/registry.py`
**Do**:
- Create `MinimalElementRegistry` class
- Implement `register_snapshot(elements)` assigning refs as @e0, @e1, @e2... using depth-first traversal order of input list. Reset counter to 0 on each register_snapshot() call.
- Implement `resolve(ref)` returning element or raising RefInvalidError
**Done when**: Can register and resolve refs; refs start at @e0 and increment

#### T0.25: Create minimal BrowserToolServer for validation
**File**: `src/subterminator/mcp/validation/tool_server.py`
**Do**:
- Create `MinimalBrowserToolServer` class
- Implement `get_snapshot()` returning ToolResult
- Implement `browser_click(ref)` executing click and returning fresh snapshot
- Use MinimalElementRegistry
**Done when**: get_snapshot and browser_click work with mock browser

#### T0.26: Create minimal TaskOrchestrator for validation
**File**: `src/subterminator/mcp/validation/orchestrator.py`
**Do**:
- Create `MinimalTaskOrchestrator` class
- Implement `run(goal)` with conversation loop
- Single tool per turn enforcement
- Max turns limit (default 20)
- No human checkpoints (testing mode)
**Done when**: Can run conversation loop with mock AI

#### T0.27: Create real AIClient for validation
**File**: `src/subterminator/mcp/validation/ai_client.py`
**Do**:
- Create `ValidationAIClient` class
- Use model `claude-sonnet-4-20250514`, read API key from `ANTHROPIC_API_KEY` env var, set max_tokens=4096
- Connect to real Claude API (anthropic SDK)
- Format messages for API
- Parse tool_calls from response
**Done when**: Can make API calls and get tool calls back; raises clear error if ANTHROPIC_API_KEY not set

#### T0.28: Create test for minimal components
**File**: `tests/unit/mcp/test_validation_components.py`
**Do**:
- Test MinimalElementRegistry ref assignment
- Test MinimalBrowserToolServer get_snapshot
- Test MinimalTaskOrchestrator loop with mock AI
**Done when**: Minimal components work together

### Group 0F: Validation Harness (depends on 0E)

#### T0.29: Create validation harness
**File**: `src/subterminator/mcp/validation/harness.py`
**Do**:
- Create `ValidationHarness` class
- Load Netflix fixtures in order: account_active → cancel_page → retention_offer → confirmation → cancelled
- Run scenario with mock browser and real AI
- Use goal: "Cancel Netflix subscription by clicking through the cancellation flow. Call complete_task when you see confirmation that membership is cancelled."
- Collect metrics: success/failure, turns, failure mode
- Handle API errors by recording as failure mode "api_error"
**Done when**: Can run single scenario and get metrics dict with keys: success, turns, failure_mode

#### T0.30: Add batch execution to harness
**File**: `src/subterminator/mcp/validation/harness.py`
**Do**:
- Add `run_batch(n_scenarios)` method
- Run n=20 scenarios using the same fixtures but with fresh AI conversation each time (no variations in fixtures - we test determinism of AI behavior)
- Aggregate metrics (success rate, avg turns, failure mode distribution)
- Output to CSV with columns: scenario_id, success, turns, failure_mode, timestamp
**Done when**: Can run 20 scenarios and get summary stats; CSV file created

#### T0.31: Add CLI entry point for validation
**File**: `src/subterminator/mcp/validation/__main__.py`
**Do**:
- Add main() to run harness
- Command line args: --scenarios N, --output PATH
- Print summary to console
**Done when**: `python -m subterminator.mcp.validation --scenarios 20` works

### Group 0G: Validation Gate (manual, depends on 0F)

#### T0.32: Run Phase 0 validation [MANUAL]
**No file** - manual execution
**Do**:
- Run `python -m subterminator.mcp.validation --scenarios 20`
- Collect CSV output
- Analyze success rate and failure modes
**Done when**: Have metrics CSV file

#### T0.33: Document validation results
**File**: `docs/features/007-ai-mcp-browser-control/validation-report.md`
**Do**:
- Record success rate
- Document common failure modes
- Record decision: PROCEED / ITERATE / STOP
**Done when**: Report exists with decision

---

## VALIDATION GATE

**STOP**: If success rate <50%, do not proceed to Phase 1.
**ITERATE**: If 50-70%, revise tool descriptions (T0.9) and re-run (T0.32).
**PROCEED**: If >70%, continue to Phase 1.

---

## Phase 1: Core Components (Production)

**Prerequisite**: Phase 0 validation passed (>70%)

### Group 1A: ElementRegistry (depends on Phase 0)

#### T1.1: Write ElementRegistry tests
**File**: `tests/unit/mcp/test_registry.py`
**Do**:
- Test ref assignment follows @e{N} pattern
- Test refs invalidated after new snapshot
- Test resolve() raises RefInvalidError for unknown refs
- Test list_refs() returns all valid refs
**Done when**: Tests written (will fail - no implementation yet)

#### T1.2: Implement ElementRegistry
**File**: `src/subterminator/mcp/registry.py`
**Do**:
- Create `ElementRegistry` class
- Implement register_snapshot(): assigns @e0, @e1, @e2... using depth-first order of input list; counter resets to 0 on each call
- Implement resolve(ref): returns ElementInfo or raises RefInvalidError
- Implement invalidate(): clears all refs
- Implement list_refs(): returns all valid refs
- Add snapshot_id property
**Done when**: All T1.1 tests pass; refs start at @e0 for each new snapshot (counter resets)

### Group 1B: SnapshotFactory (depends on Phase 0)

#### T1.3: Write SnapshotFactory tests
**File**: `tests/unit/mcp/test_snapshot.py`
**Do**:
- Test pruning rules (roles, depth, count)
- Test name truncation at 200 chars
- Test max 100 elements
- Test bbox from a11y tree
- Test bbox fallback
**Done when**: Tests written

#### T1.4: Implement SnapshotFactory create()
**File**: `src/subterminator/mcp/snapshot.py`
**Do**:
- Create `SnapshotFactory` class with browser dependency
- Implement `create(viewport_only)` returning (Snapshot, list[ElementInfo])
- Extract elements from accessibility tree
- Capture and encode screenshot as base64
**Done when**: create() returns valid (Snapshot, list[ElementInfo]) tuple; tests for creation, a11y extraction, and screenshot encoding pass

#### T1.5: Implement SnapshotFactory pruning
**File**: `src/subterminator/mcp/snapshot.py`
**Do**:
- Add INTERACTIVE_ROLES, LANDMARK_ROLES constants
- Implement `_should_include(node)` predicate
- Implement `_prune_elements(elements)` enforcing max 100
- Implement element priority ranking per spec 1.3.3:
  1. Viewport visibility: fully in viewport > partially visible > offscreen
  2. Role priority: button, link > checkbox, radio, textbox > combobox, listbox > heading > region, dialog > others
  3. Document order (tiebreaker)
- Remove lowest-ranked elements until count <= 100
**Done when**: All pruning tests pass; verify with pytest tests/unit/mcp/test_snapshot.py -v

#### T1.6: Implement bbox fallback
**File**: `src/subterminator/mcp/snapshot.py`
**Do**:
- Detect when a11y tree lacks bbox
- Use asyncio.gather() for parallel element.bounding_box() calls
- Merge bbox into ElementInfo
**Done when**: Bbox fallback test passes

### Group 1C: ActionExecutor (depends on Phase 0)

#### T1.7: Write ActionExecutor tests
**File**: `tests/unit/mcp/test_executor.py`
**Do**:
- Test click by selector
- Test click by bbox fallback
- Test fill with clear_first
- Test error mapping from Playwright errors
- Test timeout enforcement
**Done when**: Tests written

#### T1.8: Implement ActionExecutor
**File**: `src/subterminator/mcp/executor.py`
**Do**:
- Create `ActionExecutor` class with browser and timeout
- Implement click(), fill(), select(), scroll_to_element(), scroll_page()
- Implement `_map_playwright_error()` converting to MCPError types
**Done when**: All T1.7 tests pass

### Group 1D: ServiceConfig (depends on Phase 0)

#### T1.9: Write ServiceConfig tests
**File**: `tests/unit/mcp/test_services.py`
**Do**:
- Test checkpoint conditions trigger
- Test success indicators match
- Test failure indicators match
- Test service registry lookup
**Done when**: Tests written

#### T1.10: Implement ServiceConfig
**File**: `src/subterminator/mcp/services/base.py`
**Do**:
- Create `ServiceConfig` dataclass
- Implement check_checkpoint(), verify_success(), check_failure()
- Create SERVICE_CONFIGS dict and register_service(), get_service()
**Done when**: Base service config works

#### T1.11: Implement NETFLIX_CONFIG
**File**: `src/subterminator/mcp/services/netflix.py`
**Do**:
- Create NETFLIX_CONFIG with checkpoint conditions
- Add completion criteria for cancellation
- Register with SERVICE_CONFIGS
**Done when**: Netflix service tests pass

---

## Phase 2: Tool Server (Integration Layer)

### Group 2A: BrowserToolServer Core (depends on Group 1A-1C)

#### T2.1: Write BrowserToolServer core tests
**File**: `tests/unit/mcp/test_tool_server.py`
**Do**:
- Test get_snapshot returns valid ToolResult
- Test snapshot includes all required fields
- Test registry populated after get_snapshot
**Done when**: Tests written

#### T2.2: Implement BrowserToolServer core
**File**: `src/subterminator/mcp/tool_server.py`
**Do**:
- Create `BrowserToolServer` class
- Initialize ElementRegistry, SnapshotFactory, ActionExecutor
- Implement `_refresh_snapshot()` and `get_snapshot()`
- Implement `execute(tool_name, arguments)` router
**Done when**: Core tests pass

### Group 2B: Action Tools (depends on 2A)

#### T2.3: Write action tools tests
**File**: `tests/unit/mcp/test_tool_server.py` (continued)
**Do**:
- Test browser_click returns fresh snapshot
- Test invalid ref returns ref_invalid error
- Test browser_fill, browser_select work
- Test browser_scroll parameter validation
**Done when**: Tests written

#### T2.4: Implement browser_click
**File**: `src/subterminator/mcp/tool_server.py`
**Do**:
- Implement `browser_click(ref)` method
- Resolve ref, execute click, refresh snapshot
- Handle errors with fresh snapshot
**Done when**: Click tests pass

#### T2.5: Implement browser_fill, browser_select, browser_scroll
**File**: `src/subterminator/mcp/tool_server.py`
**Do**:
- Implement `browser_fill(ref, value, clear_first)`
- Implement `browser_select(ref, value)`
- Implement `browser_scroll(ref, direction, amount)` with param validation
**Done when**: All action tool tests pass

### Group 2C: Special Tools (depends on 2A)

#### T2.6: Write special tools tests
**File**: `tests/unit/mcp/test_tool_server.py` (continued)
**Do**:
- Test request_human_approval raises NotImplementedError
- Test complete_task raises NotImplementedError
**Done when**: Tests written

#### T2.7: Implement special tools
**File**: `src/subterminator/mcp/tool_server.py`
**Do**:
- Add `request_human_approval()` raising NotImplementedError
- Add `complete_task()` raising NotImplementedError
**Done when**: Special tool tests pass

---

## Phase 3: AI Client (Production)

### Group 3A: AIClient (can start after Group 0B)

#### T3.1: Write AIClient tests
**File**: `tests/unit/mcp/test_ai_client.py`
**Do**:
- Test message formatting for Anthropic
- Test tool call extraction
- Test history truncation at 10000 tokens
- Test retry logic with mock errors
**Done when**: Tests written

#### T3.2: Implement AIClient core
**File**: `src/subterminator/mcp/ai_client.py`
**Do**:
- Create `AIClient` class implementing AIClientProtocol
- Implement chat() calling anthropic SDK
- Implement _format_messages() and _parse_response()
**Done when**: Basic chat works; message tests pass

#### T3.3: Implement history truncation
**File**: `src/subterminator/mcp/ai_client.py`
**Do**:
- Add `_truncate_history(messages)` method
- Keep: (1) system message, (2) first user message with goal, (3) last 10 message pairs (user+assistant = 1 turn)
- Generate summary of dropped turns as single user message: "Previous actions: [bullet list of tool_name(args) -> outcome]"
- Example summary: "• browser_click(@e5) -> success\n• browser_fill(@e8, \"test\") -> success"
**Done when**: Truncation test passes; verify with pytest tests/unit/mcp/test_ai_client.py -v

#### T3.4: Implement retry logic
**File**: `src/subterminator/mcp/ai_client.py`
**Do**:
- Add retry decorator with exponential backoff
- Retry on: connection errors, 5xx server errors, 429 rate limit
- Do NOT retry on: 400, 401, 403, 404 (client errors)
- Config: initial 1s, multiplier 2, max 3 attempts, max delay 10s
**Done when**: Retry tests pass; verify with pytest tests/unit/mcp/test_ai_client.py -v

### Group 3B: Mock AI Client (can start after Group 0B)

#### T3.5: Write MockAIClient tests
**File**: `tests/unit/mcp/test_mock_ai.py`
**Do**:
- Test scripted tool calls returned in order
- Test prompt recording
- Test conversation reset
**Done when**: Tests written

#### T3.6: Implement MockAIClient
**File**: `src/subterminator/mcp/testing/mock_ai.py`
**Do**:
- Create `MockAIClient` implementing AIClientProtocol
- Take list of scripted responses
- Record all prompts for assertions
**Done when**: Mock AI tests pass

---

## Phase 4: Orchestrator (Top-Level Coordinator)

### Group 4A: TaskOrchestrator Core (depends on Groups 2C, 3A, 3B, 1D)

#### T4.1: Write TaskOrchestrator core tests
**File**: `tests/unit/mcp/test_orchestrator.py`
**Do**:
- Test conversation loop executes
- Test single tool per turn (first only)
- Test max turns limit
- Test prompts AI to complete when no tool call
**Done when**: Tests written

#### T4.2: Implement TaskOrchestrator core
**File**: `src/subterminator/mcp/orchestrator.py`
**Do**:
- Create `TaskOrchestrator` class
- Implement run(goal) conversation loop
- Implement _build_system_prompt() with service additions
- Implement _format_snapshot() as text block:
  ```
  Current Page: {url}
  Title: {title}
  Elements:
  {element_list}
  ```
  where element_list is one element per line: `{ref} [{role}] "{name}" (state: {state})`
- Define ORCHESTRATOR_HANDLED_TOOLS = {"request_human_approval", "complete_task"}
**Done when**: Core tests pass; verify with pytest tests/unit/mcp/test_orchestrator.py -v

### Group 4B: Human Approval (depends on 4A)

#### T4.3: Write human approval tests
**File**: `tests/unit/mcp/test_orchestrator.py` (continued)
**Do**:
- Test AI-requested approval calls handler
- Test server checkpoint triggers
- Test rejected approval returns human_rejected
- Test no handler = approval skipped
**Done when**: Tests written

#### T4.4: Implement _execute_tool with routing
**File**: `src/subterminator/mcp/orchestrator.py`
**Do**:
- Implement `_execute_tool(tool_call)` method
- Route request_human_approval to _handle_human_approval
- Route complete_task to _handle_complete_task
- Others go to tool_server.execute()
**Done when**: Tool routing works

#### T4.5: Implement human approval handling
**File**: `src/subterminator/mcp/orchestrator.py`
**Do**:
- Implement `_handle_human_approval(arguments)`
- Implement `_check_checkpoint(snapshot)` for server-enforced
- Call human_handler if present; skip if None
**Done when**: Human approval tests pass

### Group 4C: Completion Verification (depends on 4A)

#### T4.6: Write completion verification tests
**File**: `tests/unit/mcp/test_orchestrator.py` (continued)
**Do**:
- Test verified success acknowledged
- Test unverified success returns acknowledged=false
- Test failed tasks always acknowledged
**Done when**: Tests written

#### T4.7: Implement completion verification
**File**: `src/subterminator/mcp/orchestrator.py`
**Do**:
- Implement `_handle_complete_task(arguments)`
- Implement `_verify_completion(status, snapshot)`
- Use service_config.verify_success()
**Done when**: Completion tests pass

---

## Phase 5: Integration Testing

### Group 5A: Happy Path (depends on Phase 4)

#### T5.1: Write happy path integration test
**File**: `tests/integration/mcp/test_orchestrator_integration.py`
**Do**:
- Set up MockBrowser with Netflix fixtures (account_active → cancel_page → retention_offer → confirmation → cancelled)
- Set up MockAI with tool sequence matching fixture refs (refs are assigned during registry.register_snapshot() based on depth-first order):
  - get_snapshot
  - browser_click(<ref for "Cancel Membership" button in account_active fixture>)
  - browser_click(<ref for checkbox in cancel_page fixture>)
  - browser_click(<ref for "Continue" button>)
  - browser_click(<ref for "No thanks" button in retention_offer fixture>)
  - browser_click(<ref for "Finish Cancellation" button in confirmation fixture>)
  - complete_task("success", "Cancellation confirmed")
- Run orchestrator with goal: "Cancel Netflix subscription"
- Assert success=True, correct turn count, verification passed
- **Important**: Determine exact refs by loading fixtures into ElementRegistry and inspecting assigned refs
**Done when**: Happy path test passes; verify with pytest tests/integration/mcp/test_orchestrator_integration.py -v

### Group 5B: Error Recovery (depends on 5A)

#### T5.2: Write error recovery tests
**File**: `tests/integration/mcp/test_error_recovery.py`
**Do**:
- Test invalid ref error with AI retry
- Test element disabled handling
- Test human rejection flow
- Test max turns exceeded
- Test network error retry (mock failures)
**Done when**: All error tests pass

---

## Phase 6: Real Browser Integration

### Group 6A: Browser Adapter (depends on Phase 5)

#### T6.1: Write browser adapter tests
**File**: `tests/integration/mcp/test_browser_adapter.py`
**Do**:
- Test adapter wraps PlaywrightBrowser
- Test accessibility_tree extraction
- Test screenshot capture
**Done when**: Tests written

#### T6.2: Implement browser adapter
**File**: `src/subterminator/mcp/browser_adapter.py`
**Do**:
- Create `BrowserAdapter` class
- Wrap existing PlaywrightBrowser
- Implement interface expected by SnapshotFactory and ActionExecutor
**Done when**: Adapter tests pass

### Group 6B: CLI Integration (depends on 6A)

#### T6.3: Add experimental flag to CLI
**File**: `src/subterminator/cli/main.py`
**Do**:
- Add `--experimental-ai-led` flag
- When set, use new TaskOrchestrator instead of CancellationEngine
- Load appropriate service config
**Done when**: Flag recognized and routes correctly

#### T6.4: Write CLI smoke test
**File**: `tests/integration/mcp/test_cli_integration.py`
**Do**:
- Test --experimental-ai-led flag is recognized
- Test help text includes new flag
**Done when**: CLI smoke test passes

---

## Summary

| Phase | Tasks | Parallel Groups |
|-------|-------|-----------------|
| P0 | 33 | 7 (0A-0G) |
| P1 | 11 | 4 (1A-1D) |
| P2 | 7 | 3 (2A-2C) |
| P3 | 6 | 2 (3A-3B) |
| P4 | 7 | 3 (4A-4C) |
| P5 | 2 | 2 (5A-5B) |
| P6 | 4 | 2 (6A-6B) |
| **Total** | **52** | **12** |
