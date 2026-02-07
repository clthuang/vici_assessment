# Tasks: Claude-DA

**Feature**: 001-claude-da
**Plan**: [plan.md](./plan.md)

---

## Phase 1: Project Scaffold + Foundations

### Group 1.1 — Scaffold (sequential)

- [ ] **T-001**: Create `claude-litellm/pyproject.toml` with src layout, Python >=3.11, runtime deps (`litellm>=1.0,<2.0`, `claude-agent-sdk>=0.1.30,<0.2.0`), dev deps (`pytest`, `pytest-asyncio`, `ruff`, `mypy`)
  - **Done when**: File exists with correct `[project]`, `[build-system]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` sections

- [ ] **T-002**: Create package init and test directories: `src/claude_da/__init__.py` (with `__version__ = "0.1.0"`), `tests/unit/`, `tests/integration/`, `tests/conftest.py` (with `pytest-asyncio` auto mode)
  - **Done when**: `uv sync && uv run python -c "from claude_da import __version__; print(__version__)"` prints `0.1.0`
  - **Depends on**: T-001

### Group 1.2 — Exceptions (sequential after 1.1)

- [ ] **T-003**: Implement `exceptions.py` — `ClaudeDAError` base, `ConfigurationError`, `InputValidationError` (400, `input_too_long`), `AgentTimeoutError` (504, `agent_timeout`), `RateLimitError` (429, `rate_limited`), `DatabaseUnavailableError` (503, `database_unavailable`). Each with `status_code` and `error_code` class attributes.
  - **Done when**: Module importable, all 5 subclasses exist with correct attributes
  - **Depends on**: T-002

- [ ] **T-004**: Write unit tests for exceptions — verify inheritance chain (`isinstance(ConfigurationError(), ClaudeDAError)`), verify `status_code` and `error_code` attributes on each exception, verify `str()` works
  - **Done when**: `uv run pytest tests/unit/test_exceptions.py -v` passes
  - **Depends on**: T-003

### Group 1.3 — Config (sequential after 1.2)

- [ ] **T-005**: Implement `config.py` — `ClaudeDAConfig` frozen dataclass (9 fields per spec REQ-07), `load_config()` function, `_get_int_env()`, `_get_float_env()`, `_get_bool_env()` helpers. Validate `ANTHROPIC_API_KEY` required, numeric parsing, `log_output` enum (`stdout`|`file`|`both`).
  - **Done when**: `load_config()` returns correct dataclass with defaults when only `ANTHROPIC_API_KEY` is set
  - **Depends on**: T-003

- [ ] **T-006**: Write unit tests for config — test defaults applied, env var overrides for each field, missing `ANTHROPIC_API_KEY` raises `ConfigurationError`, invalid numeric (`CLAUDE_DA_MAX_TURNS=abc`) raises `ConfigurationError`, invalid `log_output` raises `ConfigurationError`
  - **Done when**: `uv run pytest tests/unit/test_config.py -v` passes (6+ test cases)
  - **Depends on**: T-005

### Group 1.4 — Audit (sequential after 1.3)

- [ ] **T-007**: Implement `audit.py` — `AuditMetadata` and `AuditEntry` dataclasses, `AuditLogger` class with `async def log(entry)` method. Stdout outputs JSON, file outputs JSONL via `asyncio.to_thread()`. Internal try/except catches all errors, logs to stderr.
  - **Done when**: `AuditLogger(config).log(entry)` writes valid JSON to stdout and/or valid JSONL to file depending on config
  - **Depends on**: T-005

- [ ] **T-008**: Write unit tests for audit — JSON serialization round-trip, stdout output is valid JSON, file output creates valid JSONL (one object per line), stderr logged on write failure (mock file I/O error), verbose mode includes full results, summary mode omits them
  - **Done when**: `uv run pytest tests/unit/test_audit.py -v` passes (5+ test cases)
  - **Depends on**: T-007

**Phase 1 gate**: `uv run pytest tests/unit/ -v` — all tests pass.

---

## Phase 2: Schema + Prompt

### Group 2.1 — Demo Database (sequential)

- [ ] **T-009**: Create `scripts/seed_demo_db.py` — schema creation (4 tables from spec Section 3: customers, products, orders, order_items with correct types, constraints, and FKs), data population (50+ customers, 20+ products, 200+ orders, 500+ order items distributed across 6+ months), `chmod 444` as final step. Idempotent (delete + recreate if exists).
  - **Done when**: Running `uv run python scripts/seed_demo_db.py` creates `demo.db` with read-only permissions, correct table count, and minimum data counts
  - **Depends on**: T-002

