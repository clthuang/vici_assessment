# Implementation Plan: AI-Driven Browser Control

**Feature ID**: 006
**Status**: Draft (Revision 3)
**Created**: 2026-02-05

## Overview

This plan implements the AI-driven browser control feature as specified in design.md. The implementation follows the dependency graph from Section 7, using TDD (Red-Green-Refactor) methodology.

## Build Order & Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IMPLEMENTATION PHASES                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: Data Structures (protocols.py)                                    │
│      │    - ActionRecord, ErrorRecord, TargetStrategy                        │
│      │    - ActionPlan, AgentContext, ExecutionResult, ValidationResult      │
│      │    TDD: Write tests FIRST, then implement                            │
│      │                                                                       │
│      ▼                                                                       │
│  Phase 2: BrowserProtocol Extensions (protocols.py + browser.py)            │
│      │    - Protocol method signatures (OPTIONAL - duck-typed)               │
│      │    - PlaywrightBrowser implementations (new methods)                 │
│      │    - evaluate() method for JavaScript execution                       │
│      │    - click_by_role() method for ARIA targeting                        │
│      │    TDD: Write tests FIRST, existing tests must still pass            │
│      │                                                                       │
│      ▼                                                                       │
│  Phase 3: ClaudeActionPlanner (ai.py)                                       │
│      │    - TOOL_SCHEMA, SYSTEM_PROMPT, SELF_CORRECT_PROMPT                 │
│      │    - plan_action() with asyncio.to_thread()                          │
│      │    - _build_messages(), _parse_tool_response()                       │
│      │    TDD: Write tests FIRST with mock Claude responses                 │
│      │                                                                       │
│      ▼                                                                       │
│  Phase 4: AIBrowserAgent (agent.py - NEW FILE)                              │
│      │    - perceive(), plan(), execute(), validate(), self_correct()       │
│      │    - handle_state() with STATE_TRANSITIONS mapping                   │
│      │    - Uses browser.evaluate() for HTML snippet extraction             │
│      │    TDD: Write tests FIRST with mock browser/planner/heuristic        │
│      │                                                                       │
│      ▼                                                                       │
│  Phase 5: Engine Integration (engine.py)                                    │
│           - Add agent parameter to __init__                                  │
│           - _ai_driven_handle(), _hardcoded_handle() separation             │
│           - API outage fallback                                             │
│           TDD: Write tests FIRST, existing tests must still pass            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Design Decisions (Addressing Reviewer Feedback)

### D1: TDD Order Enforcement

Each phase follows strict RED-GREEN-REFACTOR:
1. **RED**: Write failing test for the interface
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Clean up while keeping tests green

Tests are written WITHIN each phase, not collected at the end.

### D2: BrowserProtocol as Duck-Typed Interface

BrowserProtocol remains a `typing.Protocol` which is duck-typed:
- **No inheritance required** - classes are compatible if they have matching method signatures
- **New optional methods** don't break existing mocks - mocks only need methods that are actually called
- **Agent checks capability** before calling optional methods via `supports_*()` helpers

### D3: JavaScript Evaluation via evaluate() Method

To enable HTML snippet extraction, add `evaluate()` method to BrowserProtocol:
```python
async def evaluate(self, script: str) -> Any: ...
```
This delegates to Playwright's `page.evaluate()` and enables AIBrowserAgent to extract interactive elements without direct page access.

### D4: ARIA Strategy via click_by_role() Method

To enable pure ARIA targeting (not CSS with fallback), add `click_by_role()` method:
```python
async def click_by_role(self, role: str, name: str | None = None) -> None: ...
```
This wraps Playwright's `page.get_by_role()` directly.

### D5: Accessibility Tree Null Handling

`page.accessibility.snapshot()` can return `None` for certain pages or during navigation. The implementation must handle this explicitly:
```python
async def accessibility_tree(self) -> str:
    snapshot = await self._page.accessibility.snapshot()
    if snapshot is None:
        return "{}"  # Return empty tree, not crash
    pruned = self._prune_a11y_tree(snapshot, max_depth=5)
    return json.dumps(pruned, indent=2)
```

### D6: Thread Safety for asyncio.to_thread()

