# Design: AI-Driven Browser Control

**Feature ID**: 006
**Status**: Approved
**Created**: 2026-02-05

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SubTerminator CLI                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ CancellationEngine│────▶│  AIBrowserAgent  │────▶│ ClaudeActionPlanner │
│  │  (Orchestrator)   │     │   (AI Control)   │     │   (Claude API)     │
│  └────────┬─────────┘     └────────┬─────────┘     └──────────────────┘    │
│           │                        │                                        │
│           │                        │                                        │
│           ▼                        ▼                                        │
│  ┌──────────────────┐     ┌──────────────────┐                             │
│  │ PlaywrightBrowser │     │HeuristicInterpreter│                          │
│  │  (Browser Ops)    │◀───│   (Validation)     │                           │
│  └──────────────────┘     └──────────────────┘                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────┐
                          │  Chromium/Chrome  │
                          │    (Browser)      │
                          └──────────────────┘
```

### 1.2 Component Responsibilities

| Component | Responsibility | Layer |
|-----------|---------------|-------|
| `CancellationEngine` | Orchestrates flow, manages state transitions, human checkpoints | Application |
| `AIBrowserAgent` | AI-driven perceive-plan-execute-validate loop | Agent |
| `ClaudeActionPlanner` | Claude API integration for action planning | AI |
| `HeuristicInterpreter` | Fast rule-based validation (repurposed) | Validation |
| `PlaywrightBrowser` | Browser automation operations | Infrastructure |

### 1.3 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI-Driven State Handling                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. PERCEIVE          2. PLAN              3. EXECUTE         4. VALIDATE  │
│   ┌──────────┐        ┌──────────┐         ┌──────────┐       ┌──────────┐ │
│   │Screenshot│        │ Claude   │         │ Browser  │       │Heuristic │ │
│   │A11y Tree │───────▶│ tool_use │────────▶│  click/  │──────▶│ Interpret│ │
│   │HTML Snip │        │          │         │  fill    │       │          │ │
│   │URL/Text  │        │ActionPlan│         │          │       │ Compare  │ │
│   └──────────┘        └──────────┘         └──────────┘       └────┬─────┘ │
│                                                                     │       │
│                              ┌──────────────────────────────────────┘       │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │ State matches?   │                                     │
│                    │   expected?      │                                     │
│                    └────────┬─────────┘                                     │
│                             │                                               │
│               ┌─────────────┴─────────────┐                                │
│               │                           │                                │
│               ▼ YES                       ▼ NO                             │
│        ┌────────────┐              ┌────────────┐                          │
│        │ Next State │              │Self-Correct│                          │
│        │            │              │ (max 3x)   │                          │
│        └────────────┘              └────────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Component Design

### 2.1 AIBrowserAgent

**Purpose**: Encapsulates the AI-driven browser control loop.

**Location**: `src/subterminator/core/agent.py` (new file)

**Dependencies**:
- `BrowserProtocol` - for browser operations
- `ClaudeActionPlanner` - for AI planning
- `HeuristicInterpreter` - for validation

```
┌─────────────────────────────────────────────────────────────────┐
│                        AIBrowserAgent                            │
├─────────────────────────────────────────────────────────────────┤
│ - browser: BrowserProtocol                                      │
│ - planner: ClaudeActionPlanner                                  │
│ - heuristic: HeuristicInterpreter                               │
│ - max_retries: int = 3                                          │
│ - _action_history: list[ActionRecord]                           │
│ - _error_history: list[ErrorRecord]                             │
├─────────────────────────────────────────────────────────────────┤
│ + perceive() -> AgentContext                                    │
│ + plan(context, goal) -> ActionPlan                             │
│ + execute(plan) -> ExecutionResult                              │
│ + validate(result) -> ValidationResult                          │
│ + self_correct(context, failure, attempt) -> ActionPlan         │
│ + handle_state(state) -> State                                  │
├─────────────────────────────────────────────────────────────────┤
│ - _gather_accessibility_tree() -> str                           │
│ - _extract_html_snippet() -> str                                │
│ - _try_target_strategy(strategy) -> bool                        │
│ - _record_action(action, success)                               │
│ - _record_error(error, strategy)                                │
└─────────────────────────────────────────────────────────────────┘
```

**State Machine**:
```
                     ┌──────────────┐
                     │   PERCEIVE   │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
              ┌──────│    PLAN      │
              │      └──────┬───────┘
              │             │
              │             ▼
              │      ┌──────────────┐
              │      │   EXECUTE    │
              │      └──────┬───────┘
              │             │
              │             ▼
              │      ┌──────────────┐
              │      │   VALIDATE   │──────┐
              │      └──────────────┘      │
              │             │              │
              │      success│        fail  │ (attempt < 3)
              │             ▼              │
              │      ┌──────────────┐      │
              │      │  NEXT STATE  │      │
              │      └──────────────┘      │
              │                            │
              │                            ▼
              │                     ┌──────────────┐
              └─────────────────────│ SELF-CORRECT │
                                    └──────────────┘
                                           │
                                           │ (attempt >= 3)
                                           ▼
                                    ┌──────────────┐
                                    │   UNKNOWN    │
                                    └──────────────┘
```

### 2.2 ClaudeActionPlanner

**Purpose**: Interfaces with Claude API for action planning.

**Location**: `src/subterminator/core/ai.py` (extend existing file)

**Key Design Decisions**:
1. Uses `tool_use` API for structured output
2. Includes screenshot as vision input
3. Context includes accessibility tree + HTML snippet for hybrid identification

```
┌─────────────────────────────────────────────────────────────────┐
│                      ClaudeActionPlanner                         │
├─────────────────────────────────────────────────────────────────┤
│ - client: anthropic.Anthropic                                   │
│ - model: str = "claude-sonnet-4-20250514"                       │
│ - timeout: int = 30                                             │
├─────────────────────────────────────────────────────────────────┤
│ + plan_action(context, goal, error_context?) -> ActionPlan      │
├─────────────────────────────────────────────────────────────────┤
│ - _build_messages(context, goal, error_context) -> list         │
│ - _parse_tool_response(response) -> ActionPlan                  │
│ - _build_system_prompt() -> str                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Claude API Message Structure**:
```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_base64
                }
            },
            {
                "type": "text",
                "text": f"""
                Goal: {goal}
                URL: {context.url}

                Accessibility Tree:
                {context.accessibility_tree}

                HTML Snippet:
                {context.html_snippet}

                Previous Actions: {context.previous_actions}
                Errors: {context.error_history}
                """
            }
        ]
    }
]
```

### 2.3 BrowserProtocol Extensions

**Purpose**: Add optional capabilities for AI agent.

**Location**: `src/subterminator/core/protocols.py` (extend existing)

**Backward Compatibility Strategy**:
- New methods have default implementations that raise `NotImplementedError`
- Capability check methods return `False` by default
- Agent gracefully degrades when capabilities unavailable

