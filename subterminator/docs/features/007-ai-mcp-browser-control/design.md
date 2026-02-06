# Design: AI Browser Orchestration via Existing MCP Tools

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Terminal                               │
│                                                                          │
│  $ subterminator cancel netflix                                          │
│  $ ANTHROPIC_API_KEY=xxx subterminator cancel netflix --model gpt-4o     │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         subterminator CLI                                │
│                    (src/subterminator/cli/main.py)                       │
│                                                                          │
│  - Parse arguments (service, model, max-turns, dry-run, verbose)         │
│  - Load environment variables (API keys)                                 │
│  - Initialize orchestrator                                               │
│  - Display progress and results                                          │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Orchestration Layer                                │
│                (src/subterminator/mcp_orchestrator/)                     │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  MCPClient      │  │  LLMClient      │  │  ServiceRegistry        │  │
│  │                 │  │                 │  │                         │  │
│  │  - connect()    │  │  - invoke()     │  │  - get_config(name)     │  │
│  │  - list_tools() │  │  - with_tools() │  │  - NETFLIX_CONFIG       │  │
│  │  - call_tool()  │  │  - timeout      │  │  - checkpoint_conditions│  │
│  │  - close()      │  │  - retries      │  │  - success_indicators   │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘  │
│           │                    │                        │               │
│           └────────────────────┼────────────────────────┘               │
│                                ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      TaskRunner                                   │  │
│  │                                                                   │  │
│  │  - run(goal, service, max_turns) -> TaskResult                    │  │
│  │  - Single-tool-per-turn orchestration loop                        │  │
│  │  - Checkpoint evaluation and human approval                       │  │
│  │  - Completion verification                                        │  │
│  │  - Error recovery (MCPToolError -> continue)                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   CheckpointHandler                               │  │
│  │                                                                   │  │
│  │  - should_checkpoint(tool_call, snapshot, config) -> bool         │  │
│  │  - request_approval(tool_call, snapshot) -> bool                  │  │
│  │  - Display: action, URL, screenshot path                          │  │
│  │  - Prompt: "Approve? [y/N]"                                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
┌───────────────────────────────┐  ┌───────────────────────────────────────┐
│   Playwright MCP Server       │  │        LLM Provider APIs              │
│   (External - via npx)        │  │        (External)                     │
│                               │  │                                       │
│   npx @playwright/mcp@latest  │  │   - Anthropic (Claude)                │
│   --user-data-dir ~/.sub...   │  │   - OpenAI (GPT-4)                    │
│                               │  │                                       │
│   Tools:                      │  │   Tool format conversion:             │
│   - browser_snapshot          │  │   - MCP schema -> Anthropic tools     │
│   - browser_click             │  │   - MCP schema -> OpenAI functions    │
│   - browser_navigate          │  │                                       │
│   - browser_type              │  │                                       │
│   - browser_select_option     │  │                                       │
│   - ... (15+ tools)           │  │                                       │
└───────────────────────────────┘  └───────────────────────────────────────┘
```

### 1.2 Package Structure

```
src/subterminator/
├── cli/
│   └── main.py              # CLI entry point (existing, extend)
├── mcp_orchestrator/        # NEW PACKAGE
│   ├── __init__.py
│   ├── types.py             # Data types: TaskResult, ToolCall, NormalizedSnapshot
│   ├── exceptions.py        # Error classes
│   ├── mcp_client.py        # MCPClient wrapper
│   ├── llm_client.py        # LLMClient with provider abstraction
│   ├── task_runner.py       # TaskRunner orchestration loop
│   ├── checkpoint.py        # CheckpointHandler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py          # ServiceConfig dataclass
│   │   ├── registry.py      # ServiceRegistry
│   │   └── netflix.py       # Netflix-specific config
│   └── snapshot.py          # normalize_snapshot() function
└── core/                    # Existing (keep for fallback)
    ├── agent.py             # Deprecated but kept
    ├── browser.py           # Keep - potential fallback
    └── ...
```

### 1.3 Component Responsibilities

| Component | Responsibility | Dependencies |
|-----------|----------------|--------------|
| **CLI** | Parse args, display progress, exit codes | TaskRunner |
| **MCPClient** | Manage Playwright MCP subprocess, tool execution | mcp SDK, subprocess |
| **LLMClient** | Provider abstraction, tool format conversion, retries | langchain-anthropic, langchain-openai |
| **TaskRunner** | Orchestration loop, message history, termination | MCPClient, LLMClient, ServiceRegistry, CheckpointHandler |
| **CheckpointHandler** | Evaluate conditions, display prompt, get user input | stdin/stdout |
| **ServiceRegistry** | Load service configs by name | ServiceConfig |
| **ServiceConfig** | Define service-specific predicates | NormalizedSnapshot |

---

## 2. Technical Decisions

### 2.1 MCP Client Implementation

**Decision**: Use official MCP Python SDK directly (not mcp-use)

**Rationale**:
- mcp-use is a convenience wrapper that may hide errors
- Official SDK provides full control over connection lifecycle
- Better for debugging during POC phase
- Can switch to mcp-use later if it proves stable

**Implementation**:
```python
# mcp_client.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    async def connect(self):
        self._server_params = StdioServerParameters(
            command="npx",
            args=["@playwright/mcp@latest", "--user-data-dir", self._profile_dir]
        )
        # stdio_client returns (read_stream, write_stream)
        # ClientSession wraps these for JSON-RPC communication
