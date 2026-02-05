# Design: AI-Led MCP Browser Control Redesign

## 1. Architecture Overview

### 1.1 System Context

```
┌────────────────────────────────────────────────────────────────────────┐
│                           CLI / Application                            │
│                                                                        │
│  User runs: subterminator cancel --service netflix                     │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          TaskOrchestrator                              │
│                                                                        │
│  - Owns conversation loop                                              │
│  - Coordinates AI ↔ Tools                                              │
│  - Enforces single-tool-per-turn                                       │
│  - Manages conversation history                                        │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
┌─────────────────────┐ ┌─────────────┐ ┌─────────────────────┐
│    AIClient         │ │ToolRegistry │ │  ServiceConfig      │
│                     │ │             │ │                     │
│ - Anthropic API     │ │ - 7 tools   │ │ - Checkpoints       │
│ - Tool schemas      │ │ - Execute   │ │ - Completion rules  │
│ - Conversation mgmt │ │ - Validate  │ │ - Service guidance  │
└─────────────────────┘ └──────┬──────┘ └─────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          BrowserToolServer                             │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ ElementRegistry  │  │ SnapshotFactory  │  │ ActionExecutor   │     │
│  │                  │  │                  │  │                  │     │
│  │ - Ref mapping    │  │ - A11y tree      │  │ - Click          │     │
│  │ - Ref validation │  │ - Screenshot     │  │ - Fill           │     │
│  │ - Ref lifecycle  │  │ - Pruning        │  │ - Select         │     │
│  └──────────────────┘  └──────────────────┘  │ - Scroll         │     │
│                                              └──────────────────┘     │
│                                                       │               │
│                                                       ▼               │
│                                            ┌──────────────────┐       │
│                                            │ PlaywrightBrowser│       │
│                                            │ (existing)       │       │
│                                            └──────────────────┘       │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

| Component | Responsibility | Dependencies |
|-----------|---------------|--------------|
| **TaskOrchestrator** | Conversation loop, turn management, human checkpoints, tool dispatch | AIClient, BrowserToolServer, ServiceConfig |
| **AIClient** | Claude API communication, tool schema management, history truncation | anthropic SDK |
| **ServiceConfig** | Service-specific checkpoints, completion criteria, prompts | None |
| **BrowserToolServer** | Tool implementations, snapshot generation, tool dispatch via execute() | ElementRegistry, SnapshotFactory, ActionExecutor |
| **ElementRegistry** | Element ref lifecycle, ref-to-element mapping | None |
| **SnapshotFactory** | Accessibility tree extraction, screenshot, pruning | PlaywrightBrowser |
| **ActionExecutor** | Browser action execution with error handling | PlaywrightBrowser |

**Note on ToolRegistry**: The architecture diagram shows "ToolRegistry" as a conceptual component. In the implementation, this is collapsed into `BrowserToolServer.execute()` which routes tool calls to appropriate methods. No separate ToolRegistry class exists.

### 1.3 Data Flow

```
1. User starts task
   │
   ▼
2. TaskOrchestrator creates initial snapshot
   │
   ▼
3. TaskOrchestrator sends goal + snapshot to AIClient
   │
   ▼
4. AIClient calls Claude API with tools
   │
   ▼
5. Claude returns tool_call (e.g., browser_click(@e7))
   │
   ▼
6. TaskOrchestrator dispatches to ToolRegistry
   │
   ▼
7. ToolRegistry validates and executes via BrowserToolServer
   │
   ├── ElementRegistry resolves @e7 to element
   ├── ActionExecutor performs click
   └── SnapshotFactory creates fresh snapshot
   │
   ▼
8. Result with new snapshot returned to TaskOrchestrator
   │
   ├── Check service checkpoints
   │   └── If triggered: request human approval
   │
   ▼
9. Add result to conversation, go to step 4
   │
   (Loop continues until complete_task or max_turns)
```

---

## 2. Component Design

### 2.1 TaskOrchestrator

**Purpose**: Owns the AI conversation loop and coordinates all components.

**Key Decisions**:
- Single class owns the loop (no distributed state machines)
- Conversation history is in-memory (no persistence requirement per spec)
- Human checkpoints evaluated after each tool execution
- Intercepts `request_human_approval` and `complete_task` tools before dispatching to tool_server

**Human Approval Control Flow**:
```
Two sources of human approval:

1. SERVER-ENFORCED CHECKPOINTS (after any action tool):
   a. Tool executes, returns ToolResult with snapshot
   b. Orchestrator calls _check_checkpoint(snapshot)
   c. If checkpoint matches: call human_handler.request_approval()
   d. If rejected: override ToolResult with human_rejected error

2. AI-REQUESTED APPROVAL (via request_human_approval tool):
   a. AI calls request_human_approval tool
   b. Orchestrator intercepts (does NOT dispatch to tool_server)
   c. Orchestrator calls human_handler.request_approval()
   d. Returns approval result to AI

Integration:
- If human_handler is None, checkpoints are logged but not enforced (testing mode)
- CLI provides human_handler implementation with input()
```

**Complete Task Control Flow**:
```
1. AI calls complete_task(status, reason)
2. Orchestrator intercepts (does NOT dispatch to tool_server)
3. If status="success":
   a. Get current snapshot from tool_server.get_snapshot()
   b. Call _verify_completion(status, snapshot)
   c. If verification fails: return acknowledged=false with message
4. If status="failed":
   a. Log failure with current snapshot
   b. Return acknowledged=true