```
┌─────────────────────────────────────────────────────────────────┐
│                  BrowserProtocol (Extended)                      │
├─────────────────────────────────────────────────────────────────┤
│ EXISTING (unchanged):                                            │
│ + launch() -> None                                               │
│ + navigate(url, timeout) -> None                                 │
│ + click(selector, fallback_role?, timeout) -> None               │
│ + fill(selector, value) -> None                                  │
│ + select_option(selector, value?) -> None                        │
│ + screenshot(path?) -> bytes                                     │
│ + html() -> str                                                  │
│ + url() -> str                                                   │
│ + text_content() -> str                                          │
│ + close() -> None                                                │
│ + is_cdp_connection: bool                                        │
├─────────────────────────────────────────────────────────────────┤
│ NEW (optional):                                                  │
│ + accessibility_tree() -> str    [default: NotImplementedError]  │
│ + click_coordinates(x, y) -> None [default: NotImplementedError] │
│ + scroll_to(x, y) -> None        [default: NotImplementedError]  │
│ + viewport_size() -> tuple       [default: NotImplementedError]  │
│ + scroll_position() -> tuple     [default: NotImplementedError]  │
│ + click_by_text(text) -> None    [default: NotImplementedError]  │
│ + supports_accessibility_tree() -> bool [default: False]         │
│ + supports_coordinate_clicking() -> bool [default: False]        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 PlaywrightBrowser Extensions

**Purpose**: Implement new optional methods.

**Location**: `src/subterminator/core/browser.py` (extend existing)

**Implementation Mapping**:
| New Method | Playwright API |
|------------|---------------|
| `accessibility_tree()` | `page.accessibility.snapshot()` |
| `click_coordinates(x, y)` | `page.mouse.click(x, y)` |
| `scroll_to(x, y)` | `page.evaluate(f"window.scrollTo({x}, {y})")` |
| `viewport_size()` | `page.viewport_size` |
| `scroll_position()` | `page.evaluate("[window.scrollX, window.scrollY]")` |
| `click_by_text(text)` | `page.get_by_text(text).click()` |

### 2.5 CancellationEngine Integration

**Purpose**: Integrate AI agent while preserving backward compatibility.

**Location**: `src/subterminator/core/engine.py` (modify existing)

**Changes**:
1. Add optional `agent` parameter to constructor
2. Modify `_handle_state()` to delegate to agent when available
3. Preserve all existing hardcoded logic as fallback

```python
class CancellationEngine:
    def __init__(
        self,
        service: ServiceProtocol,
        browser: BrowserProtocol,
        heuristic: HeuristicInterpreter,
        ai: AIInterpreterProtocol | None,
        session: SessionLogger,
        config: AppConfig,
        output_callback: Callable[[str, str], None] | None = None,
        input_callback: Callable[[str, int], str | None] | None = None,
        agent: AIBrowserAgent | None = None,  # NEW
    ):
        # ... existing init
        self.agent = agent  # NEW
```

**State Routing Decision Tree**:
```
_handle_state(state):
    │
    ├── state == START?
    │   └── Always: navigate to entry_url (hardcoded)
    │
    ├── state == LOGIN_REQUIRED?
    │   └── Always: human checkpoint AUTH (hardcoded)
    │
    ├── agent available?
    │   ├── YES: return await agent.handle_state(state)
    │   │        └── On exception: fallback to hardcoded
    │   │
    │   └── NO: existing hardcoded switch/case
    │
    └── FINAL_CONFIRMATION with AI?
        └── human checkpoint CONFIRM still required
```

## 3. Technical Decisions

### 3.1 Tool Use vs Raw JSON

**Decision**: Use Claude's `tool_use` API for action planning.

**Rationale**:
- Structured output guaranteed by API
- Type validation on inputs
- Better error messages on malformed responses
- Lower chance of JSON parsing errors

**Alternative Considered**: Raw JSON in message content (current approach for `ClaudeInterpreter`). Rejected due to fragility.

### 3.2 Context Windowing Strategy

**Decision**: Send pruned context to balance accuracy and cost.

| Context | Strategy | Rationale |
|---------|----------|-----------|
| Screenshot | Full page | Vision is primary understanding method |
| Accessibility Tree | Pruned to max_depth=5, visible only | Large trees dilute signal |
| HTML Snippet | Interactive elements (`button`, `a`, `input`, `select`) in viewport | Focus on actionable elements |
| Action History | Last 5 | Sufficient for context |
| Error History | All in current flow | Important for self-correction |

**Pruning Algorithm for Accessibility Tree**:
```python
def prune_a11y_tree(node, depth=0, max_depth=5):
    if depth > max_depth:
        return None

    pruned = {
        "role": node.get("role"),
        "name": node.get("name", "")[:100],  # Truncate long names
    }

    if "children" in node:
        pruned["children"] = [
            child for child in
            (prune_a11y_tree(c, depth+1, max_depth) for c in node["children"])
            if child is not None
        ]

    return pruned
```

### 3.3 Fallback Strategy Order

**Decision**: Try element identification in order: CSS → ARIA → Text → Coordinates.

**Rationale**:
1. **CSS**: Most precise, fastest execution
2. **ARIA**: Semantic, resilient to styling changes
3. **Text**: User-visible, resilient to DOM changes
4. **Coordinates**: Last resort, requires screenshot recapture

**Timeout per Strategy**: 3 seconds (total max: 12 seconds)

### 3.4 Self-Correction Prompt Engineering

**Decision**: Reflection prompt explicitly forbids repeating failed strategies.

```python
SELF_CORRECT_PROMPT = """
FAILED ACTION:
- Attempted: {action_type} on {target_description}
- Strategy: {failed_strategy}
- Error: {error_message}

PREVIOUS ATTEMPTS THIS ACTION:
{previous_attempts_list}

REQUIREMENT:
You MUST use a DIFFERENT targeting strategy.
Strategies already tried: {strategies_tried}

If CSS failed, try ARIA.
If ARIA failed, try text search.
If text failed, try coordinates (last resort).

Analyze the screenshot and accessibility tree to find an alternative path.
"""
```

### 3.5 API Outage Handling

**Decision**: Catch `anthropic.APIError` and fall back to hardcoded logic.

```python
async def handle_state(self, state: State) -> State:
    try:
        return await self._ai_driven_handle(state)
    except anthropic.APIError as e:
        logger.warning(f"Claude API unavailable: {e}. Falling back to hardcoded.")
        return await self._hardcoded_handle(state)
```

## 4. Detailed Algorithms (Addressing Review Feedback)

### 4.1 Goal Selection for State Handling

**Issue**: How does handle_state() determine what goal to pass to plan()?

**Solution**: Use state-to-goal mapping with expected next state:

```python
# In AIBrowserAgent

STATE_TRANSITIONS: dict[State, tuple[str, State | None]] = {
    # (goal_description, expected_next_state)
    State.ACCOUNT_ACTIVE: (
        "Click the cancel membership link to start cancellation flow",
        State.RETENTION_OFFER  # May also be EXIT_SURVEY or FINAL_CONFIRMATION
    ),
    State.RETENTION_OFFER: (
        "Decline the retention offer and continue with cancellation",
        State.EXIT_SURVEY  # May also be FINAL_CONFIRMATION
    ),
    State.EXIT_SURVEY: (
        "Complete or skip the exit survey to proceed",
        State.FINAL_CONFIRMATION
    ),
    State.FINAL_CONFIRMATION: (
        "Click the final confirmation button to complete cancellation",
        State.COMPLETE
    ),
    State.THIRD_PARTY_BILLING: (
        "Identify third-party billing provider information",
        None  # Terminal for AI - reports to engine
    ),
    State.ACCOUNT_CANCELLED: (
        "Verify the account shows as cancelled",
        State.COMPLETE
    ),
    State.UNKNOWN: (
        "Analyze the page to identify current state and find navigation path",
        None  # Expected state determined by Claude's state detection
    ),
}

