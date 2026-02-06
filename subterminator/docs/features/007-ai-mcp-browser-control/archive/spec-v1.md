# Specification: AI-Led MCP Browser Control Redesign

## Overview

This specification defines the technical requirements for replacing SubTerminator's current perceive-plan-execute-validate loop with an AI-led tool invocation model. The AI model calls browser control tools directly; our system executes actions and returns fresh state.

---

## 1. Functional Requirements

### 1.1 Tool Interface (FR1)

#### 1.1.1 Tool Set Definition

The system SHALL provide exactly 7 tools:

| ID | Tool Name | Description |
|----|-----------|-------------|
| T1 | `get_snapshot` | Capture page state with element refs and screenshot |
| T2 | `browser_click` | Click element by ref |
| T3 | `browser_fill` | Fill input field by ref |
| T4 | `browser_select` | Select dropdown option by ref |
| T5 | `browser_scroll` | Scroll page or element into view |
| T6 | `request_human_approval` | Request human confirmation |
| T7 | `complete_task` | Signal task completion |

#### 1.1.2 Tool Response Contract

All tools except `complete_task` and `request_human_approval` SHALL return:
```json
{
  "success": boolean,
  "snapshot": Snapshot,      // Always present, even on error
  "error": string | null     // Error code if success=false
}
```

Error codes SHALL be one of:
- `ref_invalid`: Element ref not found in current snapshot
- `element_disabled`: Element has disabled state
- `element_obscured`: Element is covered by another element
- `element_not_visible`: Element is outside viewport
- `action_failed`: Browser action threw exception (use when error doesn't match specific categories above)
- `timeout`: Action exceeded timeout
- `human_rejected`: Human denied approval
- `invalid_params`: Required parameters missing or conflicting (e.g., browser_scroll with neither ref nor direction)

#### 1.1.3 Tool Schemas

**T1: get_snapshot**
```json
{
  "name": "get_snapshot",
  "description": "Capture the current page state including accessibility tree and screenshot. Call this to see what's on the page before taking action.",
  "input_schema": {
    "type": "object",
    "properties": {
      "viewport_only": {
        "type": "boolean",
        "default": true,
        "description": "If true, only include elements visible in viewport"
      }
    }
  }
}
```

**T2: browser_click**
```json
{
  "name": "browser_click",
  "description": "Click an element by its ref from the most recent snapshot. IMPORTANT: After this action, all refs become invalid. You will receive a fresh snapshot with new refs.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ref": {
        "type": "string",
        "pattern": "^@e\\d+$",
        "description": "Element reference (e.g., '@e7')"
      }
    },
    "required": ["ref"]
  }
}
```

**T3: browser_fill**
```json
{
  "name": "browser_fill",
  "description": "Fill a text input field with the specified value. The element must have role 'textbox' or be an input element.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ref": {
        "type": "string",
        "pattern": "^@e\\d+$",
        "description": "Element reference for the input field"
      },
      "value": {
        "type": "string",
        "description": "Text to enter into the field"
      },
      "clear_first": {
        "type": "boolean",
        "default": true,
        "description": "If true, clear existing content before filling"
      }
    },
    "required": ["ref", "value"]
  }
}
```

**T4: browser_select**
```json
{
  "name": "browser_select",
  "description": "Select an option from a dropdown/combobox. The element must have role 'combobox' or be a select element.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ref": {
        "type": "string",
        "pattern": "^@e\\d+$",
        "description": "Element reference for the dropdown"
      },
      "value": {
        "type": "string",
        "description": "Option value or visible text to select"
      }
    },
    "required": ["ref", "value"]
  }
}
```

**T5: browser_scroll**
```json
{
  "name": "browser_scroll",
  "description": "Scroll the page or bring an element into view. Use when you need to see elements that are off-screen. Provide EITHER 'ref' to scroll element into view, OR 'direction' to scroll the page.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ref": {
        "type": "string",
        "pattern": "^@e\\d+$",
        "description": "Element to scroll into view. If provided, direction is ignored."
      },
      "direction": {
        "type": "string",
        "enum": ["up", "down", "top", "bottom"],
        "description": "Scroll direction. Required if ref not provided."
      },
      "amount": {
        "type": "integer",
        "default": 300,
        "description": "Pixels to scroll if using direction"
      }
    }
  }
}
```

**browser_scroll Parameter Rules:**
1. If `ref` is provided: scroll that element into view (direction/amount ignored)
2. If `ref` is NOT provided and `direction` IS provided: scroll page in that direction
3. If NEITHER `ref` nor `direction` is provided: return error `invalid_params`
```

**T6: request_human_approval**
```json
{
  "name": "request_human_approval",
  "description": "Request human approval before proceeding. The system will pause until the human responds. Note: The server may automatically trigger this at critical points.",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "description": "Description of the action requiring approval"
      },
      "reason": {
        "type": "string",
        "description": "Why this action needs approval"
      }
    },
    "required": ["action", "reason"]
  }
}
```

Response:
```json
{
  "approved": boolean,
  "message": string | null  // Human's feedback if rejected
}
```

**T7: complete_task**
```json
{
  "name": "complete_task",
  "description": "Signal that the task is complete. You MUST call this when the goal is achieved or when you determine it cannot be achieved.",
  "input_schema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["success", "failed"],
        "description": "Whether the goal was achieved"
      },
      "reason": {
        "type": "string",
        "description": "Explanation of the outcome"
      }
    },
    "required": ["status", "reason"]
  }
}
```

Response:
```json
{
  "acknowledged": boolean,
  "message": string | null  // If acknowledgment failed, explains why
}
```

### 1.2 Element Reference System (FR2)

#### 1.2.1 Reference Format

Element references SHALL follow the pattern `@e{N}` where N is a non-negative integer assigned during snapshot creation.

#### 1.2.2 Reference Lifecycle

1. References ARE valid only for the snapshot that created them
2. References BECOME invalid after ANY tool that returns a snapshot
3. The system SHALL NOT attempt to reuse references across snapshots
4. Invalid reference errors SHALL include the fresh snapshot for retry

#### 1.2.3 Reference Assignment

References SHALL be assigned in document order (depth-first traversal of accessibility tree) to ensure deterministic ordering.

### 1.3 Snapshot Structure (FR3)

#### 1.3.1 Snapshot Schema

```typescript
interface Snapshot {
  snapshot_id: string;           // UUID for this snapshot
  timestamp: string;             // ISO 8601 timestamp
  elements: Element[];           // Pruned accessibility elements
  focused: string | null;        // Ref of focused element, if any
  page: PageInfo;
  screenshot: string;            // Base64-encoded PNG
  viewport: ViewportInfo;
}

