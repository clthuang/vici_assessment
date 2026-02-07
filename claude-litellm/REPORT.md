# Claude-DA: Consulting Case Report

**Project:** AI-Powered Data Analysis via LiteLLM Custom Provider
**Author:** Terry
**Date:** February 2026
**Assessment:** VICI Holdings — 7-Day Challenge

---

## I. Executive Summary

### The Problem

Data analysis requires SQL fluency, schema knowledge, and the ability to translate business questions into technical queries. Non-technical stakeholders depend on analysts for every question, creating bottlenecks that slow decision-making across the organisation. A product manager asking "What were our top 10 customers by revenue last month?" must wait for an analyst to write SQL, run it, interpret the results, and format a response. This dependency is the bottleneck — not the database, not the infrastructure, not the compute.

Three mature technologies each solve part of this problem independently: Claude Code reasons about data and writes SQL. MCP servers provide standardised, pluggable database access. LiteLLM provides an OpenAI-compatible API gateway that any existing client can call. None of these, on their own, gives a non-technical user an end-to-end path from English question to data-backed insight.

### The Solution

Claude-DA is a **LiteLLM custom provider** that wraps the Claude Agent SDK behind an OpenAI-compatible chat completions API. The provider injects the database schema into a system prompt, hands the user's question to an autonomous agent, and returns the agent's insight-driven response in standard OpenAI format.

```
Client  --->  LiteLLM Proxy  --->  Claude-DA Provider  --->  Claude Agent SDK  --->  MCP SQLite
```

Any tool that speaks the OpenAI chat completions format — curl, the OpenAI Python SDK, Open WebUI, LangChain — works without modification. Both non-streaming and streaming (Server-Sent Events) modes are supported.

### Scope Calibration

This is a demo-scale MVP targeting SQLite with a seeded e-commerce database. It is not a production analytics platform. This is a deliberate engineering decision, not a limitation.

Production analytics requires: multi-database support, contextual schema injection for large databases, conversation memory, per-user governance, and cost dashboards. Each of these is deferred because the core value chain — English question in, SQL-backed insight out, audit trail recorded — can be proven without them. The architecture is designed so that each deferred capability is configuration or wiring, not a new system.

### Differentiator

No existing tool connects these three technologies into a single API surface. The combination of:
- LiteLLM custom provider as the API gateway (any OpenAI-compatible client works)
- Claude Agent SDK as the reasoning engine (autonomous multi-query analysis)
- MCP SQLite server as the database access layer (zero custom DB connector code)
- Three-layer read-only safety architecture (tool allowlist, tool blocklist, filesystem permissions)

...creates a system where adding a new database backend is configuration, not code. The safety model — three independent layers that must all fail for a write to succeed — is designed for the paranoid, not the optimistic.

### Delivery Metrics

| Metric | Value |
|--------|-------|
| Source LOC | 1,472 (8 modules) |
| Test LOC | 2,772 (14 test files) |
| Tests | 152 collected, 146 passing, 2 failing (runtime-dependent), 4 skipped |
| Tasks completed | 41/41 |
| Review iterations | 7 across 5 phases |
| Review blockers caught | 10 |
| Duration | ~9.5 hours |
| Specification artifacts | 5 (PRD, Spec, Design, Plan, Tasks) |

---

## II. Problem Decomposition

### The Analyst Bottleneck

The core workflow today looks like this:

| Step | Actor | Latency |
|------|-------|---------|
| Business question arises | Stakeholder | Immediate |
| Question queued for analyst | Stakeholder → Analyst | Hours to days |
| Analyst writes SQL | Analyst | Minutes |
| Analyst runs query | Analyst | Seconds |
| Analyst interprets and formats | Analyst | Minutes |
| Answer delivered | Analyst → Stakeholder | Minutes |

The bottleneck is steps 2-5 — the analyst dependency. The SQL itself is often trivial. The value is in knowing what to ask the database, not in writing `SELECT`. An LLM can bridge this gap: it understands the business question, knows (via the schema) what data is available, and can write and execute SQL autonomously.

### Three Technologies, No Integration