async def handle_state(self, state: State) -> State:
    goal, expected_next = self.STATE_TRANSITIONS.get(
        state,
        ("Navigate to proceed with cancellation", None)
    )

    for attempt in range(self.max_retries):
        context = await self.perceive()
        plan = await self.plan(context, goal)

        # For UNKNOWN state, Claude detects expected state
        if expected_next is None:
            expected_next = plan.expected_state

        plan.expected_state = expected_next
        # ... continue with execute/validate
```

### 4.2 Validation Interface with HeuristicInterpreter

**Issue**: How does validate() call HeuristicInterpreter and create ValidationResult?

**Solution**: validate() fetches URL/text from browser and calls heuristic.interpret():

```python
async def validate(self, result: ExecutionResult) -> ValidationResult:
    """Validate action succeeded using heuristics.

    Algorithm:
    1. Get current URL and text content from browser
    2. Call heuristic.interpret(url, text) to detect actual state
    3. Compare detected state with expected state from action plan
    4. Return ValidationResult
    """
    # Get current page state via browser
    url = await self.browser.url()
    text = await self.browser.text_content()

    # Use heuristic for fast state detection
    interpretation = self.heuristic.interpret(url, text)

    expected = result.action_plan.expected_state or State.UNKNOWN
    actual = interpretation.state

    return ValidationResult(
        success=(actual == expected) or (
            # Also accept if we reached a later state in the flow
            # e.g., expected RETENTION_OFFER but got EXIT_SURVEY
            self._is_valid_state_progression(expected, actual)
        ),
        expected_state=expected,
        actual_state=actual,
        confidence=interpretation.confidence,
        message=interpretation.reasoning,
    )

def _is_valid_state_progression(self, expected: State, actual: State) -> bool:
    """Check if actual state is a valid progression from expected.

    Sometimes we skip states (e.g., no retention offer shown).
    """
    VALID_PROGRESSIONS = {
        State.RETENTION_OFFER: {State.EXIT_SURVEY, State.FINAL_CONFIRMATION},
        State.EXIT_SURVEY: {State.FINAL_CONFIRMATION, State.COMPLETE},
        State.FINAL_CONFIRMATION: {State.COMPLETE},
    }
    return actual in VALID_PROGRESSIONS.get(expected, set())
```

### 4.3 HTML Snippet Extraction Algorithm

**Issue**: How to extract interactive elements within viewport?

**Solution**: Use Playwright's JavaScript evaluation to filter elements:

```python
async def _extract_html_snippet(self) -> str:
    """Extract interactive elements within current viewport.

    Algorithm:
    1. Get viewport dimensions
    2. Query all interactive elements (button, a, input, select, [role])
    3. Filter to those within viewport bounds
    4. Serialize outerHTML with truncation

    Returns:
        HTML string of interactive elements (~5KB max).
    """
    if not self._page:
        raise RuntimeError("Browser not launched")

    # JavaScript to extract interactive elements in viewport
    script = """
    () => {
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const selectors = 'button, a, input, select, [role="button"], [role="link"], [role="checkbox"], [role="textbox"]';
        const elements = document.querySelectorAll(selectors);
        const results = [];

        for (const el of elements) {
            const rect = el.getBoundingClientRect();
            // Check if element is at least partially in viewport
            if (rect.bottom > 0 && rect.top < vh &&
                rect.right > 0 && rect.left < vw &&
                rect.width > 0 && rect.height > 0) {

                // Get a reasonable representation
                let html = el.outerHTML;
                if (html.length > 500) {
                    // Truncate long elements, keep tag and key attributes
                    const tag = el.tagName.toLowerCase();
                    const attrs = [];
                    for (const attr of ['id', 'class', 'name', 'type', 'role', 'aria-label', 'href']) {
                        if (el.hasAttribute(attr)) {
                            attrs.push(`${attr}="${el.getAttribute(attr)}"`);
                        }
                    }
                    html = `<${tag} ${attrs.join(' ')}>${el.textContent?.slice(0, 100) || ''}...truncated</${tag}>`;
                }
                results.push(html);
            }
        }
        return results.slice(0, 50);  // Max 50 elements
    }
    """

    elements = await self._page.evaluate(script)

    # Join and truncate to ~5KB
    snippet = "\n".join(elements)
    if len(snippet) > 5000:
        snippet = snippet[:5000] + "\n<!-- truncated -->"

    return snippet
```

### 4.4 Tool Schema with Multiple Targeting Strategies

**Issue**: Tool schema allows single target, but ActionPlan needs primary + fallbacks.

**Solution**: Update tool schema to accept array of targets:

```python
TOOL_SCHEMA = {
    "name": "browser_action",
    "description": "Execute a browser action to progress toward the goal",
    "input_schema": {
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "Detected current page state",
                "enum": [
                    "LOGIN_REQUIRED", "ACCOUNT_ACTIVE", "ACCOUNT_CANCELLED",
                    "THIRD_PARTY_BILLING", "RETENTION_OFFER", "EXIT_SURVEY",
                    "FINAL_CONFIRMATION", "COMPLETE", "FAILED", "UNKNOWN"
                ]
            },
            "expected_next_state": {
                "type": "string",
                "description": "Expected state after this action succeeds",
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
            "targets": {
                "type": "array",
                "description": "Element targeting strategies in priority order (provide 2-4)",
                "items": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["css", "aria", "text", "coordinates"]
                        },
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
                    },
                    "required": ["method"]
                },
                "minItems": 1,
                "maxItems": 4
            },
            "value": {"type": "string"},
            "reasoning": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": ["state", "action_type", "targets", "reasoning", "confidence"]
    }
}
```

**Parsing Updated Response**:
```python
def _parse_tool_response(self, response: anthropic.Message) -> ActionPlan:
    # Find tool_use block
    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None
    )
    if not tool_use or tool_use.name != "browser_action":
        raise StateDetectionError("No browser_action tool use in response")

    data = tool_use.input

    # Parse targets array into TargetStrategy objects
    targets = []
    for t in data["targets"]:
        targets.append(TargetStrategy(
            method=t["method"],
            css_selector=t.get("css"),
            aria_role=t.get("aria_role"),
            aria_name=t.get("aria_name"),
            text_content=t.get("text"),
            coordinates=tuple(t["coordinates"]) if t.get("coordinates") else None,
        ))

    # Map expected_next_state to State enum
    expected_state = None
    if "expected_next_state" in data:
        try:
            expected_state = State[data["expected_next_state"]]
        except KeyError:
            pass

    return ActionPlan(
        action_type=data["action_type"],
        primary_target=targets[0],
        fallback_targets=targets[1:4],  # Max 3 fallbacks
        value=data.get("value"),
        reasoning=data.get("reasoning", ""),
        confidence=data.get("confidence", 0.5),
        expected_state=expected_state,
    )
```

### 4.5 Confidence Threshold Retry Logic

**Issue**: What happens when confidence < 0.6?

**Solution**: plan_action() retries once, then raises if still low:

```python
async def plan_action(
    self,
    context: AgentContext,
    goal: str,
    error_context: str | None = None,
) -> ActionPlan:
    """Generate action plan with confidence check.

    If confidence < 0.6, retries once with explicit instruction.
    If still low, raises StateDetectionError.
    """
    import asyncio

    # First attempt
    plan = await asyncio.to_thread(
        self._call_claude, context, goal, error_context, require_high_confidence=False
    )

    if plan.confidence >= 0.6:
        return plan

    # Retry with explicit high-confidence instruction
    plan = await asyncio.to_thread(
        self._call_claude, context, goal, error_context, require_high_confidence=True
    )

    if plan.confidence < 0.6:
        raise StateDetectionError(
            f"Claude returned low confidence ({plan.confidence}) even after retry. "
            f"Reasoning: {plan.reasoning}"
        )

    return plan