```

### 2.2 LLM Provider Abstraction

**Decision**: Use LangChain's BaseChatModel abstraction

**Rationale**:
- Unified interface for Claude and OpenAI
- Built-in tool/function calling support
- Handles provider-specific message formats
- Well-tested, production-ready

**Trade-off**: Adds ~10MB dependency. Acceptable for convenience gained.

### 2.3 Virtual Tool Injection

**Decision**: Virtual tools (`complete_task`, `request_human_approval`) are injected into tool list at runtime

**Rationale**:
- LLM sees consistent tool interface
- Virtual tools handled by TaskRunner, not forwarded to MCP
- Clean separation: MCP tools execute browser actions, virtual tools control flow

**Implementation**:
```python
# task_runner.py
VIRTUAL_TOOLS = {
    "complete_task": COMPLETE_TASK_SCHEMA,
    "request_human_approval": REQUEST_APPROVAL_SCHEMA,
}

def get_all_tools(mcp_tools: list) -> list:
    return mcp_tools + list(VIRTUAL_TOOLS.values())

def is_virtual_tool(name: str) -> bool:
    return name in VIRTUAL_TOOLS
```

### 2.4 Snapshot Normalization

**Decision**: Normalize Playwright MCP snapshot to `NormalizedSnapshot` dataclass

**Rationale**:
- Checkpoint predicates need stable interface
- MCP output format may vary between versions
- Normalization function adapts to actual format discovered in POC

**Implementation Strategy**:
1. POC phase: Log raw MCP output, identify fields
2. Implement `normalize_snapshot()` based on actual format
3. Unit tests use sample MCP output as fixtures

### 2.5 Screenshot Handling

**Decision**: Use `browser_take_screenshot` tool separately from `browser_snapshot`

**Context**: Playwright MCP provides two distinct tools:
- `browser_snapshot`: Returns accessibility tree (text content for LLM reasoning)
- `browser_take_screenshot`: Returns screenshot as base64 or saves to file

**Implementation**:
```python
# checkpoint.py
async def _capture_screenshot_for_checkpoint(self, mcp_client: MCPClient) -> str | None:
    """Capture screenshot before checkpoint approval"""
    try:
        result = await mcp_client.call_tool("browser_take_screenshot", {})
        # Playwright MCP returns base64 data - save to temp file
        if isinstance(result, dict) and "data" in result:
            import base64
            import tempfile
            data = base64.b64decode(result["data"])
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".png", prefix="subterminator_checkpoint_"
            ) as f:
                f.write(data)
                return f.name
        return None
    except MCPToolError:
        return None  # Screenshot is optional - don't fail checkpoint
```

**Rationale**:
- Screenshots are only needed at checkpoints (human approval)
- Normal orchestration uses text accessibility tree for LLM
- Screenshot is optional - checkpoint can proceed without it

### 2.6 SIGINT Handling (Graceful Shutdown)

**Decision**: Handle Ctrl+C gracefully by cleaning up MCP subprocess

**Implementation**:
```python
# task_runner.py
import signal

class TaskRunner:
    async def run(self, service: str, max_turns: int = 20) -> TaskResult:
        # Register SIGINT handler
        original_handler = signal.getsignal(signal.SIGINT)
        shutdown_requested = False

        def sigint_handler(signum, frame):
            nonlocal shutdown_requested
            shutdown_requested = True
            print("\n⚠️ Interrupt received, cleaning up...")

        signal.signal(signal.SIGINT, sigint_handler)

        try:
            # ... orchestration loop ...
            for turn in range(max_turns):
                if shutdown_requested:
                    return TaskResult(
                        success=False,
                        verified=False,
                        reason="human_rejected",  # User interrupted
                        turns=turn
                    )
                # ... rest of loop ...
        finally:
            signal.signal(signal.SIGINT, original_handler)
            await self._mcp.close()  # Always cleanup
```

### 2.7 Dry-Run Mode

**Decision**: Dry-run stops after first LLM action is identified (before execution)

**Implementation**:
```python
# task_runner.py
async def run(self, service: str, max_turns: int = 20, dry_run: bool = False) -> TaskResult:
    # ... setup ...

    for turn in range(max_turns):
        response = await self._llm.invoke(messages, all_tools)

        if response.tool_calls:
            tc = ToolCall(...)

            if dry_run:
                # Return immediately with the first proposed action
                return TaskResult(
                    success=True,
                    verified=False,
                    reason="completed",
                    turns=turn + 1,
                    final_url=snapshot.url,
                    error=f"DRY-RUN: Would execute {tc.name}({tc.args})"
                )

            # ... normal execution ...
