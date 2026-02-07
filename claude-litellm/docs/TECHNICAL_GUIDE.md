# Claude-DA: Technical Guide

This document is a reference for engineers onboarding to the Claude-DA codebase. It covers architecture, module-by-module internals with line-number references, the request lifecycle, safety enforcement, error handling, testing, and tooling.

**Prerequisites**: Python 3.11+, Node.js 18+ (for `npx`), uv (Python package manager), an Anthropic API key for integration tests.

For user-facing setup and usage instructions, see [../README.md](../README.md). For the problem statement, design rationale, and business context, see [../REPORT.md](../REPORT.md).

---

## Project Structure

```
claude-litellm/
├── src/claude_da/
│   ├── __init__.py              # Package init, __version__ = "0.1.0"
│   ├── exceptions.py            # Exception hierarchy (lines 9-43)
│   ├── config.py                # Env var config + validation (lines 22-154)
│   ├── schema.py                # Schema discovery + read-only check (lines 20-251)
│   ├── prompt.py                # System prompt assembly (lines 13-89)
│   ├── audit.py                 # Structured audit logging (lines 17-144)
│   ├── agent.py                 # Agent SDK wrapper (lines 34-418)
│   └── provider.py              # LiteLLM CustomLLM interface (lines 48-375)
├── scripts/
│   └── seed_demo_db.py          # Demo database seeder (lines 210-268)
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── unit/                    # 8 test files (no external deps)
│   └── integration/             # 6 test files (require ANTHROPIC_API_KEY)
├── litellm_config.yaml          # LiteLLM proxy configuration
├── pyproject.toml               # Package config, deps, tool settings
├── .env.template                # Environment variable template
├── README.md                    # User-facing documentation
├── REPORT.md                    # Interviewer-facing report
└── docs/
    └── TECHNICAL_GUIDE.md       # This file
```

---

## Architecture Deep-Dive

### Module Dependency Graph

Dependencies are acyclic. Every module imports only from modules below it in this chain:

```
provider
  ├── agent
  │     ├── config
  │     └── exceptions
  ├── audit
  ├── config
  ├── schema
  │     └── exceptions
  ├── prompt
  │     ├── schema (DatabaseSchema type)
  │     └── exceptions
  └── exceptions
```

### Module Responsibilities

| Module | Responsibility | Depends On |
|---|---|---|
| `exceptions.py` | Exception hierarchy with HTTP status codes | (none) |
| `config.py` | Load and validate 9 env vars into a frozen dataclass | `exceptions` |
| `schema.py` | SQLite schema discovery via PRAGMA; read-only verification | `exceptions` |
| `prompt.py` | Assemble system prompt from role, schema, rules, safety instructions | `schema` (types), `exceptions` |
| `audit.py` | Structured JSON/JSONL audit logging to stdout, file, or both | (none -- receives config values as constructor args) |
| `agent.py` | Wrap Agent SDK `query()` for non-streaming and streaming; extract SQL and metadata from messages | `config`, `exceptions` |
| `provider.py` | LiteLLM `CustomLLM` subclass; lazy init, input validation, error translation, audit dispatch | `agent`, `audit`, `config`, `schema`, `prompt`, `exceptions` |

---

## Request Lifecycle

This section traces a non-streaming request from entry to exit, with code references at each step.

### Non-Streaming (`acompletion`)

```
1. LiteLLM Proxy routes to claude-da/analyst
          │
          ▼
2. provider.py:278  →  await self._ensure_initialized()
          │
          ▼
3. provider.py:279  →  self._validate_input_length(messages)
          │                └── Raises InputValidationError (400) if too long
          ▼
4. agent.py:229     →  prompt = _messages_to_prompt(messages)
          │
          ▼
5. agent.py:230     →  options = self._build_options()
          │                └── MCP config, tool allowlist/blocklist, model, budget
          ▼
6. agent.py:235     →  asyncio.wait_for(self._collect_messages(...), timeout=240)
          │                └── Raises AgentTimeoutError (504) on timeout
          ▼
7. agent.py:292     →  async for message in query(prompt, options):
          │                ├── AssistantMessage + TextBlock  → accumulate response text
          │                ├── AssistantMessage + ToolUseBlock → extract SQL
          │                ├── ResultMessage → extract token/cost metadata
          │                └── Other → extract tool results for audit
          ▼
8. provider.py:284  →  ModelResponse(choices=[...], usage={...})
          │
          ▼
9. provider.py:308  →  self._fire_audit(messages, result)
          │                └── asyncio.create_task, fire-and-forget
          ▼
10. Return ModelResponse to LiteLLM Proxy → Client
```

