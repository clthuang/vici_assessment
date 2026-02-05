# Implementation Plan: AI Browser Orchestration via MCP Tools

## Overview

This plan implements feature 007 following TDD principles. Each phase builds on the previous, with validation gates ensuring quality before proceeding.

**Total Phases**: 5
**Estimated Tasks**: ~20 (to be broken down in create-tasks phase)

---

## Phase 0: Foundation & Validation (POC)

**Goal**: Validate core assumptions before building full implementation.

### P0.1: Data Types and Exceptions
- **Files**: `src/subterminator/mcp_orchestrator/types.py`, `exceptions.py`
- **Deliverables**:
  - `TaskResult`, `ToolCall`, `NormalizedSnapshot` dataclasses
  - `TaskReason` Literal type
  - All exception classes from design Section 4.2
  - **NOTE**: `ToolCall.args` (not `arguments`) - matches LangChain convention
- **Exception Hierarchy Decision**:
  - `OrchestratorError` SHALL inherit from existing `SubTerminatorError` (in utils/exceptions.py)
  - This provides consistent exception handling across the codebase
  - Existing `ConfigurationError` in utils/exceptions.py will be reused (not duplicated)
  - New exceptions: `MCPConnectionError`, `MCPToolError`, `LLMError`, `CheckpointRejectedError`, `SnapshotValidationError`, `ServiceNotFoundError`
- **Tests**: Type instantiation, equality, serialization
- **Dependencies**: None
- **Codebase Integration**: Review existing `src/subterminator/utils/exceptions.py` first

### P0.2: MCP Connection Validation
- **Files**: `src/subterminator/mcp_orchestrator/mcp_client.py`
- **Deliverables**:
  - `MCPClient.connect()` - start Playwright MCP subprocess
  - `MCPClient.list_tools()` - validate tools available
  - `MCPClient.close()` - cleanup subprocess
  - Node.js validation (`_validate_nodejs`)
- **Tests**:
  - Integration test: Connect, list tools, verify `browser_snapshot` exists
  - Unit test: Node.js version check, error paths
- **Dependencies**: P0.1

