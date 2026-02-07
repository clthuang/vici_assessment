# Design: Claude-DA — Natural Language Data Analysis API

**Feature**: 001-claude-da
**Phase**: design
**Spec**: [spec.md](./spec.md)

---

## 0. Prior Art Research

### Codebase Patterns (subterminator)

| Pattern | Location | Reuse |
|---|---|---|
| Config: dataclass + env var loader with `_get_int_env` | `subterminator/utils/config.py` | Replicate pattern for Claude-DA config |
| Exceptions: base → category → specific hierarchy | `subterminator/utils/exceptions.py` | Replicate with Claude-DA-specific errors |
| Async timeout: `asyncio.wait_for()` | `subterminator/mcp_orchestrator/llm_client.py` | Same pattern for Agent SDK timeout |
| Session logging: structured JSON with correlation | `subterminator/utils/session.py` | Replicate for audit logging |
| Testing: pytest, AsyncMock, class-based, 85% coverage | `subterminator/tests/` | Same conventions |
| Project: Python >=3.11, src layout, ruff/mypy/pytest, uv | `subterminator/pyproject.toml` | Same toolchain |

### External Research

| Finding | Source | Impact on Design |
|---|---|---|
| LiteLLM requires module-level instance: `my_provider = MyProvider()` | LiteLLM docs | Provider module must export instance at module scope |
| `GenericStreamingChunk` requires `text`, `is_finished`, `finish_reason`, `index` | LiteLLM source | Streaming yield format is fixed |
| Agent SDK `ResultMessage` includes `total_cost_usd`, `usage`, `duration_ms` | SDK docs | Built-in audit data — no custom cost tracking needed |
| SQLite MCP tools: `read_query`, `write_query`, `create_table`, `list_tables`, `describe-table` | MCP server source | `allowed_tools` should permit only `read_query`, `list_tables`, `describe-table` |
| Agent SDK hooks (`PreToolUse`/`PostToolUse`) can intercept tool calls | SDK docs | Alternative audit capture mechanism (but message iteration is simpler for MVP) |
| `can_use_tool` callback for programmatic tool permission | SDK docs | Additional safety layer beyond `allowed_tools`/`disallowed_tools` |
| cabinlab/litellm-claude-code confirms `custom_provider_map` pattern works | GitHub | Validates our approach end-to-end |
| SQLite MCP server installed via `npx @modelcontextprotocol/server-sqlite` or `uvx mcp-server-sqlite` | MCP docs | Two installation paths; npx is specified in spec |

### Spec Reviewer Notes (to resolve in design)

| Note | Resolution |
|---|---|
| 30s query timeout mechanism unspecified | MCP SQLite server's native behavior; surfaced via Agent SDK tool error messages. Not provider-enforced. Documented in Section 1.5. |
| `disallowed_tools` narrower than PRD (missing Glob, Grep) | `allowed_tools: ["mcp__sqlite__*"]` implicitly blocks all non-MCP tools. `disallowed_tools` is a belt-and-suspenders layer for the most dangerous tools only. Documented in Section 1.4. |
| Audit log timing for streaming requests | Log written after final chunk sent; SQL/response accumulated in memory during iteration. Documented in Section 1.3. |
| Exact PyPI package name for Agent SDK | Verified: `pip install claude-agent-sdk` (v0.1.31). The old `claude-code-sdk` package is deprecated. Import: `from claude_agent_sdk import query, ClaudeAgentOptions`. Documented in Section 1.2. |
| Python minimum version | Python >=3.11 (matching subterminator). Documented in Section 3. |
| Sample LiteLLM proxy config | Included as a deliverable. Documented in Section 1.1. |

---

## 1. Architecture

### 1.1 Component Overview