### Streaming (`astreaming`)

The streaming path (`provider.py:318`) follows the same initialisation and validation steps. The key difference:

- **Entry point**: `agent.py:320` `run_streaming()` yields `GenericStreamingChunk`-compatible dicts as `AssistantMessage` text blocks arrive.
- **Accumulation**: SQL queries, query results, and metadata are accumulated in local lists during iteration, not yielded.
- **Result holder**: A mutable `list[AgentResult | None]` is passed to `run_streaming()`. After the final chunk, `result_holder[0]` is populated with the complete `AgentResult` (`agent.py:413`).
- **Audit timing**: The audit entry is fired after the stream completes (`provider.py:363-364`), once `result_holder[0]` is available.

---

## Module-by-Module Reference

### exceptions.py

Path: `src/claude_da/exceptions.py` (43 lines)

Defines 5 exception classes in a flat hierarchy. All inherit from `ClaudeDAError`. Exceptions that map to HTTP failures carry `status_code` and `error_code` class attributes.

| Class | Line | status_code | error_code |
|---|---|---|---|
| `ClaudeDAError` | 9 | -- | -- |
| `ConfigurationError` | 13 | -- | -- |
| `InputValidationError` | 17 | 400 | `input_too_long` |
| `AgentTimeoutError` | 24 | 504 | `agent_timeout` |
| `RateLimitError` | 31 | 429 | `rate_limited` |
| `DatabaseUnavailableError` | 38 | 503 | `database_unavailable` |

`ConfigurationError` has no status code because it is raised at startup (before any HTTP request).

### config.py

Path: `src/claude_da/config.py` (155 lines)

**Key components**:

- `ClaudeDAConfig` dataclass (lines 23-46): frozen, immutable configuration with 9 fields.
- `load_config()` (lines 112-154): reads environment variables, validates, returns a `ClaudeDAConfig`.
- Helper parsers: `_get_int_env` (line 49), `_get_float_env` (line 71), `_get_bool_env` (line 93).
- `_VALID_LOG_OUTPUTS` (line 19): `frozenset({"stdout", "file", "both"})`.
- Dotenv support: `load_dotenv()` called at module import time (line 17).

**Environment variables** (9 total):

| Variable | Config Field | Type | Default |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `anthropic_api_key` | str | (required) |
| `CLAUDE_DA_DB_PATH` | `db_path` | str | `./demo.db` |
| `CLAUDE_DA_MODEL` | `model` | str | `claude-sonnet-4-5-20250929` |
| `CLAUDE_DA_MAX_TURNS` | `max_turns` | int | `10` |
| `CLAUDE_DA_MAX_BUDGET_USD` | `max_budget_usd` | float | `0.50` |
| `CLAUDE_DA_INPUT_MAX_CHARS` | `input_max_chars` | int | `10000` |
| `CLAUDE_DA_LOG_OUTPUT` | `log_output` | str | `stdout` |
| `CLAUDE_DA_LOG_FILE` | `log_file` | str | `./claude-da-audit.jsonl` |
| `CLAUDE_DA_LOG_VERBOSE` | `log_verbose` | bool | `False` |

Validation is fail-fast: missing `ANTHROPIC_API_KEY`, non-numeric values for int/float fields, or invalid `log_output` values all raise `ConfigurationError` immediately.

### schema.py

Path: `src/claude_da/schema.py` (252 lines)

**Dataclasses** (lines 22-114):

