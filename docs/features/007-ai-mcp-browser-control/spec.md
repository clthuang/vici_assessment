# Specification: AI Browser Orchestration via Existing MCP Tools

## 1. Overview

This specification defines the technical requirements for a thin orchestration layer that connects existing MCP browser servers (Playwright MCP) to AI models (Claude, GPT-4) for automated subscription cancellation tasks.

**Scope**: Orchestration logic, service configs, CLI interface only. Browser control tools are provided by Playwright MCP.

---

## 2. Functional Requirements

### 2.1 MCP Server Connection (FR1)

#### 2.1.1 Server Startup
The system SHALL start Playwright MCP server as a subprocess using:
```
npx @playwright/mcp@latest
```

#### 2.1.2 Connection Protocol
- Transport: stdio (stdin/stdout)
- Protocol: MCP JSON-RPC
- Initialization: `initialize` handshake before tool calls

#### 2.1.3 Tool Discovery
After connection, the system SHALL:
1. Call `tools/list` to get available tools
2. Cache tool schemas for the session
3. Merge with virtual tools (section 2.3)

#### 2.1.4 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-1.1 | System connects to Playwright MCP within 10 seconds | Integration test with timeout |
| AC-1.2 | Tool list contains at minimum: `browser_snapshot`, `browser_click`, `browser_navigate`, `browser_type` | Assert tool names in list |
| AC-1.3 | Connection failure raises `MCPConnectionError` with actionable message | Unit test error path |
| AC-1.4 | System gracefully shuts down MCP subprocess on exit | Integration test cleanup |
| AC-1.5 | System validates Node.js >= 18 is available before startup, raises `ConfigurationError` with install instructions if missing | Unit test |

---

### 2.2 LLM Integration (FR2)

#### 2.2.1 Supported Models
| Model | Provider | Environment Variable |
|-------|----------|---------------------|
| claude-sonnet-4-20250514 | Anthropic | `ANTHROPIC_API_KEY` |
| claude-opus-4-20250514 | Anthropic | `ANTHROPIC_API_KEY` |
| gpt-4o | OpenAI | `OPENAI_API_KEY` |
| gpt-4-turbo | OpenAI | `OPENAI_API_KEY` |

#### 2.2.2 Model Selection
Priority order:
1. `--model` CLI flag
2. `SUBTERMINATOR_MODEL` environment variable
3. Default: `claude-sonnet-4-20250514`

#### 2.2.3 Tool Format Conversion
MCP tool schemas SHALL be converted to provider-specific formats:
- Anthropic: `tools` array with `input_schema`
- OpenAI: `tools` array with `function.parameters`

#### 2.2.4 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-2.1 | Claude API call succeeds with tool schemas | Integration test |
| AC-2.2 | OpenAI API call succeeds with tool schemas | Integration test |
| AC-2.3 | Missing API key raises `ConfigurationError("Missing {PROVIDER}_API_KEY")` | Unit test |
| AC-2.4 | Invalid model name raises `ConfigurationError("Unsupported model: {name}")` | Unit test |
| AC-2.5 | LLM API call exceeding 60 seconds raises `LLMError` with timeout message | Unit test with mock slow response |

**Note**: Model identifiers may change. The system SHALL accept any model name starting with "claude-" for Anthropic or "gpt-" for OpenAI, allowing future models without code changes.

---

### 2.3 Virtual Tools (FR3)

The orchestrator SHALL inject two virtual tools not provided by Playwright MCP:

#### 2.3.1 `complete_task`
```json
{
  "name": "complete_task",
  "description": "Signal that the task is complete. Call when goal is achieved or cannot be achieved.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["success", "failed"],
        "description": "Whether the goal was achieved"
      },
      "reason": {
        "type": "string",
        "description": "Explanation of outcome"
      }
    },
    "required": ["status", "reason"]
  }
}
```

#### 2.3.2 `request_human_approval`
```json
{
  "name": "request_human_approval",
  "description": "Pause and request human approval before proceeding.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "description": "What action requires approval"
      },
      "reason": {
        "type": "string",
        "description": "Why approval is needed"
      }
    },
    "required": ["action", "reason"]
  }
}
```

#### 2.3.3 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-3.1 | Virtual tools appear in tool list sent to LLM | Unit test tool merging |
| AC-3.2 | `complete_task` terminates orchestration loop | Unit test |
| AC-3.3 | `request_human_approval` pauses for user input | Integration test |

---

### 2.4 Orchestration Loop (FR3)