- [ ] **T-010**: Write unit test for seeder — runs idempotently (run twice, no error), output file is read-only (`os.access(path, os.W_OK)` returns False), data counts meet minimums (query each table), orders span 6+ distinct months
  - **Done when**: `uv run pytest tests/unit/test_seed_demo_db.py -v` passes
  - **Depends on**: T-009

### Group 2.2 — Schema Discovery (sequential after 2.1)

- [ ] **T-011**: Implement `schema.py` — `ColumnInfo`, `ForeignKey`, `TableSchema`, `DatabaseSchema` dataclasses per design Section 2.3
  - **Done when**: All 4 dataclasses importable with correct fields
  - **Depends on**: T-003

- [ ] **T-012**: Implement `discover_schema(db_path)` in `schema.py` — open read-only SQLite (`?mode=ro`), query `sqlite_master` for table names, `PRAGMA table_info` for columns, `PRAGMA foreign_key_list` for FKs. Raise `ConfigurationError` if DB cannot be opened or schema is empty.
  - **Done when**: `discover_schema(test_db)` returns `DatabaseSchema` with correct tables, columns, types, and FK relationships; raises `ConfigurationError` on nonexistent file
  - **Depends on**: T-011

- [ ] **T-013**: Implement `verify_read_only(db_path)` in `schema.py` — attempt `CREATE TABLE _claude_da_write_check (id INTEGER)`, verify it fails. If write succeeds, raise `ConfigurationError("Database is not read-only. Refusing to start.")`.
  - **Done when**: Returns silently on `chmod 444` file; raises `ConfigurationError` on writable file
  - **Depends on**: T-011

- [ ] **T-014**: Implement `DatabaseSchema.to_prompt_text()` — human-readable schema text showing table names, columns (name, type, PK, nullable), and foreign key relationships. Designed for LLM consumption.
  - **Done when**: Output is readable text listing all tables/columns/types/FKs, under 8K chars for 4 tables (leaving room for role/rules in the 12K total prompt)
  - **Depends on**: T-011

- [ ] **T-015**: Write unit tests for schema — pytest fixture creates temp DB with 4-table schema and few rows. Tests: `discover_schema` finds 4 tables with correct columns/types/FKs, `to_prompt_text` output is readable and under 8K chars, `verify_read_only` passes on read-only file, `verify_read_only` raises on writable file, `discover_schema` raises on nonexistent file.
  - **Done when**: `uv run pytest tests/unit/test_schema.py -v` passes (5+ test cases)
  - **Depends on**: T-012, T-013, T-014

### Group 2.3 — Prompt Assembly (sequential after 2.2)

- [ ] **T-016**: Implement `prompt.py` — `build_system_prompt(schema: DatabaseSchema) -> str`. Assembles: (1) role definition (data analyst for internal use), (2) schema from `schema.to_prompt_text()`, (3) behavioral rules (explain insights, note trends, limit results), (4) read-only instructions, (5) non-data question handling. Raise `ConfigurationError` if total exceeds 12,000 chars.
  - **Done when**: Returns complete prompt string under 12K chars for demo schema
  - **Depends on**: T-014

- [ ] **T-017**: Write unit tests for prompt — prompt contains all required sections (role, schema, rules, read-only, non-data), total under 12K chars, raises `ConfigurationError` on oversized schema (mock a huge schema)
  - **Done when**: `uv run pytest tests/unit/test_prompt.py -v` passes (3+ test cases)
  - **Depends on**: T-016

**Phase 2 gate**: `uv run pytest tests/unit/ -v` — all Phase 1 + 2 tests pass.

---

## Phase 3: Agent SDK Integration

### Group 3.1 — Agent Core (sequential)

- [ ] **T-018**: Implement `_messages_to_prompt()` in `agent.py` — system messages skipped, single user message used directly, multi-turn formatted as `User: {content}\nAssistant: {content}\nUser: {content}`
  - **Done when**: Correctly converts single message, multi-turn, and filters system messages
  - **Depends on**: T-005

- [ ] **T-019**: Implement `AgentResult` and `AgentResultMetadata` dataclasses in `agent.py` per design Section 2.6
  - **Done when**: Both dataclasses importable with correct fields (response_text, sql_queries, query_results, metadata)
  - **Depends on**: T-003

- [ ] **T-020**: Implement `DataAnalystAgent.__init__()` in `agent.py` — store config and system_prompt
  - **Done when**: Constructor accepts `ClaudeDAConfig` and `str`, stores as instance attributes
  - **Depends on**: T-005, T-019