| Class | Line | Fields |
|---|---|---|
| `ColumnInfo` | 22 | `name`, `type`, `nullable`, `primary_key` |
| `ForeignKey` | 38 | `from_column`, `to_table`, `to_column` |
| `TableSchema` | 53 | `name`, `columns: list[ColumnInfo]`, `foreign_keys: list[ForeignKey]` |
| `DatabaseSchema` | 69 | `tables: list[TableSchema]` |

`DatabaseSchema.to_prompt_text()` (line 78) renders the schema as human-readable text for LLM consumption (column types, PK flags, nullable flags, foreign keys).

**Functions**:

| Function | Line | Purpose |
|---|---|---|
| `discover_schema(db_path)` | 120 | Opens SQLite in read-only mode (`?mode=ro`), queries `sqlite_master` for tables, uses `PRAGMA table_info` and `PRAGMA foreign_key_list` for column/FK metadata |
| `_discover_columns(conn, table_name)` | 171 | Reads column metadata for a single table |
| `_discover_foreign_keys(conn, table_name)` | 194 | Reads foreign key metadata for a single table |
| `verify_read_only(db_path)` | 222 | Attempts `CREATE TABLE _claude_da_write_check`; if the write succeeds, raises `ConfigurationError("Database is not read-only. Refusing to start.")`; if it fails, returns silently |

Table name validation: `_SAFE_TABLE_NAME` regex (line 16) prevents SQL injection in PRAGMA statements.

### prompt.py

Path: `src/claude_da/prompt.py` (90 lines)

**Constants**:

- `_MAX_PROMPT_CHARS = 12_000` (line 13)
- `_ROLE_SECTION` (line 15): expert data analyst role definition
- `_RULES_SECTION` (line 22): 6 behavioral rules (explain insights, note trends, limit to 50 rows, etc.)
- `_READ_ONLY_SECTION` (line 31): hard instruction to use only SELECT statements
- `_NON_DATA_SECTION` (line 40): redirect non-data questions back to analysis

**Function**:

`build_system_prompt(schema)` (lines 51-89): joins the 5 sections (role, schema text, rules, read-only, non-data handling) with double newlines. Raises `ConfigurationError` if the assembled prompt exceeds 12,000 characters.

### audit.py

Path: `src/claude_da/audit.py` (145 lines)

**Dataclasses**:

| Class | Line | Key Fields |
|---|---|---|
| `AuditMetadata` | 18 | `model`, `prompt_tokens`, `completion_tokens`, `cost_estimate_usd`, `duration_seconds`, `tool_call_count` |
| `AuditEntry` | 39 | `session_id`, `timestamp`, `user_question`, `sql_queries_executed`, `query_results_summary`, `final_response`, `metadata: AuditMetadata` |

`AuditEntry.to_dict()` (line 69): converts to a plain dict via `dataclasses.asdict()`.

**AuditLogger** (line 78):

| Method | Line | Behaviour |
|---|---|---|
| `__init__(log_output, log_file, verbose)` | 88 | Stores configuration; no I/O |
| `log(entry)` | 98 | Async; writes to configured outputs; removes `query_results_summary` when `verbose=False` (line 110) |
| `_write_stdout(data)` | 118 | JSON with indent=2 to stdout |
| `_write_file(data)` | 127 | JSONL via `asyncio.to_thread` (non-blocking file append) |
| `_log_error(message)` | 140 | Static; writes to stderr; never raises |

All I/O errors are caught internally and written to stderr. Audit failures never crash the application.

### agent.py

Path: `src/claude_da/agent.py` (419 lines)

**Constants**:

- `_AGENT_TIMEOUT_SECONDS = 240` (line 34)

**Helper functions**:

| Function | Line | Purpose |
|---|---|---|
| `_messages_to_prompt(messages)` | 37 | Converts OpenAI-format message list to a flat prompt string. Skips system messages. Single user message: use content directly. Multi-turn: format as `Role: content` lines. |
| `_extract_sql_from_tool_use(block)` | 126 | Returns SQL string from a `ToolUseBlock` if the tool name starts with `mcp__sqlite__` |
| `_extract_tool_results(message)` | 133 | Extracts query result dicts from `ToolResultBlock` content |
| `_build_result_metadata(message, model)` | 153 | Builds `AgentResultMetadata` from a `ResultMessage` (usage, cost, duration) |