#### 2.4.1 Loop Invariants
1. Exactly ONE tool call executed per turn
2. Conversation history maintained across turns
3. Loop terminates when:
   - `complete_task` called
   - Max turns (20) exceeded
   - Fatal error occurs
   - Human rejects checkpoint

#### 2.4.2 Turn Sequence
```
1. Send messages + tools to LLM
2. Receive response
3. IF no tool_calls:
   - Increment no_action_count
   - IF no_action_count >= 3: return TaskResult(success=False, reason="llm_no_action")
   - Prompt "Call a tool or complete_task", GOTO 1
4. Reset no_action_count to 0
5. Extract FIRST tool_call only
   - If multiple tool_calls returned, log debug: "Ignoring {n-1} additional tool calls"
   - No warning to user - this is expected LLM behavior
6. IF tool is virtual: handle locally
   ELSE: forward to MCP server
7. Append assistant message and tool result to history
8. IF complete_task: return result
9. IF turn >= max_turns: return failure
10. GOTO 1
```

#### 2.4.3 Message History Format
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Goal: {goal}\n\n{initial_snapshot}"},
    {"role": "assistant", "content": "...", "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "...", "content": "..."},
    # ... continues
]
```

#### 2.4.4 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-4.1 | Only first tool_call executed if multiple returned | Unit test with mock LLM |
| AC-4.2 | Max turns (20) terminates loop with `max_turns_exceeded` | Unit test |
| AC-4.3 | Conversation history grows by 2 messages per turn | Unit test |
| AC-4.4 | `complete_task(success)` returns `TaskResult(success=True)` | Unit test |
| AC-4.5 | 3 consecutive no-action responses returns `llm_no_action` | Unit test |
| AC-4.6 | MCPToolError formats as `{"error": true, "message": ...}` and continues loop | Unit test |

#### 2.4.5 Error Recovery (AC-4.6 Detail)
When `MCPToolError` occurs during tool execution:
1. Format error as tool result: `{"error": true, "message": str(error)}`
2. Append to conversation history as normal tool result
3. Continue loop - AI decides whether to retry action or `complete_task(failed)`

This allows the AI to adapt to transient failures without terminating the task.

---

### 2.5 Human Checkpoints (FR4)

#### 2.5.1 Checkpoint Triggering
Checkpoints are evaluated BEFORE tool execution:
```python
def should_checkpoint(tool_call, snapshot, config) -> bool:
    for condition in config.checkpoint_conditions:
        if condition(tool_call, snapshot):
            return True
    return False
```

#### 2.5.2 Normalized Snapshot Interface

Playwright MCP snapshot output SHALL be normalized to this interface before checkpoint evaluation:

```python
@dataclass
class NormalizedSnapshot:
    url: str                        # Current page URL (required)
    title: str                      # Page title (required)
    content: str                    # Accessibility tree as text (required)
    screenshot_path: str | None = None  # Path to screenshot file (optional)

def normalize_snapshot(mcp_output: dict) -> NormalizedSnapshot:
    """
    Extract required fields from Playwright MCP output.
    Raises SnapshotValidationError if required fields missing.
    """
    # Exact field mapping TBD in Phase 1 (POC)
    # Phase 1 will log actual MCP output and update this function
    # At minimum, must extract url, title, and text content