5. Return TaskResult
```

```python
class TaskOrchestrator:
    """Coordinates AI-led browser task execution."""

    # Tools that orchestrator handles directly (not dispatched to tool_server)
    ORCHESTRATOR_HANDLED_TOOLS = {"request_human_approval", "complete_task"}

    def __init__(
        self,
        ai_client: AIClientProtocol,
        tool_server: BrowserToolServer,
        service_config: ServiceConfig,
        human_handler: HumanApprovalHandler | None = None,
        max_turns: int = 20,
    ):
        self.ai_client = ai_client
        self.tool_server = tool_server
        self.service_config = service_config
        self.human_handler = human_handler
        self.max_turns = max_turns
        self.conversation: list[Message] = []
        self.turn_count: int = 0

    async def run(self, goal: str) -> TaskResult:
        """Execute task with AI-led tool invocation."""
        # Initialize
        initial_snapshot = await self.tool_server.get_snapshot()
        self.conversation = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=f"Goal: {goal}\n\nCurrent state:\n{self._format_snapshot(initial_snapshot.snapshot)}")
        ]

        for turn in range(self.max_turns):
            response = await self.ai_client.chat(self.conversation, tools=TOOL_SCHEMAS, system="")

            if not response.tool_calls:
                # Prompt for explicit completion
                self.conversation.append(Message(role="assistant", content=response.content))
                self.conversation.append(Message(role="user", content="Please call complete_task."))
                continue

            tool_call = response.tool_calls[0]  # Single tool per turn
            result = await self._execute_tool(tool_call)

            # Add to conversation
            self.conversation.append(Message(role="assistant", content=response.content, tool_calls=[tool_call]))
            self.conversation.append(Message(role="tool", content=result.to_json(), tool_call_id=tool_call.id))

            # Check for completion
            if tool_call.name == "complete_task":
                return TaskResult(
                    success=result.success and tool_call.arguments.get("status") == "success",
                    reason=tool_call.arguments.get("reason", ""),
                    turns=turn + 1,
                    final_snapshot=result.snapshot
                )

        return TaskResult(success=False, reason="max_turns_exceeded", turns=self.max_turns)

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute tool, handling orchestrator-managed tools specially."""
        if tool_call.name == "request_human_approval":
            return await self._handle_human_approval(tool_call.arguments)
        if tool_call.name == "complete_task":
            return await self._handle_complete_task(tool_call.arguments)

        # Dispatch to tool server
        result = await self.tool_server.execute(tool_call.name, tool_call.arguments)

        # Check server-enforced checkpoints
        if result.snapshot and self.human_handler:
            if self.service_config.check_checkpoint(result.snapshot):
                approved, message = await self.human_handler.request_approval(
                    action=f"Checkpoint triggered: {result.snapshot.page.title}",
                    reason="Server-enforced checkpoint",
                    screenshot=base64.b64decode(result.snapshot.screenshot)
                )
                if not approved:
                    return ToolResult(
                        success=False,
                        error="human_rejected",
                        message=f"User feedback: {message}",
                        snapshot=result.snapshot
                    )

        return result

    async def _handle_human_approval(self, arguments: dict) -> ToolResult:
        """Handle AI-requested human approval."""
        if not self.human_handler:
            return ToolResult(success=True, message="Approval skipped (no handler)")

        snapshot = await self.tool_server.get_snapshot()
        approved, message = await self.human_handler.request_approval(
            action=arguments.get("action", ""),
            reason=arguments.get("reason", ""),
            screenshot=base64.b64decode(snapshot.snapshot.screenshot)
        )
        return ToolResult(
            success=approved,
            error="human_rejected" if not approved else None,
            message=message,
            snapshot=snapshot.snapshot
        )

    async def _handle_complete_task(self, arguments: dict) -> ToolResult:
        """Handle task completion with verification."""
        status = arguments.get("status", "failed")
        reason = arguments.get("reason", "")
        snapshot = (await self.tool_server.get_snapshot()).snapshot

        if status == "success":
            if not self.service_config.verify_success(snapshot):
                return ToolResult(
                    success=False,
                    message="Cannot verify success. Please check the page state.",
                    snapshot=snapshot
                )
        return ToolResult(success=True, snapshot=snapshot)
```

### 2.2 AIClient

**Purpose**: Abstracts Claude API communication.

**Key Decisions**:
- Wraps anthropic SDK for easier testing
- Owns tool schema definitions
- Handles conversation formatting

```python
class AIClient:
    """Claude API client with tool support."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: list[Message],
        tools: list[Tool],
        system: str,
    ) -> AIResponse:
        """Send conversation to Claude and get response with tool calls."""
        ...
```

### 2.3 BrowserToolServer

**Purpose**: Implements the 7 browser control tools.

**Key Decisions**:
- Each tool is a method that returns ToolResult
- All action tools (click, fill, select, scroll) return fresh snapshot
- Tool validation happens before execution
- `request_human_approval` and `complete_task` return marker results (actual handling by orchestrator)

**Data Flow: Snapshot → Registry → Tool Result**:
```
1. SnapshotFactory.create() returns (Snapshot, list[ElementInfo])
   - Snapshot: serializable data for AI
   - ElementInfo list: includes selectors for action execution

2. BrowserToolServer._refresh_snapshot() orchestrates:
   snapshot, elements = await self.snapshot_factory.create()
   self.registry.register_snapshot(elements)  # Assigns refs
   return snapshot