**Result dataclasses**:

| Class | Line | Key Fields |
|---|---|---|
| `AgentResultMetadata` | 75 | `model`, `prompt_tokens`, `completion_tokens`, `total_cost_usd`, `duration_seconds`, `tool_call_count` |
| `AgentResult` | 96 | `response_text`, `sql_queries`, `query_results`, `metadata: AgentResultMetadata` |

**DataAnalystAgent** (line 171):

| Method | Line | Behaviour |
|---|---|---|
| `__init__(config, system_prompt)` | 182 | Stores config and pre-built system prompt |
| `_build_options()` | 186 | Returns `ClaudeAgentOptions` with MCP SQLite server config (`npx @modelcontextprotocol/server-sqlite`), `allowed_tools=["mcp__sqlite__*"]`, `disallowed_tools=["Bash", "Write", "Edit"]`, `permission_mode="bypassPermissions"` |
| `run(messages)` | 213 | Non-streaming: converts messages to prompt, calls `_collect_messages()` inside `asyncio.wait_for(timeout=240)`, returns `AgentResult` |
| `_collect_messages(prompt, options)` | 269 | Iterates `query(prompt, options)`, collects text, SQL, results, metadata |
| `run_streaming(messages, result_holder)` | 320 | Streaming: yields `GenericStreamingChunk`-compatible dicts per text block. Accumulates SQL/results/metadata. Final chunk has `is_finished=True` and usage data. Populates `result_holder[0]` with `AgentResult` after stream ends. |

**MCP server configuration** (inside `_build_options`, lines 198-206):

```python
mcp_servers={
    "sqlite": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite", self._config.db_path],
    }
}
```

The MCP SQLite server is launched as a stdio subprocess by the Agent SDK on each session. `npx -y` auto-installs the package on first use.

### provider.py

Path: `src/claude_da/provider.py` (376 lines)

**ClaudeDAProvider** (line 48): subclass of `litellm.types.llms.custom_llm.CustomLLM`.

| Method | Line | Behaviour |
|---|---|---|
| `__init__()` | 56 | Sets `_initialized=False`, creates `asyncio.Lock`. No heavy init. |
| `completion()` | 67 | Raises `NotImplementedError` (sync not supported) |
| `streaming()` | 77 | Raises `NotImplementedError` (sync not supported) |
| `_handle_error(exc)` | 89 | Translates `ClaudeDAError` to `CustomLLMError` with OpenAI-format JSON body |
| `_ensure_initialized()` | 119 | Double-check locking pattern: loads config, discovers schema, verifies read-only, builds prompt, creates agent and audit logger. On failure, caches error so subsequent calls fail immediately. |
| `_validate_input_length(messages)` | 165 | Sums content lengths; raises `InputValidationError` if over limit |
| `_build_audit_entry(messages, result)` | 185 | Constructs `AuditEntry` from messages and `AgentResult` |
| `_fire_audit(messages, result)` | 216 | Creates `asyncio.Task` for `self._audit.log(entry)`. Exceptions suppressed via done callback. |
| `acompletion(...)` | 242 | Async non-streaming: init → validate → run agent → format ModelResponse → audit → return |
| `astreaming(...)` | 318 | Async streaming: init → validate → yield chunks from `run_streaming()` → audit after stream |

**Error type mapping** (lines 35-40):

```python
_ERROR_TYPE_MAP = {400: "invalid_request_error", 429: "rate_limit_error", 503: "server_error", 504: "server_error"}
```

**Module-level singleton** (line 375):

```python
claude_da_provider = ClaudeDAProvider()
```

This instance is referenced by `litellm_config.yaml` as `claude_da.provider.claude_da_provider`. LiteLLM requires a module-level instance for custom provider registration.