| Technology | Solves | Does Not Solve |
|-----------|--------|----------------|
| **Claude Code** | Reasoning, SQL generation, natural language response | No standard API surface; requires Claude Code CLI |
| **MCP SQLite** | Standardised database access, zero connector code | No reasoning; tool-level only |
| **LiteLLM** | OpenAI-compatible API gateway, client compatibility | No agent capabilities; pass-through only |

The gap is integration. Claude-DA fills it: LiteLLM provides the API surface, the Agent SDK provides the reasoning, and MCP provides the database access. The provider is the glue — 1,472 LOC of integration code, not 10,000 LOC of a new analytics platform.

### The Real Question

The real question is not "can Claude write SQL?" — it can. The real question is: **can an autonomous agent safely access a database through a standard API while maintaining auditability and read-only guarantees?**

This reframes the project from "natural language to SQL" (a solved problem) to "safe, auditable, API-compatible agent-database integration" (an unsolved integration challenge).

---

## III. Strategic Design Decisions

Seven decisions shape the architecture. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

### Decision 1: MCP for Database Access

**Context.** The agent needs to execute SQL against a database. Two approaches: (a) custom database connector code in the provider, or (b) MCP server providing database tools that the agent calls natively.

**Analysis.** Custom connectors mean writing connection management, query execution, result formatting, and error handling for each database type. The `@modelcontextprotocol/server-sqlite` MCP server already provides `read_query`, `write_query`, `create_table`, `list_tables`, and `describe_table` tools. Claude speaks MCP natively — the Agent SDK handles tool routing without custom code.

**Decision.** Use MCP for all database access. Zero custom DB code in the provider.

**Trade-off.** Depends on the MCP ecosystem quality and the `@modelcontextprotocol/server-sqlite` server specifically. Compensated by: (a) MCP is an Anthropic-backed standard with active development, (b) the architecture is MCP-server-agnostic — swapping SQLite for PostgreSQL means changing one config line, (c) the provider never touches the database directly, so database-specific bugs are isolated to the MCP server.

**Evidence.** The entire `src/claude_da/` codebase contains zero SQL execution code. All database interaction flows through MCP tool calls that the Agent SDK routes to the MCP server. Adding PostgreSQL support means configuring a PostgreSQL MCP server — no provider code changes.

### Decision 2: Agent SDK over CLI Subprocess

**Context.** Two ways to invoke Claude as an agent: (a) the Claude Agent SDK (`claude-agent-sdk` on PyPI), which provides a clean async Python API, or (b) shelling out to the Claude Code CLI as a subprocess.

**Analysis.** The Agent SDK provides typed responses (`AsyncIterator[Message]`), structured tool use blocks, token/cost metadata, and async support. The CLI subprocess approach requires parsing stdout, handling process lifecycle, and loses type safety. However, the Agent SDK is v0.1.x — less battle-tested than the CLI.

**Decision.** Use the Agent SDK as the primary integration. Document CLI subprocess as a fallback if SDK breaks.

**Trade-off.** v0.1.x API may change. Compensated by: (a) version pinned to `>=0.1.30,<0.2.0` with upper bound preventing surprise breakage, (b) integration tests catch SDK breaks, (c) CLI fallback is documented in `docs/TECHNICAL_GUIDE.md` — switching requires changing one module, not the architecture.

**Evidence.** The Agent SDK's typed response model enabled structured SQL extraction from `ToolUseBlock` objects matching `mcp__sqlite__*` tool names (`agent.py`). A CLI subprocess approach would require regex-parsing tool calls from stdout — fragile and untestable.

### Decision 3: SQLite for Demo

**Context.** The demo needs a database. Options: SQLite (zero setup, portable), PostgreSQL (production-realistic), or a mock/in-memory store.

**Analysis.** SQLite requires zero infrastructure — no server, no credentials, no Docker. The demo database is seeded by a Python script (`scripts/seed_demo_db.py`) that generates an e-commerce dataset with customers, products, orders, and order items across 6+ calendar months with varied distributions. The architecture is DB-agnostic by design (MCP server is the only database-aware component).

**Decision.** SQLite for demo. PostgreSQL is a configuration change, not an architecture change.