- [ ] **T-021**: Implement `DataAnalystAgent.run()` in `agent.py` — build `ClaudeAgentOptions` (system_prompt, model, max_turns, max_budget_usd, mcp_servers as plain dict, allowed_tools `["mcp__sqlite__*"]`, disallowed_tools `["Bash", "Write", "Edit"]`, permission_mode `"bypassPermissions"`), wrap `query()` in `asyncio.wait_for(timeout=240)`, iterate messages (accumulate text from AssistantMessage, capture SQL from tool use blocks matching `mcp__sqlite__*`, capture query results from tool result messages, extract metadata from ResultMessage with null-safe usage handling), return `AgentResult`. Map `asyncio.TimeoutError` → `AgentTimeoutError`, SDK errors → appropriate exceptions. **Note**: The spec's `query_timeout` error code (30s MCP timeout) is handled natively by the MCP server within the agent loop (design Section 1.5) — no separate provider-level exception is needed.
  - **Done when**: Method exists with complete implementation; unit test with mocked SDK passes
  - **Depends on**: T-018, T-019, T-020

- [ ] **T-022**: Write unit tests for agent core — `_messages_to_prompt` (single msg, multi-turn, system filtered), `DataAnalystAgent` construction with mock config, `run()` with mocked `query()` returning mock AssistantMessage + ResultMessage sequences, verify AgentResult contains correct text/sql/metadata. Test timeout mapping.
  - **Done when**: `uv run pytest tests/unit/test_agent.py -v` passes (5+ test cases)
  - **Depends on**: T-021

- [ ] **T-023**: Write integration test for agent smoke test — `DataAnalystAgent.run()` with real API key against demo.db, ask "How many customers are there?", verify response contains a number, verify `sql_queries` is non-empty, verify metadata has cost/duration
  - **Done when**: `uv run pytest tests/integration/test_agent_smoke.py -v` passes (skipped if no API key)
  - **Depends on**: T-021, T-009

### Group 3.2 — Agent Streaming (sequential after 3.1)

- [ ] **T-024**: Implement `DataAnalystAgent.run_streaming()` in `agent.py` — async generator yielding `GenericStreamingChunk` dicts (`text`, `is_finished`, `finish_reason`, `index`, `tool_use: None`). Intermediate chunks: `is_finished=False`. Final chunk: `is_finished=True`, `finish_reason="stop"`, `usage` from ResultMessage (null-safe). Accumulates AgentResult in passed-in `result_holder` list.
  - **Done when**: Method exists with complete implementation
  - **Depends on**: T-021

- [ ] **T-025**: Write unit tests for streaming — mock Agent SDK messages, verify chunk sequence (intermediate chunks have text, final chunk has `is_finished=True`), verify result_holder populated with AgentResult after iteration
  - **Done when**: `uv run pytest tests/unit/test_agent.py::TestStreaming -v` passes
  - **Depends on**: T-024

- [ ] **T-026**: Write integration test for streaming — stream a data question, verify chunks arrive, final chunk has `is_finished=True` and `finish_reason="stop"`
  - **Done when**: `uv run pytest tests/integration/test_agent_streaming.py -v` passes (skipped if no API key)
  - **Depends on**: T-024, T-009

**Phase 3 gate (critical)**: Integration smoke tests pass. If they fail, fall back to CLI subprocess approach.

---

## Phase 4: LiteLLM Provider

### Group 4.1 — Provider Structure (sequential)

- [ ] **T-027**: Implement `ClaudeDAProvider(CustomLLM)` in `provider.py` — `__init__` (sets `_initialized=False`, `_init_lock`, `_init_error=None`), `_ensure_initialized()` with double-check locking (load config, discover schema, verify read-only, build prompt, create agent + audit logger; on failure cache error in `_init_error`), `completion()` and `streaming()` → `raise NotImplementedError`, `_handle_error()` translates `ClaudeDAError` → `CustomLLMError` with OpenAI error JSON format. Module-level instance: `claude_da_provider = ClaudeDAProvider()`.
  - **Done when**: Module importable, `claude_da_provider` is `CustomLLM` instance, sync methods raise `NotImplementedError`
  - **Depends on**: T-021, T-016, T-012, T-013, T-007

- [ ] **T-028**: Write unit tests for provider structure — `claude_da_provider` is `CustomLLM` subclass, `completion()` raises `NotImplementedError`, `streaming()` raises `NotImplementedError`, `_handle_error()` produces correct OpenAI error JSON for each exception type, init failure is cached (second call returns same error without retrying)
  - **Done when**: `uv run pytest tests/unit/test_provider.py -v` passes (5+ test cases)
  - **Depends on**: T-027

### Group 4.2 — acompletion (parallel with 4.3, after 4.1)

- [ ] **T-029**: Implement `acompletion()` in `provider.py` — `_ensure_initialized()`, validate input length (`InputValidationError` if exceeded), call `agent.run(messages)`, format as `ModelResponse` (set `choices[0].message.content`), fire-and-forget `asyncio.create_task(audit.log(...))` with `task.add_done_callback()` for exception suppression
  - **Done when**: Method handles full request lifecycle
  - **Depends on**: T-027

