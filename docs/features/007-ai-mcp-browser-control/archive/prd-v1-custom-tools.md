# PRD: AI-Led MCP Browser Control Redesign

## Executive Summary

Fundamentally rethink SubTerminator's browser automation architecture to be **AI-led with MCP-style tool invocation**. The AI model (currently Claude) becomes the orchestrator that decides which actions to take, while our system acts as an **active MCP server** providing tools, executing actions, managing state, and returning rich feedback.

### Key Insight

The current design fails because it treats AI as a consultant (ask for a plan, execute it ourselves) rather than as the driver. In the new design:
- **AI decides**: The model chooses which tool to call and with what parameters
- **We execute**: Our server runs the action and returns structured results with fresh state
- **We provide context**: Rich, well-calibrated information to help AI make good decisions
- **We validate**: Ensure AI's tool calls produce expected outcomes

### Critical Hypothesis (Requires Validation)

**This PRD is built on an unverified assumption**: that giving Claude direct tool control will improve action sequencing compared to the current plan-then-execute approach. Before full implementation, **Phase 0 validation is required** (see Implementation Approach).

---

## Problem Statement

### Current Architecture Failures

Based on codebase analysis, the current implementation fails for these reasons:

| Failure Point | Description | Evidence |
|---------------|-------------|----------|
| **Element targeting unreliable** | `click_by_text` uses Playwright's `get_by_text` which can match wrong elements in complex UIs. `click_by_bbox` exists but isn't passed to Claude in prompt context | `browser.py:749`, `protocols.py:357-389` |
| **One action per cycle** | Perceive-plan-execute loop executes ONE action, then re-perceives. Complex flows (expand → check → click) lose context between API calls | `agent.py:699-765` |
| **Rigid state machine** | `STATE_TRANSITIONS` hardcodes linear flow. Netflix's actual UI may not match expected progression | `agent.py:34-40` |
| **Context lacks coordinates** | `AgentContext.to_prompt_context()` provides accessibility tree but no element bounding boxes. Claude can't specify precise click locations | `protocols.py:357-389` |
| **Error details lost** | `_try_target_strategy` catches all exceptions, returns `False`. Self-correction has no info about WHY strategy failed | `agent.py:413-467` |
| **Accessibility tree over-pruned** | 5-level depth limit, 100-char name truncation may lose critical elements on complex pages | `browser.py:637-694` |

### User's Core Requirements

1. **Testability**: Make system more composable and easier to test
2. **Service for AI agents**: Other AI systems can use browser automation as MCP tools
3. **AI makes all decisions**: We maintain state, execute actions, provide context
4. **Fix element targeting**: Current approach picks wrong elements
5. **Fix action sequencing**: AI doesn't know correct order of operations

---

## Research Findings

### MCP Tool Design Best Practices

