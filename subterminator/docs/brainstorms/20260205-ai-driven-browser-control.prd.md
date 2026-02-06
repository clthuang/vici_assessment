# PRD: AI-Driven Browser Control for SubTerminator

**Status**: Draft (Reviewed)
**Created**: 2026-02-05
**Author**: Brainstorming Session

## Executive Summary

Transform SubTerminator from a heuristic-first, hardcoded-action system to an AI-first browser automation framework where Claude controls the main flow with heuristics validating outcomes. This architectural flip prioritizes accuracy over speed, leveraging the hybrid approach of semantic elements + pixel coordinates + HTML dump for maximum reliability.

## Problem Statement

### Current Design (Deliberate Choice)

The current architecture **deliberately** limits AI to state classification only. This was a reasonable starting point that prioritized simplicity and predictability. However, user feedback indicates we should expand AI's role for better adaptability.

### Limitations We Want to Address

1. **Rigid State-Action Mapping**: Each state has hardcoded selectors (`cancel_link`, `decline_offer`). When UI changes, the system breaks.

2. **AI Role Limited by Design**: Claude Vision currently handles state classification only. The `actions` field in `AIInterpretation` is populated but not acted upon - this PRD proposes expanding AI's role to action planning and execution.

3. **No Adaptive Recovery**: When `ElementNotFound` occurs, the system transitions to `UNKNOWN` and asks humans instead of trying alternative approaches.

4. **Single Context Source**: AI only receives screenshots, missing structured DOM and accessibility tree data that research shows improves accuracy.

## Goals

| Goal | Metric | Baseline | Target |
|------|--------|----------|--------|
| Reduce manual intervention | Human checkpoint triggers | ~40% of flows | <12% of flows (-70%) |
| Handle UI changes gracefully | Success rate on modified layouts | ~50% | >85% |
| Improve state detection accuracy | Correct state identification | ~85% | >95% |
| Enable self-correction | Recovery without human input | 0% | >80% of failures |

*Baselines estimated from test suite analysis. Exact measurements to be captured in Phase 1.*

## Non-Goals

- Building a general-purpose browser agent (we remain subscription-cancellation focused)
- Real-time performance (<1s latency)
- Cost optimization (accuracy prioritized)

## Technical Feasibility Verification

### Playwright Accessibility Tree Support

**Verified**: Playwright provides `page.accessibility.snapshot()` for accessibility tree extraction.

```python
# Playwright API (verified in docs)
snapshot = await page.accessibility.snapshot()
# Returns: {"role": "WebArea", "name": "", "children": [...]}
```

**Known Limitations**:
- Cross-origin iframes may not be accessible
- Shadow DOM elements require special handling
- Large pages produce large trees (addressed in Context Strategy section)