```

### 2.8 Error Recovery Strategy

**Decision**: MCPToolError is returned to LLM as error result, loop continues

**Rationale**:
- Transient failures (element not found) should allow retry
- LLM can decide to try different approach or give up
- Fatal errors (connection lost) terminate immediately

**Implementation**:
```python
# task_runner.py
try:
    result = await self._mcp_client.call_tool(tool_call.name, tool_call.args)
except MCPToolError as e:
    result = {"error": True, "message": str(e)}
# Continue loop - append error result to history
```

---

## 3. Component Design

### 3.1 MCPClient

```
┌─────────────────────────────────────────────────────────────┐
│                         MCPClient                            │
├─────────────────────────────────────────────────────────────┤
│ Attributes:                                                  │
│   - _profile_dir: str                                       │
│   - _session: ClientSession | None                          │
│   - _process: subprocess.Popen | None                       │
│   - _tools: list[dict] | None (cached)                      │
├─────────────────────────────────────────────────────────────┤
│ Methods:                                                     │
│   + async connect() -> None                                  │
│   + async list_tools() -> list[dict]                        │
│   + async call_tool(name: str, args: dict) -> dict          │
│   + async close() -> None                                   │
│   + async __aenter__() -> MCPClient                         │
│   + async __aexit__(...) -> None                            │
└─────────────────────────────────────────────────────────────┘
```

**State Machine**:
```
DISCONNECTED --connect()--> CONNECTED --close()--> DISCONNECTED
                               │
                               ├── list_tools()
                               ├── call_tool()
                               └── (on error) --> DISCONNECTED
```

### 3.2 LLMClient

```
┌─────────────────────────────────────────────────────────────┐
│                         LLMClient                            │
├─────────────────────────────────────────────────────────────┤
│ Attributes:                                                  │
│   - _model: BaseChatModel                                   │
│   - _model_name: str                                        │
│   - _timeout: int = 60                                      │
│   - _max_retries: int = 3                                   │
├─────────────────────────────────────────────────────────────┤
│ Methods:                                                     │
│   + __init__(model_name: str | None = None)                 │
│   + async invoke(messages: list, tools: list) -> Response   │
│   + _convert_tools_for_provider(tools: list) -> list        │
│   + _get_provider() -> str  # "anthropic" | "openai"        │
│   + _resolve_model_name(model_name: str | None) -> str      │
└─────────────────────────────────────────────────────────────┘
```

**Model Resolution (Priority Order)**:
1. Explicit `model_name` parameter (from CLI `--model`)
2. `SUBTERMINATOR_MODEL` environment variable
3. Default: `"claude-opus-4-6"`

**Provider Detection**:
- Model name starts with "claude" → Anthropic
- Model name starts with "gpt-" → OpenAI
- Otherwise → ConfigurationError

### 3.3 TaskRunner

```
┌─────────────────────────────────────────────────────────────┐
│                        TaskRunner                            │
├─────────────────────────────────────────────────────────────┤
│ Attributes:                                                  │
│   - _mcp_client: MCPClient                                  │
│   - _llm_client: LLMClient                                  │
│   - _checkpoint_handler: CheckpointHandler                   │
│   - _service_registry: ServiceRegistry                       │
├─────────────────────────────────────────────────────────────┤
│ Methods:                                                     │
│   + async run(service: str, max_turns: int) -> TaskResult   │
│   - async _execute_turn(messages, tools, config) -> ...     │
│   - async _handle_tool_call(tool_call, snapshot, config)    │
│   - _build_system_prompt(config: ServiceConfig) -> str      │
│   - _verify_completion(snapshot, config) -> bool            │
└─────────────────────────────────────────────────────────────┘
```

**Orchestration Loop Sequence**:
```
1. Load ServiceConfig by name
2. Connect to MCP, get tools
3. Get initial snapshot via browser_snapshot
4. Build initial messages (system + user with goal)
5. LOOP (max_turns):
   a. Invoke LLM with messages + tools
   b. If no tool_calls: prompt for action, increment no_action_count
      - If no_action_count >= 3: return llm_no_action
   c. Extract first tool_call
   d. If virtual tool:
      - complete_task: verify and return result
      - request_human_approval: prompt user
   e. If checkpoint condition matches: request approval
      - If rejected: return human_rejected
   f. Execute tool via MCP
   g. Append messages (assistant + tool result)
   h. Continue loop
6. Return max_turns_exceeded
```

### 3.4 CheckpointHandler

```
┌─────────────────────────────────────────────────────────────┐
│                    CheckpointHandler                         │
├─────────────────────────────────────────────────────────────┤
│ Attributes:                                                  │
│   - _mcp: MCPClient  # For screenshot capture               │
│   - _disabled: bool = False  # For testing                  │
├─────────────────────────────────────────────────────────────┤
│ Methods:                                                     │
│   + should_checkpoint(tool_call, snapshot, config) -> bool  │
│   + async request_approval(tool_call, snapshot) -> bool     │
│   - async _capture_screenshot() -> str | None               │
│   - _display_checkpoint_info(tool_call, snapshot, path)     │
│   - _get_user_input() -> bool                               │
└─────────────────────────────────────────────────────────────┘
```

**Checkpoint Display Format**:
```
⚠️ Human approval required