interface Element {
  ref: string;                   // e.g., "@e7"
  role: string;                  // ARIA role
  name: string;                  // Accessible name (max 200 chars)
  state: string[];               // e.g., ["enabled", "visible", "checked"]
  bbox: BoundingBox;             // Position in viewport coordinates
  value?: string;                // For inputs: current value
  level?: number;                // For headings: 1-6
  children?: string[];           // Refs of child elements (if any)
}

interface BoundingBox {
  x: number;      // Left edge, pixels from viewport left
  y: number;      // Top edge, pixels from viewport top
  width: number;
  height: number;
}

interface PageInfo {
  url: string;
  title: string;
}

interface ViewportInfo {
  width: number;
  height: number;
  scroll_x: number;
  scroll_y: number;
}
```

#### 1.3.2 Element Pruning Rules

Elements SHALL be included if they match ANY of:
1. Role is one of: `button`, `link`, `checkbox`, `radio`, `textbox`, `combobox`, `listbox`, `menuitem`, `menuitemcheckbox`, `menuitemradio`, `tab`, `switch`, `slider`
2. Role is `heading` with level 1, 2, or 3
3. Role is `region`, `dialog`, `alert`, `alertdialog` (landmarks)
4. Element is keyboard focusable (has tabindex >= 0 or is natively focusable element like button, a, input)

Note: Synthetic onclick handlers cannot be reliably detected from accessibility tree. We rely on focusability as a proxy for interactivity.

Elements SHALL be excluded if:
1. Role is `generic`, `presentation`, `none`, `separator`
2. Role is `StaticText` unless parent is interactive
3. Element is hidden (aria-hidden="true" or display:none)
4. Element is outside viewport AND viewport_only=true

#### 1.3.3 Depth and Truncation

- Maximum tree depth: 10 levels
- Name truncation: 200 characters, append "..." if truncated
- Maximum elements per snapshot: 100

**Element Pruning Priority (when >100 elements):**
Elements are ranked for inclusion by:
1. **Viewport visibility**: Elements fully in viewport > partially visible > offscreen
2. **Role priority**: button, link > checkbox, radio, textbox > combobox, listbox > heading > region, dialog > others
3. **Document order**: Earlier elements preferred (tiebreaker)

Remove lowest-ranked elements until count <= 100.

#### 1.3.4 Element State Values

State array SHALL include applicable values from:
- Visibility: `visible`, `hidden`, `offscreen`
- Interactivity: `enabled`, `disabled`, `readonly`
- Selection: `checked`, `unchecked`, `mixed` (for checkboxes)
- Expansion: `expanded`, `collapsed`
- Focus: `focused`
- Busy: `busy`

### 1.4 Conversation Loop (FR4)

#### 1.4.1 Loop Structure

```
1. Create initial snapshot
2. Send to AI with goal and system prompt
3. Receive AI response
4. If response has tool_call:
   a. Execute FIRST tool call only
   b. If tool is complete_task: return result
   c. Add tool result to conversation
   d. Go to 3