```

**Validation**: If MCP output lacks url, title, or content-equivalent field, raise `SnapshotValidationError` with diagnostic info.

#### 2.5.3 Checkpoint Conditions (Netflix)

Checkpoint predicates operate on `NormalizedSnapshot`:

| Condition | Predicate | Rationale |
|-----------|-----------|-----------|
| Final cancel page | `"finish" in snap.content.lower() and "cancel" in snap.content.lower()` | Final confirmation page contains both keywords |
| Confirm URL pattern | `"/confirm" in snap.url or "/cancelplan" in snap.url` | Netflix cancellation URLs contain these paths |
| Destructive button target | `tool.name == "browser_click" and any(kw in tool.args.get("element", "").lower() for kw in ["finish", "confirm", "complete"])` | Clicking buttons with finality keywords |

**Implementation**:
```python
NETFLIX_CHECKPOINT_CONDITIONS = [
    lambda tool, snap: (
        "finish" in snap.content.lower() and
        "cancel" in snap.content.lower()
    ),
    lambda tool, snap: (
        "/confirm" in snap.url or "/cancelplan" in snap.url
    ),
    lambda tool, snap: (
        tool.name == "browser_click" and
        any(kw in tool.args.get("element", "").lower()
            for kw in ["finish", "confirm", "complete"])
    ),
]
```

#### 2.5.4 User Interaction Protocol
```
1. Display: "⚠️ Human approval required"
2. Display: Action description
3. Display: Current URL
4. Save screenshot to temp file, display path
5. Prompt: "Approve? [y/N]: "
6. If 'y' or 'Y': return True
7. Else: return False
```

#### 2.5.5 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-5.1 | Checkpoint triggers BEFORE tool execution | Unit test execution order |
| AC-5.2 | User input 'y' allows continuation | Integration test |
| AC-5.3 | User input 'n' or empty returns `human_rejected` | Integration test |
| AC-5.4 | Screenshot file exists at displayed path | Integration test |
| AC-5.5 | Snapshot normalization extracts url, title, content fields | Unit test with sample MCP output |
| AC-5.6 | Missing required snapshot field raises `SnapshotValidationError` | Unit test |
| AC-5.7 | Phase 1 POC validates normalize_snapshot() against real Playwright MCP output | Integration test in POC |

---

### 2.6 Service Configuration (FR5)

#### 2.6.1 ServiceConfig Interface
```python
@dataclass
class ServiceConfig:
    name: str                              # "netflix"
    initial_url: str                       # "https://www.netflix.com/account"
    goal_template: str                     # Task description for LLM
    checkpoint_conditions: list[Callable]  # [(tool, snapshot) -> bool]
    success_indicators: list[Callable]     # [(snapshot) -> bool]
    failure_indicators: list[Callable]     # [(snapshot) -> bool]
    system_prompt_addition: str = ""       # Service-specific instructions
```

#### 2.6.2 Netflix Configuration
| Field | Value |
|-------|-------|
| name | `"netflix"` |
| initial_url | `"https://www.netflix.com/account"` |
| goal_template | "Cancel the Netflix subscription. Navigate to cancellation, complete the flow. Decline any retention offers. Call complete_task when you see confirmation that membership is cancelled." |
| system_prompt_addition | "Netflix may show retention offers with discounts. Always decline these and proceed with cancellation." |

**Success Indicators** (any match = verified):
```python
NETFLIX_SUCCESS_INDICATORS = [
    lambda snap: "cancelled" in snap.title.lower(),
    lambda snap: "membership ends" in snap.content.lower(),
    lambda snap: "cancellation confirmed" in snap.content.lower(),
    lambda snap: "/cancelsuccess" in snap.url.lower(),
]
```

**Failure Indicators** (any match = NOT verified):
```python
NETFLIX_FAILURE_INDICATORS = [
    lambda snap: "error" in snap.url.lower(),
    lambda snap: "something went wrong" in snap.content.lower(),
    lambda snap: "unable to process" in snap.content.lower(),
    lambda snap: "/login" in snap.url and "netflix.com" in snap.url,  # Logged out
]
```

#### 2.6.3 Completion Verification
When AI calls `complete_task(status="success")`:
1. Get current snapshot
2. Check `success_indicators` - if ANY match, verified
3. Check `failure_indicators` - if ANY match, NOT verified
4. If not verified, return error to AI as tool result:
   ```json
   {
     "error": true,
     "message": "Cannot verify success. Page does not show expected cancellation confirmation. Current URL: {url}. Check page state and retry, or call complete_task(status='failed') if cancellation is not possible."
   }
   ```

When AI calls `complete_task(status="failed")`:
1. Return `TaskResult(success=False, verified=True, reason=tool_args["reason"])` immediately
2. No indicator checking - AI's failure determination is trusted

#### 2.6.4 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-6.1 | ServiceConfig loads from registry by name | Unit test |
| AC-6.2 | Unknown service raises `ServiceNotFoundError` | Unit test |
| AC-6.3 | Verified success returns `TaskResult(success=True, verified=True)` | Unit test |
| AC-6.4 | Unverified success prompts AI to retry | Integration test |

---

### 2.7 Authentication Handling (FR6)

#### 2.7.1 Profile Strategy
Playwright MCP SHALL run with persistent profile:
- Profile location: `~/.subterminator/browser-profile/`
- Sessions persist across runs
- User logs in manually ONCE, profile saves session

**Configuration**: Pass profile directory via environment variable or command args:
```bash
# Playwright MCP uses --user-data-dir for profile persistence
npx @playwright/mcp@latest --user-data-dir ~/.subterminator/browser-profile/
```

If `--user-data-dir` is not supported by Playwright MCP, fall back to launching Playwright directly with profile and connecting MCP to that instance (to be determined in design phase).

#### 2.7.2 Login Detection
If page URL matches login patterns, trigger checkpoint:
| Service | Login URL Pattern |
|---------|-------------------|
| Netflix | `*/login*` |

#### 2.7.3 Edge Case Handling
| Scenario | Behavior |
|----------|----------|
| 2FA prompt detected | Checkpoint: "2FA required. Complete authentication." |
| CAPTCHA detected | Checkpoint: "CAPTCHA detected. Please solve." |
| Session expired mid-task | Checkpoint: "Session expired. Please log in." |

**Detection Predicates** (checked on each snapshot):
```python
AUTH_EDGE_CASE_DETECTORS = [
    # 2FA detection
    lambda snap: any(kw in snap.content.lower() for kw in [
        "two-factor", "verification code", "2fa", "authenticator"
    ]),
    # CAPTCHA detection
    lambda snap: any(kw in snap.content.lower() for kw in [
        "captcha", "robot", "verify you're human", "security check"
    ]),
    # Session expiry (redirected to login)
    lambda snap: "/login" in snap.url and snap.url != initial_url,
]
```

#### 2.7.4 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-7.1 | Playwright MCP starts with persistent profile | Integration test |
| AC-7.2 | Login page triggers checkpoint | Integration test with login URL |
| AC-7.3 | After login checkpoint, task resumes | Integration test |

---

### 2.8 CLI Interface (FR7)

#### 2.8.1 Command Syntax
```
subterminator cancel <service> [options]
```

#### 2.8.2 Arguments
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| service | string | Yes | Service name (e.g., "netflix") |

#### 2.8.3 Options
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--model` | string | claude-sonnet-4-20250514 | LLM model to use |
| `--max-turns` | int | 20 | Maximum orchestration turns |
| `--dry-run` | flag | false | Show plan without executing |
| `-v, --verbose` | flag | false | Show detailed progress |
| `--no-checkpoint` | flag | false | Skip human checkpoints (testing only) |