Action: browser_click
Target: "Finish Cancellation"
URL: https://www.netflix.com/cancelplan/confirm
Screenshot: /tmp/subterminator_checkpoint_abc123.png

Approve? [y/N]:
```

### 3.5 ServiceConfig and Registry

```
┌─────────────────────────────────────────────────────────────┐
│                      ServiceConfig                           │
├─────────────────────────────────────────────────────────────┤
│ Fields (dataclass):                                          │
│   - name: str                                               │
│   - initial_url: str                                        │
│   - goal_template: str                                      │
│   - checkpoint_conditions: list[Callable]                   │
│   - success_indicators: list[Callable]                      │
│   - failure_indicators: list[Callable]                      │
│   - system_prompt_addition: str = ""                        │
│   - auth_edge_case_detectors: list[Callable] = []          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ServiceRegistry                           │
├─────────────────────────────────────────────────────────────┤
│ Class Attributes:                                            │
│   - _configs: dict[str, ServiceConfig]                      │
├─────────────────────────────────────────────────────────────┤
│ Methods:                                                     │
│   + get(name: str) -> ServiceConfig                         │
│   + list_services() -> list[str]                            │
│   + register(config: ServiceConfig) -> None                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Interfaces

### 4.1 Data Types (types.py)

```python
from dataclasses import dataclass
from typing import Literal

TaskReason = Literal[
    "completed",
    "human_rejected",
    "max_turns_exceeded",
    "llm_no_action",
    "llm_error",
    "mcp_error",
    "verification_failed",
]

@dataclass
class TaskResult:
    success: bool
    verified: bool
    reason: TaskReason
    turns: int
    final_url: str | None = None
    error: str | None = None

@dataclass
class ToolCall:
    """Normalized tool call (matches LangChain's format)"""
    id: str
    name: str
    args: dict  # LangChain uses 'args', not 'arguments'

@dataclass
class NormalizedSnapshot:
    url: str
    title: str
    content: str
    screenshot_path: str | None = None
```

### 4.2 Exceptions (exceptions.py)

```python
class OrchestratorError(Exception):
    """Base for all orchestrator errors"""
    pass

class ConfigurationError(OrchestratorError):
    """Missing API key, invalid model, unknown service"""
    pass

class MCPConnectionError(OrchestratorError):
    """Cannot connect to MCP server"""
    pass

class MCPToolError(OrchestratorError):
    """MCP tool execution failed"""
    pass

class LLMError(OrchestratorError):
    """LLM API call failed after retries"""
    pass

class CheckpointRejectedError(OrchestratorError):
    """Human rejected checkpoint"""
    pass

class SnapshotValidationError(OrchestratorError):
    """MCP snapshot missing required fields"""
    pass

class ServiceNotFoundError(OrchestratorError):
    """Unknown service name"""
    pass
```

### 4.3 MCPClient Interface (mcp_client.py)

```python
from typing import Protocol

class MCPClientProtocol(Protocol):
    """Protocol for MCP client implementations"""

    async def connect(self) -> None:
        """Connect to MCP server. Raises MCPConnectionError on failure."""
        ...

    async def list_tools(self) -> list[dict]:
        """Get available tools. Must be connected."""
        ...

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute tool. Raises MCPToolError on failure."""
        ...

    async def close(self) -> None:
        """Close connection and cleanup subprocess."""
        ...

class MCPClient:
    """Concrete implementation using official MCP SDK"""

    def __init__(self, profile_dir: str = "~/.subterminator/browser-profile/"):
        self._profile_dir = os.path.expanduser(profile_dir)
        self._session: ClientSession | None = None
        self._tools: list[dict] | None = None

    async def connect(self) -> None:
        # Validate Node.js version first
        self._validate_nodejs()

        server_params = StdioServerParameters(
            command="npx",
            args=["@playwright/mcp@latest", "--user-data-dir", self._profile_dir]
        )

        try:
            self._read, self._write = await stdio_client(server_params).__aenter__()
            self._session = await ClientSession(self._read, self._write).__aenter__()
            await self._session.initialize()
        except Exception as e:
            raise MCPConnectionError(
                f"Failed to connect to Playwright MCP. Ensure Node.js >= 18 is installed. "
                f"Error: {e}"
            )

    async def list_tools(self) -> list[dict]:
        if not self._session:
            raise MCPConnectionError("Not connected")
        if self._tools is None:
            result = await self._session.list_tools()
            self._tools = [tool.model_dump() for tool in result.tools]
        return self._tools

    async def call_tool(self, name: str, arguments: dict) -> dict:
        if not self._session:
            raise MCPConnectionError("Not connected")
        try:
            result = await self._session.call_tool(name, arguments)
            return result.content[0].text if result.content else {}
        except Exception as e:
            raise MCPToolError(f"Tool '{name}' failed: {e}")

    async def close(self) -> None:
        """Close connection and cleanup subprocess."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass  # Best effort cleanup
            self._session = None
        # Ensure subprocess is terminated
        if hasattr(self, '_process') and self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()  # Force kill if terminate fails

    async def reconnect(self) -> None:
        """Reconnect after connection loss (single retry)."""
        await self.close()
        self._tools = None  # Clear cached tools
        await self.connect()

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _validate_nodejs(self) -> None:
        import subprocess
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip()
            major = int(version.lstrip('v').split('.')[0])
            if major < 18:
                raise ConfigurationError(
                    f"Node.js >= 18 required, found {version}. "
                    f"Install from https://nodejs.org/"
                )
        except FileNotFoundError:
            raise ConfigurationError(
                "Node.js not found. Install from https://nodejs.org/"
            )
```