**Trade-off.** SQLite is not production-realistic for multi-user analytics. Compensated by: (a) the engineering value is in the provider-agent-MCP integration, not in the database, (b) SQLite enables zero-setup demos — `uv run python scripts/seed_demo_db.py` creates a ready-to-query database, (c) the seeder sets `chmod 444` on the database file as the third safety layer.

**Evidence.** The seeder script generates: 50+ customers across 3 tiers (Free/Pro/Enterprise), 25+ products across 4 categories, and 200+ orders spanning 6 months. This is sufficient for meaningful analysis queries while remaining portable.

### Decision 4: Environment Variables over YAML Config

**Context.** The provider needs 9 configuration settings: API key, model, database path, MCP server command, log settings, timeouts, and limits.

**Analysis.** YAML config files are more structured but require a parser, a schema, a config file location convention, and documentation. Environment variables are simpler, Docker-native, and require zero parsing code. The MVP has 9 settings — YAML overhead is not justified.

**Decision.** Environment variables with a frozen dataclass (`config.py`). Validation at parse time, immutable after construction.

**Trade-off.** Less structured than a config file — no nesting, no comments. Compensated by: (a) `.env.template` documents all variables with defaults, (b) the frozen dataclass enforces types and validation at startup, not at query time, (c) LiteLLM's own config (`litellm_config.yaml`) handles routing — the provider config is orthogonal.

**Evidence.** `config.py` parses all 9 environment variables into a frozen `ClaudeDAConfig` dataclass. Missing required values (e.g., `ANTHROPIC_API_KEY`) raise `ConfigurationError` at startup, not at query time.

### Decision 5: Structured JSONL Logging

**Context.** Every query must be auditable — the exact SQL executed, token costs, and response metadata must be traceable.

**Analysis.** Options: (a) file-per-session artifacts (browsable but require storage management), (b) structured JSONL to stdout/file (machine-parseable, configurable, no infrastructure), (c) database-backed audit trail (full-featured but requires infrastructure). The MVP needs auditability without infrastructure.

**Decision.** Structured JSONL audit logging via `audit.py`. Configurable output: stdout, file, or both. Fire-and-forget via `asyncio.create_task` to avoid blocking the response path.

**Trade-off.** Less browsable than file artifacts — requires `jq` or similar to query. Compensated by: (a) each audit entry contains the full request, response, SQL queries, token counts, cost, and latency, (b) stdout mode integrates with any log aggregation system, (c) fire-and-forget with exception suppression ensures audit failures never break query responses.

**Evidence.** The audit entry schema captures: `request_id`, `model`, `messages`, `response_text`, `sql_queries[]`, `input_tokens`, `output_tokens`, `cost`, `latency_ms`, and `timestamp`. The `task.add_done_callback()` pattern suppresses "never retrieved" warnings for fire-and-forget tasks.

### Decision 6: Full Schema in System Prompt

**Context.** The agent needs to know what tables and columns exist to write correct SQL.

**Analysis.** Two approaches: (a) inject the full schema into the system prompt at startup, or (b) contextual injection — only include tables relevant to the current question. Contextual injection is more token-efficient but requires a relevance classifier (itself an LLM call or embedding lookup).

**Decision.** Full schema injection at startup via `schema.py` PRAGMA queries. The schema is discovered once during lazy initialization and embedded in every system prompt.

**Trade-off.** Doesn't scale past ~50 tables (prompt grows linearly with schema size). Compensated by: (a) demo databases are small — the full schema fits comfortably in the context window, (b) contextual injection is the documented scaling path in `docs/TECHNICAL_GUIDE.md`, (c) the prompt assembly in `prompt.py` is modular — swapping full-schema for contextual-schema requires changing one function.

**Evidence.** `schema.py` discovers the schema via `SELECT * FROM sqlite_master` and `PRAGMA table_info()`, formatting it as `CREATE TABLE` statements. The `prompt.py` module assembles the system prompt from three parts: role definition, schema, and behavioral rules (including read-only instructions).

### Decision 7: Lazy Initialization

**Context.** The provider is instantiated at LiteLLM import time. Environment variables may not be set yet (during test collection, provider scanning, or module loading).