def _call_claude(
    self,
    context: AgentContext,
    goal: str,
    error_context: str | None,
    require_high_confidence: bool,
) -> ActionPlan:
    """Synchronous Claude API call (run in thread)."""
    messages = self._build_messages(context, goal, error_context)

    if require_high_confidence:
        messages[0]["content"][-1]["text"] += (
            "\n\nIMPORTANT: Your previous response had low confidence. "
            "Please analyze more carefully and provide a response with confidence >= 0.6. "
            "If you cannot identify the target with high confidence, explain why in reasoning."
        )

    response = self.client.messages.create(
        model=self.model,
        max_tokens=1000,
        system=self.SYSTEM_PROMPT,
        tools=[self.TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "browser_action"},
        messages=messages,
    )

    return self._parse_tool_response(response)
```

### 4.6 Async Threading for Claude API

**Issue**: Anthropic SDK is synchronous; async methods need threading.

**Solution**: All Claude API calls use `asyncio.to_thread()`:

```python
import asyncio

async def plan_action(self, context, goal, error_context=None) -> ActionPlan:
    # Run synchronous API call in thread pool to avoid blocking event loop
    return await asyncio.to_thread(
        self._call_claude_sync, context, goal, error_context
    )

def _call_claude_sync(self, context, goal, error_context) -> ActionPlan:
    """Synchronous implementation (called from thread)."""
    messages = self._build_messages(context, goal, error_context)
    response = self.client.messages.create(...)  # Synchronous
    return self._parse_tool_response(response)
```

### 4.7 ARIA Strategy Relaxation

**Issue**: TargetStrategy requires both aria_role and aria_name, but role-only is valid.

**Solution**: Make aria_name optional:

```python
@dataclass
class TargetStrategy:
    method: Literal["css", "aria", "text", "coordinates"]
    css_selector: str | None = None
    aria_role: str | None = None
    aria_name: str | None = None  # Optional - can target by role only
    text_content: str | None = None
    coordinates: tuple[int, int] | None = None

    def __post_init__(self):
        if self.method == "css" and not self.css_selector:
            raise ValueError("css_selector required when method='css'")
        if self.method == "aria" and not self.aria_role:
            # aria_name is optional, aria_role is required
            raise ValueError("aria_role required when method='aria'")
        if self.method == "text" and not self.text_content:
            raise ValueError("text_content required when method='text'")
        if self.method == "coordinates" and not self.coordinates:
            raise ValueError("coordinates required when method='coordinates'")
```

### 4.8 BrowserProtocol Default Implementations

**Issue**: Python Protocol doesn't support default implementations.

**Solution**: Use a mixin class or move defaults to PlaywrightBrowser:

```python
# protocols.py - Keep Protocol for type checking only
class BrowserProtocol(Protocol):
    # All methods declared without defaults
    async def accessibility_tree(self) -> str: ...
    async def click_coordinates(self, x: int, y: int) -> None: ...
    def supports_accessibility_tree(self) -> bool: ...
    # etc.


# browser.py - Base class with defaults
class BaseBrowser:
    """Base class providing default implementations for optional methods."""

    async def accessibility_tree(self) -> str:
        raise NotImplementedError("accessibility_tree not supported")

    async def click_coordinates(self, x: int, y: int) -> None:
        raise NotImplementedError("click_coordinates not supported")

    def supports_accessibility_tree(self) -> bool:
        return False

    def supports_coordinate_clicking(self) -> bool:
        return False


class PlaywrightBrowser(BaseBrowser):
    """Full implementation with all capabilities."""

    async def accessibility_tree(self) -> str:
        # Real implementation
        ...

    def supports_accessibility_tree(self) -> bool:
        return True  # Override default
```

### 4.9 Engine History Flag Initialization

**Issue**: _action_history_cleared flag not initialized.

**Solution**: Initialize in constructor and reset in run():

```python
class CancellationEngine:
    def __init__(self, ..., agent: AIBrowserAgent | None = None):
        # ... existing init
        self.agent = agent
        self._agent_history_cleared = False  # Initialize flag

    async def run(self, dry_run: bool = False) -> CancellationResult:
        self.dry_run = dry_run
        self._agent_history_cleared = False  # Reset for new run

        try:
            await self.browser.launch()
            # ... existing run logic
```

## 5. File Structure

```
src/subterminator/core/
├── __init__.py          # Add: AIBrowserAgent, AgentContext, ActionPlan exports
├── agent.py             # NEW: AIBrowserAgent implementation
├── ai.py                # MODIFY: Add ClaudeActionPlanner class
├── browser.py           # MODIFY: Add optional methods to PlaywrightBrowser + BaseBrowser
├── engine.py            # MODIFY: Add agent integration
├── protocols.py         # MODIFY: Extend BrowserProtocol, add new dataclasses
└── states.py            # UNCHANGED

tests/
├── unit/
│   ├── test_agent.py    # NEW: AIBrowserAgent unit tests
│   └── test_ai.py       # MODIFY: Add ClaudeActionPlanner tests
└── integration/
    └── test_ai_driven_flow.py  # NEW: End-to-end AI flow tests
```

## 6. Risk Assessment

### 5.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Claude hallucinates invalid selectors | Medium | Medium | Heuristic validation catches wrong outcomes |
| Accessibility tree too large (>context limit) | Medium | Low | Pruning strategy with max_depth |
| Coordinate clicks miss due to scroll | Medium | Medium | Re-capture screenshot before coordinate click |
| Claude API latency spikes | Medium | Low | 30-second timeout, fallback to hardcoded |

### 5.2 Integration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Low | High | Agent is optional, all existing paths preserved |
| Protocol extension breaks mocks | Medium | Medium | Default implementations return NotImplementedError |
| Engine behavior changes unexpectedly | Low | High | Feature flag approach: agent=None by default |

### 5.3 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cost overrun from API calls | Medium | Low | Cost tracking in session logs, ~$0.20/flow expected |
| Slow execution (user perception) | High | Medium | Progress indicators, expected 2-3 min communicated |

## 7. Dependency Graph

```
                    ┌───────────────┐
                    │   anthropic   │
                    │   (external)  │
                    └───────┬───────┘
                            │
                            ▼
┌───────────────┐   ┌───────────────┐
│ BrowserProtocol│◀──│ClaudeAction  │
│               │   │  Planner     │
└───────┬───────┘   └───────┬───────┘
        │                   │
        │                   │
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ Playwright    │   │AIBrowserAgent │◀───────┐
│ Browser       │◀──│               │        │
└───────────────┘   └───────┬───────┘        │
                            │                │
                            ▼                │
                    ┌───────────────┐        │
                    │ Heuristic     │        │
                    │ Interpreter   │────────┘
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Cancellation  │
                    │   Engine      │
                    └───────────────┘