### seed_demo_db.py

Path: `scripts/seed_demo_db.py` (291 lines)

`seed_database(db_path)` (lines 210-268):

1. Removes existing file if present (handles read-only by restoring write permissions first).
2. Creates SQLite database with 4-table schema (customers, products, orders, order_items).
3. Uses `random.Random(42)` for deterministic seeding.
4. Generates data:
   - **55 customers**: tier distribution 55% free / 30% pro / 15% enterprise (`_TIER_WEIGHTS` at line 86).
   - **25 products**: across 5 categories (Electronics, Accessories, Books, Furniture, Office Supplies).
   - **220 orders**: spanning Jan--Oct 2024; status distribution 10% pending / 70% completed / 12% cancelled / 8% refunded (`_STATUS_WEIGHTS` at line 117).
   - **550+ order items**: 1--5 per order, minimum 550 guaranteed.
5. Sets file permissions to `chmod 444` (read-only for all users) at line 266.

---

## Safety Architecture

This section expands on the safety summary in [REPORT.md](../REPORT.md) with exact code references.

### Three Enforcement Layers

**Layer 1: Tool Allowlist** (SDK-enforced)
```
allowed_tools=["mcp__sqlite__*"]    # agent.py:208
```
Restricts the agent to MCP SQLite tools only. All other tools (Bash, Write, Edit, Glob, Grep, Read, etc.) are implicitly blocked. This alone prevents sandbox escape.