### 4.4 LLMClient Interface (llm_client.py)

```python
import asyncio
import os
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

DEFAULT_MODEL = "claude-opus-4-6"

class LLMClient:
    """Provider-agnostic LLM client"""

    def __init__(self, model_name: str | None = None, timeout: int = 60, max_retries: int = 3):
        self._model_name = self._resolve_model_name(model_name)
        self._timeout = timeout
        self._max_retries = max_retries
        self._model = self._create_model()

    def _resolve_model_name(self, model_name: str | None) -> str:
        """Resolve model name from parameter, env var, or default"""
        if model_name:
            return model_name
        env_model = os.environ.get("SUBTERMINATOR_MODEL")
        if env_model:
            return env_model
        return DEFAULT_MODEL

    def _create_model(self) -> BaseChatModel:
        if self._model_name.startswith("claude"):
            from langchain_anthropic import ChatAnthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ConfigurationError(
                    "Missing ANTHROPIC_API_KEY. Set it via environment variable "
                    "or use --model gpt-4o with OPENAI_API_KEY."
                )
            return ChatAnthropic(model=self._model_name, api_key=api_key)

        elif self._model_name.startswith("gpt"):
            from langchain_openai import ChatOpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ConfigurationError(
                    "Missing OPENAI_API_KEY. Set it via environment variable "
                    "or use a Claude model with ANTHROPIC_API_KEY."
                )
            return ChatOpenAI(model=self._model_name, api_key=api_key)

        else:
            raise ConfigurationError(f"Unsupported model: {self._model_name}")

    async def invoke(
        self,
        messages: list[dict],
        tools: list[dict]
    ) -> AIMessage:
        """Invoke LLM with messages and tools. Returns AIMessage with tool_calls."""

        # Convert dict messages to LangChain message objects
        lc_messages = self._convert_messages(messages)

        # Bind tools to model
        model_with_tools = self._model.bind_tools(tools)

        # Invoke with timeout and retries
        for attempt in range(self._max_retries):
            try:
                return await asyncio.wait_for(
                    model_with_tools.ainvoke(lc_messages),
                    timeout=self._timeout
                )
            except asyncio.TimeoutError:
                if attempt == self._max_retries - 1:
                    raise LLMError(
                        f"LLM API call timed out after {self._timeout}s "
                        f"({self._max_retries} attempts)"
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == self._max_retries - 1:
                    raise LLMError(f"LLM API call failed: {e}")
                await asyncio.sleep(2 ** attempt)

    def _convert_messages(self, messages: list[dict]) -> list:
        """Convert dict messages to LangChain message objects"""
        result = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                result.append(SystemMessage(content=msg["content"]))
            elif role == "user":
                result.append(HumanMessage(content=msg["content"]))
            elif role == "assistant":
                result.append(AIMessage(
                    content=msg.get("content", ""),
                    tool_calls=msg.get("tool_calls", [])
                ))
            elif role == "tool":
                result.append(ToolMessage(
                    content=msg["content"],
                    tool_call_id=msg["tool_call_id"]
                ))
        return result
```

### 4.5 TaskRunner Interface (task_runner.py)