5. If response has no tool_call:
   a. Prompt AI to call complete_task
   b. Go to 3
6. If max_turns exceeded: return failure
```

#### 1.4.2 Turn Limits

- Default max_turns: 20
- Configurable per task type
- Exceeding limit returns `TaskResult(success=False, reason="max_turns_exceeded")`

#### 1.4.3 Single Tool Enforcement

If AI returns multiple tool_calls in one response:
1. Execute only the FIRST tool_call
2. Log warning about ignored tool calls
3. Continue conversation normally

### 1.5 Tool Descriptions (FR5)

#### 1.5.1 Description Requirements

Each tool description SHALL include:
1. **Purpose**: What the tool does in 1-2 sentences
2. **Ref invalidation warning**: Explicit statement that refs become invalid
3. **When to use**: Specific scenarios
4. **Common patterns**: 2-3 examples of typical usage
5. **Error conditions**: List of possible error codes
6. **Example**: Input/output pair

#### 1.5.2 System Prompt Structure

```
You are controlling a web browser to accomplish a task.

IMPORTANT RULES:
1. Element refs (like @e7) are only valid for ONE action. After any action, you'll get new refs.
2. Call one tool at a time. Wait for the result before deciding what to do next.
3. Always check the snapshot carefully before acting.
4. Call complete_task when done or when you determine the goal cannot be achieved.

CURRENT GOAL: {goal}