### P0.3: Snapshot Format Discovery & Parser Implementation
- **Files**: `src/subterminator/mcp_orchestrator/snapshot.py`
- **Deliverables**:
  - Call `browser_snapshot` with real Playwright MCP
  - **Log actual output format** (critical for normalize_snapshot)
  - **NOTE**: Playwright MCP returns markdown-formatted TEXT, not dict:
    ```
    ### Page state
    - Page URL: https://...
    - Page Title: ...
    - Page Snapshot:
    ```yaml
    - document [ref=@e0]:
      - navigation [ref=@e1]:
    ...
    ```
  - Implement `normalize_snapshot()` as markdown text parser:
    - Extract URL from "- Page URL: ..." line
    - Extract title from "- Page Title: ..." line
    - Extract content (everything after "- Page Snapshot:")
  - Call `browser_take_screenshot` to validate screenshot format
- **Tests**:
  - Integration test with real MCP output
  - Store sample outputs as test fixtures
  - Unit tests for text parsing edge cases
- **Dependencies**: P0.2
- **Validation**: Must successfully extract url, title, content from real output before proceeding

### P0.4: LLM Tool Calling Validation
- **Files**: `src/subterminator/mcp_orchestrator/llm_client.py`
- **Deliverables**:
  - `LLMClient._resolve_model_name()` - env var priority
  - `LLMClient._create_model()` - Anthropic/OpenAI detection
  - `LLMClient.invoke()` - with timeout and retries
- **Tests**:
  - Integration test: Send tools to Claude, verify tool_calls format
  - Integration test: Send tools to GPT-4o, verify tool_calls format
  - Unit test: Model resolution priority, error paths
- **Dependencies**: P0.1

### VALIDATION GATE
After P0.4, verify:
- [ ] MCP connects and lists tools within 10 seconds
- [ ] `browser_snapshot` returns markdown text output
- [ ] `normalize_snapshot()` correctly parses text and extracts url, title, content
- [ ] `browser_take_screenshot` format validated (base64, path, or other)
- [ ] Claude responds with tool_calls in expected format (name, args, id)
- [ ] OpenAI responds with tool_calls in expected format

**If validation fails**:
1. **P0.3 fails** (snapshot parsing): DO NOT proceed to P1.x. Fix normalize_snapshot() parser first.
2. **P0.4 fails** (LLM format): Update _convert_messages() and tool_call handling before P1.2.
3. Document actual formats in test fixtures for regression testing.

**Gate is HARD BLOCK**: All 6 checkboxes must pass before starting Phase 1.

---

## Phase 1: Core Components

**Goal**: Implement all components with unit tests (mocked dependencies).

### P1.1: MCPClient Full Implementation
- **Files**: `mcp_client.py`
- **Deliverables**:
  - `call_tool()` implementation
  - `reconnect()` for connection recovery
  - Context manager (`__aenter__`, `__aexit__`)
  - Proper subprocess cleanup on error
- **Tests**:
  - Mock subprocess for unit tests
  - Test error paths (MCPToolError, MCPConnectionError)
  - Test reconnection logic
- **Dependencies**: P0.2

### P1.2: LLMClient Full Implementation
- **Files**: `llm_client.py`
- **Deliverables**:
  - `_convert_messages()` implementation
  - Full retry logic with exponential backoff
  - 60s timeout handling
- **Tests**:
  - Mock LangChain models
  - Test timeout behavior
  - Test retry on transient failures
  - Test error conversion
- **Dependencies**: P0.4

### P1.3: ServiceConfig and Registry
- **Files**: `mcp_orchestrator/services/base.py`, `mcp_orchestrator/services/registry.py`, `mcp_orchestrator/services/netflix.py`
- **Deliverables**:
  - `ServiceConfig` dataclass (separate from existing `services/registry.py` ServiceInfo)
  - `ServiceRegistry.get()`, `register()`, `list_services()`
  - `NETFLIX_CONFIG` with all predicates from spec Section 2.6.2
  - **NOTE**: mcp_orchestrator has its own services subpackage, separate from existing subterminator/services/
- **Tests**:
  - Unit tests for predicate evaluation with REAL sample snapshots from P0.3
  - Test ServiceNotFoundError
  - Test Netflix checkpoint conditions against markdown text content
  - Test Netflix success/failure indicators
- **Dependencies**: P0.1, P0.3 (for NormalizedSnapshot AND sample fixtures)
- **Codebase Note**: Existing `services/registry.py` is for different purpose (service metadata). New registry is for orchestration configs.

### P1.4: CheckpointHandler
- **Files**: `checkpoint.py`
- **Deliverables**:
  - `should_checkpoint()` with service conditions
  - `request_approval()` with screenshot capture
  - `_capture_screenshot()` using browser_take_screenshot
  - `_display_checkpoint_info()`, `_get_user_input()`
- **Tests**:
  - Mock MCPClient for screenshot
  - Mock stdin for approval input
  - Test condition evaluation
  - Test auth edge case detection
- **Dependencies**: P1.1, P1.3

---

## Phase 2: Orchestration Loop

**Goal**: Implement TaskRunner with full loop logic.

### P2.1: Virtual Tools
- **Files**: `task_runner.py`
- **Deliverables**:
  - `VIRTUAL_TOOLS` schemas
  - Tool list merging (MCP + virtual)
  - `is_virtual_tool()` check
- **Tests**:
  - Verify schemas match spec Section 2.3
  - Test tool merging
- **Dependencies**: P0.1

### P2.2: TaskRunner Core Loop
- **Files**: `task_runner.py`
- **Deliverables**:
  - `run()` method with full loop
  - System prompt building
  - Message history management
  - Single-tool-per-turn enforcement
  - No-action counter (3 strikes)
- **Tests**:
  - Mock MCPClient + LLMClient
  - Test complete happy path
  - Test max_turns termination
  - Test no_action termination
- **Dependencies**: P1.1, P1.2, P1.3, P1.4, P2.1

### P2.3: Virtual Tool Handlers
- **Files**: `task_runner.py`
- **Deliverables**:
  - `_handle_complete_task()` with verification retry
  - request_human_approval flow
  - Checkpoint triggering before MCP tools
- **Tests**:
  - Test verification success path
  - Test verification failure → retry
  - Test human rejection
- **Dependencies**: P2.2

### P2.4: Error Recovery
- **Files**: `task_runner.py`
- **Deliverables**:
  - MCPToolError → formatted error result → continue
  - SIGINT handling with graceful shutdown
  - Dry-run mode (return after first action)
- **Tests**:
  - Test error recovery continues loop
  - Test SIGINT cleanup
  - Test dry-run early exit
- **Dependencies**: P2.2

---

## Phase 3: CLI Integration

**Goal**: Wire orchestrator to CLI, implement exit codes.

### P3.1: CLI Command Extension
- **Files**: `src/subterminator/cli/main.py`
- **Deliverables**:
  - `cancel` command with service argument
  - Options: `--model`, `--max-turns`, `--dry-run`, `-v/--verbose`, `--no-checkpoint`
  - Progress display (turn-by-turn)
- **Tests**:
  - CLI argument parsing
  - Help text validation
- **Dependencies**: P2.4
- **Codebase Note**: Existing CLI uses **Typer** (not Click). Existing `cancel` command takes `--service` option.
- **CLI Strategy Decision**: Modify existing `cancel` command to add `--auto` flag:
  - `subterminator cancel --service netflix` → Existing manual flow
  - `subterminator cancel --service netflix --auto` → New AI-driven MCP orchestration
  - This approach maintains backward compatibility while adding new capability
  - Alternative: `subterminator cancel netflix --ai` (positional service, `--ai` flag)
  - Final CLI signature to be confirmed during P3.1 implementation based on existing code review

### P3.2: Exit Code Handling
- **Files**: `cli/main.py`
- **Deliverables**:
  - Exit code 0: Success
  - Exit code 1: Failure
  - Exit code 2: Configuration error
  - Exit code 3: Connection error
  - Exit code 130: SIGINT
- **Tests**:
  - Test each exit code path
- **Dependencies**: P3.1

### P3.3: Verbose Output
- **Files**: `cli/main.py`
- **Deliverables**:
  - Normal: Turn number + tool name
  - Verbose: Full snapshot content + arguments
  - Error messages with actionable guidance
- **Tests**:
  - Output format validation
- **Dependencies**: P3.1

---

## Phase 4: Integration Testing

**Goal**: End-to-end validation with real components.

### P4.1: MCP + Mock LLM Integration
- **Files**: `tests/integration/test_mcp_integration.py`
- **Deliverables**:
  - Real Playwright MCP + deterministic mock LLM
  - Test full loop with predefined tool responses
  - Verify checkpoint triggers correctly
- **Dependencies**: P2.4

### P4.2: LLM Integration (Rate-Limited)
- **Files**: `tests/integration/test_llm_integration.py`
- **Deliverables**:
  - Real Claude API call with tools
  - Real OpenAI API call with tools
  - Verify tool_calls format matches expectations
- **Dependencies**: P1.2

### P4.3: CLI Integration
- **Files**: `tests/integration/test_cli.py`
- **Deliverables**:
  - End-to-end CLI test with mock LLM
  - Verify exit codes
  - Verify output format
- **Dependencies**: P3.3

---

## Dependency Graph

```
P0.1 ─────────────────────────────────────────┐
  │                                           │
  ├─────────────────┐                         │
  ▼                 ▼                         │