```python
class TaskRunner:
    """Main orchestration loop"""

    VIRTUAL_TOOLS = {
        "complete_task": {
            "name": "complete_task",
            "description": "Signal that the task is complete.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "failed"]},
                    "reason": {"type": "string"}
                },
                "required": ["status", "reason"]
            }
        },
        "request_human_approval": {
            "name": "request_human_approval",
            "description": "Pause and request human approval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "reason": {"type": "string"}
                },
                "required": ["action", "reason"]
            }
        }
    }

    def __init__(
        self,
        mcp_client: MCPClient,
        llm_client: LLMClient,
        service_registry: ServiceRegistry,
        disable_checkpoints: bool = False  # For testing
    ):
        self._mcp = mcp_client
        self._llm = llm_client
        self._services = service_registry
        # CheckpointHandler needs MCPClient for screenshots
        self._checkpoint = CheckpointHandler(mcp_client, disabled=disable_checkpoints)

    async def run(self, service: str, max_turns: int = 20) -> TaskResult:
        """Run orchestration loop for the given service."""

        # Load service config
        config = self._services.get(service)

        # Get tools (MCP + virtual)
        mcp_tools = await self._mcp.list_tools()
        all_tools = mcp_tools + list(self.VIRTUAL_TOOLS.values())

        # Navigate to initial URL and get snapshot
        await self._mcp.call_tool("browser_navigate", {"url": config.initial_url})
        snapshot_raw = await self._mcp.call_tool("browser_snapshot", {})
        snapshot = normalize_snapshot(snapshot_raw)

        # Build initial messages
        messages = [
            {"role": "system", "content": self._build_system_prompt(config)},
            {"role": "user", "content": f"Goal: {config.goal_template}\n\nCurrent page:\n{snapshot.content}"}
        ]

        no_action_count = 0

        for turn in range(max_turns):
            # Invoke LLM
            response = await self._llm.invoke(messages, all_tools)

            # Check for no tool calls
            if not response.tool_calls:
                no_action_count += 1
                if no_action_count >= 3:
                    return TaskResult(
                        success=False,
                        verified=False,
                        reason="llm_no_action",
                        turns=turn + 1
                    )
                messages.append({"role": "user", "content": "Call a tool or complete_task."})
                continue

            no_action_count = 0
            tool_call = response.tool_calls[0]

            # Log if multiple tool calls (debug only)
            if len(response.tool_calls) > 1:
                logger.debug(f"Ignoring {len(response.tool_calls) - 1} additional tool calls")

            # Convert LangChain tool_call dict to ToolCall dataclass
            # Note: LangChain uses 'args', not 'arguments'
            tc = ToolCall(id=tool_call["id"], name=tool_call["name"], args=tool_call["args"])

            # Handle virtual tools
            if tc.name == "complete_task":
                complete_result = await self._handle_complete_task(tc, snapshot, config, turn + 1)
                if isinstance(complete_result, TaskResult):
                    return complete_result
                # Verification failed - return error to LLM and continue loop
                result = complete_result  # dict with error message

            if tc.name == "request_human_approval":
                approved = await self._checkpoint.request_approval(tc, snapshot)
                if not approved:
                    return TaskResult(
                        success=False,
                        verified=False,
                        reason="human_rejected",
                        turns=turn + 1
                    )
                result = {"approved": True}
            else:
                # Check server-enforced checkpoint
                if self._checkpoint.should_checkpoint(tc, snapshot, config):
                    approved = await self._checkpoint.request_approval(tc, snapshot)
                    if not approved:
                        return TaskResult(
                            success=False,
                            verified=False,
                            reason="human_rejected",
                            turns=turn + 1
                        )

                # Execute MCP tool
                try:
                    result = await self._mcp.call_tool(tc.name, tc.args)
                except MCPToolError as e:
                    result = {"error": True, "message": str(e)}

                # Update snapshot after tool execution
                snapshot_raw = await self._mcp.call_tool("browser_snapshot", {})
                snapshot = normalize_snapshot(snapshot_raw)

            # Append to message history
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": tc.id, "name": tc.name, "args": tc.args}]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result) if isinstance(result, dict) else str(result)
            })

        return TaskResult(
            success=False,
            verified=False,
            reason="max_turns_exceeded",
            turns=max_turns,
            final_url=snapshot.url
        )

    async def _handle_complete_task(
        self,
        tool_call: ToolCall,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig,
        turns: int
    ) -> TaskResult | dict:
        """
        Handle complete_task virtual tool.

        Returns:
            TaskResult: If task is truly complete (success or LLM-declared failure)
            dict: Error result to return to LLM if verification fails (allows retry)
        """
        status = tool_call.args["status"]
        reason = tool_call.args["reason"]

        if status == "failed":
            # LLM declares failure - trust it
            return TaskResult(
                success=False,
                verified=True,  # LLM verified it cannot succeed
                reason="completed",
                turns=turns,
                final_url=snapshot.url,
                error=reason
            )

        # Verify success via service-specific indicators
        verified = self._verify_completion(snapshot, config)
        if not verified:
            # Return error to LLM as tool result (NOT terminate)
            # This allows LLM to retry or take corrective action
            return {
                "error": True,
                "message": (
                    f"Verification failed: Success indicators not found on page. "
                    f"URL: {snapshot.url}. "
                    f"Either continue the task or call complete_task with status='failed'."
                )
            }

        # Verification passed
        return TaskResult(
            success=True,
            verified=True,
            reason="completed",
            turns=turns,
            final_url=snapshot.url
        )

    def _verify_completion(self, snapshot: NormalizedSnapshot, config: ServiceConfig) -> bool:
        """Check success/failure indicators"""
        # Check failure first
        for indicator in config.failure_indicators:
            if indicator(snapshot):
                return False

        # Check success
        for indicator in config.success_indicators:
            if indicator(snapshot):
                return True

        return False

    def _build_system_prompt(self, config: ServiceConfig) -> str:
        return f"""You are a browser automation agent. Your goal is to complete tasks by calling browser tools.

Available tools:
- browser_snapshot: Get current page state (accessibility tree)
- browser_click: Click an element by ref or text
- browser_navigate: Navigate to a URL
- browser_type: Type text into an element
- browser_select_option: Select from dropdown
- complete_task: Signal task completion (call when done or stuck)
- request_human_approval: Request human help

Rules:
1. Call ONE tool per turn
2. Use browser_snapshot to see current state
3. Call complete_task when the goal is achieved or impossible
4. Be concise in your reasoning

{config.system_prompt_addition}
"""
```

