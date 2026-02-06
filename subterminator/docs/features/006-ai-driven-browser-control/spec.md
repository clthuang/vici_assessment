# Specification: AI-Driven Browser Control

**Feature ID**: 006
**Status**: Approved
**Created**: 2026-02-05

## 1. Overview

This specification defines the requirements for transforming SubTerminator from a heuristic-first, hardcoded-action system to an AI-first browser automation framework. The AI agent will perceive page context, plan actions, execute them, and use heuristics for validation.

## 2. Functional Requirements

### 2.1 Multi-Modal Context Gathering (FR-001)

**ID**: FR-001
**Priority**: P0 (Critical)

The system SHALL gather multi-modal context before each AI decision:

| Context Type | Requirement | Max Size |
|--------------|-------------|----------|
| Screenshot | Full-page PNG | Unbounded |
| Accessibility Tree | Playwright `page.accessibility.snapshot()` | ~3KB after pruning |
| HTML Snippet | Interactive elements within viewport | ~5KB |
| URL | Current page URL | N/A |
| Visible Text | Body text content | ~2KB |
| Action History | Last 5 actions taken | ~1KB |
| Error History | Previous failures in this flow | ~1KB |

**Acceptance Criteria**:
- [ ] AC-001.1: `accessibility_tree()` returns JSON string from Playwright
- [ ] AC-001.2: `html_snippet()` extracts only `<button>`, `<a>`, `<input>`, `<select>` elements within viewport
- [ ] AC-001.3: Context gathering completes in <2 seconds
- [ ] AC-001.4: If accessibility tree fails (e.g., cross-origin), gracefully degrade to screenshot + HTML only

### 2.2 AI Action Planning (FR-002)

**ID**: FR-002
**Priority**: P0 (Critical)

The system SHALL use Claude to plan browser actions given the gathered context.

**Input**: `AgentContext` containing all multi-modal data
**Output**: `ActionPlan` with structured action specification

**Action Types Supported**:
| Type | Description | Required Fields |
|------|-------------|-----------------|
| `click` | Click an element | Target (any method) |
| `fill` | Type into input field | Target + value |
| `select` | Select dropdown option | Target + value |
| `scroll` | Scroll to element or coordinates | Target or direction |
| `wait` | Wait for element or condition | Target or duration_ms |
| `navigate` | Navigate to URL | url |

**Acceptance Criteria**:
- [ ] AC-002.1: Claude returns structured response via `tool_use` API
- [ ] AC-002.2: Response includes confidence score (0.0-1.0)
- [ ] AC-002.3: Response includes reasoning string
- [ ] AC-002.4: Actions with confidence <0.6 are rejected with request for retry
- [ ] AC-002.5: Timeout for Claude API call: 30 seconds

### 2.3 Hybrid Element Identification (FR-003)

**ID**: FR-003
**Priority**: P0 (Critical)

The system SHALL support multiple element identification strategies, tried in order:

1. **CSS Selector**: Direct CSS selector (e.g., `#cancel-btn`, `.primary-button`)
2. **ARIA Selector**: Role + name (e.g., `("button", "Cancel Membership")`)
3. **Text Content**: Visible text matching (e.g., `"Cancel Membership"`)
4. **Coordinates**: Pixel coordinates `(x, y)` as last resort

**Acceptance Criteria**:
- [ ] AC-003.1: CSS selector tried first with 3-second timeout
- [ ] AC-003.2: If CSS fails, ARIA selector tried with 3-second timeout
- [ ] AC-003.3: If ARIA fails, text search tried with 3-second timeout (case-insensitive substring match using `page.get_by_text()`)
- [ ] AC-003.4: If all semantic methods fail, coordinates used with scroll-into-view
- [ ] AC-003.5: Each strategy logs its attempt and result

### 2.4 Action Execution (FR-004)

**ID**: FR-004
**Priority**: P0 (Critical)

The system SHALL execute planned actions via the browser protocol.

**Pre-execution Checks**:
- Verify element is visible (not obscured by overlay)
- Verify element is within viewport or scroll to it
- For coordinates: re-capture screenshot to verify position