3. All action tools call _refresh_snapshot() after execution
```

```python
class BrowserToolServer:
    """Implements browser control tools."""

    def __init__(self, browser: PlaywrightBrowser):
        self.registry = ElementRegistry()
        self.snapshot_factory = SnapshotFactory(browser)
        self.executor = ActionExecutor(browser)

    async def _refresh_snapshot(self, viewport_only: bool = True) -> Snapshot:
        """Create fresh snapshot and register elements."""
        snapshot, elements = await self.snapshot_factory.create(viewport_only)
        self.registry.register_snapshot(elements)
        return snapshot

    async def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        """Execute tool by name. Routes to appropriate method."""
        method = getattr(self, tool_name, None)
        if not method:
            return ToolResult(success=False, error="action_failed", message=f"Unknown tool: {tool_name}")
        return await method(**arguments)

    async def get_snapshot(self, viewport_only: bool = True) -> ToolResult:
        """Capture current page state."""
        snapshot = await self._refresh_snapshot(viewport_only)
        return ToolResult(success=True, snapshot=snapshot)

    async def browser_click(self, ref: str) -> ToolResult:
        """Click element by ref."""
        try:
            element = self.registry.resolve(ref)
            await self.executor.click(element)
            snapshot = await self._refresh_snapshot()
            return ToolResult(success=True, snapshot=snapshot)
        except RefInvalidError:
            snapshot = await self._refresh_snapshot()
            return ToolResult(success=False, error="ref_invalid", snapshot=snapshot)
        except (ElementDisabledError, ElementObscuredError, TimeoutError) as e:
            snapshot = await self._refresh_snapshot()
            return ToolResult(success=False, error=self._map_exception(e), snapshot=snapshot)

    async def browser_fill(self, ref: str, value: str, clear_first: bool = True) -> ToolResult:
        """Fill input field."""
        # Similar pattern to browser_click
        ...

    async def browser_select(self, ref: str, value: str) -> ToolResult:
        """Select dropdown option."""
        ...

    async def browser_scroll(self, ref: str | None = None, direction: str | None = None, amount: int = 300) -> ToolResult:
        """Scroll page or element into view."""
        ...

    async def request_human_approval(self, action: str, reason: str) -> ToolResult:
        """Return marker for orchestrator to handle."""
        # Returns a special marker - actual approval handled by orchestrator
        return ToolResult(success=True, message="APPROVAL_REQUESTED")

    async def complete_task(self, status: str, reason: str) -> ToolResult:
        """Return marker for orchestrator to handle."""
        # Returns a special marker - actual verification handled by orchestrator
        return ToolResult(success=True, message=f"COMPLETION_{status.upper()}")

    def _map_exception(self, e: Exception) -> ErrorCode:
        """Map exception to error code."""
        if isinstance(e, ElementDisabledError):
            return "element_disabled"
        if isinstance(e, ElementObscuredError):
            return "element_obscured"
        if isinstance(e, TimeoutError):
            return "timeout"
        return "action_failed"
```

### 2.4 ElementRegistry

**Purpose**: Manages element reference lifecycle.

**Key Decisions**:
- Refs are invalidated after any action (per spec)
- Uses dict for O(1) lookup
- Generates refs via depth-first traversal

```python
class ElementRegistry:
    """Manages element references within a snapshot lifecycle."""

    def __init__(self):
        self._current_refs: dict[str, ElementInfo] = {}
        self._snapshot_id: str | None = None

    def register_snapshot(self, elements: list[ElementInfo]) -> None:
        """Register elements from a new snapshot, invalidating old refs."""
        self._current_refs = {}
        self._snapshot_id = str(uuid4())
        for i, elem in enumerate(elements):
            ref = f"@e{i}"
            elem.ref = ref
            self._current_refs[ref] = elem

    def resolve(self, ref: str) -> ElementInfo:
        """Resolve ref to element. Raises RefInvalidError if not found."""
        if ref not in self._current_refs:
            raise RefInvalidError(ref)
        return self._current_refs[ref]

    def invalidate(self) -> None:
        """Invalidate all current refs (called after any action)."""
        self._current_refs = {}
        self._snapshot_id = None
```

### 2.5 SnapshotFactory

**Purpose**: Creates snapshots from page state.

**Key Decisions**:
- Uses Playwright's accessibility tree API
- Implements pruning rules from spec
- Always captures screenshot
- Returns tuple: (Snapshot for AI, ElementInfo list for registry)

**Bounding Box Strategy**:
- Playwright's accessibility tree includes bounding boxes via `boundingBox` property
- If not available, we make parallel `element.bounding_box()` calls using asyncio.gather()
- With 100 elements, ~100 parallel calls complete in <500ms on typical connections
- This is factored into the <1s snapshot creation target

```python
class SnapshotFactory:
    """Creates snapshots from page state."""

    INTERACTIVE_ROLES = frozenset([
        "button", "link", "checkbox", "radio", "textbox", "combobox",
        "listbox", "menuitem", "menuitemcheckbox", "menuitemradio",
        "tab", "switch", "slider"
    ])

    LANDMARK_ROLES = frozenset(["region", "dialog", "alert", "alertdialog"])

    MAX_ELEMENTS = 100
    MAX_DEPTH = 10
    MAX_NAME_LENGTH = 200

    def __init__(self, browser: PlaywrightBrowser):
        self.browser = browser

    async def create(self, viewport_only: bool = True) -> tuple[Snapshot, list[ElementInfo]]:
        """Create snapshot with accessibility tree and screenshot.

        Returns:
            Tuple of:
            - Snapshot: serializable data for AI (no selectors)
            - list[ElementInfo]: full data including selectors for action execution
        """
        raw_tree = await self.browser.accessibility_tree()
        screenshot = await self.browser.screenshot()
        viewport = await self.browser.viewport_size()

        # Extract elements with full info (including selectors)
        full_elements = await self._extract_elements(raw_tree, viewport_only, viewport)
        full_elements = self._prune_elements(full_elements)

        # Create snapshot for AI (serializable, no selectors)
        snapshot = Snapshot(
            snapshot_id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            elements=[self._to_snapshot_element(e) for e in full_elements],
            focused=self._find_focused(full_elements),
            page=PageInfo(
                url=await self.browser.url(),
                title=await self.browser.title(),
            ),
            screenshot=base64.b64encode(screenshot).decode(),
            viewport=viewport,
        )

        return snapshot, full_elements

    def _to_snapshot_element(self, elem: ElementInfo) -> SnapshotElement:
        """Convert ElementInfo to serializable SnapshotElement (strips selector)."""
        return SnapshotElement(
            ref=elem.ref,
            role=elem.role,
            name=elem.name[:self.MAX_NAME_LENGTH] + ("..." if len(elem.name) > self.MAX_NAME_LENGTH else ""),
            state=elem.state,
            bbox=elem.bbox,
            value=elem.value,
            level=elem.level,
        )
```

### 2.6 ActionExecutor

**Purpose**: Executes browser actions with error handling.

**Key Decisions**:
- Takes ElementInfo (with selector) for action execution
- **Raises exceptions** on failure (caught by BrowserToolServer)
- Maps Playwright errors to our exception types
- Enforces timeouts

**Error Handling Strategy**:
```
ActionExecutor RAISES exceptions:
  - ElementDisabledError
  - ElementObscuredError
  - TimeoutError
  - MCPError (generic fallback)

