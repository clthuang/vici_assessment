# Implementation Plan: AI-Led MCP Browser Control Redesign

## Overview

This plan details the implementation order for Feature 007, following TDD principles. **Critical**: Phase 0 validation must pass before proceeding to full implementation per PRD mandate.

---

## Phase 0: Validation Infrastructure & Hypothesis Testing

**Goal**: Build minimal infrastructure to test the hypothesis that Claude can sequence browser actions. **GATE**: Must achieve >70% success rate before proceeding to Phase 1.

### P0.1: Data Types and Exceptions
**Files**: `src/subterminator/mcp/types.py`, `src/subterminator/mcp/exceptions.py`

**Deliverables**:
- `BoundingBox`, `ElementInfo`, `PageInfo`, `ViewportInfo`, `Snapshot` dataclasses
- `ToolResult`, `TaskResult`, `CompletionCriteria` dataclasses
- `Message`, `ToolCall`, `AIResponse` dataclasses
- `ErrorCode` type alias
- `MCPError`, `RefInvalidError`, `ElementDisabledError`, `ElementObscuredError`, `TimeoutError`, `InvalidParamsError` exceptions

**Tests**: Unit tests for dataclass serialization (`to_dict`, `to_json`)

**Dependencies**: None

### P0.2: Protocol Definitions
**Files**: `src/subterminator/mcp/protocols.py`

**Deliverables**:
- `AIClientProtocol` - interface for AI implementations
- `HumanApprovalHandler` - interface for approval UI

**Tests**: Protocol compliance tests

**Dependencies**: P0.1 (types for Message, ToolCall, AIResponse)

### P0.3: Tool Schema Definitions
**Files**: `src/subterminator/mcp/tool_schemas.py`

**Deliverables**:
- `TOOL_SCHEMAS` list with all 7 tool definitions
- Schema validation helper

**Tests**: Schema validation against JSON Schema draft-07

**Dependencies**: None

### P0.4: Mock Browser Implementation
**Files**: `src/subterminator/mcp/testing/mock_browser.py`

**Deliverables**:
- `MockPlaywrightBrowser` that returns predefined snapshots
- Must implement: `accessibility_tree()`, `screenshot()`, `viewport_size()`, `url()`, `title()`, `click()`, `fill()`, `select_option()`, `scroll()`
- Support for scripted action success/failure
- Action recording for assertions

**Tests**: Unit tests for mock behavior

**Dependencies**: P0.1 (types)

### P0.5: Snapshot Fixtures
**Files**: `tests/fixtures/mcp/snapshots/`, `tests/fixtures/mcp/snapshot_schema.json`

**Deliverables**:
- JSON Schema file for snapshot validation
- Netflix fixture snapshots:
  - `netflix_account_active.json`
  - `netflix_cancel_page.json`
  - `netflix_retention_offer.json`
  - `netflix_confirmation.json`
  - `netflix_cancelled.json`

**Tests**: Fixtures validate against schema

**Dependencies**: P0.1 (types for schema reference)

### P0.6: Minimal Validation Components
**Files**: `src/subterminator/mcp/validation/`

**Deliverables**:
- Minimal `ElementRegistry` (just enough for validation)
- Minimal `BrowserToolServer` (get_snapshot, browser_click, complete_task only)
- Minimal `TaskOrchestrator` (conversation loop, no human checkpoints)
- Real `AIClient` with Claude API

**Tests**: Unit tests for minimal components

**Dependencies**: P0.1, P0.2, P0.3, P0.4, P0.5

### P0.7: Validation Harness
**Files**: `src/subterminator/mcp/validation/harness.py`

**Deliverables**:
- Validation script that runs Netflix scenarios with mock browser
- Metrics collection (success rate, turns, failure modes)
- CSV output for analysis
- Estimated cost: ~200 API calls ($2-5 at current pricing)

**Tests**: Harness smoke test

**Dependencies**: P0.6

### P0.8: Run Validation (GATE)
**Files**: N/A (manual execution)

**Deliverables**:
- Run 20 Netflix cancellation scenarios
- Collect metrics
- Document results in `docs/features/007-ai-mcp-browser-control/validation-report.md`

**Success Criteria** (from PRD):
- **>70% completion rate**: Proceed to Phase 1
- **50-70% completion rate**: Identify failure patterns, revise tool descriptions, re-test
- **<50% completion rate**: **STOP - Abandon this approach**

**Dependencies**: P0.7

---

## VALIDATION GATE

**Before proceeding to Phase 1**:
1. P0.8 validation must show >70% success rate
2. Results documented in validation-report.md
3. Decision recorded in `.meta.json`