```

**Build Order**:
1. `protocols.py` extensions (dataclasses + protocol methods)
2. `browser.py` extensions (implement new methods)
3. `ai.py` additions (ClaudeActionPlanner)
4. `agent.py` (new file, AIBrowserAgent)
5. `engine.py` modifications (integration)
6. Tests

---

## 9. Interface Contracts

### 7.1 Data Classes (protocols.py)

#### ActionRecord

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class ActionRecord:
    """Immutable record of a previously executed action.

    Used to provide context to Claude about what actions have been taken.

    Attributes:
        action_type: The type of action (click, fill, select, etc.)
        target_description: Human-readable description of the target element
        success: Whether the action succeeded
        timestamp: ISO format timestamp when action was executed

    Example:
        >>> record = ActionRecord(
        ...     action_type="click",
        ...     target_description="Cancel Membership button",
        ...     success=True,
        ...     timestamp="2026-02-05T12:00:00Z"
        ... )
    """
    action_type: str
    target_description: str
    success: bool
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "action": self.action_type,
            "target": self.target_description,
            "success": self.success,
            "time": self.timestamp,
        }
```

#### ErrorRecord

```python
@dataclass(frozen=True)
class ErrorRecord:
    """Immutable record of an error during execution.

    Used for self-correction context - tells Claude what went wrong.

    Attributes:
        action_type: The action that was attempted
        error_type: Exception class name (ElementNotFound, etc.)
        error_message: The error message
        strategy_attempted: Which targeting method was used (css, aria, text, coordinates)
        timestamp: ISO format timestamp

    Example:
        >>> error = ErrorRecord(
        ...     action_type="click",
        ...     error_type="ElementNotFound",
        ...     error_message="Selector '#cancel-btn' not found",
        ...     strategy_attempted="css",
        ...     timestamp="2026-02-05T12:00:05Z"
        ... )
    """
    action_type: str
    error_type: str
    error_message: str
    strategy_attempted: str
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "action": self.action_type,
            "error": f"{self.error_type}: {self.error_message}",
            "strategy": self.strategy_attempted,
            "time": self.timestamp,
        }
```

#### TargetStrategy

```python
from typing import Literal

@dataclass
class TargetStrategy:
    """A single element targeting method.

    Represents one way to identify and interact with an element.
    Only one of the targeting fields should be set based on `method`.

    Attributes:
        method: The targeting method type
        css_selector: CSS selector (when method="css")
        aria_role: ARIA role (when method="aria")
        aria_name: ARIA accessible name (when method="aria")
        text_content: Visible text to match (when method="text")
        coordinates: (x, y) pixel coordinates (when method="coordinates")

    Invariants:
        - If method="css", css_selector must be set
        - If method="aria", aria_role must be set (aria_name optional)
        - If method="text", text_content must be set
        - If method="coordinates", coordinates must be set

    Example:
        >>> css_strategy = TargetStrategy(method="css", css_selector="#cancel-btn")
        >>> aria_strategy = TargetStrategy(
        ...     method="aria",
        ...     aria_role="button",
        ...     aria_name="Cancel Membership"
        ... )
    """
    method: Literal["css", "aria", "text", "coordinates"]
    css_selector: str | None = None
    aria_role: str | None = None
    aria_name: str | None = None
    text_content: str | None = None
    coordinates: tuple[int, int] | None = None

    def __post_init__(self):
        """Validate that required fields are set for the method."""
        if self.method == "css" and not self.css_selector:
            raise ValueError("css_selector required when method='css'")
        if self.method == "aria" and not self.aria_role:
            # aria_name is optional - can target by role only
            raise ValueError("aria_role required when method='aria'")
        if self.method == "text" and not self.text_content:
            raise ValueError("text_content required when method='text'")
        if self.method == "coordinates" and not self.coordinates:
            raise ValueError("coordinates required when method='coordinates'")

    def describe(self) -> str:
        """Human-readable description of this strategy."""
        if self.method == "css":
            return f"CSS: {self.css_selector}"
        elif self.method == "aria":
            return f"ARIA: role={self.aria_role} name='{self.aria_name}'"
        elif self.method == "text":
            return f"Text: '{self.text_content}'"
        else:
            return f"Coordinates: ({self.coordinates[0]}, {self.coordinates[1]})"
```

#### ActionPlan

```python
@dataclass
class ActionPlan:
    """Planned browser action from AI.

    Represents a complete action plan including primary and fallback
    targeting strategies. The executor tries strategies in order:
    primary_target first, then fallback_targets[0], [1], [2].

    Attributes:
        action_type: The type of browser action to execute
        primary_target: First targeting strategy to try
        fallback_targets: Alternative strategies (max 3)
        value: Value for fill/select actions
        reasoning: AI's explanation for choosing this action
        confidence: AI's confidence in this plan (0.0-1.0)
        expected_state: State we expect to reach after this action

    Invariants:
        - len(fallback_targets) <= 3
        - 0.0 <= confidence <= 1.0
        - If action_type in ("fill", "select"), value must be set

    Example:
        >>> plan = ActionPlan(
        ...     action_type="click",
        ...     primary_target=TargetStrategy(method="css", css_selector=".cancel-btn"),
        ...     fallback_targets=[
        ...         TargetStrategy(method="aria", aria_role="button", aria_name="Cancel"),
        ...         TargetStrategy(method="text", text_content="Cancel Membership"),
        ...     ],
        ...     reasoning="Clicking cancel button to start cancellation flow",
        ...     confidence=0.85,
        ...     expected_state=State.RETENTION_OFFER
        ... )
    """
    action_type: Literal["click", "fill", "select", "scroll", "wait", "navigate"]
    primary_target: TargetStrategy
    fallback_targets: list[TargetStrategy]
    value: str | None = None
    reasoning: str = ""
    confidence: float = 0.0
    expected_state: State | None = None

    def __post_init__(self):
        if len(self.fallback_targets) > 3:
            raise ValueError("Maximum 3 fallback targets allowed")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if self.action_type in ("fill", "select") and not self.value:
            raise ValueError(f"value required for {self.action_type} action")

    def all_targets(self) -> list[TargetStrategy]:
        """Return all targets in execution order."""
        return [self.primary_target] + self.fallback_targets
```

#### AgentContext

```python
@dataclass
class AgentContext:
    """Multi-modal context for AI decision making.

    Gathered by AIBrowserAgent.perceive() and passed to ClaudeActionPlanner.

    Attributes:
        screenshot: Full-page screenshot as PNG bytes
        accessibility_tree: JSON string of pruned accessibility tree
        html_snippet: HTML of interactive elements in viewport
        url: Current page URL
        visible_text: Body text content (truncated to ~2KB)
        previous_actions: Last 5 actions taken
        error_history: All errors in current flow
        viewport_size: (width, height) in pixels
        scroll_position: (x, y) scroll offset

    Example:
        >>> context = agent.perceive()
        >>> print(f"URL: {context.url}")
        >>> print(f"Actions taken: {len(context.previous_actions)}")
    """
    screenshot: bytes
    accessibility_tree: str
    html_snippet: str
    url: str
    visible_text: str
    previous_actions: list[ActionRecord]
    error_history: list[ErrorRecord]
    viewport_size: tuple[int, int]
    scroll_position: tuple[int, int]

    def to_prompt_context(self) -> str:
        """Format context for inclusion in Claude prompt.

        Returns formatted string suitable for text portion of message.
        Screenshot is handled separately as an image block.
        """
        actions_text = "\n".join(
            f"  - {a.action_type} on {a.target_description}: {'✓' if a.success else '✗'}"
            for a in self.previous_actions[-5:]
        ) or "  (none)"

        errors_text = "\n".join(
            f"  - {e.action_type} failed ({e.strategy_attempted}): {e.error_message}"
            for e in self.error_history
        ) or "  (none)"

        return f"""URL: {self.url}
Viewport: {self.viewport_size[0]}x{self.viewport_size[1]}
Scroll: ({self.scroll_position[0]}, {self.scroll_position[1]})

ACCESSIBILITY TREE:
{self.accessibility_tree}

HTML SNIPPET:
{self.html_snippet}

PREVIOUS ACTIONS:
{actions_text}

ERRORS:
{errors_text}
"""
```