BrowserToolServer CATCHES and converts to ToolResult:
  - try: await self.executor.click(element)
  - except RefInvalidError: return ToolResult(error="ref_invalid")
  - except ElementDisabledError: return ToolResult(error="element_disabled")
  - etc.

This separation keeps ActionExecutor pure (raises on failure)
while BrowserToolServer handles the ToolResult conversion.
```

```python
class ActionExecutor:
    """Executes browser actions with error handling."""

    def __init__(self, browser: PlaywrightBrowser, default_timeout: int = 2000):
        self.browser = browser
        self.default_timeout = default_timeout

    async def click(self, element: ElementInfo) -> None:
        """Click element. Raises on failure."""
        try:
            if element.selector:
                await self.browser.click(element.selector, timeout=self.default_timeout)
            elif element.bbox:
                await self.browser.click_coordinates(element.bbox.center())
            else:
                raise MCPError(f"Element {element.ref} has no selector or bbox")
        except playwright.async_api.Error as e:
            raise self._map_playwright_error(e, element.ref)

    async def fill(self, element: ElementInfo, value: str, clear_first: bool = True) -> None:
        """Fill input element. Raises on failure."""
        try:
            if clear_first:
                await self.browser.fill(element.selector, "")
            await self.browser.fill(element.selector, value, timeout=self.default_timeout)
        except playwright.async_api.Error as e:
            raise self._map_playwright_error(e, element.ref)

    def _map_playwright_error(self, e: playwright.async_api.Error, ref: str) -> MCPError:
        """Map Playwright error to our exception types."""
        msg = str(e).lower()
        if "disabled" in msg:
            return ElementDisabledError(ref)
        if "obscured" in msg or "intercept" in msg:
            return ElementObscuredError(ref)
        if "timeout" in msg:
            return TimeoutError(f"click on {ref}", self.default_timeout)
        return MCPError(f"Action failed on {ref}: {e}")
```

### 2.7 ServiceConfig

**Purpose**: Service-specific configuration.

**Key Decisions**:
- Registry pattern for multiple services
- Checkpoint conditions are predicates on snapshots
- Completion criteria are success/failure indicator lists

```python
@dataclass
class ServiceConfig:
    """Service-specific configuration."""

    name: str
    checkpoint_conditions: list[Callable[[Snapshot], bool]]
    completion_criteria: CompletionCriteria
    system_prompt_addition: str = ""

NETFLIX_CONFIG = ServiceConfig(
    name="netflix",
    checkpoint_conditions=[
        lambda s: "finish cancellation" in s.page.title.lower(),
        lambda s: any(
            e.role == "button" and e.name and "finish cancel" in e.name.lower()
            for e in s.elements
        ),
    ],
    completion_criteria=CompletionCriteria(
        success_indicators=[
            lambda s: "cancelled" in s.page.title.lower(),
        ],
        failure_indicators=[
            lambda s: "error" in s.page.url.lower(),
        ],
    ),
    system_prompt_addition="Netflix-specific: Look for 'Cancel Membership' buttons, handle retention offers by declining.",
)
```

---

## 3. Technical Decisions

### 3.1 Why New Components vs Extending Existing

| Decision | Rationale |
|----------|-----------|
| New `TaskOrchestrator` instead of modifying `CancellationEngine` | Engine is tightly coupled to state machine pattern; cleaner to build new orchestrator than refactor |
| New `BrowserToolServer` instead of extending `AIBrowserAgent` | Agent's perceive-plan-execute loop contradicts AI-led design; new component needed |
| Reuse `PlaywrightBrowser` | Browser abstraction is sound; new components wrap it |
| New `SnapshotFactory` instead of using existing a11y methods | Need structured output with refs, pruning, screenshots combined |

### 3.2 Async Design

All browser operations and AI calls are async:
- Playwright operations are async
- Claude API calls are async
- Human approval requests can use async input handlers

```python
# All public methods are async
async def run(self, goal: str) -> TaskResult: ...
async def get_snapshot(self) -> Snapshot: ...
async def browser_click(self, ref: str) -> ToolResult: ...
```

### 3.3 Error Handling Strategy

| Error Type | Handling |
|------------|----------|
| Ref validation errors | Return `ref_invalid` error with fresh snapshot |
| Playwright errors | Map to specific error codes (element_disabled, element_obscured, etc.) |
| Network errors (AI) | Retry with exponential backoff per NFR4 |
| Timeout errors | Return `timeout` error with fresh snapshot |
| Unexpected errors | Log, return `action_failed` with details |

### 3.4 Token Management

History truncation is handled by AIClient:
- Track estimated token count per message
- When approaching limit, summarize old turns
- Summary format defined in spec

```python
class AIClient:
    MAX_HISTORY_TOKENS = 10000

    def _truncate_history(self, messages: list[Message]) -> list[Message]:
        """Truncate history if exceeding token limit."""
        total_tokens = sum(self._estimate_tokens(m) for m in messages)
        if total_tokens <= self.MAX_HISTORY_TOKENS:
            return messages

        # Keep system, initial user message, and last 10 turns
        system = messages[0]
        initial = messages[1]
        recent = messages[-20:]  # 10 turns = 20 messages (assistant + tool)

        # Summarize dropped messages
        dropped = messages[2:-20]
        summary = self._summarize_actions(dropped)

        return [system, initial, Message(role="user", content=summary)] + recent