P0.2             P0.4                         │
  │                │                          │
  ▼                ▼                          │
P0.3 ────────────► P1.2                       │
  │                │                          │
  ├────► P1.1      │                          │
  │                │                          │
  ├────► P1.3 ◄────┤                          │
  │        │       │                          │
  │        ▼       │                          │
  │     P1.4 ◄─────┴──────────────────────────┤
  │        │                                  │
  │        │                                  │
  │        ▼                                  │
  │     P2.1 ──► P2.2 ──► P2.3 ──► P2.4       │
  │                                  │        │
  │                                  ▼        │
  │                               P3.1 ──► P3.2 ──► P3.3
  │                                  │
  │                                  ▼
  │                               P4.1
  │                                  │
  └──────────────────────────────► P4.2 (parallel with P4.1)
                                     │
                                     ▼
                                   P4.3
```

**Key Dependency Paths:**
- P0.3 feeds into P1.1 (MCPClient), P1.3 (ServiceConfig fixtures), and indirectly P1.2
- P0.4 feeds into P1.2 (LLMClient)
- P4.2 can run in parallel with P4.1 after P1.2 completes

**Critical Path**: P0.1 → P0.2 → P0.3 → P1.3 → P1.4 → P2.2 → P2.4 → P3.1 → P4.1

---

## Implementation Order Summary

| Phase | Items | Focus |
|-------|-------|-------|
| **P0** | P0.1, P0.2, P0.3, P0.4 | Foundation + POC Validation |
| **P1** | P1.1, P1.2, P1.3, P1.4 | Core Components |
| **P2** | P2.1, P2.2, P2.3, P2.4 | Orchestration Loop |
| **P3** | P3.1, P3.2, P3.3 | CLI Integration |
| **P4** | P4.1, P4.2, P4.3 | Integration Testing |

---

## Parallel Execution Opportunities

Within each phase, some items can run in parallel:

- **P0**: P0.2 and P0.4 can run in parallel after P0.1
- **P1**: P1.1 and P1.2 can run in parallel
- **P2**: P2.1 is independent (can start after P0.1)
- **P3**: P3.2 and P3.3 can run in parallel after P3.1
- **P4**: P4.2 (LLM integration) depends only on P1.2, so can run in parallel with P4.1 after P1.2 completes

---

## Reconnection Trigger Points

Design noted reconnection logic but didn't specify triggers. This plan clarifies:

**When to call `MCPClient.reconnect()`**:
1. After `MCPConnectionError` in `call_tool()` - single retry
2. NOT for `MCPToolError` (tool execution failure, not connection)
3. NOT for timeout (let operation fail)

**Implementation in TaskRunner**:
```python
try:
    result = await self._mcp.call_tool(...)