```
claude-litellm/
├── src/claude_da/
│   ├── __init__.py          # Package init, __version__
│   ├── provider.py          # CustomLLM subclass + module-level instance
│   ├── agent.py             # Agent SDK wrapper (query orchestration)
│   ├── schema.py            # Schema discovery (direct SQLite)
│   ├── prompt.py            # System prompt construction
│   ├── audit.py             # Structured audit logging
│   ├── config.py            # Env var loading + validation
│   └── exceptions.py        # Exception hierarchy
├── scripts/
│   └── seed_demo_db.py      # Demo database seeder
├── tests/
│   ├── unit/                # No external deps
│   └── integration/         # Requires ANTHROPIC_API_KEY
├── litellm_config.yaml      # Sample LiteLLM proxy config
├── pyproject.toml
└── README.md
```

**6 source modules**, each with a single responsibility:

| Module | Responsibility | Depends on |
|---|---|---|
| `provider.py` | LiteLLM CustomLLM interface | `agent`, `audit`, `config`, `schema`, `prompt`, `exceptions` |
| `agent.py` | Agent SDK session lifecycle | `config`, `prompt`, `audit`, `exceptions` |
| `schema.py` | SQLite schema discovery at startup | `config`, `exceptions` |
| `prompt.py` | System prompt assembly | `schema` |
| `audit.py` | Structured JSON logging | `config` |
| `config.py` | Env var parsing + validation | `exceptions` |
| `exceptions.py` | Error hierarchy | (none) |

Dependency flow is acyclic: `provider` → `agent` → `prompt` → `schema` → `config` → `exceptions`.

### 1.2 Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Package name** | `claude-agent-sdk` (PyPI, v0.1.31) | Verified: `pip install claude-agent-sdk`. Import: `from claude_agent_sdk import query, ClaudeAgentOptions`. The old `claude-code-sdk` package (v0.0.25) is deprecated. Options class is `ClaudeAgentOptions` (renamed from `ClaudeCodeOptions` in v0.1.0). |
| **Provider registration** | `custom_provider_map` in litellm_config.yaml | Simpler than full provider registration. cabinlab confirms this works. |
| **Streaming approach** | Yield text chunks from Agent SDK messages as they arrive | Agent SDK returns `AsyncIterator[Message]`. Text content from `AssistantMessage` is yielded; tool calls are captured but not streamed. |
| **Audit capture** | Message iteration (not hooks) | Simpler: iterate messages, inspect tool use blocks, accumulate SQL. Hooks would require additional wiring for the same data. |
| **Schema discovery** | Direct SQLite at startup (not MCP) | Avoids needing an Agent SDK session during initialization. Spec AC-04.3 mandates this. |
| **Read-only enforcement** | `chmod 444` + `allowed_tools` + `disallowed_tools` | Three independent layers. `allowed_tools` wildcard is primary; `disallowed_tools` is defense-in-depth; filesystem permissions are infrastructure-level. |

### 1.3 Request Flow (detailed)

```
Client POST /v1/chat/completions
    │
    ▼
LiteLLM Proxy (routes to claude-da/analyst)
    │
    ▼
provider.py: acompletion() or astreaming()
    │
    ├─ 1. Validate input length (config.input_max_chars)
    │     → 400 if exceeded
    │
    ├─ 2. Extract messages from request
    │
    ├─ 3. Call agent.run_query(messages, stream=bool)
    │     │
    │     ▼
    │   agent.py: run_query()
    │     │
    │     ├─ 4. Build prompt (prompt.py: build_system_prompt())
    │     │
    │     ├─ 5. Configure ClaudeAgentOptions:
    │     │     - system_prompt
    │     │     - model
    │     │     - max_turns
    │     │     - mcp_servers: {"sqlite": McpStdioServerConfig(...)}
    │     │     - allowed_tools: ["mcp__sqlite__*"]
    │     │     - disallowed_tools: ["Bash", "Write", "Edit"]
    │     │     - permission_mode: ...
    │     │
    │     ├─ 6. asyncio.wait_for(query(...), timeout=240)
    │     │     │
    │     │     ▼
    │     │   async for message in query(prompt, options):
    │     │     ├─ AssistantMessage with text → accumulate response
    │     │     ├─ AssistantMessage with tool_use → capture SQL
    │     │     ├─ ResultMessage → extract cost/usage metadata
    │     │     └─ (stream mode: yield GenericStreamingChunk per text block)
    │     │
    │     ├─ 7. Return AgentResult(response_text, sql_queries, metadata)
    │     │
    │     └─ 8. On error: map to provider exception
    │
    ├─ 9. Format as ChatCompletion response (or final streaming chunk)
    │
    └─ 10. Fire-and-forget: audit.log_request(session_id, ...)
```