```

---

## 4. Risk Analysis

### 4.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Playwright accessibility tree doesn't provide bounding boxes | Low | High | Fallback to `element.bounding_box()` call per element |
| Screenshot size exceeds vision token budget | Medium | Medium | Resize to 1024x768 before encoding |
| Claude ignores single-tool-per-turn instruction | Medium | Low | Server enforces (only execute first tool_call) |
| ElementRegistry ref collision | Very Low | High | Use UUIDs for snapshot_id, sequential ints for refs |

### 4.2 Integration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PlaywrightBrowser interface changes break integration | Low | Medium | Use adapter pattern, pin interface version |
| Existing tests expect old agent behavior | High | Low | Keep old agent code, new feature is additive |
| Service configs need frequent updates | Certain | Low | Make configs data-driven, easy to modify |

---

## 5. Testing Strategy

### 5.1 Unit Testing

| Component | Mock Strategy |
|-----------|---------------|
| TaskOrchestrator | Mock AIClient and BrowserToolServer |
| AIClient | Mock anthropic.Anthropic |
| BrowserToolServer | Mock PlaywrightBrowser |
| ElementRegistry | No mocks needed (pure logic) |
| SnapshotFactory | Mock PlaywrightBrowser methods |
| ActionExecutor | Mock PlaywrightBrowser methods |

### 5.2 Integration Testing

```python
class TestTaskOrchestrator:
    """Integration tests with mock AI and browser."""

    async def test_successful_cancellation_flow(self):
        """AI correctly sequences: click expand -> check checkbox -> click confirm."""
        mock_ai = MockAIClient([
            ToolCall("browser_click", {"ref": "@e3"}),  # expand
            ToolCall("browser_click", {"ref": "@e7"}),  # checkbox
            ToolCall("browser_click", {"ref": "@e12"}), # confirm
            ToolCall("complete_task", {"status": "success", "reason": "Cancelled"}),
        ])
        mock_browser = MockBrowser([
            Snapshot(elements=[...]),  # initial
            Snapshot(elements=[...]),  # after expand
            Snapshot(elements=[...]),  # after checkbox
            Snapshot(elements=[...]),  # after confirm (success page)
        ])

        orchestrator = TaskOrchestrator(mock_ai, BrowserToolServer(mock_browser), NETFLIX_CONFIG)
        result = await orchestrator.run("Cancel Netflix subscription")

        assert result.success
        assert result.turns == 4
```

### 5.3 Fixture Requirements

Per spec section 2.3.3:
- JSON schema for Snapshot validation
- Netflix-specific snapshot fixtures for cancellation flow stages:
  - Account active state
  - Retention offer state
  - Confirmation page state
  - Success/cancelled state

---

## 6. File Structure

```
src/subterminator/
├── core/
│   ├── browser.py          # Existing PlaywrightBrowser (unchanged)
│   ├── protocols.py        # Existing protocols (add new types)
│   └── ...
├── mcp/                     # New package for AI-led design
│   ├── __init__.py
│   ├── orchestrator.py     # TaskOrchestrator
│   ├── ai_client.py        # AIClient
│   ├── tool_server.py      # BrowserToolServer
│   ├── registry.py         # ElementRegistry
│   ├── snapshot.py         # SnapshotFactory, Snapshot dataclass
│   ├── executor.py         # ActionExecutor
│   ├── types.py            # ToolResult, Message, etc.
│   └── services/
│       ├── __init__.py
│       ├── base.py         # ServiceConfig base
│       └── netflix.py      # Netflix-specific config
tests/
├── unit/
│   └── mcp/
│       ├── test_orchestrator.py
│       ├── test_ai_client.py
│       ├── test_tool_server.py
│       ├── test_registry.py
│       ├── test_snapshot.py
│       └── test_executor.py
├── integration/
│   └── mcp/
│       └── test_orchestrator_integration.py
└── fixtures/
    └── mcp/
        ├── snapshots/
        │   ├── netflix_account_active.json
        │   ├── netflix_retention_offer.json
        │   └── netflix_cancelled.json
        └── snapshot_schema.json
```

---

## 7. Migration Strategy

### 7.1 Coexistence

The new AI-led design lives in `src/subterminator/mcp/` alongside existing code:
- Existing `CancellationEngine` and `AIBrowserAgent` remain functional
- CLI can route to either path based on flag: `--experimental-ai-led`
- Gradual migration once validated

### 7.2 Migration Steps

1. **Phase 0**: Implement core components, test with mock browser/AI
2. **Phase 1**: Wire to real Playwright and Claude
3. **Phase 2**: Add Netflix service config, test manually
4. **Phase 3**: Add CLI integration with experimental flag
5. **Phase 4**: Measure success rate, compare to existing
6. **Phase 5**: Deprecate old path if new performs better

---

## 8. Open Design Questions Resolved

| Question | Resolution |
|----------|------------|
| Where to store conversation history? | In-memory on TaskOrchestrator (spec says no persistence across sessions) |
| How to handle human approval UI? | Async callback passed to orchestrator; CLI implements with simple input() |
| How to get bounding boxes? | SnapshotFactory calls element.bounding_box() for each included element |
| JSON schema for snapshots | TypeScript interface in spec serves as schema; generate JSON Schema from Pydantic model |

---

## 9. Interface Definitions

### 9.1 Protocol Definitions

```python
# protocols.py additions

from typing import Protocol, Callable, Awaitable
from dataclasses import dataclass

@dataclass
class Message:
    """A message in the conversation."""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list["ToolCall"] | None = None
    tool_call_id: str | None = None

@dataclass
class ToolCall:
    """A tool invocation from the AI."""
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class AIResponse:
    """Response from AI client."""
    content: str
    tool_calls: list[ToolCall]
    stop_reason: Literal["end_turn", "tool_use", "max_tokens"]

class AIClientProtocol(Protocol):
    """Protocol for AI client implementations."""

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict],
        system: str,
    ) -> AIResponse:
        """Send conversation to AI and get response."""
        ...

class HumanApprovalHandler(Protocol):
    """Protocol for human approval UI implementations."""

    async def request_approval(
        self,
        action: str,
        reason: str,
        screenshot: bytes,
    ) -> tuple[bool, str | None]:
        """Request human approval. Returns (approved, message)."""
        ...
```

### 9.2 Data Types

```python
# types.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