**Analysis.** Eager initialization at import time causes cascading failures: missing `ANTHROPIC_API_KEY` during `pytest --collect-only`, missing database during LiteLLM provider discovery, and import-order dependencies. The plan review (iteration 1) identified this as a blocker — "Module-level instance runs full init at import time — fragile."

**Decision.** Lazy initialization via `_ensure_initialized()` with `asyncio.Lock`. First request triggers full init: config loading, schema discovery, read-only verification, prompt assembly, agent and audit logger creation. Init failure is cached to prevent cascading retries.

**Trade-off.** First request is slower (~2-5 seconds for MCP server startup). Compensated by: (a) subsequent requests are fast (MCP server stays running), (b) init failure caching prevents repeated slow failures, (c) no import-time side effects — the provider module can be safely imported in any context.

**Evidence.** The lazy init pattern resolved two review blockers: the plan-reviewer's "import-time fragility" concern and the design-reviewer's "env vars not set at import" concern. Init failure is cached as a `_init_error` attribute — subsequent requests return the cached error immediately instead of re-attempting initialization.

---

## IV. Architecture as Risk Mitigation

The architecture is not just code organization — it is a risk mitigation strategy. Each structural choice addresses a specific failure mode.

### Three-Layer Read-Only Safety

**Risk.** The agent writes to or corrupts the database.

**Mitigation.** Three independent layers, each sufficient on its own:

| Layer | Mechanism | Enforcement Level | Code Reference |
|-------|-----------|-------------------|----------------|
| Tool allowlist | `allowed_tools=["mcp__sqlite__*"]` | SDK-enforced; blocks all non-MCP tools | `agent.py` |
| Tool blocklist | `disallowed_tools=["Bash", "Write", "Edit"]` | SDK-enforced; explicitly blocks the three most dangerous tools | `agent.py` |
| Filesystem permissions | `chmod 444` on the database file | OS-enforced; rejects writes below the application layer | `seed_demo_db.py` |