**Streaming detail**: For streaming requests, step 6 yields `GenericStreamingChunk` for each text block as it arrives from the Agent SDK. SQL queries and metadata are still accumulated in memory. The audit log (step 10) is written after the final chunk (`is_finished=True`) is sent.

### 1.4 Safety Architecture

Three independent enforcement layers, each sufficient on its own:

**Layer 1: Tool Allowlist (SDK-enforced)**
```
allowed_tools: ["mcp__sqlite__*"]
```
This restricts the agent to only MCP SQLite tools. All other tools (Bash, Write, Edit, Glob, Grep, Read, etc.) are implicitly blocked. This alone prevents sandbox escape.

**Layer 2: Explicit Tool Blocklist (SDK-enforced, defense-in-depth)**
```
disallowed_tools: ["Bash", "Write", "Edit"]
```
Redundant with Layer 1, but explicitly blocks the three most dangerous tools. If a bug in `allowed_tools` handling were to surface (as happened in SDK v0.1.5–0.1.9, issue #361), this layer would still block the critical paths.

**Layer 3: Filesystem Permissions (OS-enforced)**
```
chmod 444 demo.db
```
Even if the agent somehow gained write tool access, the OS prevents writes. The startup check (AC-05.4) validates this.

**Why three layers**: Any single layer is sufficient. Three layers mean two must fail simultaneously for a write to succeed. The `allowed_tools` bug in early SDK versions (#361) demonstrates that "one layer is enough" assumptions can fail.

### 1.5 Timeout Architecture

```
LiteLLM Proxy timeout: 300s (default, configurable)
    └─ Agent SDK timeout: 240s (asyncio.wait_for)
         └─ MCP query timeout: 30s (SQLite MCP server native)
```

Each layer times out before its parent. The 30s MCP query timeout is **not provider-enforced** — it is the SQLite MCP server's native behavior. When a query times out, the MCP server returns an error via the tool result, which the Agent SDK surfaces as a tool error message. The agent may then retry with a simpler query or give up.

If the agent enters a retry loop, `max_turns` (default: 10) caps iterations. If the entire session hangs, `asyncio.wait_for(timeout=240)` fires and the provider returns HTTP 504.

### 1.6 Error Mapping

| Source Exception | Detection | HTTP | Error Code |
|---|---|---|---|
| Input too long | `len(user_message) > config.input_max_chars` | 400 | `input_too_long` |
| `asyncio.TimeoutError` from `wait_for` | Catch `asyncio.TimeoutError` | 504 | `agent_timeout` |
| Agent SDK rate limit error | Catch SDK exception with rate limit indicator | 429 | `rate_limited` |
| MCP server unreachable | Agent SDK reports tool connection failure | 503 | `database_unavailable` |
| Agent SDK generic error | Catch-all for unknown SDK exceptions | 500 | `internal_error` |
| Agent exhausts `max_turns` | Normal completion — agent returns best-effort answer | 200 | (normal) |

**Note on `query_timeout`**: The spec error table lists a 30s `query_timeout` code. This is the MCP SQLite server's native behavior — when a query exceeds the server's timeout, the tool call returns an error result. The agent sees this as a tool failure and may retry with a simpler query or report the error. This is **not separately surfaced as HTTP 504** from the provider; it is handled within the agent's agentic loop. If repeated query timeouts exhaust `max_turns`, the agent returns a best-effort response (200). If the entire session times out at 240s, it becomes `agent_timeout` (504). The `query_timeout` error code in the spec's error table applies only if the provider detects a query-specific timeout in the agent's output (e.g., the agent's final response mentions "query timed out"); this is a best-effort classification, not a guaranteed detection.

Error detection for MCP and rate limit errors depends on the specific exception types/messages from the Agent SDK. The SDK exposes `ProcessError`, `CLIJSONDecodeError`, and `ClaudeSDKError`. These will be mapped during implementation.

---

## 2. Interfaces

### 2.1 `config.py` — Configuration

```python
@dataclass(frozen=True)
class ClaudeDAConfig:
    anthropic_api_key: str
    db_path: str                # default: "./demo.db"
    model: str                  # default: "claude-sonnet-4-5-20250929"
    max_turns: int              # default: 10
    max_budget_usd: float       # default: 0.50
    input_max_chars: int        # default: 10000
    log_output: str             # default: "stdout" ("stdout"|"file"|"both")
    log_file: str               # default: "./claude-da-audit.jsonl"
    log_verbose: bool           # default: False
```

```python
def load_config() -> ClaudeDAConfig:
    """Load and validate config from environment variables.

    Raises:
        ConfigurationError: If ANTHROPIC_API_KEY missing or numeric values invalid.
    """
```

Pattern: follows subterminator's `ConfigLoader` with `_get_int_env`/`_get_float_env` helpers.

### 2.2 `exceptions.py` — Error Hierarchy

```python
class ClaudeDAError(Exception):
    """Base exception for Claude-DA."""

class ConfigurationError(ClaudeDAError):
    """Invalid or missing configuration. Raised at startup."""

class InputValidationError(ClaudeDAError):
    """User input failed validation (e.g., too long)."""
    status_code: int = 400
    error_code: str = "input_too_long"

class AgentTimeoutError(ClaudeDAError):
    """Agent SDK session exceeded timeout."""
    status_code: int = 504
    error_code: str = "agent_timeout"

class RateLimitError(ClaudeDAError):
    """Anthropic API rate limited."""
    status_code: int = 429
    error_code: str = "rate_limited"

class DatabaseUnavailableError(ClaudeDAError):
    """MCP database server unreachable."""
    status_code: int = 503
    error_code: str = "database_unavailable"
```

Each error carries `status_code` and `error_code` as class attributes. `provider.py` catches these and re-raises as LiteLLM's `CustomLLMError(status_code, message)`, which is LiteLLM's standard mechanism for returning HTTP error codes from custom providers. The translation happens in a shared error handler:

```python
from litellm.exceptions import CustomLLMError

def _handle_error(error: ClaudeDAError) -> None:
    """Translate ClaudeDAError to CustomLLMError for LiteLLM.

    Formats as OpenAI-compatible error JSON and raises CustomLLMError
    with the appropriate status code.
    """
    error_body = {
        "error": {
            "message": str(error),
            "type": _error_type(error.status_code),
            "code": error.error_code,
        }
    }
    raise CustomLLMError(
        status_code=error.status_code,
        message=json.dumps(error_body),
    ) from error
```

Both `acompletion()` and `astreaming()` wrap their logic in `try/except ClaudeDAError` and call `_handle_error()`. The `asyncio.TimeoutError` is caught first and wrapped in `AgentTimeoutError` before translation.

### 2.3 `schema.py` — Schema Discovery

```python
@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    primary_key: bool

@dataclass
class ForeignKey:
    from_column: str
    to_table: str
    to_column: str

@dataclass
class TableSchema:
    name: str
    columns: list[ColumnInfo]
    foreign_keys: list[ForeignKey]

@dataclass
class DatabaseSchema:
    tables: list[TableSchema]

    def to_prompt_text(self) -> str:
        """Format schema for inclusion in system prompt.

        Returns human-readable text showing tables, columns, types,
        and relationships. Output is designed for LLM consumption.
        """
```

```python
def discover_schema(db_path: str) -> DatabaseSchema:
    """Open a read-only SQLite connection and discover the schema.

    Queries sqlite_master for table definitions, PRAGMA table_info
    for columns, and PRAGMA foreign_key_list for relationships.

    Args:
        db_path: Path to the SQLite database file.

    Raises:
        ConfigurationError: If the database cannot be opened or schema is empty.
    """
```

### 2.4 `prompt.py` — System Prompt Assembly

```python
def build_system_prompt(schema: DatabaseSchema) -> str:
    """Assemble the data analyst system prompt with schema.

    Components:
    1. Role definition (data analyst for internal use)
    2. Schema section (from schema.to_prompt_text())
    3. Behavioral rules (explain insights, note trends, limit results)
    4. Read-only instructions (soft guardrail)
    5. Non-data question handling

    Returns:
        System prompt string, guaranteed under 12,000 characters for demo schema.

    Raises:
        ConfigurationError: If assembled prompt exceeds 12,000 characters.
    """
```

### 2.5 `audit.py` — Structured Audit Logging

```python
@dataclass
class AuditEntry:
    session_id: str             # UUID v4
    timestamp: str              # ISO 8601
    user_question: str
    sql_queries_executed: list[str]
    query_results_summary: list[dict]  # [{table, row_count, columns}]
    final_response: str
    metadata: AuditMetadata

@dataclass
class AuditMetadata:
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_estimate_usd: float | None
    duration_seconds: float
    tool_call_count: int
```

```python
class AuditLogger:
    """Writes structured audit log entries.

    Configured via ClaudeDAConfig for output destination and verbosity.
    """

    def __init__(self, config: ClaudeDAConfig) -> None: ...

    async def log(self, entry: AuditEntry) -> None:
        """Write audit entry to configured destination(s).

        Async to avoid blocking the event loop during file I/O.
        Called via asyncio.create_task() from provider (fire-and-forget).
        Errors are caught internally and logged to stderr, never raised.
        When log_output is "stdout" or "both": prints JSON to stdout.
        When log_output is "file" or "both": appends JSON line to log_file
        using asyncio.to_thread() for non-blocking file writes.
        """
```

### 2.6 `agent.py` — Agent SDK Wrapper

```python
@dataclass
class AgentResult:
    response_text: str
    sql_queries: list[str]
    query_results: list[dict]   # For verbose audit logging
    metadata: AgentResultMetadata

@dataclass
class AgentResultMetadata:
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_cost_usd: float | None
    duration_seconds: float
    tool_call_count: int
```

```python
class DataAnalystAgent:
    """Wraps the Claude Agent SDK for data analysis requests."""

    def __init__(self, config: ClaudeDAConfig, system_prompt: str) -> None: ...

    async def run(self, messages: list[dict]) -> AgentResult:
        """Execute a non-streaming analysis request.

        Converts OpenAI messages to a single prompt string, creates a
        new Agent SDK session, iterates all response messages,
        accumulates text and SQL queries, returns structured result.

        Wrapped in asyncio.wait_for(timeout=240s).

        Raises:
            AgentTimeoutError: If session exceeds 240 seconds.
            RateLimitError: If Anthropic API returns 429.
            DatabaseUnavailableError: If MCP server connection fails.
        """

    async def run_streaming(
        self, messages: list[dict]
    ) -> tuple[AsyncIterator[GenericStreamingChunk], asyncio.Future[AgentResult]]:
        """Execute a streaming analysis request.

        Returns a tuple of (chunk_iterator, result_future).
        - chunk_iterator yields GenericStreamingChunk for each text block.
          Final chunk has is_finished=True, finish_reason="stop", and
          includes usage data (prompt_tokens, completion_tokens, total_tokens).
        - result_future resolves to AgentResult after iteration completes,
          containing accumulated SQL queries and metadata for audit logging.

        This avoids mutable instance state (self.last_result) and is safe
        for concurrent requests.

        Raises:
            Same as run().
        """
```

**Message processing logic** (inside `run` and `run_streaming`):

The Agent SDK returns an `AsyncIterator[Message]`. Each message is inspected:

| Message Type | Contains | Action |
|---|---|---|
| `AssistantMessage` | Text content blocks | Append to response text. (Stream: yield chunk.) |
| `AssistantMessage` | Tool use blocks (name matches `mcp__sqlite__*`) | Extract SQL from tool input args, append to `sql_queries`. |
| `ResultMessage` | `total_cost_usd`, `usage`, `duration_ms` | Extract into `AgentResultMetadata`. |
| Other message types | Various | Skip (not relevant to output). |

**Message-to-prompt conversion** (resolves AC-01.8):

The Agent SDK's `query()` accepts `prompt: str`, not an OpenAI messages list. Conversion strategy:

```python
def _messages_to_prompt(messages: list[dict]) -> str:
    """Convert OpenAI-format messages to a single prompt string.

    The system_prompt is handled separately via ClaudeAgentOptions.
    This function formats user/assistant message history into a
    conversational prompt string that preserves turn structure.

    Strategy:
    - System messages: Skipped (handled by ClaudeAgentOptions.system_prompt)
    - Single user message (most common): Use content directly as prompt
    - Multi-turn history: Format as labeled turns:
        User: {content}
        Assistant: {content}
        User: {content}
    """
```

For the MVP (stateless requests, no conversation memory), the typical case is a single user message. Multi-turn formatting is included for completeness since the spec requires forwarding full history (AC-01.8), but in practice each request is independent.

**Streaming chunk format**:

Intermediate chunks:
```python
GenericStreamingChunk(
    text="partial text...",
    is_finished=False,
    finish_reason="",
    index=0,
)
```

Final chunk (after `ResultMessage` received):
```python
GenericStreamingChunk(
    text="",
    is_finished=True,
    finish_reason="stop",
    index=0,
    usage={"prompt_tokens": N, "completion_tokens": N, "total_tokens": N},
)
```

Usage data is extracted from `ResultMessage.usage` and included in the final chunk for LiteLLM's cost tracking.

### 2.7 `provider.py` — LiteLLM Custom Provider

```python
class ClaudeDAProvider(CustomLLM):
    """LiteLLM custom provider for Claude-DA data analysis."""

    def __init__(self) -> None:
        """Initialize provider: load config, discover schema, build prompt, create agent."""

    def completion(self, *args, **kwargs) -> ModelResponse:
        """Sync completion — raises NotImplementedError.

        The LiteLLM proxy always uses async variants (acompletion/astreaming).
        Sync methods are never called in proxy mode. Raising NotImplementedError
        avoids asyncio.run() issues when called inside an existing event loop.
        """

    async def acompletion(
        self, model: str, messages: list, **kwargs
    ) -> ModelResponse:
        """Async non-streaming completion.

        1. Validate input length
        2. Call agent.run(messages)
        3. Format as ModelResponse
        4. Fire-and-forget audit log
        """

    def streaming(self, *args, **kwargs) -> Iterator[GenericStreamingChunk]:
        """Sync streaming — raises NotImplementedError."""

    async def astreaming(
        self, model: str, messages: list, **kwargs
    ) -> AsyncIterator[GenericStreamingChunk]:
        """Async streaming.

        1. Validate input length
        2. Yield chunks from agent.run_streaming(messages)
        3. After final chunk: fire-and-forget audit log
        """
```

```python
# Module-level instance (required by LiteLLM)
claude_da_provider = ClaudeDAProvider()
```

**Initialization strategy — lazy init on first request**:

The `__init__` method does NOT run the full initialization sequence. Instead, it defers heavy initialization (schema discovery, DB validation, prompt building) to the first request. This avoids import-time failures when env vars are not yet set (e.g., during test collection or LiteLLM provider scanning).

```python
def __init__(self) -> None:
    self._initialized = False

async def _ensure_initialized(self) -> None:
    """Lazy initialization on first request. Thread-safe via asyncio.Lock."""
    if self._initialized:
        return
    async with self._init_lock:
        if self._initialized:
            return  # Double-check after lock
        config = load_config()
        schema = discover_schema(config.db_path)
        verify_read_only(config.db_path)
        system_prompt = build_system_prompt(schema)
        self._agent = DataAnalystAgent(config, system_prompt)
        self._audit = AuditLogger(config)
        self._config = config
        self._initialized = True
```

Both `acompletion()` and `astreaming()` call `await self._ensure_initialized()` before processing. If initialization fails, the error propagates as a `ConfigurationError` → `CustomLLMError(500)`.

**`verify_read_only(db_path)`** lives in `schema.py` alongside `discover_schema()`:

```python
def verify_read_only(db_path: str) -> None:
    """Attempt a write operation and verify it fails.

    Opens a direct SQLite connection and attempts:
        CREATE TABLE _claude_da_write_check (id INTEGER)
    If the write succeeds, raises ConfigurationError with message:
        "Database is not read-only. Refusing to start."
    If the write fails (expected), returns silently.
    """
```

### 2.8 `litellm_config.yaml` — Sample Proxy Configuration

```yaml
model_list:
  - model_name: claude-da/analyst
    litellm_params:
      model: claude-da/analyst

litellm_settings:
  custom_provider_map:
    - provider: claude-da
      custom_handler: claude_da.provider.claude_da_provider
```

This file is a deliverable. The user runs:
```
litellm --config litellm_config.yaml
```

### 2.9 Demo Database Seeder (`scripts/seed_demo_db.py`)

A standalone script that:
1. Creates `demo.db` with the e-commerce schema (4 tables from spec Section 3)
2. Populates with realistic data: 50+ customers, 200+ orders, 500+ order items
3. Distributes orders across 6+ calendar months with varied counts
4. Sets file permissions to read-only (`chmod 444`)

This script is run once during setup, not at runtime. The seeded `demo.db` is committed to the repository (it's small, ~200KB) so setup is zero-step for reviewers.

---

## 3. Runtime Requirements

| Requirement | Version | Purpose |
|---|---|---|
| Python | >=3.11 | Language runtime |
| Node.js | >=18 | MCP SQLite server (via npx) |
| `claude-agent-sdk` | >=0.1.30 | Agent SDK (import: `claude_agent_sdk`) |
| `litellm` | >=1.0 | Proxy + CustomLLM base class |

---

## 4. Technical Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `claude-agent-sdk` API changes (v0.1.x) | Medium | Pin version. Integration test catches breaks. Fallback: CLI subprocess. |
| LiteLLM `CustomLLM` interface changes | Low | Pin version. Unit test verifies registration. |
| Agent SDK message types don't match expected structure | Medium | Integration test with real Agent SDK validates message iteration. Implement defensive parsing with fallbacks. |
| MCP SQLite server tool names differ from expected | Low | Integration smoke test validates tool naming. `allowed_tools` pattern is flexible (`mcp__sqlite__*`). |
| `asyncio.wait_for` cancellation doesn't cleanly stop Agent SDK session | Medium | Cancellation is best-effort. The SDK session may continue in the background briefly. Acceptable for MVP (single-user). |

---

## 5. Testing Architecture

### Unit Tests (no external deps)

| Test | Module | Validates |
|---|---|---|
| Config loading with defaults | `config.py` | All env vars parsed, defaults applied, validation errors raised |
| Config loading with invalid values | `config.py` | `ConfigurationError` raised for non-numeric values |
| Schema discovery from test DB | `schema.py` | Tables, columns, types, foreign keys extracted correctly |
| Schema to prompt text | `schema.py` | Output is human-readable, under 12,000 chars |
| System prompt assembly | `prompt.py` | Contains role, schema, rules; under character limit |
| Audit entry serialization | `audit.py` | JSON structure, field presence, JSONL format |
| Audit logger file output | `audit.py` | Writes to file, non-blocking on error |
| Input validation | `provider.py` | Rejects oversized input with correct error format |
| Error formatting | `provider.py` | Maps exceptions to OpenAI error response format |
| Provider registration | `provider.py` | `claude_da_provider` is a `CustomLLM` instance |

### Integration Tests (require ANTHROPIC_API_KEY)

| Test | Validates |
|---|---|
| Smoke: Agent SDK → MCP SQLite → query → response | End-to-end plumbing works |
| Data question → insight with real data references | Agent queries DB and explains results |
| Streaming → valid SSE chunks → final stop chunk | Streaming format correct |
| Non-data question → no tool calls | Agent handles conversationally |
| Read-only → write attempt fails | Safety layers enforced |

### Test Framework

- **pytest** with `pytest-asyncio` (asyncio_mode="auto")
- **Coverage**: 85% target (matching subterminator)
- **Mocking**: `unittest.mock` (AsyncMock for Agent SDK)
- Integration tests skipped when `ANTHROPIC_API_KEY` not set (`pytest.mark.skipif`)