### 4.6 CheckpointHandler Interface (checkpoint.py)

```python
import base64
import tempfile

class CheckpointHandler:
    """Handle human checkpoint approval"""

    def __init__(self, mcp_client: MCPClient, disabled: bool = False):
        self._mcp = mcp_client
        self._disabled = disabled

    def should_checkpoint(
        self,
        tool_call: ToolCall,
        snapshot: NormalizedSnapshot,
        config: ServiceConfig
    ) -> bool:
        """Check if this tool call requires human approval"""
        if self._disabled:
            return False

        # Check service-specific conditions
        for condition in config.checkpoint_conditions:
            if condition(tool_call, snapshot):
                return True

        # Check auth edge cases
        for detector in config.auth_edge_case_detectors:
            if detector(snapshot):
                return True

        return False

    async def request_approval(
        self,
        tool_call: ToolCall,
        snapshot: NormalizedSnapshot
    ) -> bool:
        """Display checkpoint info and get user approval"""
        if self._disabled:
            return True

        # Capture screenshot for human review
        screenshot_path = await self._capture_screenshot()

        self._display_checkpoint_info(tool_call, snapshot, screenshot_path)
        return self._get_user_input()

    async def _capture_screenshot(self) -> str | None:
        """Capture screenshot using browser_take_screenshot tool"""
        try:
            result = await self._mcp.call_tool("browser_take_screenshot", {})
            # Playwright MCP returns base64-encoded screenshot
            if isinstance(result, dict) and "data" in result:
                data = base64.b64decode(result["data"])
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png", prefix="subterminator_checkpoint_"
                ) as f:
                    f.write(data)
                    return f.name
            elif isinstance(result, str):
                # May return path directly or base64 string
                if result.endswith(".png") or result.endswith(".jpg"):
                    return result
                # Try base64 decode
                try:
                    data = base64.b64decode(result)
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".png", prefix="subterminator_checkpoint_"
                    ) as f:
                        f.write(data)
                        return f.name
                except Exception:
                    pass
            return None
        except MCPToolError:
            return None  # Screenshot is optional - don't fail checkpoint

    def _display_checkpoint_info(
        self,
        tool_call: ToolCall,
        snapshot: NormalizedSnapshot,
        screenshot_path: str | None
    ) -> None:
        """Display checkpoint information to user"""
        print("\n⚠️ Human approval required\n")
        print(f"Action: {tool_call.name}")
        if tool_call.args:
            for key, value in tool_call.args.items():
                print(f"  {key}: {value}")
        print(f"\nURL: {snapshot.url}")
        if screenshot_path:
            print(f"Screenshot: {screenshot_path}")
        print()

    def _get_user_input(self) -> bool:
        """Get y/n input from user"""
        try:
            response = input("Approve? [y/N]: ").strip().lower()
            return response == 'y'
        except (EOFError, KeyboardInterrupt):
            return False
```

### 4.7 Snapshot Normalization (snapshot.py)

```python
def normalize_snapshot(mcp_output: dict | str) -> NormalizedSnapshot:
    """
    Normalize Playwright MCP snapshot output to NormalizedSnapshot.

    Note: Exact field mapping TBD in Phase 1 POC.
    This implementation assumes fields based on Playwright MCP documentation.
    """
    if isinstance(mcp_output, str):
        # Try to parse as JSON
        try:
            mcp_output = json.loads(mcp_output)
        except json.JSONDecodeError:
            # Treat as plain text content
            return NormalizedSnapshot(
                url="unknown",
                title="unknown",
                content=mcp_output
            )

    # Expected fields (to be validated in POC)
    url = mcp_output.get("url") or mcp_output.get("page", {}).get("url")
    title = mcp_output.get("title") or mcp_output.get("page", {}).get("title")
    content = mcp_output.get("content") or mcp_output.get("accessibility_tree") or str(mcp_output)
    screenshot = mcp_output.get("screenshot_path") or mcp_output.get("screenshot")

    if not url:
        raise SnapshotValidationError(
            f"MCP snapshot missing 'url' field. Available fields: {list(mcp_output.keys())}"
        )
    if not title:
        raise SnapshotValidationError(
            f"MCP snapshot missing 'title' field. Available fields: {list(mcp_output.keys())}"
        )
    if not content:
        raise SnapshotValidationError(
            f"MCP snapshot missing content field. Available fields: {list(mcp_output.keys())}"
        )

    return NormalizedSnapshot(
        url=url,
        title=title,
        content=content,
        screenshot_path=screenshot
    )
```

---

## 5. Data Flow

