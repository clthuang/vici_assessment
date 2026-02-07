# Implementation Plan: Claude-DA

**Feature**: 001-claude-da
**Design**: [design.md](./design.md)

---

## Build Order

Implementation follows the dependency chain bottom-up: foundations first, then each layer that depends on them. Each phase produces testable artifacts before the next begins.

```
Phase 1: Project Scaffold + Foundations (no external deps)
    ↓
Phase 2: Schema + Prompt (SQLite only, no Agent SDK)
    ↓
Phase 3: Agent SDK Integration (requires ANTHROPIC_API_KEY)
    ↓
Phase 4: LiteLLM Provider (wires everything together)
    ↓
Phase 5: Demo + Documentation
```

---

## Phase 1: Project Scaffold + Foundations

**Goal**: Runnable project with config, exceptions, and audit — all unit-testable with zero external services.

### 1.1 Project scaffold
- Create `claude-litellm/pyproject.toml`:
  - Runtime dependencies: `litellm>=1.0,<2.0`, `claude-agent-sdk>=0.1.30,<0.2.0`
  - Dev dependencies: `pytest`, `pytest-asyncio`, `ruff`, `mypy` (matching subterminator's toolchain)
  - Upper bounds prevent automatic breakage from API-unstable v0.1.x Agent SDK and major LiteLLM changes
- Create `claude-litellm/src/claude_da/__init__.py` with `__version__`
- Create `claude-litellm/tests/unit/` and `claude-litellm/tests/integration/` directories
- Create `claude-litellm/tests/conftest.py` with pytest-asyncio config
- Verify: `uv sync && uv run python -c "import claude_da"`

### 1.2 exceptions.py
- Implement `ClaudeDAError` base class
- Implement `ConfigurationError`, `InputValidationError` (400), `AgentTimeoutError` (504), `RateLimitError` (429), `DatabaseUnavailableError` (503)
- Each with `status_code` and `error_code` class attributes
- **Test**: Verify all exceptions have correct attributes, inheritance chain

### 1.3 config.py
- Implement `ClaudeDAConfig` frozen dataclass (9 fields)
- Implement `load_config()` with `_get_int_env`, `_get_float_env`, `_get_bool_env` helpers
- Validate: `ANTHROPIC_API_KEY` required, numeric parsing, `log_output` enum
- **Test**: Defaults applied, env var overrides, missing key → `ConfigurationError`, invalid numeric → `ConfigurationError`

### 1.4 audit.py
- Implement `AuditEntry` and `AuditMetadata` dataclasses
- Implement `AuditLogger` class with async `log()` method
- Output to stdout (JSON), file (JSONL via `asyncio.to_thread`), or both
- Internal error handling: catch all exceptions, log to stderr
- **Test**: JSON serialization round-trip, file output creates valid JSONL, stderr on write failure, verbose vs. summary mode

**Phase 1 gate**: `uv run pytest tests/unit/ -v` passes, all foundations tested.

---

## Phase 2: Schema + Prompt

**Goal**: Schema discovery from real SQLite DB, system prompt assembly, and demo database — all testable without Agent SDK.

### 2.1 Demo database seeder (scripts/seed_demo_db.py)
- Create e-commerce schema (4 tables from spec Section 3)
- Populate: 50+ customers, 200+ orders, 500+ order items across 6+ months
- Script sets `chmod 444` on output file as its final step
- Do **not** commit `demo.db` to the repo — git does not preserve file permissions beyond the executable bit, so `chmod 444` would be lost after clone. Instead, the seeder script is run as a setup step: `uv run python scripts/seed_demo_db.py`
- The README quick start includes this as one of the 3 setup commands
- **Test**: Script runs idempotently, file is read-only after script, data counts meet minimums

### 2.2 schema.py
- Implement `ColumnInfo`, `ForeignKey`, `TableSchema`, `DatabaseSchema` dataclasses
- Implement `discover_schema(db_path)`: open read-only SQLite, query `sqlite_master` + `PRAGMA table_info` + `PRAGMA foreign_key_list`
- Implement `verify_read_only(db_path)`: attempt write, confirm failure
- Implement `DatabaseSchema.to_prompt_text()`: human-readable schema for LLM
- **Test**: Use a pytest fixture that creates a minimal test DB (4 tables, few rows) in a temp directory — does not depend on the seeder script for unit test isolation. Verify 4 tables with correct columns/types/FKs, `to_prompt_text` output is readable and under 12K chars, `verify_read_only` passes on read-only file and raises on writable file

### 2.3 prompt.py
- Implement `build_system_prompt(schema)`: role + schema + rules + read-only instructions + non-data handling
- Validate total size under 12,000 characters
- **Test**: Prompt contains all required sections, under char limit, raises `ConfigurationError` if exceeded

**Phase 2 gate**: Schema discovery + prompt assembly tested against real `demo.db`.

---

## Phase 3: Agent SDK Integration

**Goal**: Working agent that queries the database and returns structured results. This is the pre-implementation smoke test from the PRD.

### 3.1 agent.py — core
- Implement `_messages_to_prompt()`: OpenAI messages → single prompt string
  - **System messages**: Skipped (handled separately via `ClaudeAgentOptions.system_prompt`)
  - **Single user message** (most common for MVP): Use `content` directly as the prompt string
  - **Multi-turn history**: Format as labeled turns preserving role boundaries:
    ```
    User: {content}
    Assistant: {content}
    User: {content}
    ```
  - **Limitation**: The Agent SDK `query()` accepts `prompt: str`, not a messages array. Multi-turn formatting is a best-effort text serialization — role boundaries are preserved as labels but the SDK does not process them as structured turns. For the MVP (stateless, no conversation memory), the typical case is a single user message. This satisfies AC-01.8 (full history forwarded) within the SDK's constraints.
- Implement `DataAnalystAgent.__init__()`: store config and system prompt
- Implement `DataAnalystAgent.run()`:
  - Build `ClaudeAgentOptions`:
    - `system_prompt`: the data analyst prompt (built at init time)
    - `model`, `max_turns`, `max_budget_usd`: from config
    - `mcp_servers`: plain dict matching `McpStdioServerConfig` schema: `{"sqlite": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-sqlite", db_path]}}`. Use dict literals, not imported TypedDict constructors — this is the pattern shown in all official SDK examples.
    - `allowed_tools`: `["mcp__sqlite__*"]`
    - `disallowed_tools`: `["Bash", "Write", "Edit"]`
    - `permission_mode`: `"bypassPermissions"` — required for headless server operation. Without this, the SDK prompts for interactive approval on tool calls, which would hang in the LiteLLM proxy context. Security is enforced by the three-layer safety architecture (allowed_tools, disallowed_tools, filesystem permissions), not by interactive permission prompts.
  - Wrap `query()` in `asyncio.wait_for(timeout=240)`
  - Iterate `AsyncIterator[Message]`:
    - `AssistantMessage` with text → accumulate response text
    - `AssistantMessage` with tool use → capture SQL from tool use blocks (match tool names `mcp__sqlite__read_query`, `mcp__sqlite__list_tables`, `mcp__sqlite__describe-table`; extract SQL from `input` dict)
    - Tool result messages → capture query results (row data, column names) and store in `AgentResult.query_results` for verbose audit logging (AC-06.6)
    - `ResultMessage` → extract `total_cost_usd`, `usage`, `duration_ms`, `num_turns` into `AgentResultMetadata`
  - Return `AgentResult`
- Exception mapping: `asyncio.TimeoutError` → `AgentTimeoutError`, SDK errors → appropriate exceptions
- **Test (unit)**: `_messages_to_prompt` conversion (single message, multi-turn, system message filtering). Agent construction with mock config.
- **Test (integration, requires API key)**: Smoke test — ask "How many customers are there?" against demo.db, verify response contains a number, verify SQL was captured in result.

### 3.2 agent.py — streaming
- Implement `DataAnalystAgent.run_streaming()`:
  - Returns an async generator that yields `GenericStreamingChunk` dicts (LiteLLM expects TypedDict-compatible dicts with `text`, `is_finished`, `finish_reason`, `index` keys)
  - Intermediate chunks: `{"text": "...", "is_finished": False, "finish_reason": "", "index": 0}`
  - Final chunk: `{"text": "", "is_finished": True, "finish_reason": "stop", "index": 0, "usage": {...}}`
  - Internally accumulates SQL queries and metadata during iteration. After yielding the final chunk, stores the `AgentResult` on a passed-in container (e.g., a single-element list) so the caller (`astreaming`) can access it for audit logging
  - **Note**: `astreaming()` must return `AsyncIterator[GenericStreamingChunk]`, not a tuple. The agent's streaming method wraps iteration internally and exposes the accumulated result via a side-channel (mutable container or callback), not a Future return value
- **Test (unit)**: Mock Agent SDK messages, verify chunk format, verify accumulated result contains correct metadata.
- **Test (integration)**: Stream a data question, verify chunks arrive, final chunk has `is_finished=True`.

**Phase 3 gate**: Integration smoke test passes — Agent SDK → MCP SQLite → query → response. This is the PRD pre-implementation gate.

---

## Phase 4: LiteLLM Provider

**Goal**: Full OpenAI-compatible endpoint accessible via LiteLLM proxy.

### 4.1 provider.py — structure
- Implement `ClaudeDAProvider(CustomLLM)` with lazy initialization (`_ensure_initialized` with `asyncio.Lock`)
  - On initialization failure: set `self._init_error` to the exception. All subsequent requests immediately return the cached error (503 for config/DB errors) without retrying initialization. This prevents cascading failures from repeated init attempts.
- Implement `completion()` and `streaming()` → `raise NotImplementedError`
- Implement `_handle_error()`: translate `ClaudeDAError` → `CustomLLMError`
- Module-level instance: `claude_da_provider = ClaudeDAProvider()`
- **Test (unit)**: Instance is `CustomLLM` subclass, sync methods raise `NotImplementedError`, error handler produces correct JSON format, init failure is cached

### 4.2 provider.py — acompletion
- Implement `acompletion()`:
  - `_ensure_initialized()`
  - Validate input length → `InputValidationError` if exceeded
  - Call `agent.run(messages)`
  - Format as `ModelResponse`
  - Fire-and-forget `asyncio.create_task(audit.log(...))` — the audit task's internal try/except (in `AuditLogger.log()`) suppresses all exceptions. Additionally, add a `task.add_done_callback()` that catches and logs any unexpected exceptions to stderr, preventing "Task exception was never retrieved" warnings.
- **Test (unit)**: Oversized input → 400 error with correct JSON. Mock agent.run → valid ModelResponse format.
- **Test (integration)**: Full request through provider → data insight response.

### 4.3 provider.py — astreaming
- Implement `astreaming()`:
  - `_ensure_initialized()`
  - Validate input length
  - Create a result container (e.g., `result_holder = [None]`)
  - Call `agent.run_streaming(messages, result_holder)` which returns an `AsyncIterator[GenericStreamingChunk]`
  - Yield all chunks from the iterator
  - After iteration completes (final `is_finished=True` chunk yielded), the result_holder contains the accumulated `AgentResult`. Fire-and-forget audit log using `asyncio.create_task(audit.log(...))`.
- **Test (unit)**: Mock streaming → valid chunk sequence ending with `is_finished=True`, audit log receives accumulated result.
- **Test (integration)**: Full streaming request → SSE chunks → final stop chunk.

### 4.4 litellm_config.yaml
- Create sample proxy configuration with `custom_provider_map`
- **Test (integration)**: Start proxy with config, send request to `/v1/chat/completions`, verify response.

**Phase 4 gate**: End-to-end test passes via LiteLLM proxy endpoint.

---

## Phase 5: Demo + Documentation

**Goal**: Zero-friction setup for reviewers.

### 5.1 README.md
- Quick start (3 commands: `uv sync`, `uv run python scripts/seed_demo_db.py`, `uv run litellm --config litellm_config.yaml`)
- Environment variables table
- Example curl requests (non-streaming and streaming)
- Architecture overview (1 paragraph + link to design.md)

### 5.2 Integration test suite finalization
- Non-data question test (no tool calls)
- Read-only enforcement test: validates that `mcp__sqlite__*` wildcard matches `write_query` (so Layer 1 alone does not block writes), but `chmod 444` filesystem permissions (Layer 3) prevent the write. This tests the defense-in-depth design.
- Error response format test (verify OpenAI error JSON)

### 5.3 CI extension
- Add `claude-litellm` job to `.github/workflows/ci.yml`
- Lint (ruff + mypy) and unit tests (no API key needed)
- Integration tests skipped in CI (no `ANTHROPIC_API_KEY`)

**Phase 5 gate**: Reviewer can clone, run 3 commands, and ask data questions.

---

## Dependencies

```
1.1 scaffold ──► 1.2 exceptions ──► 1.3 config ──► 1.4 audit
                       │                  │
                       │                  ▼
                       │   2.1 demo DB ──► 2.2 schema ──► 2.3 prompt
                       │                                      │
                       └──────────────────────────────────────┘ (exceptions used by schema, prompt)
                                                              │
                                                              ▼
                                                 3.1 agent core ──► 3.2 agent streaming
                                                                           │
                                                                           ▼
                                                  4.1 provider structure ──┬──► 4.2 acompletion ──┬──► 4.4 litellm config
                                                                           │                       │
                                                                           └──► 4.3 astreaming ───┘
                                                                                                        │
                                                                                                        ▼
                                                                                    5.1 README ──► 5.2 tests ──► 5.3 CI
```

Notes:
- `schema.py` depends on `config.py` (for `db_path`) and `exceptions.py` (for `ConfigurationError`). `prompt.py` depends on `exceptions.py` (for `ConfigurationError` on size limit exceeded). These cross-edges are implicit in the phase ordering.
- 4.2 (acompletion) and 4.3 (astreaming) are **independent** — both depend on 4.1 but not on each other. They can be implemented in parallel. 4.4 (litellm config) depends on both.

## Risk Mitigation Checkpoints

| Checkpoint | When | What | Fail action |
|---|---|---|---|
| Phase 1 gate | After 1.4 | Config, exceptions, audit all pass unit tests | Fix before proceeding |
| Phase 2 gate | After 2.3 | Schema discovery + prompt from real demo.db | Fix before proceeding |
| **Phase 3 gate (critical)** | After 3.2 | Agent SDK smoke test (core + streaming) with live API | Fall back to CLI subprocess approach (applies to both core and streaming paths) |
| Phase 4 gate | After 4.4 | End-to-end via LiteLLM proxy | Debug provider wiring |
| Phase 5 gate | After 5.3 | Reviewer can run 3 commands and query data | Fix README/setup |