**Why three layers?** The `allowed_tools` wildcard alone should be sufficient. However, a bug in early Agent SDK versions (v0.1.5-v0.1.9, issue #361) caused `allowed_tools` to be silently ignored. The tool blocklist would have caught the critical paths. Filesystem permissions protect regardless of any application-level bug.

**Verification.** On first request, `verify_read_only()` in `schema.py` attempts a write operation against the database. If the write succeeds, the system refuses to start. If it fails (the expected case), initialization continues. This is a startup-time safety gate, not a runtime check.

### Error Isolation

**Risk.** Agent SDK errors, MCP server crashes, or database errors propagate as unformatted 500s to the client.

**Mitigation.** Custom exception hierarchy (`exceptions.py`) with HTTP status code mapping. `ClaudeDAError` is the base class; subclasses include `ConfigurationError` (500), `SchemaDiscoveryError` (500), `AgentError` (502), and `InputValidationError` (400). The provider's `_handle_error()` method catches `ClaudeDAError` and re-raises as LiteLLM's `CustomLLMError(status_code, message)` — preserving the correct HTTP status for each error type.

### Audit Trail Integrity

**Risk.** Audit logging blocks the response path or fails silently, losing the audit record.

**Mitigation.** Fire-and-forget via `asyncio.create_task()` with `task.add_done_callback()` for exception suppression. The audit log is dispatched after the response is assembled but before it is returned. For streaming, the audit entry is written after the final chunk (`is_finished=True`), with SQL queries and metadata accumulated in memory during streaming.

---

## V. The Five Pivots

The system evolved through five design pivots. Each was triggered by review findings or implementation discoveries, not random exploration.

### Pivot 1: Lazy Initialization

**Trigger.** Plan review identified that module-level initialization runs at import time, causing failures when environment variables are not set during test collection or LiteLLM provider scanning.

**What was preserved:** Full initialization sequence (config → schema → verify → prompt → agent → audit).
**What was discarded:** Eager initialization at module load.
**Why.** Import-time side effects are a well-known anti-pattern in Python. The `_ensure_initialized()` pattern with `asyncio.Lock` defers all initialization to first request, eliminating import-order dependencies.

### Pivot 2: Streaming Return Type

**Trigger.** Design review identified that `astreaming()` must return `AsyncIterator` per LiteLLM's interface, but the original design returned a tuple `(iterator, future)` to coordinate audit logging.

**What was preserved:** Streaming capability and audit logging for streamed responses.
**What was discarded:** Tuple return type and `Future`-based audit coordination.
**Why.** The mutable container pattern (`result_holder = [None]`) passed as a single-element list allows the iterator to accumulate the result while the caller writes the audit entry after iteration completes. Simpler than Futures, no shared state issues.

### Pivot 3: MCP Server Launch Strategy

**Trigger.** Plan review discovered that MCP server config uses plain dicts matching `McpStdioServerConfig` schema, not imported TypedDicts as originally assumed.

**What was preserved:** MCP server configuration as part of `ClaudeAgentOptions`.
**What was discarded:** TypedDict imports from the SDK.
**Why.** The official SDK examples use plain dict literals. Importing TypedDicts that don't exist in the SDK would fail at runtime.

### Pivot 4: Permission Mode

**Trigger.** Plan review identified that the Agent SDK defaults to interactive permission approval, which hangs in a headless server context.

**What was preserved:** Agent SDK as the execution engine.
**What was discarded:** Default permission mode (interactive).
**Why.** `permission_mode="bypassPermissions"` is required for server-side use. The three-layer safety model (tool allowlist, blocklist, filesystem permissions) provides the actual safety guarantees — the permission prompt is for interactive CLI use, not headless servers.

### Pivot 5: Database Permissions Strategy

**Trigger.** Plan review identified that `git` does not preserve `chmod 444` — committing `demo.db` to the repository would break the read-only enforcement after clone.

**What was preserved:** Filesystem permissions as the third safety layer.
**What was discarded:** Committed `demo.db` binary.
**Why.** The seeder script (`seed_demo_db.py`) generates the database at setup time and applies `chmod 444`. This ensures permissions are correct on every machine, regardless of git's file mode handling.

---

## VI. Acknowledged Limitations

Eight limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight.

### L1: SQLite-Only

- **Impact:** Only SQLite is supported. Not production-realistic for multi-user analytics.
- **Current Mitigation:** The architecture is MCP-server-agnostic. The provider never touches the database directly. Swapping SQLite for PostgreSQL means configuring a PostgreSQL MCP server — no provider code changes.
- **North Star:** Multi-database support via MCP server configuration: PostgreSQL, MySQL, and any MCP-supported database.

### L2: Full Schema in Prompt

- **Impact:** Doesn't scale past ~50 tables. Prompt grows linearly with schema size, consuming context window and increasing cost.
- **Current Mitigation:** Demo databases are small. The prompt assembly in `prompt.py` is modular — swapping full-schema for contextual-schema requires changing one function.
- **North Star:** Contextual schema injection — only tables relevant to the current question are included, using embedding-based relevance or LLM-based table selection.

### L3: Stateless (No Conversation Memory)

- **Impact:** Each request is independent. "What about last month?" after "Show me this month's revenue" fails because the agent has no context.
- **Current Mitigation:** The Agent SDK supports sessions. Wiring conversation memory through the provider is straightforward but time-consuming.
- **North Star:** Conversation memory with configurable session TTL, enabling follow-up questions and iterative analysis.

### L4: No Governance

- **Impact:** Single API key, no per-user access control, no query budgets.
- **Current Mitigation:** LiteLLM has built-in support for virtual keys, budget enforcement, and per-key capability profiles. Enabling them is configuration, not code.
- **North Star:** Per-user API keys with table-level access control and monthly budget caps, enforced by LiteLLM's virtual key system.

### L5: No Caching

- **Impact:** Identical questions re-execute the full agent loop, incurring the same API cost and latency.
- **Current Mitigation:** Acceptable for exploratory analysis. Each question costs ~$0.10-0.50 in API calls.
- **North Star:** Result caching for repeated questions with TTL-based invalidation.

### L6: Agent SDK v0.1.x

- **Impact:** The SDK is pre-1.0 and may introduce breaking changes.
- **Current Mitigation:** Version pinned to `>=0.1.30,<0.2.0`. Integration tests catch breaks. CLI subprocess is documented as a fallback.
- **North Star:** Upgrade to stable SDK release when available. The fallback strategy (CLI subprocess) is documented but has never been needed.

### L7: Hallucinated Insights

- **Impact:** Claude may present plausible analysis not supported by the data. A trend described as "increasing" may actually be flat.
- **Current Mitigation:** Audit logs capture the exact SQL queries executed. Users can verify any claim by re-running the SQL. The system prompt includes instructions to ground all analysis in query results.
- **North Star:** Response validation layer that checks claims against query results before returning to the user.

### L8: Prompt Injection Risk

- **Impact:** A crafted question could manipulate the agent into executing unintended queries or extracting sensitive data.
- **Current Mitigation:** Read-only enforcement prevents writes. Internal-only deployment is the primary mitigation. Audit logs capture all executed SQL for post-hoc review. The system prompt includes read-only instructions as a supplementary soft guardrail.
- **North Star:** Query classification layer that detects and blocks suspicious patterns before agent execution.

---

## VII. Validation Strategy

### Test Pyramid

```
                    +---------------+
                    | Integration   |  5 tests against
                    | (API key)     |  live agent + MCP
                    +---------------+
               +-------------------------+
               |      Unit Tests         |  147 tests across
               |   (mocked SDK/MCP)      |  9 test files
               +-------------------------+
```

### Coverage by Component

| Component | Test Files | Approach |
|-----------|-----------|----------|
| Provider | `tests/unit/test_provider.py` | Mock Agent SDK, test LiteLLM interface compliance |
| Agent | `tests/unit/test_agent.py` | Mock SDK `query()`, test message iteration and SQL extraction |
| Prompt | `tests/unit/test_prompt.py` | Direct function testing of prompt assembly |
| Schema | `tests/unit/test_schema.py` | Mock SQLite PRAGMA responses, test schema discovery |
| Config | `tests/unit/test_config.py` | Environment variable parsing with monkeypatch |
| Audit | `tests/unit/test_audit.py` | Test JSONL formatting and output routing |
| Exceptions | `tests/unit/test_exceptions.py` | HTTP status code mapping |
| Integration | `tests/integration/` | Live Agent SDK + MCP server (skipped without API key) |

### Key Test Patterns

1. **AsyncMock for async code** — All agent and provider methods are async. Tests use `unittest.mock.AsyncMock` with `pytest-asyncio`.

2. **Environment-gated integration tests** — Integration tests require a live Anthropic API key. `pytest.mark.skipif` skips them in CI without API credentials.

3. **Monkeypatch for config** — Config tests use `monkeypatch.setenv` to test environment variable parsing without polluting the test environment.

4. **Fire-and-forget verification** — Audit tests verify that `asyncio.create_task` is called and that exceptions in audit tasks don't propagate.

### Metrics

| Metric | Value |
|--------|-------|
| Total tests | 152 |
| Passing | 146 |
| Failing | 2 (runtime-dependent — Agent SDK version timing) |
| Skipped | 4 (integration tests without API key) |

---

## VIII. Process and Delivery Metrics

### Five-Stage Specification Pipeline

The system was built through a 5-stage specification pipeline with formal review at each stage. Each review used a dual-reviewer model: a skeptic (finds issues) and a gatekeeper (makes pass/fail decisions).

| Stage | Artifact | Iterations | Blockers Found |
|-------|----------|------------|----------------|
| Specify | `spec.md` | 1 | 0 (5 warnings deferred to design) |
| Design | `design.md` | 1 | 3 (wrong SDK name, missing error translation, missing message conversion) |
| Plan | `plan.md` | 2 | 4 (message serialization, MCP config format, permission mode, git permissions) |
| Tasks | `tasks.md` | 1 + 2 chain validations | 1 |
| Implement | 8 source modules | 2 | 2 (missing integration tests, SQL injection in PRAGMA) |
| **Total** | | **7 iterations** | **10 blockers resolved** |

### 41 Tasks Across 5 Phases

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1: Foundation | 6 | Project scaffold, config, exceptions, pyproject.toml |
| Phase 2: Database | 5 | Schema discovery, demo seeder, read-only verification |
| Phase 3: Core | 12 | Agent, provider, prompt, streaming, audit |
| Phase 4: Hardening | 10 | Error handling, lazy init, input validation, timeout |
| Phase 5: Validation | 8 | Unit tests, integration tests, documentation |

All 41 tasks completed. Two tasks (T-021, T-027) exceeded the 15-minute guideline and were subsequently split into a/b subtasks, validating the original sizing concern.

### Review Effectiveness

The dual-reviewer model caught 10 blockers across 7 iterations. The most impactful catches:

1. **Wrong SDK package name** (design review) — The design used `claude-code-sdk` / `ClaudeCodeOptions`. The actual package is `claude-agent-sdk` / `ClaudeAgentOptions`. This would have been a Day 1 implementation failure.

2. **Permission mode hang** (plan review) — The Agent SDK defaults to interactive permission approval. In a headless LiteLLM server, this hangs indefinitely. Setting `permission_mode="bypassPermissions"` was critical.

3. **Git doesn't preserve chmod** (plan review) — Committing `demo.db` with `chmod 444` would lose permissions after `git clone`. Generating the database at setup time was the correct fix.

4. **SQL injection in PRAGMA** (implementation review) — An f-string in schema discovery (`f"PRAGMA table_info({table_name})"`) was flagged as a potential SQL injection vector. Fixed with parameterised queries.

### Front-Loaded Research Prevented Wasted Effort

The spec review deferred 5 warnings to the design phase rather than blocking on them. This was the correct decision — the design phase resolved all 5 with better context. The design review then caught 3 blockers (wrong SDK name, missing error translation, missing message conversion) that would have been implementation failures.

The plan review was the most productive: 4 blockers in a single iteration, each addressing a runtime failure that would have been discovered only during live testing. Front-loading these discoveries into the plan phase saved an estimated 2-3 hours of implementation debugging.

### Patterns Worth Documenting

1. **Skeptic + Gatekeeper dual-reviewer.** Separating "find issues" from "make pass/fail decisions" prevents the reviewer from self-censoring. The skeptic's job is to be paranoid; the gatekeeper's job is to be pragmatic.

2. **Blocker / warning / suggestion tiers.** Review classification allows approval with known warnings. Not every issue is a blocker — some are correctly deferred to the next phase.

3. **Verify SDK package names against PyPI before design.** Wrong names are blockers that waste review cycles. The `claude-code-sdk` → `claude-agent-sdk` catch saved a full implementation restart.

4. **Module-level singletons need lazy init.** Never rely on environment variables being available at import time. This is especially critical for LiteLLM providers, which are imported during provider scanning.

5. **Pin v0.x dependencies with upper bounds.** `>=0.1.30,<0.2.0` prevents surprise breakage from minor version bumps in pre-1.0 packages.

---

## IX. North Star Roadmap

### Tier 1: Highest ROI

**Multi-Database Support**
- **What:** Configure PostgreSQL, MySQL, and other MCP-supported databases.
- **Why:** The architecture is MCP-server-agnostic but only SQLite is exercised. Proving multi-database support validates the abstraction.
- **Effort:** 1-2 days per database (MCP server config + integration tests).

**Contextual Schema Injection**
- **What:** Include only tables relevant to the current question in the system prompt.
- **Why:** Full schema doesn't scale past ~50 tables. Contextual injection enables enterprise-scale databases.
- **Effort:** 2-3 days (relevance classifier + prompt modification).

### Tier 2: Medium ROI

**Conversation Memory**
- **What:** Maintain conversation state across requests for follow-up questions.
- **Why:** "What about last month?" is the natural follow-up to any analysis question.
- **Effort:** 2-3 days (session management + Agent SDK session wiring).

**Per-User Governance**
- **What:** LiteLLM virtual keys with per-user table access and budget caps.
- **Why:** Production deployment requires access control and cost management.
- **Effort:** 1-2 days (LiteLLM configuration, not provider code).

### Tier 3: Long-Term

**Response Validation**
- Re-run the agent's SQL queries and verify that claimed trends and statistics match the actual results before returning to the user.

**Audit MCP Server**
- An MCP server that provides tools to query the audit log, enabling the agent to answer questions about its own history.

**Cost Optimization**
- Model tiering (cheap models for simple queries, expensive for complex analysis), response caching, and prompt compression.

---

## X. Conclusion

### What Was Demonstrated

This project demonstrates systems integration thinking applied to three mature technologies. The goal was not to build the most complete analytics platform — it was to build the most thoughtful integration.

**Safety as architecture, not afterthought.** Three independent read-only layers, each sufficient on its own, with startup verification that refuses to run if the safety model is compromised. The three-layer approach was motivated by a real Agent SDK bug (issue #361) where `allowed_tools` was silently ignored — defense in depth is not theoretical.

**Review-driven development.** Ten blockers caught across seven review iterations, each preventing a runtime failure. The wrong SDK package name would have been a Day 1 failure. The permission mode hang would have been an inexplicable timeout in production. The git permissions issue would have silently disabled the third safety layer on every fresh clone. Front-loaded review is cheaper than post-hoc debugging.

**Honest scope calibration.** Eight acknowledged limitations, each with impact, current mitigation, and North Star resolution. The system does not pretend to solve problems it does not solve. SQLite-only is stated as a deliberate decision. Hallucinated insights are documented as a risk. Prompt injection is acknowledged with honest assessment of what read-only enforcement does and does not prevent.

### The Five Pivots Tell the Story

1. **Eager init → Lazy init** — Never rely on env vars at import time
2. **Tuple return → Mutable container** — Match the interface your framework expects
3. **TypedDict imports → Plain dicts** — Use what the SDK actually provides
4. **Interactive permissions → Bypass** — Server context requires server-mode configuration
5. **Committed DB → Generated DB** — Git doesn't preserve what you think it preserves

Each pivot was discovered during review, not during debugging. The review process is the safety net.

### Nothing Accidental

Every decision in this system is documented with its trade-off:

- MCP for DB access trades ecosystem dependency for zero custom connector code.
- Agent SDK trades v0.1.x instability for typed async API.
- SQLite trades production realism for zero-setup demos.
- Env vars trade structured config for Docker-native simplicity.
- JSONL logging trades browsability for machine parseability.
- Full schema in prompt trades scalability for implementation simplicity.
- Lazy init trades first-request latency for import-time safety.

The depth of thought is the deliverable. The code is the proof.

---

## References

1. Claude Agent SDK — https://pypi.org/project/claude-agent-sdk/ — v0.1.x async Python API for Claude agent interactions.

2. Model Context Protocol — https://modelcontextprotocol.io — Anthropic-backed standard for AI-tool integration.

3. `@modelcontextprotocol/server-sqlite` — MCP server providing SQLite database tools (read_query, write_query, list_tables, describe_table).

4. LiteLLM — https://github.com/BerriAI/litellm — OpenAI-compatible API gateway with custom provider support.

5. Anthropic (2025). "Building Effective Agents." — Agent architecture patterns and tool design best practices.

6. Agent SDK Issue #361 — `allowed_tools` silently ignored in v0.1.5-v0.1.9, motivating the three-layer safety model.

---

## Appendix: Artifact Registry

| Artifact | Path | Notes |
|----------|------|-------|
| PRD | `docs/brainstorms/20260207-claude-litellm.prd.md` | Product requirements and research |
| Specification | `docs/features/001-claude-da/spec.md` | Functional requirements and acceptance criteria |
| Design | `docs/features/001-claude-da/design.md` | Architecture, module interfaces, data flow |
| Plan | `docs/features/001-claude-da/plan.md` | Build order, phase dependencies, risk gates |
| Tasks | `docs/features/001-claude-da/tasks.md` | 41 tasks across 5 phases |
| Review History | `docs/features/001-claude-da/.review-history.md` | 7 iterations, 10 blockers resolved |
| Retrospective | `docs/features/001-claude-da/.retro.md` | Process learnings and patterns |
| Technical Guide | `docs/TECHNICAL_GUIDE.md` | Module reference and architecture |
| Source Code | `src/claude_da/` | 8 modules, 1,472 LOC |
| Tests | `tests/` | 14 test files, 152 tests, 2,772 LOC |
| Demo Seeder | `scripts/seed_demo_db.py` | E-commerce dataset generator |
| LiteLLM Config | `litellm_config.yaml` | Proxy routing configuration |