#### ExecutionResult

```python
@dataclass
class ExecutionResult:
    """Result of executing an action.

    Returned by AIBrowserAgent.execute() after attempting an action plan.

    Attributes:
        success: Whether any targeting strategy succeeded
        action_plan: The plan that was executed
        strategy_used: Which targeting method worked (if success=True)
        error: Error message (if success=False)
        screenshot_after: Screenshot captured after action (for validation)
        elapsed_ms: Time taken to execute in milliseconds

    Example:
        >>> result = await agent.execute(plan)
        >>> if result.success:
        ...     print(f"Used strategy: {result.strategy_used.describe()}")
        ... else:
        ...     print(f"Failed: {result.error}")
    """
    success: bool
    action_plan: ActionPlan
    strategy_used: TargetStrategy | None = None
    error: str | None = None
    screenshot_after: bytes | None = None
    elapsed_ms: int = 0
```

#### ValidationResult

```python
@dataclass
class ValidationResult:
    """Result of heuristic validation after action.

    Returned by AIBrowserAgent.validate() to check if expected state was reached.

    Attributes:
        success: Whether expected_state matches actual_state
        expected_state: What the AI predicted would happen
        actual_state: What the heuristic detected
        confidence: Heuristic's confidence in its detection
        message: Explanation of the validation result

    Example:
        >>> validation = await agent.validate(result)
        >>> if not validation.success:
        ...     print(f"Expected {validation.expected_state}, got {validation.actual_state}")
    """
    success: bool
    expected_state: State
    actual_state: State
    confidence: float
    message: str
```

### 7.2 BrowserProtocol Extensions (protocols.py)

```python
class BrowserProtocol(Protocol):
    """Protocol defining the browser automation interface.

    Extended with optional methods for AI-driven control.
    Implementations MUST implement all existing methods.
    Implementations MAY implement new optional methods.
    """

    # =====================================================================
    # EXISTING METHODS (unchanged, required)
    # =====================================================================

    async def launch(self) -> None: ...
    async def navigate(self, url: str, timeout: int = 30000) -> None: ...
    async def click(
        self,
        selector: str | list[str],
        fallback_role: tuple[str, str] | None = None,
        timeout: int = 5000,
    ) -> None: ...
    async def fill(self, selector: str, value: str) -> None: ...
    async def select_option(self, selector: str, value: str | None = None) -> None: ...
    async def screenshot(self, path: str | None = None) -> bytes: ...
    async def html(self) -> str: ...
    async def url(self) -> str: ...
    async def text_content(self) -> str: ...
    async def close(self) -> None: ...

    @property
    def is_cdp_connection(self) -> bool: ...

    # =====================================================================
    # NEW OPTIONAL METHODS (for AI agent)
    # =====================================================================

    async def accessibility_tree(self) -> str:
        """Get accessibility tree as JSON string.

        Returns:
            JSON string representation of the accessibility tree.

        Raises:
            NotImplementedError: If browser doesn't support this.
            RuntimeError: If browser not launched.

        Note:
            Default implementation raises NotImplementedError.
            PlaywrightBrowser implements via page.accessibility.snapshot().
        """
        raise NotImplementedError("accessibility_tree not supported")

    async def click_coordinates(self, x: int, y: int) -> None:
        """Click at specific pixel coordinates.

        Args:
            x: X coordinate relative to viewport (0 = left edge).
            y: Y coordinate relative to viewport (0 = top edge).

        Raises:
            NotImplementedError: If browser doesn't support this.
            RuntimeError: If browser not launched.
            ValueError: If coordinates are negative.

        Note:
            Coordinates are viewport-relative, not page-relative.
            To click on page coordinates, scroll first.
        """
        raise NotImplementedError("click_coordinates not supported")

    async def click_by_text(self, text: str, exact: bool = False) -> None:
        """Click element by visible text.

        Args:
            text: The text to search for.
            exact: If True, require exact match. If False, substring match.

        Raises:
            NotImplementedError: If browser doesn't support this.
            ElementNotFound: If no element with text found.
        """
        raise NotImplementedError("click_by_text not supported")

    async def scroll_to(self, x: int, y: int) -> None:
        """Scroll viewport to absolute position.

        Args:
            x: Horizontal scroll position in pixels.
            y: Vertical scroll position in pixels.

        Raises:
            NotImplementedError: If browser doesn't support this.
        """
        raise NotImplementedError("scroll_to not supported")

    async def viewport_size(self) -> tuple[int, int]:
        """Get current viewport dimensions.

        Returns:
            Tuple of (width, height) in pixels.

        Raises:
            NotImplementedError: If browser doesn't support this.
        """
        raise NotImplementedError("viewport_size not supported")

    async def scroll_position(self) -> tuple[int, int]:
        """Get current scroll position.

        Returns:
            Tuple of (x, y) scroll offset in pixels.

        Raises:
            NotImplementedError: If browser doesn't support this.
        """
        raise NotImplementedError("scroll_position not supported")

    def supports_accessibility_tree(self) -> bool:
        """Check if accessibility_tree() is available.

        Returns:
            True if accessibility_tree() is implemented, False otherwise.
        """
        return False

    def supports_coordinate_clicking(self) -> bool:
        """Check if click_coordinates() is available.

        Returns:
            True if click_coordinates() is implemented, False otherwise.
        """
        return False

    def supports_text_clicking(self) -> bool:
        """Check if click_by_text() is available.

        Returns:
            True if click_by_text() is implemented, False otherwise.
        """
        return False
```

### 7.3 AIBrowserAgent (agent.py)