@dataclass
class BoundingBox:
    """Element position in viewport coordinates."""
    x: int
    y: int
    width: int
    height: int

    def center(self) -> tuple[int, int]:
        """Return center point of bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)

@dataclass
class ElementInfo:
    """Element information for snapshots."""
    ref: str = ""  # Assigned by registry
    role: str = ""
    name: str = ""
    state: list[str] = field(default_factory=list)
    bbox: BoundingBox | None = None
    value: str | None = None
    level: int | None = None  # For headings
    selector: str | None = None  # CSS selector for action execution
    children: list[str] = field(default_factory=list)

@dataclass
class PageInfo:
    """Page metadata."""
    url: str
    title: str

@dataclass
class ViewportInfo:
    """Viewport dimensions and scroll position."""
    width: int
    height: int
    scroll_x: int
    scroll_y: int

@dataclass
class Snapshot:
    """Complete page state at a point in time."""
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    elements: list[ElementInfo] = field(default_factory=list)
    focused: str | None = None
    page: PageInfo = field(default_factory=lambda: PageInfo("", ""))
    screenshot: str = ""  # Base64-encoded PNG
    viewport: ViewportInfo = field(default_factory=lambda: ViewportInfo(1024, 768, 0, 0))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "elements": [
                {
                    "ref": e.ref,
                    "role": e.role,
                    "name": e.name,
                    "state": e.state,
                    "bbox": {"x": e.bbox.x, "y": e.bbox.y, "width": e.bbox.width, "height": e.bbox.height} if e.bbox else None,
                    "value": e.value,
                    "level": e.level,
                    "children": e.children if e.children else None,
                } for e in self.elements
            ],
            "focused": self.focused,
            "page": {"url": self.page.url, "title": self.page.title},
            "screenshot": self.screenshot,
            "viewport": {
                "width": self.viewport.width,
                "height": self.viewport.height,
                "scroll_x": self.viewport.scroll_x,
                "scroll_y": self.viewport.scroll_y,
            },
        }

ErrorCode = Literal[
    "ref_invalid",
    "element_disabled",
    "element_obscured",
    "element_not_visible",
    "action_failed",
    "timeout",
    "human_rejected",
    "invalid_params",
]

@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    snapshot: Snapshot | None = None
    error: ErrorCode | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for AI."""
        result = {"success": self.success}
        if self.snapshot:
            result["snapshot"] = self.snapshot.to_dict()
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message
        return result

@dataclass
class TaskResult:
    """Final result of a task execution."""
    success: bool
    reason: str
    turns: int
    final_snapshot: Snapshot | None = None

@dataclass
class CompletionCriteria:
    """Service-specific completion verification rules."""
    success_indicators: list[Callable[[Snapshot], bool]] = field(default_factory=list)
    failure_indicators: list[Callable[[Snapshot], bool]] = field(default_factory=list)
```

### 9.3 Exception Types

```python
# exceptions.py

class MCPError(Exception):
    """Base exception for MCP browser control."""
    pass

class RefInvalidError(MCPError):
    """Element reference not found in current snapshot."""
    def __init__(self, ref: str):
        self.ref = ref
        super().__init__(f"Element reference '{ref}' not found in current snapshot")

class ElementDisabledError(MCPError):
    """Element is disabled and cannot be interacted with."""
    def __init__(self, ref: str):
        self.ref = ref
        super().__init__(f"Element '{ref}' is disabled")

class ElementObscuredError(MCPError):
    """Element is covered by another element."""
    def __init__(self, ref: str, obscuring_element: str | None = None):
        self.ref = ref
        self.obscuring_element = obscuring_element
        msg = f"Element '{ref}' is obscured"
        if obscuring_element:
            msg += f" by '{obscuring_element}'"
        super().__init__(msg)

class TimeoutError(MCPError):
    """Operation timed out."""
    def __init__(self, operation: str, timeout_ms: int):
        self.operation = operation
        self.timeout_ms = timeout_ms
        super().__init__(f"Operation '{operation}' timed out after {timeout_ms}ms")

class InvalidParamsError(MCPError):
    """Invalid or missing parameters for tool call."""
    def __init__(self, tool: str, message: str):
        self.tool = tool
        super().__init__(f"Invalid params for '{tool}': {message}")
```

### 9.4 Component Interfaces

#### 9.4.1 TaskOrchestrator Interface

```python
class TaskOrchestrator:
    """Coordinates AI-led browser task execution."""

    def __init__(
        self,
        ai_client: AIClientProtocol,
        tool_server: "BrowserToolServer",
        service_config: "ServiceConfig",
        human_handler: HumanApprovalHandler | None = None,
        max_turns: int = 20,
    ) -> None: ...

    async def run(self, goal: str) -> TaskResult:
        """
        Execute a task with AI-led tool invocation.

        Args:
            goal: Natural language description of the goal.

        Returns:
            TaskResult with success status, reason, and turn count.

        The orchestrator:
        1. Creates initial snapshot
        2. Enters conversation loop with AI
        3. Executes one tool per turn
        4. Checks for human checkpoints after each action
        5. Terminates on complete_task or max_turns
        """
        ...

    def _build_system_prompt(self) -> str:
        """Build system prompt with service-specific additions."""
        ...

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call via tool server."""
        ...

    async def _check_checkpoint(self, snapshot: Snapshot) -> bool:
        """Check if current state triggers a human checkpoint."""
        ...

    async def _verify_completion(self, status: str, snapshot: Snapshot) -> tuple[bool, str | None]:
        """Verify completion claim against service criteria."""
        ...
```

#### 9.4.2 AIClient Interface

```python
class AIClient:
    """Claude API client with tool support."""

    TOOL_SCHEMAS: list[dict]  # Class attribute with all 7 tool definitions

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> None: ...

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        system: str = "",
    ) -> AIResponse:
        """
        Send conversation to Claude and get response.

        Args:
            messages: Conversation history.
            tools: Tool schemas (defaults to TOOL_SCHEMAS).
            system: System prompt.

        Returns:
            AIResponse with content and tool_calls.
        """
        ...

    def _format_messages(self, messages: list[Message]) -> list[dict]:
        """Format messages for Anthropic API."""
        ...

    def _parse_response(self, response: anthropic.Message) -> AIResponse:
        """Parse Anthropic response into AIResponse."""
        ...

    def _truncate_history(self, messages: list[Message]) -> list[Message]:
        """Truncate history if exceeding token limit."""
        ...
```

#### 9.4.3 BrowserToolServer Interface

```python
class BrowserToolServer:
    """Implements browser control tools."""

    def __init__(self, browser: "PlaywrightBrowser") -> None:
        """
        Initialize tool server.

        Args:
            browser: PlaywrightBrowser instance for browser operations.
        """
        ...

    async def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: One of the 7 tool names.
            arguments: Tool arguments.

        Returns:
            ToolResult with success status and snapshot.
        """
        ...

    async def get_snapshot(self, viewport_only: bool = True) -> ToolResult:
        """Capture current page state."""
        ...

    async def browser_click(self, ref: str) -> ToolResult:
        """Click element by ref."""
        ...

    async def browser_fill(self, ref: str, value: str, clear_first: bool = True) -> ToolResult:
        """Fill input field by ref."""
        ...

    async def browser_select(self, ref: str, value: str) -> ToolResult:
        """Select dropdown option by ref."""
        ...

    async def browser_scroll(
        self,
        ref: str | None = None,
        direction: str | None = None,
        amount: int = 300,
    ) -> ToolResult:
        """Scroll page or element into view."""
        ...

    async def request_human_approval(self, action: str, reason: str) -> ToolResult:
        """Request human approval (returns immediately, actual approval handled by orchestrator)."""
        ...

    async def complete_task(self, status: str, reason: str) -> ToolResult:
        """Signal task completion (returns immediately, actual verification handled by orchestrator)."""
        ...