If validation fails (<50%): Archive work, document learnings, explore alternatives.
If validation marginal (50-70%): Iterate on tool descriptions, re-run validation.

---

## Phase 1: Core Components (Bottom-Up)

**Goal**: Implement production-quality core components with full test coverage.

**Prerequisite**: Phase 0 validation passed (>70% success rate)

### P1.1: ElementRegistry (Production)
**Files**: `src/subterminator/mcp/registry.py`

**Deliverables**:
- `ElementRegistry` class implementing interface from design 9.4.4:
  - `register_snapshot(elements)` - assigns refs, invalidates old
  - `resolve(ref)` - returns ElementInfo or raises RefInvalidError
  - `invalidate()` - clears all refs
  - `list_refs()` - returns valid refs
  - `snapshot_id` property

**Tests** (TDD - write first, then implement):
- Ref assignment follows @e{N} pattern
- Refs invalidated after new snapshot
- resolve() raises RefInvalidError for unknown refs
- Depth-first ordering preserved

**Dependencies**: P0.1 (types, exceptions)

### P1.2: SnapshotFactory
**Files**: `src/subterminator/mcp/snapshot.py`

**Deliverables**:
- `SnapshotFactory` class implementing interface from design 9.4.5:
  - `create(viewport_only)` - returns (Snapshot, list[ElementInfo])
  - `_extract_elements()` - traverses accessibility tree
  - `_prune_elements()` - applies pruning rules
  - `_should_include()` - inclusion predicate
- Constants: `INTERACTIVE_ROLES`, `LANDMARK_ROLES`, `MAX_ELEMENTS`, `MAX_DEPTH`, `MAX_NAME_LENGTH`

**Tests**:
- Pruning rules correctly applied (roles, depth, count)
- Name truncation at 200 chars
- Max 100 elements enforced
- Bounding boxes included (a11y tree path)
- Bounding box fallback path (parallel element.bounding_box() calls)
- Screenshot captured and base64 encoded

**Dependencies**: P0.1, P0.4 (types, mock browser)

### P1.3: ActionExecutor
**Files**: `src/subterminator/mcp/executor.py`

**Deliverables**:
- `ActionExecutor` class implementing interface from design 9.4.6:
  - `click(element)` - clicks via selector or bbox
  - `fill(element, value, clear_first)` - fills input
  - `select(element, value)` - selects option
  - `scroll_to_element(element)` - scrolls into view
  - `scroll_page(direction, amount)` - page scroll
  - `_map_playwright_error()` - error translation

**Tests**:
- Click by selector works
- Click by bbox fallback works
- Fill clears then types when clear_first=True
- Playwright errors mapped to MCPError subtypes
- Timeout enforced

**Dependencies**: P0.1, P0.4 (types, mock browser)

### P1.4: ServiceConfig
**Files**: `src/subterminator/mcp/services/base.py`, `src/subterminator/mcp/services/netflix.py`

**Deliverables**:
- `ServiceConfig` dataclass with checkpoint/completion logic
- `CompletionCriteria` dataclass
- `register_service()`, `get_service()` functions
- `NETFLIX_CONFIG` implementation

**Tests**:
- Checkpoint conditions trigger correctly
- Success indicators validated
- Failure indicators validated
- Service registry works

**Dependencies**: P0.1 (types)

---

## Phase 2: Tool Server (Integration Layer)

**Goal**: Implement BrowserToolServer that coordinates registry, snapshot factory, and executor.

### P2.1: BrowserToolServer Core
**Files**: `src/subterminator/mcp/tool_server.py`

**Deliverables**:
- `BrowserToolServer` class implementing interface from design 9.4.3:
  - `__init__(browser)` - initializes registry, factory, executor
  - `_refresh_snapshot()` - creates snapshot and registers elements
  - `execute(tool_name, arguments)` - routes to methods
  - `get_snapshot(viewport_only)` - T1 implementation

**Tests**:
- get_snapshot returns valid ToolResult
- Snapshot includes all required fields
- Registry populated after get_snapshot

**Dependencies**: P1.1, P1.2, P1.3 (registry, factory, executor)

### P2.2: Action Tools
**Files**: `src/subterminator/mcp/tool_server.py` (continued)

**Deliverables**:
- `browser_click(ref)` - T2 implementation
- `browser_fill(ref, value, clear_first)` - T3 implementation
- `browser_select(ref, value)` - T4 implementation
- `browser_scroll(ref, direction, amount)` - T5 implementation
- Error handling with fresh snapshot on failure

**Tests**:
- Each action returns fresh snapshot
- Invalid ref returns ref_invalid error
- Disabled element returns element_disabled error
- browser_scroll validates parameter rules (invalid_params error)
- All errors include fresh snapshot