```python
class AIBrowserAgent:
    """AI agent for browser automation.

    Implements a perceive-plan-execute-validate loop with self-correction.
    Used by CancellationEngine for AI-driven state handling.

    Attributes:
        browser: Browser for executing actions.
        planner: Claude-based action planner.
        heuristic: Heuristic interpreter for validation.
        max_retries: Maximum self-correction attempts (default: 3).

    Example:
        >>> browser = PlaywrightBrowser()
        >>> planner = ClaudeActionPlanner()
        >>> heuristic = HeuristicInterpreter()
        >>> agent = AIBrowserAgent(browser, planner, heuristic)
        >>>
        >>> # In CancellationEngine:
        >>> next_state = await agent.handle_state(State.ACCOUNT_ACTIVE)
    """

    # Goal descriptions for each state
    STATE_GOALS: dict[State, str] = {
        State.ACCOUNT_ACTIVE: "Click the cancel membership link to start cancellation",
        State.RETENTION_OFFER: "Decline the retention offer and continue to cancel",
        State.EXIT_SURVEY: "Complete or skip the exit survey",
        State.FINAL_CONFIRMATION: "Confirm the cancellation (user has approved)",
        State.THIRD_PARTY_BILLING: "Identify third-party billing information",
        State.ACCOUNT_CANCELLED: "Verify account is already cancelled",
        State.UNKNOWN: "Identify the current page and find a way to proceed",
    }

    def __init__(
        self,
        browser: BrowserProtocol,
        planner: ClaudeActionPlanner,
        heuristic: HeuristicInterpreter,
        max_retries: int = 3,
    ) -> None:
        """Initialize the AI browser agent.

        Args:
            browser: Browser protocol implementation.
            planner: Claude-based action planner.
            heuristic: Heuristic interpreter for validation.
            max_retries: Maximum self-correction attempts per action.

        Raises:
            ValueError: If max_retries < 1.
        """
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        self.browser = browser
        self.planner = planner
        self.heuristic = heuristic
        self.max_retries = max_retries

        self._action_history: list[ActionRecord] = []
        self._error_history: list[ErrorRecord] = []

    async def perceive(self) -> AgentContext:
        """Gather current page context.

        Collects multi-modal context from the browser:
        - Screenshot (required)
        - Accessibility tree (optional, graceful degradation)
        - HTML snippet (required)
        - URL and text content (required)

        Returns:
            AgentContext with all available modalities.

        Raises:
            RuntimeError: If browser not launched.
        """
        ...

    async def plan(self, context: AgentContext, goal: str) -> ActionPlan:
        """Plan next action given context and goal.

        Delegates to ClaudeActionPlanner and validates response.

        Args:
            context: Current page context from perceive().
            goal: Human-readable goal description.

        Returns:
            ActionPlan with targeting strategies and confidence.

        Raises:
            StateDetectionError: If Claude returns invalid/low-confidence response.
        """
        ...

    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute the planned action.

        Tries targeting strategies in order (primary, then fallbacks)
        until one succeeds or all fail.

        Execution order:
        1. Try primary_target with 3s timeout
        2. If fail, try fallback_targets[0] with 3s timeout
        3. Continue through fallbacks
        4. Return result with success=True if any worked

        Args:
            plan: The action plan to execute.

        Returns:
            ExecutionResult with success status and details.
        """
        ...

    async def validate(self, result: ExecutionResult) -> ValidationResult:
        """Validate action succeeded using heuristics.

        Compares expected state (from action plan) with actual detected state.

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

        Provides Claude with error context and requires a different strategy.

        Args:
            context: Current page context (fresh from perceive()).
            failure: The validation failure details.
            attempt: Current attempt number (1-3).

        Returns:
            New ActionPlan with different strategy.

        Raises:
            StateDetectionError: If Claude can't generate alternative.
        """
        ...

    async def handle_state(self, state: State) -> State:
        """Handle a state transition.

        Main entry point for AI-driven state handling.
        Implements the full perceive-plan-execute-validate loop with self-correction.

        Algorithm:
        1. perceive() - gather context
        2. plan() - get action from Claude
        3. execute() - try action with fallbacks
        4. validate() - check if expected state reached
        5. If validation fails and attempts < max_retries:
           - perceive() again with fresh context
           - self_correct() - get alternative plan
           - Go to step 3
        6. If max retries exceeded, return State.UNKNOWN

        Args:
            state: Current state to handle.

        Returns:
            Next state after action execution.

        Raises:
            anthropic.APIError: Propagated to engine for fallback handling.
        """
        ...

    def clear_history(self) -> None:
        """Clear action and error history.

        Called by engine at start of new flow.
        """
        self._action_history.clear()
        self._error_history.clear()
```

### 7.4 ClaudeActionPlanner (ai.py)

```python
class ClaudeActionPlanner:
    """Claude-based action planning using tool_use.

    Uses Claude's vision capabilities and structured tool_use output
    to plan browser actions.

    Attributes:
        client: Anthropic API client.
        model: Model identifier (default: claude-sonnet-4-20250514).
        timeout: API call timeout in seconds (default: 30).

    Example:
        >>> planner = ClaudeActionPlanner()
        >>> plan = await planner.plan_action(context, "Click cancel button")
        >>> print(plan.reasoning)
    """

    # Tool schema for structured action output
    TOOL_SCHEMA = {
        "name": "browser_action",
        "description": (
            "Execute a browser action to progress toward the goal. "
            "Analyze the screenshot and accessibility tree to identify "
            "the best element to interact with."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "The detected current page state",
                    "enum": [
                        "LOGIN_REQUIRED", "ACCOUNT_ACTIVE", "ACCOUNT_CANCELLED",
                        "THIRD_PARTY_BILLING", "RETENTION_OFFER", "EXIT_SURVEY",
                        "FINAL_CONFIRMATION", "COMPLETE", "FAILED", "UNKNOWN"
                    ]
                },
                "action_type": {
                    "type": "string",
                    "description": "The type of browser action to execute",
                    "enum": ["click", "fill", "select", "scroll", "wait", "navigate"]
                },
                "target": {
                    "type": "object",
                    "description": "Element targeting (provide multiple methods for fallback)",
                    "properties": {
                        "css": {
                            "type": "string",
                            "description": "CSS selector (preferred if unique)"
                        },
                        "aria_role": {
                            "type": "string",
                            "description": "ARIA role (button, link, textbox, etc.)"
                        },
                        "aria_name": {
                            "type": "string",
                            "description": "ARIA accessible name"
                        },
                        "text": {
                            "type": "string",
                            "description": "Visible text to match"
                        },
                        "coordinates": {
                            "type": "array",
                            "description": "[x, y] pixel coordinates (last resort)",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                },
                "value": {
                    "type": "string",
                    "description": "Value for fill/select actions"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation for why this action and target"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence in this action (0.0-1.0)",
                    "minimum": 0,
                    "maximum": 1
                }
            },
            "required": ["state", "action_type", "target", "reasoning", "confidence"]
        }
    }

    SYSTEM_PROMPT = """You are an AI agent controlling a browser to cancel a subscription.

Your task: Analyze the page and decide what action to take next.

ELEMENT IDENTIFICATION PRIORITY:
1. CSS selector - Use when element has unique id or class
2. ARIA role + name - Use for buttons, links with clear labels
3. Text content - Use when text is visible and unique
4. Coordinates - ONLY as last resort when semantic methods fail

RULES:
- Always provide at least 2 targeting methods when possible
- Confidence should reflect how certain you are about the target
- If page state is unclear, set state to UNKNOWN
- For fill/select actions, you MUST provide a value

IMPORTANT: After clicking, the page will change. Your expected_state in the response
should predict what state the page will be in AFTER the action completes."""

    SELF_CORRECT_PROMPT = """Your previous action FAILED. You must try a DIFFERENT approach.

FAILED ACTION:
- Action: {action_type}
- Target: {target_description}
- Strategy: {failed_strategy}
- Error: {error_message}

STRATEGIES ALREADY TRIED:
{strategies_tried}

REQUIREMENT: Use a DIFFERENT targeting strategy than the ones listed above.
- If CSS failed, try ARIA role/name
- If ARIA failed, try text content
- If text failed, try coordinates (analyze screenshot for position)

Analyze the current screenshot and accessibility tree to find an alternative."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        timeout: int = 30,
    ) -> None:
        """Initialize the planner.

        Args:
            api_key: Anthropic API key. Uses ANTHROPIC_API_KEY env var if None.
            model: Model identifier for Claude.
            timeout: API call timeout in seconds.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.timeout = timeout

    async def plan_action(
        self,
        context: AgentContext,
        goal: str,
        error_context: str | None = None,
    ) -> ActionPlan:
        """Generate an action plan using Claude.

        Args:
            context: Current page context including screenshot.
            goal: What we're trying to achieve.
            error_context: Formatted error info for self-correction.

        Returns:
            ActionPlan parsed from Claude's tool_use response.

        Raises:
            StateDetectionError: If Claude returns invalid response.
            anthropic.APIError: If API call fails.
        """
        ...

    def _build_messages(
        self,
        context: AgentContext,
        goal: str,
        error_context: str | None,
    ) -> list[dict]:
        """Build messages array for Claude API call."""
        ...

    def _parse_tool_response(self, response: anthropic.Message) -> ActionPlan:
        """Parse Claude's tool_use response into ActionPlan.

        Raises:
            StateDetectionError: If response doesn't contain valid tool_use.
        """
        ...
```