Source: [Playwright Accessibility Docs](https://playwright.dev/python/docs/accessibility-testing)

## Architecture Design

### Current vs Proposed Flow

```
CURRENT:
+-------------------------------------------------------------+
| Heuristic Detect State -> Hardcoded Action -> Loop          |
|       | (low confidence)                                    |
| AI Classify State -> Same Hardcoded Action                  |
+-------------------------------------------------------------+

PROPOSED:
+-------------------------------------------------------------+
| AI Perceive + Plan -> AI Execute Action -> Heuristic Validate|
|       ^                      |                    |         |
|       +-------- Self-Correct Loop <---------------+         |
+-------------------------------------------------------------+
```

### Core Components

#### 1. AIBrowserAgent (New)

Replaces hardcoded `_handle_state()` logic with AI-driven decision making.

```python
class AIBrowserAgent:
    """AI agent that perceives, plans, and executes browser actions."""

    async def perceive(self) -> AgentContext:
        """Gather multi-modal context: screenshot + DOM + accessibility tree."""

    async def plan(self, context: AgentContext, goal: str) -> ActionPlan:
        """Ask Claude to plan next action(s) given current context and goal."""

    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute planned action via browser protocol."""

    async def validate(self, result: ExecutionResult) -> ValidationResult:
        """Use heuristics to validate action succeeded."""

    async def self_correct(self, failure: ValidationResult) -> ActionPlan:
        """Analyze failure and generate alternative approach."""
```

#### 2. AgentContext (New)

Multi-modal context combining all available signals. Research from [arxiv.org](https://arxiv.org/html/2511.19477v1) shows hybrid context (accessibility tree + vision) improves accuracy by ~20% over single-source approaches.

```python
@dataclass
class AgentContext:
    screenshot: bytes           # Visual understanding
    html_snippet: str           # Relevant DOM (~5KB, not full page)
    accessibility_tree: str     # Pruned semantic structure
    url: str                    # Current location
    visible_text: str           # Page text content
    previous_actions: list      # Action history for context
    error_history: list         # Past failures for learning
```

#### 3. ActionPlan (New)

Structured action specification supporting multiple identification methods.

```python
@dataclass
class ActionPlan:
    action_type: Literal["click", "fill", "navigate", "select", "wait", "scroll"]

    # Hybrid element identification (try in order)
    css_selector: str | None        # Precise CSS targeting
    aria_selector: tuple | None     # (role, name) for accessibility
    text_content: str | None        # Find by visible text
    coordinates: tuple | None       # (x, y) pixel coordinates as fallback

    # Action parameters
    value: str | None               # For fill/select actions
    reasoning: str                  # Why this action (for debugging)
    confidence: float               # AI's confidence in this plan

    # Single-level fallback (not recursive)
    fallback_strategies: list[TargetStrategy]  # Alternative targeting methods
```

**Note**: `fallback_strategies` is a flat list of alternative targeting methods (CSS, ARIA, text, coords), not recursive `ActionPlan` objects. Maximum 3 alternatives per action.

#### 4. Context Windowing Strategy

To manage token costs and improve accuracy (avoiding information dilution):

| Context Type | Strategy | Estimated Size |
|--------------|----------|----------------|
| HTML | Extract elements within viewport + interactive elements only | ~5KB |
| Accessibility Tree | Prune to visible elements, max depth 5 | ~3KB |
| Screenshot | Full page, compressed PNG | ~50KB (base64: ~67KB) |
| Action History | Last 5 actions | ~1KB |

**Total estimated context per request**: ~10-15K tokens

Full HTML dump reserved for self-correction failures when targeted context is insufficient.

#### 5. Enhanced Claude Prompt

New prompt structure for action planning using Claude's tool_use for structured output:

```python
tools = [{
    "name": "browser_action",
    "description": "Execute a browser action",
    "input_schema": {
        "type": "object",
        "properties": {
            "state": {"type": "string", "enum": [list of State values]},
            "action_type": {"type": "string", "enum": ["click", "fill", "navigate", "select", "wait", "scroll"]},
            "target": {
                "type": "object",
                "properties": {
                    "css": {"type": "string"},
                    "aria_role": {"type": "string"},
                    "aria_name": {"type": "string"},
                    "text": {"type": "string"},
                    "coordinates": {"type": "array", "items": {"type": "integer"}}
                }
            },
            "value": {"type": "string"},
            "reasoning": {"type": "string"},
            "confidence": {"type": "number"}
        },
        "required": ["state", "action_type", "target", "reasoning", "confidence"]
    }
}]
```

System prompt:
```
You are controlling a browser to cancel a subscription.

CONTEXT:
- URL: {url}
- Goal: {goal}
- Previous actions: {action_history}
- Last error (if any): {error}

AVAILABLE INFORMATION:
1. Screenshot attached
2. Accessibility tree (pruned to visible elements):
{accessibility_tree}

3. HTML snippet (interactive elements in viewport):
{html_snippet}

Use the browser_action tool to specify your next action.
Prefer CSS selectors > ARIA > text > coordinates (in that order).
Only use coordinates if semantic identification is impossible.
```

### Coordinate-Based Clicking: Edge Cases

| Edge Case | Detection | Mitigation |
|-----------|-----------|------------|
| Outside viewport | Check x,y against viewport dimensions | Scroll to coordinates first |
| Page scrolled since screenshot | Track scroll position | Re-capture screenshot before coordinate click |
| Element changed | Post-click validation | Self-correction loop |
| Overlay/modal blocking | Check for overlay elements in accessibility tree | Dismiss overlay first or fail fast |

### Integration with Existing Code

#### Backward Compatibility Strategy

New methods will be added as **optional** with default implementations that raise `NotImplementedError`. This allows:
1. Existing `PlaywrightBrowser` to work without changes initially
2. Gradual implementation of new capabilities
3. Tests to continue passing during migration

```python
# protocols.py - Backward compatible extension

class BrowserProtocol(Protocol):
    # ... existing required methods (unchanged)

    # NEW: Optional methods with defaults
    async def accessibility_tree(self) -> str:
        """Get accessibility tree snapshot. Optional capability."""
        raise NotImplementedError("accessibility_tree not supported by this browser")

    async def click_coordinates(self, x: int, y: int) -> None:
        """Click at coordinates. Optional capability."""
        raise NotImplementedError("click_coordinates not supported by this browser")

    def supports_accessibility_tree(self) -> bool:
        """Check if browser supports accessibility tree extraction."""
        return False

    def supports_coordinate_clicking(self) -> bool:
        """Check if browser supports coordinate-based clicking."""
        return False
```

#### Engine Integration

```python
class CancellationEngine:
    def __init__(self, ..., agent: AIBrowserAgent | None = None):
        self.agent = agent  # New: AI agent for control

    async def _handle_state(self, state: State) -> State:
        # AI agent handles most states except:
        # - START: Just navigation, no decision needed
        # - LOGIN_REQUIRED: Requires human credentials
        if self.agent and state not in (State.START, State.LOGIN_REQUIRED):
            return await self._ai_driven_handle(state)

        # Fallback to existing hardcoded logic
        return await self._hardcoded_handle(state)
```

**Rationale for excluded states**:
- `START`: Pure navigation, no element interaction needed
- `LOGIN_REQUIRED`: Human must enter credentials; AI can't help here

### Self-Correction Loop

Based on [DEV.to research on self-correcting AI agents](https://dev.to/louis-sanna/self-correcting-ai-agents-how-to-build-ai-that-learns-from-its-mistakes-39f1):

```python
async def self_correct(self, failure: ValidationResult) -> ActionPlan:
    """
    Three-pillar self-correction:
    1. Error Detection - What went wrong?
    2. Reflection - Why did it fail?
    3. Retry with Different Strategy - What else can we try?
    """

    prompt = f"""
    FAILED ACTION:
    - Attempted: {failure.attempted_action}
    - Error: {failure.error}
    - Screenshot after failure: [attached]

    REFLECTION:
    1. Is the target element visible on screen?
    2. Did the page change unexpectedly?
    3. Was the selector correct but element not interactable?

    REQUIREMENT:
    Provide a FUNDAMENTALLY DIFFERENT approach, not just retry.
    If CSS failed, try ARIA. If ARIA failed, try text search.
    If all semantic methods failed, consider coordinates.
    """

    return await self._ask_claude_for_plan(prompt)
```

### Heuristic Validation Role

Flip heuristics from "detection" to "validation":

```python
class HeuristicValidator:
    """Validates AI actions succeeded using fast heuristic checks."""

    def validate_state_transition(
        self,
        expected_state: State,
        url: str,
        text: str
    ) -> ValidationResult:
        """Check if we reached expected state after AI action."""
        detected = self.heuristic.interpret(url, text)

        return ValidationResult(
            success=detected.state == expected_state,
            actual_state=detected.state,
            confidence=detected.confidence,
            message=detected.reasoning
        )
```

## Implementation Phases

### Phase Dependency Graph

```
Phase 1 (Foundation)
    |
    v
Phase 2 (AI Planning) ---> Phase 3 (Self-Correction)
    |                           |
    +------------+--------------+
                 |
                 v
           Phase 4 (Integration)
                 |
                 v
           Phase 5 (Testing)
```

### Phase 1: Multi-Modal Context (Foundation)

**Depends on**: Nothing (can start immediately)

**Files to modify:**
- `src/subterminator/core/browser.py` - Add `accessibility_tree()`, `click_coordinates()`
- `src/subterminator/core/protocols.py` - Add optional methods with capability checks

**Deliverables:**
- Browser can extract accessibility tree via Playwright's `page.accessibility.snapshot()`
- Pixel-coordinate clicking via Playwright's `page.mouse.click(x, y)`
- Capability detection methods
- Unit tests for new browser methods

**Verification**: Run `uv run pytest tests/unit/test_browser.py -v`

### Phase 2: AI Action Planning

**Depends on**: Phase 1 (requires accessibility_tree capability)

**Files to create:**
- `src/subterminator/core/agent.py` - `AIBrowserAgent` class

**Files to modify:**
- `src/subterminator/core/ai.py` - New `ClaudeActionPlanner` class with tool_use

**Deliverables:**
- Claude can suggest actions using tool_use (structured output)
- Action plans include hybrid identification (CSS/ARIA/text/coords)
- Confidence scores for action decisions

**Verification**: Unit tests with mocked Claude responses

### Phase 3: Self-Correction Loop

**Depends on**: Phase 2 (requires AIBrowserAgent)

**Files to modify:**
- `src/subterminator/core/agent.py` - Add `self_correct()` method
- `src/subterminator/core/ai.py` - Add reflection prompts

**Deliverables:**
- Agent retries with different strategies on failure
- Error history informs future attempts
- Maximum 3 self-correction attempts before human fallback

**Verification**: Integration tests simulating element failures

### Phase 4: Engine Integration

**Depends on**: Phase 2, Phase 3

**Files to modify:**
- `src/subterminator/core/engine.py` - Integrate `AIBrowserAgent`

**Deliverables:**
- AI controls main flow when agent provided
- Heuristics validate outcomes
- Graceful fallback to hardcoded logic if AI unavailable

**Verification**: End-to-end tests with mock server

### Phase 5: Validation & Testing

**Depends on**: Phase 4

**Files to create:**
- `tests/unit/test_agent.py`
- `tests/integration/test_ai_driven_flow.py`

**Deliverables:**
- Comprehensive unit tests for agent components
- Integration tests with mock pages
- Performance benchmarks (accuracy, latency, cost per flow)
- Baseline measurements captured

**Verification**: Full test suite passes, benchmarks documented

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AI hallucinates wrong element | Medium | High | (1) Heuristic validation after every action, (2) Confidence threshold - reject actions with confidence < 0.6, (3) Human confirmation for FINAL_CONFIRMATION state |
| AI clicks wrong but non-destructive element | Medium | Medium | Self-correction loop detects via state validation and retries |
| Increased API costs | High | Low | Acceptable per requirements; add cost tracking metrics |
| Slower execution | High | Low | Expected ~5-10s per AI decision. Full flow: 2-3 min vs current ~30s. Acceptable per requirements. |
| Claude API outage | Low | High | Fallback to hardcoded logic remains fully functional |
| Adversarial UI changes | Low | Medium | Self-correction + human fallback |
| Coordinate click misses due to scroll | Medium | Medium | Track scroll position, re-capture screenshot before coordinate clicks |

## Success Criteria

1. **Accuracy**: >95% correct state detection on test pages
2. **Adaptability**: Successfully handle 3+ UI variations per page type
3. **Self-Recovery**: >80% of `ElementNotFound` errors recovered without human
4. **Backward Compatible**: System works without AI agent (fallback to hardcoded)
5. **Latency Acceptable**: Full flow completes in <5 minutes

## Open Questions (Resolved)

1. **Token Budget**: ~~Should we limit context size?~~
   - **Decision**: Use context windowing strategy (see above). ~10-15K tokens per request. Full context only for self-correction.

2. **Action Confirmation**: ~~Should destructive actions require human confirmation?~~
   - **Decision**: Yes, keep human checkpoint for FINAL_CONFIRMATION state.

3. **Learning from Failures**: ~~Should we persist failure patterns?~~
   - **Decision**: Future enhancement, not in initial scope.

## References

- [Playwright Accessibility API](https://playwright.dev/python/docs/accessibility-testing) - Verified accessibility tree support
- [OpenClaw Browser Tool Architecture](https://docs.openclaw.ai/tools/browser) - Hybrid ref + ARIA approach
- [Browser-Use Framework](https://github.com/browser-use/browser-use) - Custom tool patterns
- [Skyvern Multi-Agent Architecture](https://github.com/Skyvern-AI/skyvern) - Planner-Actor-Validator pattern
- [Self-Correcting AI Agents](https://dev.to/louis-sanna/self-correcting-ai-agents-how-to-build-ai-that-learns-from-its-mistakes-39f1) - Three-pillar recovery
- [Building Browser Agents (arxiv)](https://arxiv.org/html/2511.19477v1) - Hybrid context management research
- [Claude Computer Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool) - Official patterns