```

#### 9.4.4 ElementRegistry Interface

```python
class ElementRegistry:
    """Manages element references within a snapshot lifecycle."""

    @property
    def snapshot_id(self) -> str | None:
        """Current snapshot ID, or None if no snapshot registered."""
        ...

    def register_snapshot(self, elements: list[ElementInfo]) -> str:
        """
        Register elements from a new snapshot.

        Args:
            elements: List of elements to register.

        Returns:
            New snapshot ID.

        All previous refs are invalidated.
        """
        ...

    def resolve(self, ref: str) -> ElementInfo:
        """
        Resolve ref to element.

        Args:
            ref: Element reference (e.g., "@e7").

        Returns:
            ElementInfo for the element.

        Raises:
            RefInvalidError: If ref not found in current snapshot.
        """
        ...

    def invalidate(self) -> None:
        """Invalidate all current refs."""
        ...

    def list_refs(self) -> list[str]:
        """List all valid refs in current snapshot."""
        ...
```

#### 9.4.5 SnapshotFactory Interface

```python
class SnapshotFactory:
    """Creates snapshots from page state."""

    def __init__(self, browser: "PlaywrightBrowser") -> None: ...

    async def create(self, viewport_only: bool = True) -> tuple[Snapshot, list[ElementInfo]]:
        """
        Create snapshot with accessibility tree and screenshot.

        Args:
            viewport_only: If True, only include elements in viewport.

        Returns:
            Tuple of (Snapshot for AI, list of ElementInfo for registry).

        The Snapshot contains serializable data for AI.
        The ElementInfo list contains full data including selectors for action execution.
        """
        ...

    def _extract_elements(
        self,
        raw_tree: dict,
        viewport_only: bool,
        viewport: ViewportInfo,
    ) -> list[ElementInfo]:
        """Extract and filter elements from raw accessibility tree."""
        ...

    def _prune_elements(self, elements: list[ElementInfo]) -> list[ElementInfo]:
        """Apply pruning rules to limit element count."""
        ...

    def _should_include(self, node: dict) -> bool:
        """Check if node matches inclusion rules."""
        ...
```

#### 9.4.6 ActionExecutor Interface

```python
class ActionExecutor:
    """Executes browser actions with error handling."""

    def __init__(
        self,
        browser: "PlaywrightBrowser",
        default_timeout: int = 2000,
    ) -> None: ...

    async def click(self, element: ElementInfo) -> None:
        """
        Click element.

        Args:
            element: Element to click.

        Raises:
            ElementDisabledError: If element is disabled.
            ElementObscuredError: If element is covered.
            TimeoutError: If click times out.
            MCPError: For other failures.
        """
        ...

    async def fill(self, element: ElementInfo, value: str, clear_first: bool = True) -> None:
        """
        Fill input element.

        Args:
            element: Input element to fill.
            value: Text to enter.
            clear_first: Whether to clear existing content.

        Raises:
            ElementDisabledError: If element is disabled.
            MCPError: For other failures.
        """
        ...

    async def select(self, element: ElementInfo, value: str) -> None:
        """
        Select dropdown option.

        Args:
            element: Dropdown element.
            value: Option value or text.

        Raises:
            ElementDisabledError: If element is disabled.
            MCPError: For other failures.
        """
        ...

    async def scroll_to_element(self, element: ElementInfo) -> None:
        """Scroll element into view."""
        ...

    async def scroll_page(self, direction: str, amount: int) -> None:
        """Scroll page in direction."""
        ...
```

#### 9.4.7 ServiceConfig Interface

```python
@dataclass
class ServiceConfig:
    """Service-specific configuration."""

    name: str
    checkpoint_conditions: list[Callable[[Snapshot], bool]]
    completion_criteria: CompletionCriteria
    system_prompt_addition: str = ""

    def check_checkpoint(self, snapshot: Snapshot) -> bool:
        """Check if any checkpoint condition is triggered."""
        return any(cond(snapshot) for cond in self.checkpoint_conditions)

    def verify_success(self, snapshot: Snapshot) -> bool:
        """Check if any success indicator is satisfied."""
        return any(ind(snapshot) for ind in self.completion_criteria.success_indicators)

    def check_failure(self, snapshot: Snapshot) -> bool:
        """Check if any failure indicator is triggered."""
        return any(ind(snapshot) for ind in self.completion_criteria.failure_indicators)


# Service registry
SERVICE_CONFIGS: dict[str, ServiceConfig] = {}

def register_service(config: ServiceConfig) -> None:
    """Register a service configuration."""
    SERVICE_CONFIGS[config.name] = config