### 7.5 CancellationEngine Integration (engine.py)

```python
# Changes to CancellationEngine.__init__
def __init__(
    self,
    service: ServiceProtocol,
    browser: BrowserProtocol,
    heuristic: HeuristicInterpreter,
    ai: AIInterpreterProtocol | None,
    session: SessionLogger,
    config: AppConfig,
    output_callback: Callable[[str, str], None] | None = None,
    input_callback: Callable[[str, int], str | None] | None = None,
    agent: AIBrowserAgent | None = None,  # NEW PARAMETER
):
    """Initialize the CancellationEngine.

    Args:
        service: Service-specific implementation.
        browser: Browser automation interface.
        heuristic: Heuristic-based page state interpreter.
        ai: Optional AI-based page state interpreter (legacy).
        session: Session logger for tracking progress.
        config: Application configuration.
        output_callback: Optional callback for status messages.
        input_callback: Optional callback for human input.
        agent: Optional AI browser agent for AI-driven control.  # NEW

    Note:
        If `agent` is provided, it takes precedence over `ai` for
        state handling (except START and LOGIN_REQUIRED).
        The system falls back to hardcoded logic if agent raises an exception.
    """
    # ... existing init code ...
    self.agent = agent  # NEW


# Changes to CancellationEngine._handle_state
async def _handle_state(self, state: State) -> State:
    """Process current state and determine next state.

    State handling priority:
    1. START, LOGIN_REQUIRED: Always use hardcoded logic
    2. If agent available: Use AI-driven handling with fallback
    3. Otherwise: Use existing hardcoded switch/case

    Args:
        state: The current state to handle.

    Returns:
        The next state to transition to.
    """
    self.output_callback(state.name, f"Handling state: {state.name}")

    # Always use hardcoded logic for START and LOGIN_REQUIRED
    if state == State.START:
        return await self._handle_start()

    if state == State.LOGIN_REQUIRED:
        return await self._handle_login_required()

    # Try AI agent if available
    if self.agent:
        try:
            return await self._ai_driven_handle(state)
        except anthropic.APIError as e:
            self.output_callback(
                state.name,
                f"Claude API unavailable ({e}). Falling back to hardcoded logic."
            )
            # Fall through to hardcoded

    # Existing hardcoded logic
    return await self._hardcoded_handle(state)


async def _ai_driven_handle(self, state: State) -> State:
    """AI-driven state handling.

    Delegates to AIBrowserAgent.handle_state() and preserves
    human checkpoints for FINAL_CONFIRMATION.

    Args:
        state: Current state to handle.

    Returns:
        Next state from AI agent.
    """
    # FINAL_CONFIRMATION still requires human checkpoint
    if state == State.FINAL_CONFIRMATION:
        if self.dry_run:
            self.output_callback(
                state.name,
                "DRY RUN: Would proceed with AI-driven confirmation"
            )
            return State.COMPLETE

        await self._human_checkpoint("CONFIRM", self.config.confirm_timeout)

    # Clear agent history at flow start
    if not self._action_history_cleared:
        self.agent.clear_history()
        self._action_history_cleared = True

    return await self.agent.handle_state(state)


async def _hardcoded_handle(self, state: State) -> State:
    """Existing hardcoded state handling (renamed from original _handle_state).

    Preserved for backward compatibility and fallback.
    """
    # ... existing switch/case logic ...
```

### 7.6 PlaywrightBrowser Extensions (browser.py)

```python
# Add to PlaywrightBrowser class

async def accessibility_tree(self) -> str:
    """Get accessibility tree as JSON string.

    Uses Playwright's page.accessibility.snapshot() and prunes
    to max_depth=5 for reasonable context size.

    Returns:
        JSON string of pruned accessibility tree.

    Raises:
        RuntimeError: If browser not launched.
    """
    if not self._page:
        raise RuntimeError("Browser not launched")

    snapshot = await self._page.accessibility.snapshot()
    pruned = self._prune_a11y_tree(snapshot, max_depth=5)
    return json.dumps(pruned, indent=2)

async def click_coordinates(self, x: int, y: int) -> None:
    """Click at specific pixel coordinates.

    Args:
        x: X coordinate relative to viewport.
        y: Y coordinate relative to viewport.

    Raises:
        RuntimeError: If browser not launched.
        ValueError: If coordinates are negative.
    """
    if not self._page:
        raise RuntimeError("Browser not launched")
    if x < 0 or y < 0:
        raise ValueError(f"Coordinates must be non-negative: ({x}, {y})")

    await self._page.mouse.click(x, y)

async def click_by_text(self, text: str, exact: bool = False) -> None:
    """Click element by visible text.

    Args:
        text: The text to search for.
        exact: If True, exact match. If False, substring match.

    Raises:
        RuntimeError: If browser not launched.
        ElementNotFound: If no matching element found.
    """
    if not self._page:
        raise RuntimeError("Browser not launched")

    try:
        locator = self._page.get_by_text(text, exact=exact)
        await locator.click(timeout=3000)
    except PlaywrightTimeoutError as e:
        raise ElementNotFound(f"No element with text '{text}'") from e

async def scroll_to(self, x: int, y: int) -> None:
    """Scroll viewport to absolute position."""
    if not self._page:
        raise RuntimeError("Browser not launched")

    await self._page.evaluate(f"window.scrollTo({x}, {y})")

async def viewport_size(self) -> tuple[int, int]:
    """Get current viewport dimensions."""
    if not self._page:
        raise RuntimeError("Browser not launched")

    size = self._page.viewport_size
    if size is None:
        return (1280, 720)  # Default fallback
    return (size["width"], size["height"])

async def scroll_position(self) -> tuple[int, int]:
    """Get current scroll position."""
    if not self._page:
        raise RuntimeError("Browser not launched")

    pos = await self._page.evaluate("[window.scrollX, window.scrollY]")
    return (int(pos[0]), int(pos[1]))

def supports_accessibility_tree(self) -> bool:
    """Check if accessibility_tree() is available."""
    return True

def supports_coordinate_clicking(self) -> bool:
    """Check if click_coordinates() is available."""
    return True

def supports_text_clicking(self) -> bool:
    """Check if click_by_text() is available."""
    return True

def _prune_a11y_tree(
    self,
    node: dict | None,
    depth: int = 0,
    max_depth: int = 5,
) -> dict | None:
    """Prune accessibility tree to manageable size.

    Args:
        node: Current node in the tree.
        depth: Current depth.
        max_depth: Maximum depth to traverse.

    Returns:
        Pruned node or None if beyond max_depth.
    """
    if node is None or depth > max_depth:
        return None

    pruned = {
        "role": node.get("role", ""),
        "name": node.get("name", "")[:100],  # Truncate long names
    }

    children = node.get("children", [])
    if children:
        pruned_children = [
            self._prune_a11y_tree(child, depth + 1, max_depth)
            for child in children
        ]
        pruned["children"] = [c for c in pruned_children if c is not None]

    return pruned
```