**Layer 2: Explicit Tool Blocklist** (SDK-enforced, defence-in-depth)
```
disallowed_tools=["Bash", "Write", "Edit"]    # agent.py:209
```
Redundant with Layer 1 but explicitly blocks the three most dangerous tools. If a bug in `allowed_tools` handling were to surface (as happened in SDK v0.1.5--v0.1.9, issue #361), this layer would still block the critical paths.

**Layer 3: Filesystem Permissions** (OS-enforced)
```
db_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)    # seed_demo_db.py:266
```
Even if the agent gained write tool access, the OS rejects writes at the filesystem level.

### Startup Validation Flow

```
provider.py:148  →  verify_read_only(config.db_path)
    │
    ▼
schema.py:222    →  verify_read_only(db_path)
    │
    ├── Opens SQLite connection (line 237)
    ├── Attempts: CREATE TABLE _claude_da_write_check (line 243)
    ├── If write succeeds → DROP TABLE, raise ConfigurationError (line 247)
    └── If write fails (expected) → return silently (line 250)
```

### SDK Bug History

The `allowed_tools` parameter was silently ignored in Agent SDK versions 0.1.5--0.1.9 (issue #361). This is why Claude-DA uses three layers rather than relying solely on the allowlist. The version is pinned to `>=0.1.30,<0.2.0` in `pyproject.toml`.

---

## Streaming Implementation

**Entry point**: `agent.py:320` `run_streaming(messages, result_holder)`.

**Chunk format** (yielded as dicts):

- Intermediate: `{"text": "...", "is_finished": False, "finish_reason": "", "index": 0, "tool_use": None}`
- Final: `{"text": "", "is_finished": True, "finish_reason": "stop", "index": 0, "tool_use": None, "usage": {...}}`

**Result accumulation**: uses a mutable container pattern. The caller passes a `list[AgentResult | None]` (always single-element). After the stream completes, `result_holder[0]` is set to the accumulated `AgentResult` (`agent.py:413`). This avoids needing to return a tuple from an `AsyncIterator`.

**Audit timing**: `provider.py:363-364` fires the audit task after the stream completes (when `result_holder[0]` is populated). This means audit entries are written after the client receives all chunks.

---

## Error Handling Chain

### Exception Hierarchy

```
Exception
  └── ClaudeDAError                      (base, line 9)
        ├── ConfigurationError           (startup errors, line 13)
        ├── InputValidationError         (400, line 17)
        ├── AgentTimeoutError            (504, line 24)
        ├── RateLimitError               (429, line 31)
        └── DatabaseUnavailableError     (503, line 38)
```

### Error Translation

`_handle_error()` at `provider.py:89-115` catches `ClaudeDAError` subclasses and translates them to `CustomLLMError` with OpenAI-compatible JSON bodies.

| Exception | HTTP Status | Error Code | Error Type |
|---|---|---|---|
| `InputValidationError` | 400 | `input_too_long` | `invalid_request_error` |
| `RateLimitError` | 429 | `rate_limited` | `rate_limit_error` |
| `DatabaseUnavailableError` | 503 | `database_unavailable` | `server_error` |
| `AgentTimeoutError` | 504 | `agent_timeout` | `server_error` |
| Other `ClaudeDAError` | 500 | `internal_error` | `server_error` |

Both `acompletion()` and `astreaming()` wrap their logic in `try/except ClaudeDAError` and delegate to `_handle_error()`.

---

## Audit System

### Entry Structure

Each request produces one `AuditEntry` (`audit.py:39`) containing:

| Field | Type | Description |
|---|---|---|
| `session_id` | str | UUID v4 |
| `timestamp` | str | ISO 8601 |
| `user_question` | str | Last message content from the request |
| `sql_queries_executed` | list[str] | All SQL queries the agent ran, in order |
| `query_results_summary` | list[dict] | Raw query results (omitted when `verbose=False`) |
| `final_response` | str | The agent's answer |
| `metadata` | AuditMetadata | model, tokens, cost, duration, tool_call_count |

### Logger Behaviour

`AuditLogger` (`audit.py:78`) supports three output modes via the `log_output` config:

- `"stdout"`: writes indented JSON to stdout
- `"file"`: appends JSONL to `log_file` via `asyncio.to_thread` (non-blocking)
- `"both"`: writes to both

When `verbose=False` (the default), `query_results_summary` is stripped from the output (line 110).

### Fire-and-Forget Pattern

`provider.py:216` `_fire_audit()` creates an `asyncio.Task` for the audit log call. A done callback (`_suppress_exception`, line 234) silently swallows any exceptions. Audit failures never affect the response to the client.

---

## Configuration System

### Environment Variables

All 9 variables are documented in [config.py module reference](#configpy) above. Key behaviour:

- `load_config()` (line 112) is the single entry point.
- `.env` file support via `python-dotenv` (`load_dotenv()` at module import, line 17).
- Fail-fast validation: missing `ANTHROPIC_API_KEY`, non-numeric int/float values, and invalid `log_output` values all raise `ConfigurationError` immediately.
- The returned `ClaudeDAConfig` is a frozen dataclass -- immutable after creation.

### Dotenv Support

The `.env.template` file in the project root provides a starting point. Copy to `.env`, set `ANTHROPIC_API_KEY`, and the config module picks it up automatically via `load_dotenv()`.

---

## Testing Architecture

### Framework

- **pytest** with **pytest-asyncio** (`asyncio_mode = "auto"` in `pyproject.toml:43`)
- Async test functions are detected and run automatically without explicit `@pytest.mark.asyncio`

### Unit Tests (8 files)

Located in `tests/unit/`. No external dependencies; all Agent SDK / MCP interactions are mocked.

| File | Module Under Test | What It Validates |
|---|---|---|
| `test_exceptions.py` | `exceptions.py` | Exception hierarchy, status_code/error_code class attributes |
| `test_config.py` | `config.py` | Env var parsing, defaults, validation errors for missing/invalid values |
| `test_schema.py` | `schema.py` | Schema discovery from a test SQLite DB, to_prompt_text format, verify_read_only |
| `test_prompt.py` | `prompt.py` | Prompt assembly, character limit enforcement, section presence |
| `test_audit.py` | `audit.py` | AuditEntry serialisation, logger output modes, non-blocking error handling |
| `test_agent.py` | `agent.py` | Message-to-prompt conversion, SQL extraction, timeout handling, streaming chunk format |
| `test_provider.py` | `provider.py` | Lazy init, input validation, error formatting, ModelResponse structure, singleton |
| `test_seed_demo_db.py` | `seed_demo_db.py` | Row counts, deterministic seeding, read-only permissions |

**Mock patterns**:
- Agent SDK mocks use custom dataclasses that mimic `AssistantMessage`, `TextBlock`, `ToolUseBlock`, `ResultMessage` to avoid importing the SDK in unit tests.
- `AsyncMock` for async Agent SDK calls.
- Provider tests bypass the real agent by mocking `DataAnalystAgent.run()` and `run_streaming()`.

### Integration Tests (6 files)

Located in `tests/integration/`. Require `ANTHROPIC_API_KEY` in the environment. Skipped automatically when the key is not set (via `pytest.mark.skipif`).

| File | What It Validates |
|---|---|
| `test_agent_smoke.py` | End-to-end: Agent SDK → MCP SQLite → query → response |
| `test_agent_streaming.py` | Streaming produces valid chunks with final stop chunk |
| `test_non_data.py` | Non-data questions handled conversationally (no tool calls) |
| `test_read_only.py` | Write attempts rejected by safety layers |
| `test_error_format.py` | Error responses match OpenAI-compatible format |
| `test_e2e_proxy.py` | Full LiteLLM proxy → provider → agent → MCP round-trip |

### Running Tests

```bash
# All unit tests (fast, no API key needed)
cd claude-litellm && uv run pytest tests/unit/ -v --tb=short

# All integration tests (requires ANTHROPIC_API_KEY)
cd claude-litellm && uv run pytest tests/integration/ -v --tb=short

# Full suite
cd claude-litellm && uv run pytest tests/ -v --tb=short
```

---

## Tooling Summary

### Development Tools

| Tool | Version Constraint | Config Location | Purpose |
|---|---|---|---|
| uv | latest | -- | Python package manager |
| ruff | `>=0.5` | `pyproject.toml:29-34` | Linter and formatter |
| mypy | `>=1.8` | `pyproject.toml:36-40` | Static type checker |
| pytest | `>=8.0` | `pyproject.toml:42-44` | Test runner |
| pytest-asyncio | `>=0.24` | `pyproject.toml:21` | Async test support |

### Ruff Configuration

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

Rules enabled: pycodestyle errors (E), pyflakes (F), isort (I), pep8-naming (N), pycodestyle warnings (W), pyupgrade (UP).

### Mypy Configuration

```toml
[tool.mypy]
python_version = "3.11"
strict = false
disallow_untyped_defs = true
check_untyped_defs = true
```

All functions must have type annotations (`disallow_untyped_defs`). Full strict mode is not enabled.

### Runtime Dependencies

| Package | Version Constraint | Purpose |
|---|---|---|
| `litellm` | `>=1.0,<2.0` | Proxy server and CustomLLM base class |
| `claude-agent-sdk` | `>=0.1.30,<0.2.0` | Claude Agent SDK for agentic queries |
| `python-dotenv` | `>=1.0` | Load `.env` files for configuration |

### LiteLLM Proxy Configuration

`litellm_config.yaml`:

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

The `custom_handler` value is a Python module path to the module-level singleton instance.

---

## Development Workflow

### Initial Setup

```bash
cd claude-litellm
uv sync                                    # Install all dependencies
uv run python scripts/seed_demo_db.py      # Create demo.db (chmod 444)
cp .env.template .env                      # Set ANTHROPIC_API_KEY in .env
```

### Start the Server

```bash
uv run litellm --config litellm_config.yaml
```

The server starts on `http://localhost:4000`. First request triggers lazy initialisation.

### Lint and Type Check

```bash
uv run ruff check src/ tests/             # Lint
uv run ruff format --check src/ tests/    # Format check
uv run mypy src/                          # Type check
```

### Run Tests

```bash
uv run pytest tests/unit/ -v --tb=short           # Unit tests only
uv run pytest tests/integration/ -v --tb=short     # Integration tests (needs API key)
uv run pytest tests/ -v --tb=short                 # Full suite
```

For usage examples (curl, Python SDK), see [../README.md](../README.md).