**Dependencies**: P2.1 (tool server core)

### P2.3: Special Tools
**Files**: `src/subterminator/mcp/tool_server.py` (continued)

**Deliverables**:
- `request_human_approval(action, reason)` - raises `NotImplementedError("Handled by orchestrator")`
- `complete_task(status, reason)` - raises `NotImplementedError("Handled by orchestrator")`

**Rationale**: These tools should NEVER be called directly on tool_server. The orchestrator intercepts them. Raising NotImplementedError prevents accidental misuse.

**Tests**:
- Calling request_human_approval directly raises NotImplementedError
- Calling complete_task directly raises NotImplementedError

**Dependencies**: P2.1

---

## Phase 3: AI Client (Production)

**Goal**: Implement production-quality Claude API client with history management.

### P3.1: AIClient Implementation
**Files**: `src/subterminator/mcp/ai_client.py`

**Deliverables**:
- `AIClient` class implementing `AIClientProtocol`:
  - `__init__(api_key, model, max_tokens)`
  - `chat(messages, tools, system)` - calls Claude API
  - `_format_messages()` - Anthropic format conversion
  - `_parse_response()` - extracts tool calls
  - `_truncate_history()` - history management per spec 2.1.3
  - `TOOL_SCHEMAS` class attribute
- Retry logic with exponential backoff (NFR4): initial 1s, multiplier 2, max 3 attempts, max 10s delay

**Tests**:
- Message formatting correct for Anthropic
- Tool calls extracted from response
- History truncation triggers at 10000 tokens
- Summary format matches spec (bullet list of tool calls and outcomes)
- Network error retries with exponential backoff

**Dependencies**: P0.1, P0.2, P0.3 (types, protocols, schemas)

### P3.2: Mock AI Client (Production)
**Files**: `src/subterminator/mcp/testing/mock_ai.py`

**Deliverables**:
- `MockAIClient` implementing `AIClientProtocol`
- Support for scripted conversations
- Prompt recording for assertions

**Tests**: Unit tests for mock behavior

**Dependencies**: P0.1, P0.2 (types, protocols)

---

## Phase 4: Orchestrator (Top-Level Coordinator)

**Goal**: Implement TaskOrchestrator that ties everything together.

### P4.1: TaskOrchestrator Core
**Files**: `src/subterminator/mcp/orchestrator.py`

**Deliverables**:
- `TaskOrchestrator` class implementing interface from design 9.4.1:
  - `__init__(ai_client, tool_server, service_config, human_handler, max_turns)`
  - `run(goal)` - main conversation loop
  - `_build_system_prompt()` - with service additions
  - `_format_snapshot()` - for AI consumption
  - Single tool per turn enforcement
  - `ORCHESTRATOR_HANDLED_TOOLS = {"request_human_approval", "complete_task"}`

**Tests**:
- Conversation loop executes correctly
- Single tool per turn enforced (first only, others logged as warning)
- Max turns limit works (returns max_turns_exceeded)
- AI prompted to complete when no tool call

**Dependencies**: P2.3, P3.1, P3.2, P1.4 (tool server, ai client, service config)

### P4.2: Human Approval Handling
**Files**: `src/subterminator/mcp/orchestrator.py` (continued)

**Deliverables**:
- `_execute_tool()` - routes orchestrator-handled tools specially
- `_handle_human_approval()` - AI-requested approval
- `_check_checkpoint()` - server-enforced checkpoints
- Checkpoint evaluation after each action tool

**Tests**:
- AI-requested approval calls handler
- Server checkpoints trigger correctly
- Rejected approval returns human_rejected error with user message
- No handler = approval skipped (testing mode, logged)

**Dependencies**: P4.1

### P4.3: Completion Verification
**Files**: `src/subterminator/mcp/orchestrator.py` (continued)

**Deliverables**:
- `_handle_complete_task()` - completion with verification
- `_verify_completion()` - against service criteria

**Tests**:
- Verified success acknowledged (acknowledged=true)
- Unverified success returns acknowledged=false with message
- Failed tasks always acknowledged (acknowledged=true)

**Dependencies**: P4.1, P1.4

---

## Phase 5: Integration Testing

**Goal**: Validate end-to-end flows with mocks.

### P5.1: Happy Path Integration
**Files**: `tests/integration/mcp/test_orchestrator_integration.py`

**Deliverables**:
- Full conversation flow tests with MockAI and MockBrowser
- Netflix cancellation scenario test

**Tests**:
- AI sequences: click expand → check checkbox → click confirm → complete
- Correct turns reported
- Success verification works

**Dependencies**: P4.3, P0.4, P0.5, P3.2 (all components, mocks, fixtures)