**Post-execution Validation**:
- Capture new screenshot
- Use heuristics to detect state change
- Compare expected vs actual state

**Acceptance Criteria**:
- [ ] AC-004.1: Action execution includes pre-checks
- [ ] AC-004.2: Post-click delay of 1 second for page transition
- [ ] AC-004.3: Execution result includes success/failure and error details
- [ ] AC-004.4: Overlay detection via accessibility tree check for `dialog` or `alertdialog` roles

### 2.5 Heuristic Validation (FR-005)

**ID**: FR-005
**Priority**: P0 (Critical)

The existing `HeuristicInterpreter` SHALL be repurposed to validate AI actions:

**Input**: Expected state (what AI predicted), URL, visible text
**Output**: `ValidationResult` with success/failure and actual state

**Acceptance Criteria**:
- [ ] AC-005.1: Validation runs after every AI-executed action
- [ ] AC-005.2: If expected state matches actual state, action considered successful
- [ ] AC-005.3: If states differ, trigger self-correction loop
- [ ] AC-005.4: Validation completes in <100ms (no API calls)

### 2.6 Self-Correction Loop (FR-006)

**ID**: FR-006
**Priority**: P1 (High)

The system SHALL implement a self-correction mechanism when actions fail:

**Trigger Conditions**:
1. Element not found by any identification method
2. Heuristic validation detects wrong state
3. Playwright throws interaction error (e.g., element not clickable)

**Loop Behavior**:
1. Capture current context (screenshot + error details)
2. Send to Claude with reflection prompt
3. Claude proposes fundamentally different approach
4. Execute new approach
5. Repeat up to 3 times

**Acceptance Criteria**:
- [ ] AC-006.1: Maximum 3 self-correction attempts per action
- [ ] AC-006.2: Each attempt uses a different identification strategy
- [ ] AC-006.3: Error history is passed to Claude for context
- [ ] AC-006.4: After 3 failures, transition to `State.UNKNOWN` for human intervention
- [ ] AC-006.5: Reflection prompt explicitly requires "different approach"

### 2.7 Engine Integration (FR-007)

**ID**: FR-007
**Priority**: P0 (Critical)

The `CancellationEngine` SHALL integrate the AI agent as an optional component:

**Modes**:
| Mode | Behavior |
|------|----------|
| AI Agent provided | AI handles states except START, LOGIN_REQUIRED |
| AI Agent not provided | Fallback to existing hardcoded logic |

**State Handling**:
| State | Handler |
|-------|---------|
| `START` | Always hardcoded (just navigation) |
| `LOGIN_REQUIRED` | Always hardcoded (human checkpoint) |
| `ACCOUNT_ACTIVE` | AI agent if available |
| `ACCOUNT_CANCELLED` | AI agent if available |
| `THIRD_PARTY_BILLING` | AI agent if available |
| `RETENTION_OFFER` | AI agent if available |
| `EXIT_SURVEY` | AI agent if available |
| `FINAL_CONFIRMATION` | AI agent + human checkpoint |
| `UNKNOWN` | AI agent attempts recovery |

**Acceptance Criteria**:
- [ ] AC-007.1: Engine constructor accepts optional `agent` parameter
- [ ] AC-007.2: If agent is None, existing hardcoded flow executes
- [ ] AC-007.3: If agent is provided, AI-driven flow executes for supported states
- [ ] AC-007.4: `FINAL_CONFIRMATION` always requires human checkpoint regardless of AI
- [ ] AC-007.5: API outage (Claude unavailable) falls back to hardcoded logic

### 2.8 Human Checkpoints (FR-008)

**ID**: FR-008
**Priority**: P0 (Critical)

Human checkpoints SHALL be preserved for critical operations:

| Checkpoint | Trigger | Required Response |
|------------|---------|-------------------|
| AUTH | `LOGIN_REQUIRED` state | User completes login manually |
| CONFIRM | `FINAL_CONFIRMATION` state | User types "confirm" |
| UNKNOWN | After 3 self-correction failures | User navigates manually |