- [ ] **T-030**: Write unit tests for acompletion — oversized input returns 400 with correct JSON body, mock `agent.run()` → valid `ModelResponse` with `choices[0].message.content`, audit task is created (mock audit logger)
  - **Done when**: `uv run pytest tests/unit/test_provider.py::TestAcompletion -v` passes
  - **Depends on**: T-029

### Group 4.3 — astreaming (parallel with 4.2, after 4.1)

- [ ] **T-031**: Implement `astreaming()` in `provider.py` — `_ensure_initialized()`, validate input length, create `result_holder = [None]`, call `agent.run_streaming(messages, result_holder)`, yield all chunks, after iteration fire-and-forget audit log from `result_holder[0]`
  - **Done when**: Method yields chunks and triggers audit after final chunk
  - **Depends on**: T-027

- [ ] **T-032**: Write unit tests for astreaming — mock streaming returns valid chunk sequence ending with `is_finished=True`, audit log receives accumulated result from result_holder, oversized input returns 400
  - **Done when**: `uv run pytest tests/unit/test_provider.py::TestAstreaming -v` passes
  - **Depends on**: T-031

### Group 4.4 — LiteLLM Config (after 4.2 + 4.3)

- [ ] **T-033**: Create `litellm_config.yaml` — `model_list` with `claude-da/analyst`, `litellm_settings.custom_provider_map` pointing to `claude_da.provider.claude_da_provider`
  - **Done when**: File exists with correct YAML structure matching design Section 2.8
  - **Depends on**: T-029, T-031

- [ ] **T-034**: Write integration test for end-to-end proxy — start LiteLLM proxy with config, send POST to `/v1/chat/completions` with a data question, verify response is valid ChatCompletion JSON
  - **Done when**: `uv run pytest tests/integration/test_e2e_proxy.py -v` passes (skipped if no API key)
  - **Depends on**: T-033

**Phase 4 gate**: End-to-end test passes via LiteLLM proxy endpoint.

---

## Phase 5: Demo + Documentation

### Group 5.1 — README (sequential)

- [ ] **T-035**: Create `README.md` — quick start (3 commands: `uv sync`, `uv run python scripts/seed_demo_db.py`, `uv run litellm --config litellm_config.yaml`), env vars table (9 vars with defaults), example curl (non-streaming + streaming), architecture overview paragraph with link to design.md
  - **Done when**: README contains all 4 sections, commands are copy-pasteable
  - **Depends on**: T-033

### Group 5.2 — Integration Tests Finalization (sequential after 5.1)

- [ ] **T-036**: Write integration test for non-data question — send "What's 2+2?" via provider, verify response is conversational, verify no SQL queries in audit result
  - **Done when**: `uv run pytest tests/integration/test_non_data.py -v` passes (skipped if no API key)
  - **Depends on**: T-029

- [ ] **T-037**: Write integration test for read-only enforcement — verify agent cannot execute write operations via MCP SQLite, `chmod 444` blocks writes at OS level
  - **Done when**: `uv run pytest tests/integration/test_read_only.py -v` passes (skipped if no API key)
  - **Depends on**: T-029, T-009

- [ ] **T-038**: Write integration test for error response format — send oversized input, verify HTTP 400 with OpenAI error JSON format (`error.message`, `error.type`, `error.code`)
  - **Done when**: `uv run pytest tests/integration/test_error_format.py -v` passes
  - **Depends on**: T-029

### Group 5.3 — CI (sequential after 5.2)

- [ ] **T-039**: Add `claude-litellm` job to `.github/workflows/ci.yml` — lint (ruff check + mypy), unit tests (no API key), integration tests skipped in CI
  - **Done when**: CI workflow runs lint + unit tests for claude-litellm package; integration tests are gracefully skipped
  - **Depends on**: T-038

**Phase 5 gate**: Reviewer can clone, run 3 commands, and ask data questions.

---

## Summary

| Phase | Tasks | Groups |
|---|---|---|
| 1: Scaffold + Foundations | T-001 – T-008 (8 tasks) | 4 sequential groups (1.1→1.2→1.3→1.4) |
| 2: Schema + Prompt | T-009 – T-017 (9 tasks) | 3 groups (2.1 ∥ 2.2 start, merge at T-015, then 2.3) |
| 3: Agent SDK | T-018 – T-026 (9 tasks) | 2 sequential groups (3.1→3.2) |
| 4: LiteLLM Provider | T-027 – T-034 (8 tasks) | 3 groups (4.1, then 4.2 ∥ 4.3, then 4.4) |
| 5: Demo + Docs | T-035 – T-039 (5 tasks) | 3 sequential groups (5.1→5.2→5.3) |
| **Total** | **39 tasks** | **1 parallel pair (4.2 ∥ 4.3)** |