#### 2.8.4 Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success - task completed and verified |
| 1 | Failure - task failed or not verified |
| 2 | Configuration error (missing API key, unknown service) |
| 3 | Connection error (MCP server, LLM API) |
| 130 | User interrupted (Ctrl+C) |

#### 2.8.5 Dry Run Behavior
When `--dry-run` is specified:
1. Connect to MCP server (validates connectivity)
2. Get initial snapshot via `browser_snapshot`
3. Send to LLM with tools
4. Display proposed first action (tool name + arguments)
5. Exit with code 0 (no tools executed)

This allows users to verify setup and see what the AI would do first.

#### 2.8.6 Output Format
**Normal mode**:
```
Starting Netflix cancellation...
[Turn 1] browser_snapshot
[Turn 2] browser_click "Cancel Membership"
[Turn 3] browser_click "Continue"
⚠️ Human approval required for: Click "Finish Cancellation"
Approve? [y/N]: y
[Turn 4] browser_click "Finish Cancellation"
[Turn 5] complete_task "success"

✓ Netflix cancellation completed successfully (5 turns)
```

**Verbose mode** (`-v`): Include full snapshot content and tool arguments.

#### 2.8.7 Acceptance Criteria
| ID | Criterion | Test Method |
|----|-----------|-------------|
| AC-8.1 | `subterminator cancel netflix` runs without error (with valid API key) | Integration test |
| AC-8.2 | `--model gpt-4o` uses OpenAI | Integration test |
| AC-8.3 | Missing API key exits with code 2 | Unit test |
| AC-8.4 | Ctrl+C exits with code 130 | Integration test |
| AC-8.5 | Success exits with code 0 | Integration test |
| AC-8.6 | `--dry-run` shows first action and exits without executing | Unit test |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| Requirement | Threshold | Measurement |
|-------------|-----------|-------------|
| MCP connection time | < 10 seconds | Time from start to `tools/list` complete |
| Turn latency | < 30 seconds (target) | Time from LLM call to tool result (excluding checkpoints) |
| Total task time | < 5 minutes (target) | Netflix cancellation (excluding checkpoints) |

**Note**: Turn latency depends on external LLM API response times. System logs turn latency for monitoring. Hard timeout of 60 seconds raises `LLMError` to prevent indefinite hangs.

### 3.2 Reliability