**Acceptance Criteria**:
- [ ] AC-008.1: AUTH checkpoint unchanged from current behavior
- [ ] AC-008.2: CONFIRM checkpoint unchanged from current behavior
- [ ] AC-008.3: UNKNOWN checkpoint triggered after AI exhausts retries
- [ ] AC-008.4: dry_run=True skips CONFIRM checkpoint (existing behavior)

## 3. Non-Functional Requirements

### 3.1 Performance (NFR-001)

| Metric | Requirement |
|--------|-------------|
| Context gathering | <2 seconds |
| AI planning call | <30 seconds |
| Action execution | <5 seconds |
| Full flow (normal) | <5 minutes |
| Full flow (with retries) | <10 minutes |

### 3.2 Accuracy (NFR-002)

| Metric | Target |
|--------|--------|
| State detection accuracy | >95% |
| Element identification success | >90% (first try) |
| Self-correction success | >80% (within 3 tries) |

### 3.3 Cost (NFR-003)

| Metric | Estimate |
|--------|----------|
| Tokens per action | ~10-15K |
| API calls per flow | ~5-15 |
| Cost per flow | ~$0.10-0.30 (Sonnet pricing) |

Cost tracking SHALL be implemented via session logging.

### 3.4 Backward Compatibility (NFR-004)

- Existing code using `CancellationEngine` without AI agent SHALL work unchanged
- Existing tests SHALL pass without modification
- New `BrowserProtocol` methods SHALL be optional with graceful degradation

## 4. Data Structures

### 4.1 AgentContext

```python
@dataclass
class AgentContext:
    """Multi-modal context for AI decision making."""
    screenshot: bytes
    accessibility_tree: str  # JSON string
    html_snippet: str
    url: str
    visible_text: str
    previous_actions: list[ActionRecord]  # Last 5 actions (see ActionRecord below)
    error_history: list[ErrorRecord]  # Failures in current flow (see ErrorRecord below)
    viewport_size: tuple[int, int]  # (width, height)
    scroll_position: tuple[int, int]  # (x, y)


@dataclass
class ActionRecord:
    """Record of a previously executed action."""
    action_type: str  # click, fill, etc.
    target_description: str  # Human-readable target description
    success: bool
    timestamp: str  # ISO format


@dataclass
class ErrorRecord:
    """Record of an error during execution."""
    action_type: str
    error_type: str  # ElementNotFound, NavigationError, etc.
    error_message: str
    strategy_attempted: str  # css, aria, text, coordinates
    timestamp: str
```

### 4.2 TargetStrategy

```python
@dataclass
class TargetStrategy:
    """A single element targeting method."""
    method: Literal["css", "aria", "text", "coordinates"]
    css_selector: str | None = None
    aria_role: str | None = None
    aria_name: str | None = None
    text_content: str | None = None
    coordinates: tuple[int, int] | None = None
```

### 4.3 ActionPlan

```python
@dataclass
class ActionPlan:
    """Planned browser action from AI."""
    action_type: Literal["click", "fill", "select", "scroll", "wait", "navigate"]
    primary_target: TargetStrategy
    fallback_targets: list[TargetStrategy]  # Max 3
    value: str | None = None  # For fill/select
    reasoning: str = ""
    confidence: float = 0.0
    expected_state: State | None = None
```

### 4.4 ExecutionResult

```python
@dataclass
class ExecutionResult:
    """Result of executing an action."""
    success: bool
    action_plan: ActionPlan
    strategy_used: TargetStrategy  # Which targeting method worked
    error: str | None = None
    screenshot_after: bytes | None = None
    elapsed_ms: int = 0
```

### 4.5 ValidationResult

```python
@dataclass
class ValidationResult:
    """Result of heuristic validation after action."""
    success: bool
    expected_state: State
    actual_state: State
    confidence: float
    message: str
```

## 5. Interface Specifications

### 5.1 BrowserProtocol Extensions