def get_service(name: str) -> ServiceConfig:
    """Get service configuration by name."""
    if name not in SERVICE_CONFIGS:
        raise ValueError(f"Unknown service: {name}")
    return SERVICE_CONFIGS[name]
```

### 9.5 Tool Schema Definitions

```python
# tool_schemas.py

TOOL_SCHEMAS = [
    {
        "name": "get_snapshot",
        "description": """Capture the current page state including accessibility tree and screenshot.

WHEN TO USE:
- At the start to see the initial page state
- After navigation if you need to see the new page
- If you're unsure about the current state

IMPORTANT: Most actions return a fresh snapshot automatically. You rarely need to call this explicitly.
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "viewport_only": {
                    "type": "boolean",
                    "default": True,
                    "description": "If true, only include elements visible in viewport"
                }
            }
        }
    },
    {
        "name": "browser_click",
        "description": """Click an element by its ref from the most recent snapshot.

IMPORTANT: Element refs (@e0, @e1, etc.) are only valid for ONE action. After clicking, you'll receive a fresh snapshot with new refs.

WHEN TO USE:
- To click buttons, links, checkboxes, or other interactive elements
- The element must have state "enabled" and "visible"

COMMON PATTERNS:
- Expand accordion: click button/region with "collapsed" in state
- Submit form: click button with name containing "Submit", "Continue", "Confirm"
- Check checkbox: click checkbox element (state will show "checked" in new snapshot)

ERROR CONDITIONS:
- ref_invalid: the ref doesn't exist in current snapshot
- element_disabled: element has "disabled" in state
- element_obscured: another element is covering the target
- click_failed: browser couldn't click (element may have moved)
""",
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
    },
    {
        "name": "browser_fill",
        "description": """Fill a text input field with the specified value.

IMPORTANT: Element refs are only valid for ONE action. After filling, you'll receive a fresh snapshot with new refs.

WHEN TO USE:
- To enter text in input fields, textareas, or contenteditable elements
- The element must have role 'textbox' and state "enabled"

ERROR CONDITIONS:
- ref_invalid: the ref doesn't exist in current snapshot
- element_disabled: element has "disabled" in state
""",
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
                    "default": True,
                    "description": "If true, clear existing content before filling"
                }
            },
            "required": ["ref", "value"]
        }
    },
    {
        "name": "browser_select",
        "description": """Select an option from a dropdown/combobox.

IMPORTANT: Element refs are only valid for ONE action. After selecting, you'll receive a fresh snapshot with new refs.

WHEN TO USE:
- To select from dropdown menus, select elements, or comboboxes
- The element must have role 'combobox' or 'listbox' and state "enabled"
""",
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
    },
    {
        "name": "browser_scroll",
        "description": """Scroll the page or bring an element into view.

WHEN TO USE:
- To see elements that are off-screen
- When you need to click an element marked as "offscreen" in state

PARAMETER RULES:
- If ref is provided: scrolls that element into view (direction/amount ignored)
- If ref is NOT provided: direction is required, scrolls the page

ERROR CONDITIONS:
- invalid_params: neither ref nor direction provided
- ref_invalid: the ref doesn't exist in current snapshot
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "pattern": "^@e\\d+$",
                    "description": "Element to scroll into view"
                },
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "top", "bottom"],
                    "description": "Scroll direction (required if ref not provided)"
                },
                "amount": {
                    "type": "integer",
                    "default": 300,
                    "description": "Pixels to scroll if using direction"
                }
            }
        }
    },
    {
        "name": "request_human_approval",
        "description": """Request human approval before proceeding with a sensitive action.

WHEN TO USE:
- Before irreversible actions like final confirmation
- When you're uncertain about proceeding
- Note: The server automatically triggers this at certain checkpoints

The system will pause until the human responds with approval or rejection.
""",
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
    },
    {
        "name": "complete_task",
        "description": """Signal that the task is complete.

WHEN TO USE:
- When the goal has been achieved (status="success")
- When you determine the goal cannot be achieved (status="failed")

You MUST call this when done. Do not simply stop responding.
""",
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
]
```

### 9.6 JSON Schema for Snapshot Validation

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["snapshot_id", "timestamp", "elements", "page", "screenshot", "viewport"],
  "properties": {
    "snapshot_id": {
      "type": "string",
      "description": "UUID for this snapshot"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    },
    "elements": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["ref", "role", "name", "state"],
        "properties": {
          "ref": {
            "type": "string",
            "pattern": "^@e\\d+$"
          },
          "role": {
            "type": "string"
          },
          "name": {
            "type": "string",
            "maxLength": 203
          },
          "state": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["visible", "hidden", "offscreen", "enabled", "disabled", "readonly", "checked", "unchecked", "mixed", "expanded", "collapsed", "focused", "busy"]
            }
          },
          "bbox": {
            "type": ["object", "null"],
            "properties": {
              "x": {"type": "integer"},
              "y": {"type": "integer"},
              "width": {"type": "integer"},
              "height": {"type": "integer"}
            },
            "required": ["x", "y", "width", "height"]
          },
          "value": {
            "type": ["string", "null"]
          },
          "level": {
            "type": ["integer", "null"],
            "minimum": 1,
            "maximum": 6
          },
          "children": {
            "type": ["array", "null"],
            "items": {
              "type": "string",
              "pattern": "^@e\\d+$"
            }
          }
        }
      },
      "maxItems": 100
    },
    "focused": {
      "type": ["string", "null"],
      "pattern": "^@e\\d+$"
    },
    "page": {
      "type": "object",
      "required": ["url", "title"],
      "properties": {
        "url": {"type": "string", "format": "uri"},
        "title": {"type": "string"}
      }
    },
    "screenshot": {
      "type": "string",
      "description": "Base64-encoded PNG"
    },
    "viewport": {
      "type": "object",
      "required": ["width", "height", "scroll_x", "scroll_y"],
      "properties": {
        "width": {"type": "integer", "minimum": 1},
        "height": {"type": "integer", "minimum": 1},
        "scroll_x": {"type": "integer", "minimum": 0},
        "scroll_y": {"type": "integer", "minimum": 0}
      }
    }
  }
}
```