### P5.2: Error Recovery Integration
**Files**: `tests/integration/mcp/test_error_recovery.py`

**Deliverables**:
- Error scenario tests

**Tests**:
- Invalid ref error with retry
- Element disabled error handling
- Human rejection handling
- Max turns exceeded
- Network error retry with exponential backoff (mock network failures)

**Dependencies**: P5.1

---

## Phase 6: Real Browser Integration

**Goal**: Connect to real Playwright browser.

### P6.1: Browser Adapter
**Files**: `src/subterminator/mcp/browser_adapter.py`

**Deliverables**:
- Adapter from existing `PlaywrightBrowser` to mcp interfaces
- Accessibility tree extraction (using existing `accessibility_snapshot`)
- Screenshot capture

**Tests**: Integration tests with real browser

**Dependencies**: Existing `PlaywrightBrowser`

### P6.2: CLI Integration
**Files**: `src/subterminator/cli/main.py` (modification)

**Deliverables**:
- `--experimental-ai-led` flag
- Route to new orchestrator when flag set

**Tests**: CLI smoke tests

**Dependencies**: P6.1

---

## Dependency Graph

```
Phase 0 (Validation - MUST PASS BEFORE CONTINUING):

P0.1 ─┬─► P0.2 ────────────────────────────────────┐
      │                                            │
      ├─► P0.3 ────────────────────────────────────┤
      │                                            │
      ├─► P0.4 ────────────────────────────────────┼─► P0.6 ─► P0.7 ─► P0.8 [GATE]
      │                                            │
      └─► P0.5 ────────────────────────────────────┘

                    ═══════════════════════════════
                    VALIDATION GATE (>70% required)
                    ═══════════════════════════════

Phase 1-5 (Only if validation passes):

P0.1 ─┬─► P1.1 ───────────────────────────────────┐
      │                                           │
      ├─► P1.4 ───────────────────────────────────┤
      │                                           │
P0.4 ─┼─► P1.2 ───────────────────────────────────┼─► P2.1 ─► P2.2 ─► P2.3
      │                                           │
      └─► P1.3 ───────────────────────────────────┘

P0.1 ─► P0.2 ─► P0.3 ─► P3.1 ──────────────────────────────────────────┐
                                                                        │
                    P3.2 ──────────────────────────────────────────────┤
                                                                        │
P2.3 ──────────────────────────────────────────────────────────────────┼─► P4.1 ─► P4.2 ─► P4.3
                                                                        │
P1.4 ──────────────────────────────────────────────────────────────────┘

P4.3 ─┬─► P5.1 ─► P5.2
      │
P0.4 ─┤
      │
P0.5 ─┤
      │
P3.2 ─┘

P5.2 ─► P6.1 ─► P6.2
```

---

## Risk Mitigation in Plan

| Risk | Mitigation in Plan |
|------|-------------------|
| Core hypothesis fails | P0.8 validation BEFORE building P1-P5; explicit gate |
| Playwright a11y tree incomplete | P1.2 includes bbox fallback logic with tests for both paths |
| Token budget exceeded | P1.2 enforces MAX_ELEMENTS=100, P3.1 includes truncation |
| Integration complexity | Bottom-up build with mocks at each layer |
| Network errors | P3.1 implements retry with exponential backoff, P5.2 tests it |
| Special tools called directly | P2.3 raises NotImplementedError to prevent misuse |

---

## Estimated Deliverables Summary

| Phase | Files | New Test Files |
|-------|-------|----------------|
| P0 (Validation) | 8 | 3 |
| P1 | 4 | 4 |
| P2 | 1 | 1 |
| P3 | 2 | 2 |
| P4 | 1 | 1 |
| P5 | 0 | 2 |
| P6 | 2 | 1 |
| **Total** | **18** | **14** |

---

## TDD Order Summary

1. **Validation First** (P0): Build minimal infrastructure, test hypothesis with real Claude
2. **GATE**: >70% success required to continue
3. **Core Components** (P1): Bottom-up, each fully tested against interfaces
4. **Tool Server** (P2): Integrates core components
5. **AI Client** (P3): Can parallelize with P1-P2 after P0.3
6. **Orchestrator** (P4): Ties everything together
7. **Integration Tests** (P5): Validate with mocks
8. **Real Browser** (P6): Final integration

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Validation before full implementation | PRD mandates hypothesis test; avoid wasted work |
| Special tools raise NotImplementedError | Prevent accidental misuse; make routing explicit |
| Minimal validation components in P0.6 | Test hypothesis with minimum viable implementation |
| P3 parallelizable with P1-P2 | Faster overall timeline; no dependency conflict |