```python
class BrowserProtocol(Protocol):
    # ... existing methods unchanged ...

    # NEW: Optional methods (default raises NotImplementedError)
    async def accessibility_tree(self) -> str:
        """Get accessibility tree as JSON string.

        Returns:
            JSON string of accessibility tree from Playwright.

        Raises:
            NotImplementedError: If not supported by implementation.
        """
        ...

    async def click_coordinates(self, x: int, y: int) -> None:
        """Click at specific pixel coordinates.

        Args:
            x: X coordinate relative to viewport.
            y: Y coordinate relative to viewport.

        Raises:
            NotImplementedError: If not supported by implementation.
        """
        ...

    async def scroll_to(self, x: int, y: int) -> None:
        """Scroll viewport to coordinates.

        Args:
            x: X scroll position.
            y: Y scroll position.
        """
        ...

    async def viewport_size(self) -> tuple[int, int]:
        """Get current viewport dimensions.

        Returns:
            Tuple of (width, height) in pixels.
        """
        ...

    async def scroll_position(self) -> tuple[int, int]:
        """Get current scroll position.

        Returns:
            Tuple of (x, y) scroll offset.
        """
        ...

    def supports_accessibility_tree(self) -> bool:
        """Check if accessibility_tree() is available."""
        ...

    def supports_coordinate_clicking(self) -> bool:
        """Check if click_coordinates() is available."""
        ...
```

### 5.2 AIBrowserAgent Interface

```python
class AIBrowserAgent:
    """AI agent for browser automation."""

    def __init__(
        self,
        browser: BrowserProtocol,
        planner: ClaudeActionPlanner,
        heuristic: HeuristicInterpreter,
        max_retries: int = 3,
    ) -> None:
        """Initialize the AI agent.

        Args:
            browser: Browser protocol implementation.
            planner: Claude-based action planner.
            heuristic: Heuristic interpreter for validation.
            max_retries: Maximum self-correction attempts.
        """
        ...

    async def perceive(self) -> AgentContext:
        """Gather current page context.

        Returns:
            AgentContext with all available modalities.
        """
        ...

    async def plan(self, context: AgentContext, goal: str) -> ActionPlan:
        """Plan next action given context and goal.

        Args:
            context: Current page context.
            goal: Human-readable goal description.

        Returns:
            ActionPlan with targeting strategies and confidence.
        """
        ...

    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute the planned action.

        Tries targeting strategies in order until one succeeds.

        Args:
            plan: The action plan to execute.

        Returns:
            ExecutionResult with success status and details.
        """
        ...

    async def validate(self, result: ExecutionResult) -> ValidationResult:
        """Validate action succeeded using heuristics.

        Args:
            result: The execution result to validate.

        Returns:
            ValidationResult indicating if expected state reached.
        """
        ...

    async def self_correct(
        self,
        context: AgentContext,
        failure: ValidationResult,
        attempt: int,
    ) -> ActionPlan:
        """Generate corrective action after failure.

        Args:
            context: Current page context.
            failure: The validation failure details.
            attempt: Current attempt number (1-3).

        Returns:
            New ActionPlan with different strategy.
        """
        ...

    async def handle_state(self, state: State) -> State:
        """Handle a state transition.

        Main entry point for AI-driven state handling.
        Implements perceive -> plan -> execute -> validate loop
        with self-correction.

        Args:
            state: Current state to handle.

        Returns:
            Next state after action execution.
        """
        ...
```

### 5.3 ClaudeActionPlanner Interface