| Requirement | Specification |
|-------------|---------------|
| LLM API retries | 3 attempts, exponential backoff (1s, 2s, 4s) |
| MCP reconnection | 1 retry on connection drop |
| Graceful shutdown | SIGINT/SIGTERM cleanup within 5 seconds |

### 3.3 Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | >= 3.10 | Runtime |
| mcp | >= 1.0 | MCP protocol client |
| langchain-anthropic | >= 0.1 | Claude integration |
| langchain-openai | >= 0.1 | OpenAI integration |
| Node.js | >= 18 | Run Playwright MCP via npx |

---

## 4. Error Handling

### 4.1 Error Taxonomy

| Error Class | Base | When |
|-------------|------|------|
| `OrchestratorError` | Exception | Base for all orchestrator errors |
| `ConfigurationError` | OrchestratorError | Missing API key, invalid model, unknown service |
| `MCPConnectionError` | OrchestratorError | Cannot connect to MCP server |
| `MCPToolError` | OrchestratorError | MCP tool execution failed |
| `LLMError` | OrchestratorError | LLM API call failed after retries |
| `CheckpointRejectedError` | OrchestratorError | Human rejected checkpoint |

### 4.2 Error Messages

| Error | User Message |
|-------|--------------|
| Missing ANTHROPIC_API_KEY | "Missing ANTHROPIC_API_KEY. Set it via environment variable or use --model gpt-4o with OPENAI_API_KEY." |
| MCP connection failed | "Failed to connect to Playwright MCP. Ensure Node.js is installed and run: npx @playwright/mcp@latest" |
| Unknown service | "Unknown service '{name}'. Available services: netflix" |

---

## 5. Data Structures

### 5.1 TaskResult
```python
from typing import Literal

TaskReason = Literal[
    "completed",           # Task completed successfully
    "human_rejected",      # Human rejected checkpoint
    "max_turns_exceeded",  # Hit max_turns limit
    "llm_no_action",       # LLM refused to call tools
    "llm_error",           # LLM API error after retries
    "mcp_error",           # MCP connection/tool error
    "verification_failed", # AI claimed success but not verified
]

@dataclass
class TaskResult:
    success: bool              # Task completed successfully
    verified: bool             # Completion verified by service config
    reason: TaskReason         # Structured reason for outcome
    turns: int                 # Number of turns taken
    final_url: str | None      # Final page URL
    error: str | None          # Error message if failed
```

### 5.2 ToolCall
```python
@dataclass
class ToolCall:
    id: str                    # Unique call ID
    name: str                  # Tool name
    arguments: dict            # Tool arguments
```

### 5.3 Snapshot (from Playwright MCP)
Raw Playwright MCP output is normalized to `NormalizedSnapshot` (see Section 2.5.2):
```python
@dataclass
class NormalizedSnapshot:
    url: str                        # Current page URL
    title: str                      # Page title
    content: str                    # Accessibility tree as text
    screenshot_path: str | None = None  # Path to screenshot file (optional)
```

**Note**: Raw MCP output format varies. The `normalize_snapshot()` function (Section 2.5.2) extracts these fields from actual MCP output discovered during POC.

---

## 6. Security Considerations

### 6.1 API Key Handling
- API keys read from environment variables only (never CLI args)
- Keys never logged or displayed
- Keys never persisted to disk by orchestrator

### 6.2 Browser Profile
- Profile stored in user home directory
- Contains session cookies - user responsibility to secure
- No credentials stored by orchestrator

---

## 7. Testing Strategy

### 7.1 Unit Tests
- Mock MCP client for orchestration loop tests
- Mock LLM client for tool routing tests
- Service config predicates with sample snapshots

### 7.2 Integration Tests
- Real Playwright MCP server
- Mock LLM responses (deterministic)
- Checkpoint flow with simulated user input

### 7.3 E2E Tests
- Real LLM API (rate-limited)
- Real Playwright MCP
- Real Netflix test account (manual execution)

---

## 8. Assumptions and Dependencies

### 8.1 Assumptions Requiring POC Validation
| Assumption | Validation |
|------------|------------|
| Playwright MCP snapshot contains parseable URL | Log output in POC |
| mcp-use library connects without issues | POC integration |
| Checkpoint predicates can detect final confirmation | Manual testing |

### 8.2 External Dependencies
| Dependency | Risk | Mitigation |
|------------|------|------------|
| Playwright MCP availability | Low | Microsoft-maintained, stable |
| Netflix UI changes | Medium | Service config is isolated, easy to update |
| LLM API availability | Low | Retry logic, multiple providers |