| Finding | Source | Relevance |
|---------|--------|-----------|
| **≤30 tools is critical threshold**. Above this, tool description overlap confuses models. At 107 tools, models hallucinate and crash | [Speakeasy MCP Guide](https://www.speakeasy.com/mcp/tool-design/less-is-more) | High |
| **Domain-aware actions beat CRUD**. Use `submit_expense_report` not `create_record`. Most important info first in descriptions | [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | High |
| **Poka-yoke design**: Change arguments to make mistakes harder. Require absolute paths, include examples in descriptions | [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) | High |
| **Snapshot + Refs pattern**: Instead of full DOM, return element references (@e1, @e2). 200-400 tokens vs 3000-5000 for full DOM | [Agent Browser](https://agent-browser.dev/) | High |
| **Accessibility-first**: Playwright MCP uses accessibility tree, bypasses need for vision. Significant token reduction vs raw DOM | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) | High |
| **Tools own state, AI reasons about it**. MCP allows state handles passed across calls for tool chaining | [MCP Best Practices](https://oshea00.github.io/posts/mcp-practices/) | High |

### Computer Use Lessons

| Finding | Source |
|---------|--------|
| **Screenshot after each step**: "Take a screenshot and carefully evaluate if you achieved the right outcome" prevents assumptions | [Anthropic Computer Use Guide](https://www.digitalapplied.com/blog/anthropic-computer-use-api-guide) |
| **Resolution matters**: Keep at ≤1024x768 for better accuracy. Higher resolutions cause missed elements | [Anthropic Developing Computer Use](https://www.anthropic.com/news/developing-computer-use) |
| **Hybrid approach**: Accessibility when available, OCR as fallback, vision for confirmation | [Claude Computer Use Limitations](https://medium.com/@nicholaiyu) |

---

## Proposed Solution

### Architecture: AI as Controller, Service as Executor

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI MODEL (Claude)                        │
│                                                                 │
│  "I see the snapshot. I'll call browser_click(@e7) first."      │
│  [Receives new snapshot in response]                            │
│  "Now I see expanded section. I'll call browser_click(@e12)."   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Tool Calls (one at a time)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BROWSER CONTROL SERVER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Tool:       │  │ Tool:       │  │ Tool:       │             │
│  │ get_snapshot│  │ browser_    │  │ browser_    │             │
│  │             │  │ click       │  │ fill        │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ State Manager                                               ││
│  │ - Element registry (refs → actual elements)                 ││
│  │ - Every action returns fresh snapshot                       ││
│  │ - Page state                                                ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Core Design Principles

1. **AI Orchestrates, We Execute**: No agent-side loops. AI calls tools in sequence, we return results.
2. **Every Action Returns Fresh State**: Each tool returns a new snapshot. No multi-tool-per-turn (see FR2 rationale).
3. **Element References**: Use `@e1, @e2` refs instead of selectors. Refs are valid for exactly one action.
4. **Rich Structured Feedback**: Every tool returns success/failure, new snapshot, error details.
5. **Minimal Tool Set**: <10 well-calibrated tools, not 30+ with overlapping functions.
6. **Screenshots Always Included**: Per research, visual confirmation prevents assumptions.

### Decision: Direct API, Not MCP Protocol

**Chosen**: Direct Python API (not MCP stdio/SSE transport)

**Rationale**:
- MCP protocol adds complexity without benefit for single-client use
- Direct API allows faster iteration during validation phase
- If successful, MCP transport can be added as thin wrapper in future phase

---

## Feature Requirements

### FR1: Tool Interface

**Description**: Expose browser control as tools that AI can invoke directly.

**Tools (Minimal Set of 7)**:

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `get_snapshot` | Get accessibility snapshot with element refs and screenshot | `viewport_only?: bool` | `{elements: [...], screenshot: base64, page: {...}}` |
| `browser_click` | Click an element by ref | `ref: string` | `{success: bool, snapshot: {...}, error?: string}` |
| `browser_fill` | Fill input field | `ref: string, value: string` | `{success: bool, snapshot: {...}, error?: string}` |
| `browser_select` | Select dropdown option | `ref: string, value: string` | `{success: bool, snapshot: {...}, error?: string}` |
| `browser_scroll` | Scroll page or element into view | `ref?: string, direction?: string` | `{success: bool, snapshot: {...}}` |
| `request_human_approval` | Pause for human confirmation (server-enforced at critical points) | `action: string, reason: string` | `{approved: bool, message?: string}` |
| `complete_task` | Signal task completion | `status: "success" \| "failed", reason: string` | `{acknowledged: bool}` |

**Note**: No `get_page_info` tool. Page info included in every snapshot.

**Acceptance Criteria**:
- [ ] All tools return structured JSON with fresh snapshot
- [ ] Tool descriptions include examples and edge cases
- [ ] Error responses include actionable details (element_not_found, element_disabled, element_obscured, etc.)

### FR2: Element Reference System (Single-Action Lifetime)

**Description**: Element references are valid for exactly ONE action after the snapshot that created them.

**Rationale for Single-Action Lifetime**:
- Any action can mutate the DOM (AJAX, animations, lazy loading)
- Multi-tool-per-turn would require AI to predict DOM mutations
- Fresh snapshot after each action eliminates stale ref errors
- Matches Playwright MCP's "action returns new snapshot" pattern

**Design**:
```python
class ElementRegistry:
    """Maps @eN references to DOM elements. Refs valid for one action only."""

    def create_snapshot(self) -> Snapshot:
        """Capture accessibility tree, screenshot, assign refs"""
        elements = self.browser.accessibility_tree()
        screenshot = self.browser.screenshot()
        for i, elem in enumerate(elements):
            elem.ref = f"@e{i}"
        self.current_refs = {e.ref: e for e in elements}
        self.snapshot_id = uuid4()
        return Snapshot(
            id=self.snapshot_id,
            elements=elements,
            screenshot=screenshot,
            page={"url": self.browser.url, "title": self.browser.title}
        )

    def execute_action(self, ref: str, action: Callable) -> ActionResult:
        """Execute action, then ALWAYS return fresh snapshot"""
        if ref not in self.current_refs:
            return ActionResult(success=False, error="ref_invalid", snapshot=self.create_snapshot())

        element = self.current_refs[ref]
        try:
            action(element)
            # Refs are now INVALID - create fresh snapshot
            new_snapshot = self.create_snapshot()
            return ActionResult(success=True, snapshot=new_snapshot)
        except Exception as e:
            new_snapshot = self.create_snapshot()
            return ActionResult(success=False, error=str(e), snapshot=new_snapshot)
```

**Acceptance Criteria**:
- [ ] Every action returns a fresh snapshot
- [ ] AI cannot call multiple tools per turn (enforced by conversation loop)
- [ ] Stale refs return error with fresh snapshot for retry
- [ ] Refs include role, name, state, and bounding box

### FR3: Structured Accessibility Snapshot with Screenshot

**Description**: Provide AI with element data + screenshot for every decision.

**Snapshot Format**:
```json
{
  "snapshot_id": "abc123",
  "elements": [
    {
      "ref": "@e0",
      "role": "heading",
      "name": "Cancel Your Plan",
      "level": 1,
      "bbox": {"x": 100, "y": 50, "width": 400, "height": 40}
    },
    {
      "ref": "@e7",
      "role": "button",
      "name": "Cancel Membership",
      "state": ["enabled", "visible"],
      "bbox": {"x": 200, "y": 400, "width": 150, "height": 40}
    },
    {
      "ref": "@e12",
      "role": "checkbox",
      "name": "I understand I will lose access",
      "state": ["unchecked", "enabled"],
      "bbox": {"x": 180, "y": 350, "width": 20, "height": 20}
    }
  ],
  "focused": "@e7",
  "page": {
    "url": "https://netflix.com/cancel",
    "title": "Cancel Plan - Netflix"
  },
  "screenshot": "base64-encoded-png..."
}
```

**Pruning Rules** (explicit, not arbitrary):
1. Include elements with these roles: button, link, checkbox, radio, textbox, combobox, menuitem, tab, heading (levels 1-3), region, dialog
2. Exclude: generic, presentation, separator, static text (unless clickable)
3. Depth limit: 10 levels (not 5)
4. Name truncation: 200 chars (not 100)
5. Only elements in viewport (configurable)

**Token Budget**:
- Target: <1000 tokens for snapshot elements + ~500 tokens for compressed screenshot description
- Actual measurement required before finalizing (see Phase 0)

**Acceptance Criteria**:
- [ ] Screenshot always included (per research findings)
- [ ] Pruning rules documented and configurable
- [ ] Bounding boxes included for all interactive elements
- [ ] Token count measured on actual Netflix pages

### FR4: AI Conversation Loop (Single Tool Per Turn)

**Description**: Multi-turn conversation where AI calls one tool per turn, receives fresh state.

**Design**:
```python
async def run_task(goal: str, max_turns: int = 20) -> TaskResult:
    """AI-led task execution with single tool per turn"""

    snapshot = self.registry.create_snapshot()
    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Goal: {goal}\n\nCurrent state:\n{format_snapshot(snapshot)}"}
    ]

    for turn in range(max_turns):
        response = await ai.chat(conversation, tools=TOOLS)

        if not response.tool_calls:
            # AI finished without calling complete_task - ask for explicit completion
            conversation.append({"role": "assistant", "content": response.content})
            conversation.append({"role": "user", "content": "Please call complete_task to indicate whether the goal was achieved."})
            continue

        # Execute FIRST tool call only (ignore any others)
        tool_call = response.tool_calls[0]
        result = execute_tool(tool_call)

        conversation.append({"role": "assistant", "content": response.content, "tool_calls": [tool_call]})
        conversation.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

        if tool_call.name == "complete_task":
            return TaskResult(
                success=result["status"] == "success",
                reason=result["reason"],
                turns=turn + 1
            )

    return TaskResult(success=False, reason="max_turns_exceeded", turns=max_turns)
```

**Acceptance Criteria**:
- [ ] Single tool call per turn enforced
- [ ] Fresh snapshot in every tool response
- [ ] Max turns limit prevents infinite loops
- [ ] `complete_task` required to end task
- [ ] Conversation history maintained for context

### FR5: Tool Calibration and Descriptions

**Description**: Write tool descriptions that help AI make correct choices.

**Example (Well-Calibrated)**:
```python
BROWSER_CLICK_TOOL = {
    "name": "browser_click",
    "description": """Click an element identified by its reference from the most recent snapshot.

IMPORTANT: Element refs (@e0, @e1, etc.) are only valid for ONE action. After clicking, you'll receive a fresh snapshot with new refs.

WHEN TO USE:
- To click buttons, links, checkboxes, or other interactive elements
- The element must have state "enabled" and "visible"

WHAT HAPPENS:
- The click is executed
- A fresh snapshot is returned (old refs become invalid)
- If the click triggers navigation, the new page's snapshot is returned

COMMON PATTERNS:
- Expand accordion: click button/region with "collapsed" in state
- Submit form: click button with name containing "Submit", "Continue", "Confirm"
- Check checkbox: click checkbox element (state will show "checked" in new snapshot)

ERROR CONDITIONS:
- element_not_found: the ref doesn't exist in current snapshot
- element_disabled: element has "disabled" in state
- element_obscured: another element is covering the target
- click_failed: browser couldn't click (element may have moved)

EXAMPLE:
  Input: {"ref": "@e7"}
  Output: {"success": true, "snapshot": {...new elements with new refs...}}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Element reference from most recent snapshot (e.g., '@e7')",
                "pattern": "^@e\\d+$"
            }
        },
        "required": ["ref"]
    }
}
```

**Acceptance Criteria**:
- [ ] Each tool has "WHEN TO USE" section
- [ ] Each tool explains that refs are single-use
- [ ] Common patterns documented with examples
- [ ] Error conditions listed
- [ ] Parameter patterns enforce correct format

### FR6: Human Checkpoint Integration (Server-Enforced)

**Description**: Server pauses for human approval at predefined critical points.

**Design Decision**: Human checkpoints are **server-enforced**, not AI-decided. This is an honest acknowledgment that:
1. We can't trust AI to correctly identify irreversible actions
2. The current system already has `HUMAN_CHECKPOINT_STATES` - this is the same pattern, formalized

**Implementation**:
```python
# Server-side, not AI-side
CHECKPOINT_CONDITIONS = {
    "netflix": [
        lambda snapshot: "Finish Cancellation" in snapshot.page.title,
        lambda snapshot: any(e.name and "confirm cancel" in e.name.lower() for e in snapshot.elements),
    ]
}

def execute_tool(tool_call) -> dict:
    result = actually_execute(tool_call)

    # Check if new state triggers checkpoint
    for condition in CHECKPOINT_CONDITIONS.get(service, []):
        if condition(result.snapshot):
            approval = request_human_approval(
                action=f"Detected critical state: {result.snapshot.page.title}",
                snapshot=result.snapshot
            )
            if not approval.approved:
                return {"success": False, "error": "human_rejected", "snapshot": result.snapshot}

    return result
```

**Acceptance Criteria**:
- [ ] Checkpoints are server-enforced, not AI-requested
- [ ] Checkpoint conditions are service-specific and explicit
- [ ] Human can approve, reject, or provide guidance
- [ ] Rejection returns control to AI with explanation

### FR7: Task Completion Verification

**Description**: Define explicit completion criteria beyond AI interpretation.

**Problem Addressed**: How does AI know the task actually succeeded? Looking at a "Cancellation confirmed" page isn't proof.

**Design**:
```python
# Completion criteria are service-specific
COMPLETION_CRITERIA = {
    "netflix_cancel": {
        "success_indicators": [
            lambda s: "membership" in s.page.url and "cancelled" in s.page.title.lower(),
            lambda s: any("cancelled" in e.name.lower() for e in s.elements if e.role == "heading"),
        ],
        "failure_indicators": [
            lambda s: "error" in s.page.url,
            lambda s: any("could not" in e.name.lower() for e in s.elements),
        ]
    }
}

def handle_complete_task(status: str, reason: str, snapshot: Snapshot) -> dict:
    criteria = COMPLETION_CRITERIA.get(current_task)
    if criteria:
        actual_success = any(c(snapshot) for c in criteria["success_indicators"])
        actual_failure = any(c(snapshot) for c in criteria["failure_indicators"])

        if status == "success" and not actual_success:
            return {
                "acknowledged": False,
                "message": "Cannot verify success. Please check the page state.",
                "snapshot": snapshot
            }

    return {"acknowledged": True}
```

**Acceptance Criteria**:
- [ ] Completion criteria defined per service/task
- [ ] AI's success claim is validated against criteria
- [ ] Mismatches return to AI for correction

---

## Non-Functional Requirements

### NFR1: Token Efficiency
- Accessibility snapshots: Target <1000 tokens (to be measured)
- Screenshot: ~500 tokens (compressed/described)
- Full conversation context: <8000 tokens
- Snapshot pruning configurable per service

### NFR2: Latency
- `get_snapshot` completes in <1s (including screenshot)
- Tool execution <3s (excluding human checkpoints)
- Total task completion: measure vs current baseline

### NFR3: Testability
- Tools testable in isolation with mock browser
- Mock AI responses for deterministic integration tests
- Snapshot format documented with JSON schema
- Tool descriptions can generate example inputs

### NFR4: Error Recovery
- Every error returns fresh snapshot for retry
- Network errors retry with exponential backoff (max 3 attempts)
- AI receives full error context in tool response

---

## Implementation Approach

### Phase 0: Hypothesis Validation (Required Before Phase 1)

**Objective**: Validate the core assumption that Claude can reliably sequence browser actions.

**Experiment**:
1. Create a simple test harness with the 7 proposed tools
2. Use mock browser that returns realistic snapshots
3. Run 20 Netflix cancellation scenarios with Claude
4. Measure:
   - Does Claude call tools in correct sequence?
   - Does Claude correctly interpret snapshot state?
   - How many turns to completion?
   - Where does it fail?

**Success Criteria**:
- >70% of scenarios reach correct completion
- Average turns <10 for successful scenarios
- Failure modes are identifiable and addressable

**Failure Response**:
- If <50% success: Abandon this approach, investigate alternatives
- If 50-70% success: Identify failure patterns, add constraints, re-test
- If >70% success: Proceed to Phase 1

### Phase 1: Core Infrastructure
1. Implement ElementRegistry with single-action ref lifetime
2. Create StructuredSnapshot generator with pruning
3. Build tool execution layer with fresh snapshot return
4. Measure actual token usage on Netflix pages

### Phase 2: AI Conversation Loop
1. Implement single-tool-per-turn conversation loop
2. Add server-enforced human checkpoints
3. Add completion verification
4. Integration tests with mock AI

### Phase 3: Migration and Measurement
1. Migrate Netflix service to new pattern
2. Measure success rate, token usage, latency
3. Compare to baseline measurements
4. Document patterns for new services

---

## Success Metrics

| Metric | Baseline | Target | Notes |
|--------|----------|--------|-------|
| Netflix cancel success rate | **TBD** (measure before Phase 1) | Baseline + 30% | Improvement over current |
| Element targeting accuracy | **TBD** | >90% first-try | Measured by action success |
| Tokens per task | **TBD** | <10K | Including screenshot |
| Turns to completion | **TBD** | <15 | For successful tasks |

**Note**: Baselines will be measured during Phase 0 validation.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AI calls tools in wrong order | Medium | High | Single-tool-per-turn, fresh snapshot after each action, explicit sequencing examples in system prompt |
| Core hypothesis fails (AI can't sequence) | Medium | Critical | Phase 0 validation before building |
| Token budget exceeded | Medium | Medium | Aggressive pruning, measure actual Netflix pages, adjust budget |
| AI loops or doesn't terminate | Low | Medium | Max turns limit, require `complete_task` to end |
| Human checkpoints annoying/frequent | Low | Low | Tune checkpoint conditions based on user feedback |
| New services need different patterns | Certain | Low | Service-specific system prompt additions, documented patterns |

---

## Recovery Semantics

**On Failure Mid-Flow**:
1. AI receives error with fresh snapshot
2. AI can attempt recovery (click different element, scroll, etc.)
3. After max retries, AI should call `complete_task(status="failed", reason="...")`
4. User is notified of partial completion state
5. Session state is logged for debugging

**On Network/System Failure**:
1. Retry with exponential backoff (max 3 attempts)
2. On persistent failure, save conversation state
3. User can resume or start fresh

---

## Out of Scope

1. **MCP Protocol Transport**: Direct API only for now. MCP wrapper can be added later.
2. **Multi-service in one task**: One service per task execution
3. **Persistent conversation across sessions**: Fresh start each time
4. **Automatic retries without AI**: AI decides whether to retry

---

## References

- [MCP Specification - Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Building Effective Agents - Anthropic](https://www.anthropic.com/research/building-effective-agents)
- [Playwright MCP - Microsoft](https://github.com/microsoft/playwright-mcp)
- [Agent Browser - Element Refs Pattern](https://agent-browser.dev/)
- [Why Less is More for MCP Tools](https://www.speakeasy.com/mcp/tool-design/less-is-more)
- Current implementation: `src/subterminator/core/agent.py`, `ai.py`, `engine.py`