except MCPConnectionError:
    # Connection lost - try reconnect once
    try:
        await self._mcp.reconnect()
        result = await self._mcp.call_tool(...)  # Retry once
    except MCPConnectionError:
        # Reconnect failed - terminate gracefully
        return TaskResult(
            success=False,
            verified=False,
            reason="mcp_error",
            turns=turn,
            error="MCP connection lost and reconnect failed"
        )
except MCPToolError as e:
    # Tool failed - return to LLM
    result = {"error": True, "message": str(e)}
```

**Failure Handling**: If reconnect() fails, TaskRunner catches the exception and returns TaskResult with reason="mcp_error" instead of propagating exception to CLI.

**Initial Connection Handling**: If initial `connect()` fails in `TaskRunner.run()`:
```python
async def run(self, service: str, max_turns: int = 20) -> TaskResult:
    try:
        await self._mcp.connect()
    except MCPConnectionError as e:
        return TaskResult(
            success=False,
            verified=False,
            reason="mcp_error",
            turns=0,
            error=f"Failed to connect to MCP: {e}"
        )
    # ... rest of orchestration
```
This ensures CLI always receives a TaskResult (for proper exit code handling) rather than an uncaught exception.

---

## Logging Strategy

Design review noted logging needed. This plan specifies:

**Log Levels**:
- `DEBUG`: Tool call arguments, full snapshots, timing
- `INFO`: Turn progression, checkpoint triggers
- `WARNING`: Multiple tool_calls ignored, verification failures
- `ERROR`: Connection failures, API errors

**Format**: `[{timestamp}] [{level}] [{component}] {message}`

**Implementation**: Use Python's `logging` module with configurable level via `-v` flag.

---

## Risk Mitigation Notes

From design review warnings:

1. **ToolCall.args vs spec.arguments**: Plan uses `args` (LangChain convention). Spec Section 5.2 uses `arguments`. This divergence was noted in design review and accepted. Spec to be updated during implementation if needed, or documented as intentional deviation.
2. **browser_take_screenshot format**: POC (P0.3) will validate actual format.
3. **normalize_snapshot falsy strings**: Add explicit `is not None` checks in implementation.