```python
class ClaudeActionPlanner:
    """Claude-based action planning using tool_use."""

    TOOL_SCHEMA = {
        "name": "browser_action",
        "description": "Execute a browser action to progress toward the goal",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Detected page state",
                    "enum": [
                        "LOGIN_REQUIRED", "ACCOUNT_ACTIVE", "ACCOUNT_CANCELLED",
                        "THIRD_PARTY_BILLING", "RETENTION_OFFER", "EXIT_SURVEY",
                        "FINAL_CONFIRMATION", "COMPLETE", "FAILED", "UNKNOWN"
                    ]
                },
                "action_type": {
                    "type": "string",
                    "enum": ["click", "fill", "select", "scroll", "wait", "navigate"]
                },
                "target": {
                    "type": "object",
                    "properties": {
                        "css": {"type": "string"},
                        "aria_role": {"type": "string"},
                        "aria_name": {"type": "string"},
                        "text": {"type": "string"},
                        "coordinates": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                },
                "value": {"type": "string"},
                "reasoning": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["state", "action_type", "target", "reasoning", "confidence"]
        }
    }

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514") -> None:
        """Initialize the planner.

        Args:
            api_key: Anthropic API key (uses env var if None).
            model: Model to use for planning.
        """
        ...

    async def plan_action(
        self,
        context: AgentContext,
        goal: str,
        error_context: str | None = None,
    ) -> ActionPlan:
        """Generate an action plan using Claude.

        Args:
            context: Current page context.
            goal: What we're trying to achieve.
            error_context: Previous error for self-correction.

        Returns:
            ActionPlan parsed from Claude's tool_use response.

        Raises:
            StateDetectionError: If Claude returns invalid response.
        """
        ...
```

## 6. Error Handling

### 6.1 Error Types

| Error | Handling |
|-------|----------|
| `ElementNotFound` | Trigger self-correction loop |
| `NavigationError` | Log and retry with timeout |
| `StateDetectionError` | Fall back to heuristic detection |
| `anthropic.APIError` | Fall back to hardcoded logic |
| `NotImplementedError` (browser capability) | Graceful degradation |

### 6.2 Graceful Degradation

```
Full AI Mode
    |
    v (accessibility tree fails)
Screenshot + HTML Mode
    |
    v (Claude API fails)
Hardcoded Logic Mode
```

## 7. Testing Requirements

### 7.1 Unit Tests

| Component | Test Cases |
|-----------|------------|
| `AgentContext` | Initialization, serialization |
| `ActionPlan` | All action types, validation |
| `AIBrowserAgent.perceive()` | Context gathering, fallbacks |
| `AIBrowserAgent.execute()` | Each targeting strategy |
| `ClaudeActionPlanner` | Mock API responses |

### 7.2 Integration Tests

| Scenario | Description |
|----------|-------------|
| Happy path | AI navigates full flow without errors |
| Element not found | Self-correction finds alternative |
| API timeout | Fallback to hardcoded |
| Wrong state detected | Validation triggers correction |

### 7.3 Test Data

Mock pages required:
- Modified Netflix pages with altered selectors
- Pages with overlays/modals
- Pages with multiple similar buttons

## 8. Scope Boundaries

### In Scope

- AI-driven action planning and execution
- Multi-modal context gathering
- Self-correction loop (3 attempts)
- Heuristic validation
- Backward-compatible engine integration
- Cost tracking in session logs

### Out of Scope

- Learning from past failures (future enhancement)
- Multi-service support in single flow
- Parallel action execution
- Custom model fine-tuning
- Real-time streaming of AI decisions

## 9. Dependencies

### Internal Dependencies

| Component | Dependency |
|-----------|------------|
| `AIBrowserAgent` | `BrowserProtocol`, `ClaudeActionPlanner`, `HeuristicInterpreter` |
| `ClaudeActionPlanner` | `anthropic` library |
| `CancellationEngine` | `AIBrowserAgent` (optional) |

### External Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `anthropic` | >=0.39.0 | Claude API client |
| `playwright` | >=1.40.0 | Browser automation |

## 10. Metrics & Observability

### Session Logging

Each AI action SHALL log:
- Timestamp
- Context size (tokens)
- Claude response time
- Action type and target
- Success/failure
- Self-correction attempts

### Aggregated Metrics (Future)

- Actions per flow
- Success rate by action type
- Self-correction effectiveness
- Cost per flow

## 11. Migration Notes

### For Existing Users

No changes required. System defaults to hardcoded logic if AI agent not provided.

### For New Integrations

```python
# Old way (still works)
engine = CancellationEngine(service, browser, heuristic, ai=None, ...)

# New way (AI-driven)
agent = AIBrowserAgent(browser, planner, heuristic)
engine = CancellationEngine(service, browser, heuristic, ai=None, agent=agent, ...)
```