### 5.1 Happy Path: Netflix Cancellation

```
User                CLI              TaskRunner           MCPClient           LLM
  │                  │                   │                    │                │
  │ cancel netflix   │                   │                    │                │
  │─────────────────>│                   │                    │                │
  │                  │ run("netflix")    │                    │                │
  │                  │──────────────────>│                    │                │
  │                  │                   │ connect()          │                │
  │                  │                   │───────────────────>│                │
  │                  │                   │ list_tools()       │                │
  │                  │                   │───────────────────>│                │
  │                  │                   │ call_tool(navigate)│                │
  │                  │                   │───────────────────>│                │
  │                  │                   │ call_tool(snapshot)│                │
  │                  │                   │───────────────────>│                │
  │                  │                   │                    │                │
  │                  │                   │ invoke(messages)   │                │
  │                  │                   │───────────────────────────────────>│
  │                  │                   │ <─ tool_call: click "Cancel"        │
  │                  │                   │                    │                │
  │                  │                   │ call_tool(click)   │                │
  │                  │                   │───────────────────>│                │
  │                  │                   │                    │                │
  │ [Turn 2]         │                   │ ... (more turns)   │                │
  │                  │                   │                    │                │
  │                  │                   │ ── checkpoint! ──  │                │
  │ Approve? [y/N]   │                   │                    │                │
  │<─────────────────│                   │                    │                │
  │ y                │                   │                    │                │
  │─────────────────>│                   │                    │                │
  │                  │                   │ call_tool(click)   │                │
  │                  │                   │───────────────────>│                │
  │                  │                   │                    │                │
  │                  │                   │ <─ complete_task   │                │
  │                  │                   │                    │                │
  │                  │<── TaskResult ────│                    │                │
  │ ✓ Success        │                   │                    │                │
  │<─────────────────│                   │                    │                │
```

### 5.2 Error Recovery: MCPToolError

```
TaskRunner                    MCPClient                    LLM
    │                            │                          │
    │ call_tool(click, ref=@e42) │                          │
    │───────────────────────────>│                          │
    │                            │ (element not found)      │
    │ <── MCPToolError ──────────│                          │
    │                            │                          │
    │ (format as error result)   │                          │
    │                            │                          │
    │ invoke(messages + error)   │                          │
    │─────────────────────────────────────────────────────>│
    │                            │                          │
    │ <──── tool_call: snapshot (retry strategy) ──────────│
    │                            │                          │
    │ (loop continues)           │                          │
```

---

## 6. Risks and Mitigations

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Playwright MCP snapshot format differs from expected | Medium | High | POC phase logs actual format; normalize_snapshot() adapts |
| MCP SDK connection instability | Low | Medium | Reconnection logic (1 retry); fallback to mcp-use library |
| LangChain tool binding issues | Low | Low | Direct API calls as fallback; well-tested library |
| Node.js version incompatibility | Low | Low | Explicit version check; clear error message |

### 6.2 Integration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Netflix UI changes break checkpoint predicates | Medium | Medium | Predicates are isolated in ServiceConfig; easy to update |
| Playwright MCP deprecates --user-data-dir | Low | Medium | Design notes fallback strategy; monitor Playwright MCP releases |

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Component | Test Focus |
|-----------|------------|
| MCPClient | Mock subprocess, test connect/list_tools/call_tool/close |
| LLMClient | Mock LangChain models, test provider detection, retries |
| TaskRunner | Mock MCPClient + LLMClient, test full loop logic |
| CheckpointHandler | Test predicate evaluation, mock stdin for approval |
| ServiceRegistry | Test get/register, ServiceNotFoundError |
| normalize_snapshot | Test with sample MCP outputs, error cases |

### 7.2 Integration Tests

| Test | Components | Method |
|------|------------|--------|
| MCP connection | MCPClient + real Playwright MCP | Start server, list tools, call browser_snapshot |
| LLM tool calling | LLMClient + real API | Send tools, verify response format |
| Checkpoint flow | CheckpointHandler + mock stdin | Simulate y/n input |
| Full loop (mock LLM) | TaskRunner + real MCP + mock LLM | Deterministic LLM responses |

### 7.3 E2E Tests

| Test | Scope | Execution |
|------|-------|-----------|
| Netflix cancellation | Full system | Manual with test account |
| Dry-run mode | CLI + MCP + LLM | Automated, verify first action |

---

## 8. Implementation Notes

### 8.1 POC Phase Priorities

1. **First**: Validate MCP connection and tool execution
2. **Second**: Log and understand snapshot format
3. **Third**: Test LLM tool calling with both providers
4. **Last**: Implement checkpoint predicates based on real data

### 8.2 Deferred to Design Phase (Now Resolved)

- ✅ Playwright MCP profile configuration: Use `--user-data-dir` flag
- ✅ Fallback if --user-data-dir not supported: Document in spec as "to be determined in design phase"

### 8.3 Dependencies to Install

```bash
pip install mcp langchain-anthropic langchain-openai
# Node.js >= 18 required for Playwright MCP
```