The Anthropic SDK uses `httpx` internally, which is thread-safe for concurrent requests. The `anthropic.Anthropic` client can be safely called from `asyncio.to_thread()`. However:
- Create one client instance per ClaudeActionPlanner (not shared across threads)
- Each call to `_call_claude_sync()` is independent and stateless

### D7: Shadow DOM Limitation

The HTML snippet extraction JavaScript uses `querySelectorAll()` which does not pierce shadow DOM boundaries. This is a **known limitation**:
- Most subscription cancellation pages (Netflix, etc.) use standard DOM
- If shadow DOM issues arise, future enhancement can add `shadowRoot` traversal
- Current implementation provides graceful degradation (missing elements won't crash)

### D8: evaluate() Method Relationship

The `evaluate()` method exists in two places:
1. **PlaywrightBrowser.evaluate()** (browser.py) - Delegates to `page.evaluate()`
2. **AIBrowserAgent._extract_html_snippet()** (agent.py) - Calls `browser.evaluate()` with the JavaScript from design Section 4.3

The agent never accesses `page` directly; it always goes through the browser protocol.

---

## Phase 1: Data Structures

**File**: `src/subterminator/core/protocols.py`
**Goal**: Define all data classes required by subsequent phases.

### TDD Order

1. **Write test file** `tests/unit/test_dataclasses.py` with tests for all dataclasses
2. **Run tests** - all fail (RED)
3. **Implement dataclasses** in protocols.py
4. **Run tests** - all pass (GREEN)

### Tasks

#### 1.1 Write tests for ActionRecord (RED)
```python
def test_action_record_creation():
    record = ActionRecord("click", "Cancel button", True, "2026-02-05T12:00:00Z")
    assert record.action_type == "click"
    assert record.to_dict()["success"] is True
```

#### 1.2 Write tests for ErrorRecord (RED)
```python
def test_error_record_creation():
    record = ErrorRecord("click", "ElementNotFound", "Selector not found", "css", "...")
    assert record.to_dict()["strategy"] == "css"
```

#### 1.3 Write tests for TargetStrategy (RED)
```python
def test_target_strategy_css_requires_selector():
    with pytest.raises(ValueError):
        TargetStrategy(method="css")  # Missing css_selector

def test_target_strategy_aria_requires_role():
    with pytest.raises(ValueError):
        TargetStrategy(method="aria")  # Missing aria_role

def test_target_strategy_aria_name_optional():
    strategy = TargetStrategy(method="aria", aria_role="button")  # OK
    assert strategy.aria_name is None
```

#### 1.4 Write tests for ActionPlan (RED)
```python
def test_action_plan_max_fallbacks():
    primary = TargetStrategy(method="css", css_selector="#btn")
    fallbacks = [TargetStrategy(method="text", text_content=f"text{i}") for i in range(4)]
    with pytest.raises(ValueError):
        ActionPlan("click", primary, fallbacks)  # >3 fallbacks

def test_action_plan_confidence_range():
    with pytest.raises(ValueError):
        ActionPlan("click", ..., confidence=1.5)  # >1.0
```

#### 1.5 Write tests for AgentContext (RED)
```python
def test_agent_context_to_prompt_context():
    context = AgentContext(...)
    prompt = context.to_prompt_context()
    assert "URL:" in prompt
    assert "ACCESSIBILITY TREE:" in prompt
```

#### 1.6 Implement all dataclasses (GREEN)
- ActionRecord, ErrorRecord, TargetStrategy
- ActionPlan, AgentContext
- ExecutionResult, ValidationResult

#### 1.7 Update protocols.py __all__ export

### Phase 1 Verification
```bash
uv run pytest tests/unit/test_dataclasses.py -v
# All new tests pass
uv run pytest tests/unit/test_protocols.py -v
# Existing protocol tests still pass
```

---

## Phase 2: BrowserProtocol Extensions

**Files**: `src/subterminator/core/protocols.py`, `src/subterminator/core/browser.py`
**Goal**: Add optional browser capabilities while preserving backward compatibility.

### TDD Order

1. **Run existing tests** - verify baseline (GREEN)
2. **Write new tests** for new methods in `tests/unit/test_browser.py`
3. **Run tests** - new tests fail, existing pass (RED for new, GREEN for existing)
4. **Implement** new methods in PlaywrightBrowser
5. **Run tests** - all pass (GREEN)

### Backward Compatibility Strategy

The new Protocol methods are **optional** in practice:
- BrowserProtocol uses `typing.Protocol` which is structurally typed
- Mock browsers in tests don't need new methods unless tests call them
- AIBrowserAgent checks `supports_*()` before calling optional methods
- `supports_*()` returns False by default (not present = not supported)

### Tasks

#### 2.1 Verify existing tests pass (baseline)
```bash
uv run pytest tests/unit/test_browser.py tests/unit/test_protocols.py -v
```

#### 2.2 Write test for evaluate() (RED)
```python
@pytest.mark.asyncio
async def test_browser_evaluate():
    browser = PlaywrightBrowser(headless=True)
    await browser.launch()
    try:
        await browser.navigate("data:text/html,<div id='test'>hello</div>")
        result = await browser.evaluate("document.getElementById('test').textContent")
        assert result == "hello"
    finally:
        await browser.close()
```

#### 2.3 Write test for accessibility_tree() (RED)
```python
@pytest.mark.asyncio
async def test_browser_accessibility_tree():
    browser = PlaywrightBrowser(headless=True)
    await browser.launch()
    try:
        await browser.navigate("data:text/html,<button>Click me</button>")
        tree = await browser.accessibility_tree()
        assert "button" in tree.lower()
    finally:
        await browser.close()
```

#### 2.4 Write test for click_coordinates() (RED)
```python
@pytest.mark.asyncio
async def test_browser_click_coordinates_negative_raises():
    browser = PlaywrightBrowser(headless=True)
    await browser.launch()
    try:
        with pytest.raises(ValueError):
            await browser.click_coordinates(-1, -1)
    finally:
        await browser.close()
```

#### 2.5 Write test for click_by_role() (RED)
```python
@pytest.mark.asyncio
async def test_browser_click_by_role():
    browser = PlaywrightBrowser(headless=True)
    await browser.launch()
    try:
        await browser.navigate("data:text/html,<button>Submit</button>")
        await browser.click_by_role("button", "Submit")  # Should not raise
    finally:
        await browser.close()
```

#### 2.6 Write test for click_by_text() (RED)
```python
@pytest.mark.asyncio
async def test_browser_click_by_text():
    browser = PlaywrightBrowser(headless=True)
    await browser.launch()
    try:
        await browser.navigate("data:text/html,<a>Cancel Membership</a>")
        await browser.click_by_text("Cancel Membership")  # Should not raise
    finally:
        await browser.close()
```

#### 2.7 Write tests for viewport/scroll methods (RED)
```python
@pytest.mark.asyncio
async def test_browser_viewport_and_scroll():
    browser = PlaywrightBrowser(headless=True)
    await browser.launch()
    try:
        size = await browser.viewport_size()
        assert size[0] > 0 and size[1] > 0

        pos = await browser.scroll_position()
        assert pos == (0, 0)  # Initial position

        await browser.scroll_to(0, 100)
        new_pos = await browser.scroll_position()
        # May or may not scroll depending on page height
    finally:
        await browser.close()
```

#### 2.8 Write tests for supports_*() methods (RED)
```python
def test_playwright_browser_supports_methods():
    browser = PlaywrightBrowser(headless=True)
    assert browser.supports_accessibility_tree() is True
    assert browser.supports_coordinate_clicking() is True
    assert browser.supports_text_clicking() is True
```

#### 2.9 Implement evaluate() in PlaywrightBrowser (GREEN)
```python
async def evaluate(self, script: str) -> Any:
    if not self._page:
        raise RuntimeError("Browser not launched")
    return await self._page.evaluate(script)
```

#### 2.10 Implement accessibility_tree() with null handling (GREEN)
```python
async def accessibility_tree(self) -> str:
    if not self._page:
        raise RuntimeError("Browser not launched")
    snapshot = await self._page.accessibility.snapshot()
    if snapshot is None:
        return "{}"  # Handle null case per D5
    pruned = self._prune_a11y_tree(snapshot, max_depth=5)
    return json.dumps(pruned, indent=2)

def _prune_a11y_tree(self, node: dict | None, depth: int = 0, max_depth: int = 5) -> dict | None:
    # Implementation from design Section 3.2
```

#### 2.11 Implement click_coordinates() (GREEN)
```python
async def click_coordinates(self, x: int, y: int) -> None:
    if not self._page:
        raise RuntimeError("Browser not launched")
    if x < 0 or y < 0:
        raise ValueError(f"Coordinates must be non-negative: ({x}, {y})")
    await self._page.mouse.click(x, y)
```

#### 2.12 Implement click_by_role() (GREEN)
```python
async def click_by_role(self, role: str, name: str | None = None) -> None:
    if not self._page:
        raise RuntimeError("Browser not launched")
    try:
        locator = self._page.get_by_role(cast(Any, role), name=name)
        await locator.click(timeout=3000)
    except PlaywrightTimeoutError as e:
        raise ElementNotFound(f"No element with role={role} name='{name}'") from e
```

#### 2.13 Implement click_by_text() (GREEN)
```python
async def click_by_text(self, text: str, exact: bool = False) -> None:
    if not self._page:
        raise RuntimeError("Browser not launched")
    try:
        locator = self._page.get_by_text(text, exact=exact)
        await locator.click(timeout=3000)
    except PlaywrightTimeoutError as e:
        raise ElementNotFound(f"No element with text '{text}'") from e
```

#### 2.14 Implement viewport/scroll methods (GREEN)
```python
async def viewport_size(self) -> tuple[int, int]:
    if not self._page:
        raise RuntimeError("Browser not launched")
    size = self._page.viewport_size
    return (size["width"], size["height"]) if size else (1280, 720)

async def scroll_position(self) -> tuple[int, int]:
    if not self._page:
        raise RuntimeError("Browser not launched")
    pos = await self._page.evaluate("[window.scrollX, window.scrollY]")
    return (int(pos[0]), int(pos[1]))

async def scroll_to(self, x: int, y: int) -> None:
    if not self._page:
        raise RuntimeError("Browser not launched")
    await self._page.evaluate(f"window.scrollTo({x}, {y})")
```

#### 2.15 Implement supports_*() methods (GREEN)
```python
def supports_accessibility_tree(self) -> bool:
    return True

def supports_coordinate_clicking(self) -> bool:
    return True

def supports_text_clicking(self) -> bool:
    return True
```

#### 2.16 Add method signatures to BrowserProtocol (documentation)
Update BrowserProtocol type hints to document the interface. These are optional - Protocol uses duck typing.

### Phase 2 Verification
```bash
# All existing tests still pass
uv run pytest tests/unit/test_browser.py tests/unit/test_protocols.py -v
# New tests pass
uv run pytest tests/unit/test_browser.py -v -k "evaluate or accessibility or coordinates or role or text or viewport or scroll or supports"
```

---

## Phase 3: ClaudeActionPlanner

**File**: `src/subterminator/core/ai.py`
**Goal**: Add Claude-based action planning with tool_use API.

### TDD Order

1. **Write test file** with mocked Claude responses
2. **Run tests** - fail (RED)
3. **Implement** ClaudeActionPlanner
4. **Run tests** - pass (GREEN)

### Tasks

#### 3.1 Write test for TOOL_SCHEMA structure (RED)
```python
def test_tool_schema_has_required_fields():
    assert ClaudeActionPlanner.TOOL_SCHEMA["name"] == "browser_action"
    schema = ClaudeActionPlanner.TOOL_SCHEMA["input_schema"]
    assert "state" in schema["properties"]
    assert "action_type" in schema["properties"]
    assert "targets" in schema["properties"]
```

#### 3.2 Write test for _parse_tool_response() (RED)
```python
def test_parse_tool_response_valid():
    planner = ClaudeActionPlanner(api_key="test")
    # Mock response with tool_use block
    mock_response = create_mock_tool_response({
        "state": "ACCOUNT_ACTIVE",
        "action_type": "click",
        "targets": [
            {"method": "css", "css": "#cancel-btn"},
            {"method": "text", "text": "Cancel"}
        ],
        "reasoning": "Click cancel button",
        "confidence": 0.9
    })
    plan = planner._parse_tool_response(mock_response)
    assert plan.action_type == "click"
    assert plan.primary_target.method == "css"
    assert len(plan.fallback_targets) == 1
```

#### 3.3 Write test for plan_action() confidence retry (RED)
```python
@pytest.mark.asyncio
async def test_plan_action_retries_on_low_confidence(mocker):
    # First call returns low confidence, second returns high
    mock_responses = [
        create_mock_tool_response(confidence=0.4),
        create_mock_tool_response(confidence=0.8),
    ]
    planner = ClaudeActionPlanner(api_key="test")
    mocker.patch.object(planner.client.messages, 'create', side_effect=mock_responses)

    context = create_test_context()
    plan = await planner.plan_action(context, "Click cancel")
    assert plan.confidence >= 0.6
    assert planner.client.messages.create.call_count == 2
```

#### 3.4 Write test for plan_action() raises on persistent low confidence (RED)
```python
@pytest.mark.asyncio
async def test_plan_action_raises_on_persistent_low_confidence(mocker):
    mock_responses = [
        create_mock_tool_response(confidence=0.3),
        create_mock_tool_response(confidence=0.4),
    ]
    planner = ClaudeActionPlanner(api_key="test")
    mocker.patch.object(planner.client.messages, 'create', side_effect=mock_responses)

    context = create_test_context()
    with pytest.raises(StateDetectionError):
        await planner.plan_action(context, "Click cancel")
```

#### 3.5 Implement TOOL_SCHEMA, SYSTEM_PROMPT, SELF_CORRECT_PROMPT (GREEN)
From design Section 4.4 and 3.4.

#### 3.6 Implement ClaudeActionPlanner.__init__() (GREEN)
```python
def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514", timeout: int = 30):
    self.client = anthropic.Anthropic(api_key=api_key)
    self.model = model
    self.timeout = timeout
```

#### 3.7 Implement _build_messages() (GREEN)
```python
def _build_messages(self, context: AgentContext, goal: str, error_context: str | None) -> list[dict]:
    # Build message with image block + text block
    # Include error_context in text if provided
```

#### 3.8 Implement _parse_tool_response() (GREEN)
```python
def _parse_tool_response(self, response: anthropic.Message) -> ActionPlan:
    # Find tool_use block
    # Parse targets array into TargetStrategy objects
    # Return ActionPlan
```

#### 3.9 Implement _call_claude_sync() (GREEN)
```python
def _call_claude_sync(self, context, goal, error_context, require_high_confidence) -> ActionPlan:
    messages = self._build_messages(context, goal, error_context)
    if require_high_confidence:
        # Append high-confidence instruction
    response = self.client.messages.create(...)
    return self._parse_tool_response(response)
```

#### 3.10 Implement plan_action() with asyncio.to_thread() (GREEN)
```python
async def plan_action(self, context: AgentContext, goal: str, error_context: str | None = None) -> ActionPlan:
    plan = await asyncio.to_thread(self._call_claude_sync, context, goal, error_context, False)
    if plan.confidence >= 0.6:
        return plan
    plan = await asyncio.to_thread(self._call_claude_sync, context, goal, error_context, True)
    if plan.confidence < 0.6:
        raise StateDetectionError(f"Low confidence: {plan.confidence}")
    return plan
```

### Phase 3 Verification
```bash
uv run pytest tests/unit/test_ai.py -v -k "ClaudeActionPlanner"
```

---

## Phase 4: AIBrowserAgent

**File**: `src/subterminator/core/agent.py` (NEW)
**Goal**: Implement the perceive-plan-execute-validate loop.

### TDD Order

1. **Create test file** `tests/unit/test_agent.py`
2. **Write tests** with mock browser/planner/heuristic
3. **Run tests** - fail (RED)
4. **Create agent.py** and implement
5. **Run tests** - pass (GREEN)

### Tasks

#### 4.1 Write test for AIBrowserAgent.__init__() (RED)
```python
def test_agent_init_validates_max_retries():
    with pytest.raises(ValueError):
        AIBrowserAgent(mock_browser, mock_planner, mock_heuristic, max_retries=0)
```

#### 4.2 Write test for perceive() (RED)
```python
@pytest.mark.asyncio
async def test_agent_perceive_returns_context():
    agent = create_test_agent()
    context = await agent.perceive()
    assert isinstance(context, AgentContext)
    assert context.screenshot is not None
    assert context.url != ""
```

#### 4.3 Write test for perceive() graceful degradation (RED)
```python
@pytest.mark.asyncio
async def test_agent_perceive_handles_a11y_failure():
    mock_browser = create_mock_browser()
    mock_browser.supports_accessibility_tree.return_value = False
    agent = AIBrowserAgent(mock_browser, ...)

    context = await agent.perceive()
    assert context.accessibility_tree == "{}"  # Empty fallback
```

#### 4.4 Write test for _extract_html_snippet() via evaluate() (RED)
```python
@pytest.mark.asyncio
async def test_agent_extract_html_snippet():
    mock_browser = create_mock_browser()
    mock_browser.evaluate.return_value = ["<button>Click</button>"]
    agent = AIBrowserAgent(mock_browser, ...)

    snippet = await agent._extract_html_snippet()
    assert "<button>" in snippet
```

#### 4.5 Write test for execute() fallback chain (RED)
```python
@pytest.mark.asyncio
async def test_agent_execute_tries_fallbacks():
    mock_browser = create_mock_browser()
    # CSS fails, text succeeds
    mock_browser.click.side_effect = ElementNotFound("not found")
    mock_browser.click_by_text.return_value = None

    agent = AIBrowserAgent(mock_browser, ...)
    plan = ActionPlan(
        action_type="click",
        primary_target=TargetStrategy(method="css", css_selector="#btn"),
        fallback_targets=[TargetStrategy(method="text", text_content="Button")],
    )

    result = await agent.execute(plan)
    assert result.success is True
    assert result.strategy_used.method == "text"
```

#### 4.6 Write test for execute() with click_by_role for ARIA (RED)
```python
@pytest.mark.asyncio
async def test_agent_execute_uses_click_by_role_for_aria():
    mock_browser = create_mock_browser()
    agent = AIBrowserAgent(mock_browser, ...)

    plan = ActionPlan(
        action_type="click",
        primary_target=TargetStrategy(method="aria", aria_role="button", aria_name="Submit"),
        fallback_targets=[],
    )

    await agent.execute(plan)
    mock_browser.click_by_role.assert_called_with("button", "Submit")
```

#### 4.7 Write test for validate() success and failure (RED)
```python
@pytest.mark.asyncio
async def test_agent_validate_success():
    mock_heuristic = create_mock_heuristic(state=State.RETENTION_OFFER)
    agent = AIBrowserAgent(..., mock_heuristic)

    plan = ActionPlan(..., expected_state=State.RETENTION_OFFER)
    result = ExecutionResult(success=True, action_plan=plan)

    validation = await agent.validate(result)
    assert validation.success is True
    assert validation.actual_state == State.RETENTION_OFFER

@pytest.mark.asyncio
async def test_agent_validate_accepts_state_progression():
    # Expected RETENTION_OFFER but got EXIT_SURVEY (skipped state)
    mock_heuristic = create_mock_heuristic(state=State.EXIT_SURVEY)
    agent = AIBrowserAgent(..., mock_heuristic)

    plan = ActionPlan(..., expected_state=State.RETENTION_OFFER)
    result = ExecutionResult(success=True, action_plan=plan)

    validation = await agent.validate(result)
    assert validation.success is True  # Acceptable progression
```

#### 4.8 Write test for handle_state() full loop (RED)
```python
@pytest.mark.asyncio
async def test_agent_handle_state_full_loop():
    mock_browser = create_mock_browser()
    mock_planner = create_mock_planner(plan=create_test_plan())
    mock_heuristic = create_mock_heuristic(state=State.RETENTION_OFFER)

    agent = AIBrowserAgent(mock_browser, mock_planner, mock_heuristic)
    next_state = await agent.handle_state(State.ACCOUNT_ACTIVE)

    assert next_state == State.RETENTION_OFFER
    mock_planner.plan_action.assert_called_once()
```

#### 4.9 Write test for self-correction loop (RED)
```python
@pytest.mark.asyncio
async def test_agent_self_corrects_on_failure():
    mock_browser = create_mock_browser()
    mock_browser.click.side_effect = [ElementNotFound(""), ElementNotFound(""), None]
    mock_planner = create_mock_planner()
    mock_heuristic = create_mock_heuristic(state=State.RETENTION_OFFER)

    agent = AIBrowserAgent(mock_browser, mock_planner, mock_heuristic, max_retries=3)
    next_state = await agent.handle_state(State.ACCOUNT_ACTIVE)

    # Should have called plan_action multiple times
    assert mock_planner.plan_action.call_count >= 2
```

#### 4.10 Create agent.py with STATE_TRANSITIONS (GREEN)
```python
from subterminator.core.states import State

STATE_TRANSITIONS: dict[State, tuple[str, State | None]] = {
    State.ACCOUNT_ACTIVE: ("Click the cancel membership link", State.RETENTION_OFFER),
    State.RETENTION_OFFER: ("Decline the retention offer", State.EXIT_SURVEY),
    # ... etc from design Section 4.1
}
```

#### 4.11 Implement AIBrowserAgent.__init__() (GREEN)

#### 4.12 Implement perceive() with error handling (GREEN)
```python
async def perceive(self) -> AgentContext:
    try:
        screenshot = await self.browser.screenshot()
        a11y_tree = await self._gather_accessibility_tree()
        html_snippet = await self._extract_html_snippet()
        # ... etc
    except Exception as e:
        # Log and provide degraded context
        logger.warning(f"perceive() partial failure: {e}")
        # Return context with available data
```

#### 4.13 Implement _extract_html_snippet() using browser.evaluate() (GREEN)

**Note:** Uses JavaScript algorithm from **design.md Section 4.3** (see D8 for relationship).
Does NOT pierce shadow DOM (see D7 for limitation).

```python
async def _extract_html_snippet(self) -> str:
    # Full JavaScript implementation from design Section 4.3:
    # - Query interactive elements: button, a, input, select, [role="button"], etc.
    # - Filter to elements within viewport bounds
    # - Truncate long outerHTML to key attributes
    # - Return max 50 elements
    script = """
    () => {
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const selectors = 'button, a, input, select, [role="button"], [role="link"], [role="checkbox"], [role="textbox"]';
        const elements = document.querySelectorAll(selectors);
        const results = [];

        for (const el of elements) {
            const rect = el.getBoundingClientRect();
            if (rect.bottom > 0 && rect.top < vh &&
                rect.right > 0 && rect.left < vw &&
                rect.width > 0 && rect.height > 0) {
                let html = el.outerHTML;
                if (html.length > 500) {
                    const tag = el.tagName.toLowerCase();
                    const attrs = [];
                    for (const attr of ['id', 'class', 'name', 'type', 'role', 'aria-label', 'href']) {
                        if (el.hasAttribute(attr)) {
                            attrs.push(attr + '="' + el.getAttribute(attr) + '"');
                        }
                    }
                    html = '<' + tag + ' ' + attrs.join(' ') + '>' + (el.textContent?.slice(0, 100) || '') + '...truncated</' + tag + '>';
                }
                results.push(html);
            }
        }
        return results.slice(0, 50);
    }
    """
    try:
        elements = await self.browser.evaluate(script)
        snippet = "\n".join(elements)
        return snippet[:5000] if len(snippet) > 5000 else snippet
    except Exception:
        return ""  # Graceful degradation per D7
```

#### 4.14 Implement _try_target_strategy() with click_by_role() (GREEN)
```python
async def _try_target_strategy(self, strategy: TargetStrategy, action_type: str, value: str | None) -> bool:
    try:
        if strategy.method == "css":
            await self.browser.click(strategy.css_selector)
        elif strategy.method == "aria":
            await self.browser.click_by_role(strategy.aria_role, strategy.aria_name)
        elif strategy.method == "text":
            await self.browser.click_by_text(strategy.text_content)
        elif strategy.method == "coordinates":
            await self.browser.click_coordinates(*strategy.coordinates)
        return True
    except (ElementNotFound, PlaywrightTimeoutError):
        return False
```

#### 4.15 Implement execute(), validate(), self_correct(), handle_state() (GREEN)

#### 4.16 Implement clear_history() and _record_* helpers (GREEN)

### Phase 4 Verification
```bash
uv run pytest tests/unit/test_agent.py -v
```

---

## Phase 5: Engine Integration

**File**: `src/subterminator/core/engine.py`
**Goal**: Integrate AIBrowserAgent with backward compatibility.

### TDD Order

1. **Run existing tests** - verify baseline (GREEN)
2. **Write new tests** for agent integration
3. **Run tests** - new tests fail, existing pass (RED for new)
4. **Implement** integration
5. **Run tests** - all pass (GREEN)

### Tasks

#### 5.1 Verify existing tests pass (baseline)
```bash
uv run pytest tests/unit/test_engine.py -v
```

#### 5.2 Write test for engine with agent=None (RED)
```python
@pytest.mark.asyncio
async def test_engine_without_agent_uses_hardcoded():
    engine = CancellationEngine(..., agent=None)
    # Should use existing hardcoded logic
```

#### 5.3 Write test for engine with agent provided (RED)
```python
@pytest.mark.asyncio
async def test_engine_with_agent_delegates():
    mock_agent = create_mock_agent()
    engine = CancellationEngine(..., agent=mock_agent)

    # Simulate state handling
    mock_agent.handle_state.return_value = State.RETENTION_OFFER
    # ... trigger _handle_state
    mock_agent.handle_state.assert_called()
```

#### 5.4 Write test for START and LOGIN_REQUIRED bypass agent (RED)
```python
@pytest.mark.asyncio
async def test_engine_start_state_ignores_agent():
    mock_agent = create_mock_agent()
    engine = CancellationEngine(..., agent=mock_agent)

    # START should use hardcoded, not agent
    # ... trigger START state
    mock_agent.handle_state.assert_not_called()
```

#### 5.5 Write test for API outage fallback (RED)
```python
@pytest.mark.asyncio
async def test_engine_falls_back_on_api_error():
    mock_agent = create_mock_agent()
    mock_agent.handle_state.side_effect = anthropic.APIError("timeout")
    engine = CancellationEngine(..., agent=mock_agent)

    # Should fall back to hardcoded logic, not crash
```

#### 5.6 Add agent parameter to __init__ (GREEN)
```python
def __init__(self, ..., agent: AIBrowserAgent | None = None):
    ...
    self.agent = agent
    self._action_history_cleared = False
```

#### 5.7 Refactor _handle_state to _hardcoded_handle (GREEN)
Rename existing logic, preserve behavior.

#### 5.8 Implement new _handle_state with routing (GREEN)
```python
async def _handle_state(self, state: State) -> State:
    if state in (State.START, State.LOGIN_REQUIRED):
        return await self._handle_specific_state(state)  # Existing logic

    if self.agent:
        try:
            return await self._ai_driven_handle(state)
        except anthropic.APIError:
            # Log and fall through

    return await self._hardcoded_handle(state)
```

#### 5.9 Implement _ai_driven_handle (GREEN)
```python
async def _ai_driven_handle(self, state: State) -> State:
    if state == State.FINAL_CONFIRMATION and not self.dry_run:
        await self._human_checkpoint("CONFIRM", self.config.confirm_timeout)

    if not self._action_history_cleared:
        self.agent.clear_history()
        self._action_history_cleared = True

    return await self.agent.handle_state(state)
```

#### 5.10 Reset flag in run() (GREEN)
```python
async def run(self, dry_run: bool = False) -> CancellationResult:
    self._action_history_cleared = False  # Reset for new run
    # ... existing logic
```

### Phase 5 Verification
```bash
# All existing tests still pass
uv run pytest tests/unit/test_engine.py -v
# Integration test
uv run pytest tests/integration/ -v
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Protocol changes break mocks | Duck typing - mocks only need called methods |
| Circular imports | agent.py imports from protocols only |
| _extract_html_snippet page access | Uses browser.evaluate() |
| ARIA click with empty selector | Uses new click_by_role() method |
| perceive() exceptions | Wrapped with try/except, graceful degradation |

## Estimated Complexity

| Phase | Tests | New Code | Modified Code |
|-------|-------|----------|---------------|
| Phase 1 | ~120 lines | ~150 lines | 0 |
| Phase 2 | ~100 lines | ~100 lines | ~50 lines |
| Phase 3 | ~150 lines | ~200 lines | 0 |
| Phase 4 | ~250 lines | ~400 lines | 0 |
| Phase 5 | ~100 lines | ~50 lines | ~30 lines |
| **Total** | **~720 lines** | **~900 lines** | **~80 lines** |

## Success Criteria

1. All existing tests pass (backward compatibility)
2. New unit tests achieve >90% coverage of new code
3. Engine works with agent=None (fallback mode)
4. Engine works with agent provided (AI mode)
5. API outage triggers graceful fallback
6. TDD order verified: tests written before implementation