{service-specific guidance if any}
```

### 1.6 Human Checkpoints (FR6)

#### 1.6.1 Checkpoint Trigger Conditions

Checkpoints SHALL be evaluated after every tool execution that returns a snapshot.

Checkpoint conditions are service-specific callables:
```python
CheckpointCondition = Callable[[Snapshot], bool]
```

#### 1.6.2 Built-in Checkpoint Conditions for Netflix

```python
NETFLIX_CHECKPOINTS = [
    lambda s: "finish cancellation" in s.page.title.lower(),
    lambda s: any(
        e.role == "button" and
        e.name and
        "finish cancel" in e.name.lower()
        for e in s.elements
    ),
]
```

#### 1.6.3 Checkpoint Behavior

When checkpoint triggered:
1. Display snapshot to user (screenshot + context)
2. Prompt: "The system wants to proceed with: {action}. Approve?"
3. Wait for user response (no timeout)
4. If approved: continue execution
5. If rejected:
   a. Return error `human_rejected` with user's message
   b. User's rejection message is included in the tool response
   c. Message is appended to conversation context so AI can incorporate feedback
   d. AI may adjust approach based on user guidance

**Rejection Response Format:**
```json
{
  "success": false,
  "error": "human_rejected",
  "message": "User feedback: {user's rejection message}",
  "snapshot": {...}
}
```

### 1.7 Completion Verification (FR7)

#### 1.7.1 Verification Criteria

Completion criteria are service-specific:
```python
CompletionCriteria = {
    "success_indicators": list[Callable[[Snapshot], bool]],
    "failure_indicators": list[Callable[[Snapshot], bool]],
}
```

#### 1.7.2 Netflix Completion Criteria

```python
NETFLIX_CANCEL_CRITERIA = {
    "success_indicators": [
        lambda s: "cancelled" in s.page.title.lower(),
        lambda s: any(
            e.role == "heading" and
            "cancelled" in (e.name or "").lower()
            for e in s.elements
        ),
    ],
    "failure_indicators": [
        lambda s: "error" in s.page.url.lower(),
        lambda s: any(
            "could not" in (e.name or "").lower() or
            "unable to" in (e.name or "").lower()
            for e in s.elements
        ),
    ],
}
```

#### 1.7.3 Verification Logic

**When AI calls `complete_task(status="success")`:**
1. Evaluate success_indicators against current snapshot
2. If ANY success_indicator returns True: acknowledge success
3. If NO success_indicator returns True:
   - Return `acknowledged: false`
   - Include message explaining verification failed
   - AI should reassess and try again or fail explicitly

**When AI calls `complete_task(status="failed")`:**
1. Evaluate failure_indicators against current snapshot (for logging)
2. Log final snapshot with failure reason for debugging
3. Return `acknowledged: true` (failed tasks are always acknowledged)
4. No verification needed - AI's judgment that goal cannot be achieved is accepted

---

## 2. Non-Functional Requirements

### 2.1 Token Efficiency (NFR1)

#### 2.1.1 Token Budgets

| Component | Target | Hard Limit |
|-----------|--------|------------|
| Snapshot elements | <1000 tokens | 2000 tokens |
| Screenshot (base64 in vision) | ~500 tokens | N/A (image tokens) |
| System prompt | <500 tokens | 1000 tokens |
| Conversation history | <6000 tokens | 10000 tokens |
| Total per turn | <8000 tokens | 15000 tokens |

#### 2.1.2 Token Counting

Token counts SHALL be measured empirically by:
1. Serializing snapshot to JSON (for elements)
2. Sending to Claude API and observing `usage.input_tokens` in response
3. Token budgets are approximate targets; actual counts may vary

Note: Claude uses its own tokenizer, not OpenAI's cl100k_base. Budgets are empirical targets validated during Phase 0.

#### 2.1.3 History Truncation

When conversation exceeds 10000 tokens:
1. Keep system prompt and initial goal
2. Keep last 10 turns
3. Summarize dropped turns as: "Previous actions: {action_summary}"

**Action Summary Format (system-generated):**
```
Previous actions:
- browser_click(@e5): success
- browser_fill(@e8, "test"): success
- browser_click(@e12): failed (element_disabled)
```

Summary is prepended to conversation after system prompt.

### 2.2 Latency (NFR2)

#### 2.2.1 Latency Targets

| Operation | Target | Max |
|-----------|--------|-----|
| Snapshot creation | <1s | 3s |
| Click execution | <500ms | 2s |
| Fill execution | <500ms | 2s |
| Select execution | <500ms | 2s |
| Scroll execution | <300ms | 1s |
| AI response | <5s | 30s |

#### 2.2.2 Timeout Handling

Operations exceeding max latency SHALL:
1. Abort the operation
2. Return error `timeout`
3. Include fresh snapshot in response

### 2.3 Testability (NFR3)

#### 2.3.1 Mock Browser Interface

The system SHALL support a mock browser that:
1. Returns predefined snapshots for each action
2. Simulates action success/failure based on configuration
3. Records all tool calls for assertion

#### 2.3.2 Mock AI Interface

The system SHALL support a mock AI that:
1. Returns predefined tool calls in sequence
2. Supports scripted conversations for integration tests
3. Records all prompts for assertion

#### 2.3.3 Snapshot Fixtures

The system SHALL provide:
1. JSON schema for snapshot validation
2. Sample snapshots for common page types
3. Netflix-specific snapshot fixtures for cancellation flow

### 2.4 Error Recovery (NFR4)

#### 2.4.1 Retry Policy

Network errors SHALL retry with:
- Initial delay: 1 second
- Backoff multiplier: 2
- Max attempts: 3
- Max delay: 10 seconds

#### 2.4.2 Error Propagation

All errors SHALL:
1. Be logged with full context (snapshot, tool call, error details)
2. Return to AI with fresh snapshot for decision
3. Not crash the conversation loop

---

## 3. Acceptance Criteria

### 3.1 Tool Interface

- [ ] AC-T1: `get_snapshot` returns valid Snapshot JSON matching schema
- [ ] AC-T2: `browser_click` with valid ref returns success and fresh snapshot
- [ ] AC-T3: `browser_click` with invalid ref returns error `ref_invalid` and fresh snapshot
- [ ] AC-T4: `browser_fill` populates input and returns fresh snapshot
- [ ] AC-T5: `browser_select` selects option and returns fresh snapshot
- [ ] AC-T6: `browser_scroll` scrolls page and returns fresh snapshot with updated viewport
- [ ] AC-T7: `request_human_approval` pauses until user responds
- [ ] AC-T8: `complete_task` with verified success returns acknowledged=true
- [ ] AC-T9: `complete_task` with unverified success returns acknowledged=false with message

### 3.2 Element References

- [ ] AC-R1: Refs follow pattern `@e{N}` with N starting at 0
- [ ] AC-R2: Refs are assigned via depth-first traversal of accessibility tree, producing deterministic ordering across identical page states
- [ ] AC-R3: Attempting to use ref from previous snapshot returns `ref_invalid`
- [ ] AC-R4: Each snapshot has unique snapshot_id

### 3.3 Snapshot Structure

- [ ] AC-S1: Snapshot includes all required fields per schema
- [ ] AC-S2: Elements are pruned according to inclusion rules
- [ ] AC-S3: Element names are truncated at 200 chars
- [ ] AC-S4: Maximum 100 elements per snapshot
- [ ] AC-S5: Bounding boxes are in viewport coordinates

### 3.4 Conversation Loop

- [ ] AC-L1: Only first tool call is executed per turn
- [ ] AC-L2: Loop terminates on `complete_task`
- [ ] AC-L3: Loop terminates after max_turns with failure
- [ ] AC-L4: AI without tool call is prompted to complete
- [ ] AC-L5: Conversation history is maintained across turns

### 3.5 Human Checkpoints

- [ ] AC-H1: Checkpoint conditions are evaluated after each action
- [ ] AC-H2: Matching checkpoint pauses for human approval
- [ ] AC-H3: Approved checkpoint continues execution
- [ ] AC-H4: Rejected checkpoint returns error to AI

### 3.6 Completion Verification

- [ ] AC-V1: Success claims are validated against criteria
- [ ] AC-V2: Unverified success returns acknowledgment failure
- [ ] AC-V3: Verified success returns acknowledgment success

### 3.7 Performance

- [ ] AC-P1: Snapshot creation completes in <3s
- [ ] AC-P2: Action execution completes in <2s
- [ ] AC-P3: Snapshot elements (JSON) consume <2000 tokens when sent to Claude API (measured via usage.input_tokens)
- [ ] AC-P4: AI response received within 30s or operation times out with error `timeout`

---

## 4. Dependencies

### 4.1 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| playwright | >=1.40.0 | Browser automation |
| anthropic | >=0.18.0 | Claude API client |
| pydantic | >=2.0.0 | Data validation |

### 4.2 Internal Dependencies

| Component | Purpose |
|-----------|---------|
| PlaywrightBrowser | Existing browser abstraction (to be extended) |
| Existing services | Netflix service definition (to be migrated) |

---

## 5. Constraints

### 5.1 Technical Constraints

1. Single tool per turn (no parallel tool execution)
2. Refs valid for exactly one action
3. Screenshots always included (per research)
4. Python 3.11+ required (for async features)

### 5.2 Operational Constraints

1. One service per task execution
2. Human checkpoints cannot be bypassed
3. Max 20 turns per task (configurable)

### 5.3 Budget Constraints

1. Token budget per task: <10K total
2. API cost should not exceed current implementation

---

## 6. Out of Scope

1. MCP protocol transport (stdio/SSE)
2. Multi-service tasks
3. Persistent conversations across sessions
4. Automatic retries without AI involvement
5. Vision-only mode (no accessibility tree)
6. Non-Claude AI models

---

## 7. Glossary

| Term | Definition |
|------|------------|
| Ref | Element reference in format `@e{N}`, valid for one action |
| Snapshot | Complete page state including elements, screenshot, and metadata |
| Turn | One AI response + tool execution cycle |
| Checkpoint | Server-enforced pause for human approval |
| Completion criteria | Service-specific rules for verifying task success |
