# PRD: Claude-DA — Natural Language Data Analysis API

**Created**: 2026-02-07

---

## 1. Problem

Data analysis requires SQL fluency, schema knowledge, and the ability to translate business questions into technical queries. Non-technical stakeholders depend on analysts for every question, creating bottlenecks.

Three mature technologies exist that, individually, solve parts of this problem:
- **Claude Code** reasons about data, writes SQL, executes queries, and explains results
- **MCP servers** provide standardized, pluggable database access
- **LiteLLM** provides an OpenAI-compatible API gateway for any LLM provider

Claude-DA connects these three pieces: point it at your databases, and any OpenAI-compatible client becomes an AI data analyst.

## 2. Solution

Claude-DA is a **LiteLLM custom provider** that exposes Claude Code's agentic data analysis capabilities through a standard OpenAI-compatible API.

```
Any OpenAI client ──► LiteLLM Proxy ──► Claude-DA Provider ──► Claude Agent SDK
(Open WebUI, Slack,    (auth, routing,    (system prompt,        ├── MCP: SQLite
 curl, custom app)      budgets)           schema injection,     ├── MCP: PostgreSQL
                                           audit logging)        └── MCP: MySQL
```

**Target audience**: Internal teams, developers, and analysts who trust the deployment environment. Not designed for public-facing or adversarial use.

| For whom | Value |
|---|---|
| Non-technical team members | Ask data questions in plain English via any chat UI |
| Developers | Standard OpenAI API — no new SDK to learn, works with existing tools |
| Team leads | Centralized access with cost tracking via audit logs |
| Assessment reviewers | Demonstrates systems integration, security thinking, and product design |

## 3. User Stories

1. **Data question**: "What were our top 10 customers by revenue last month?" → Insight-driven answer with trends and context, not raw SQL output.
2. **API integration**: Standard `POST /v1/chat/completions` with a data question → structured insight embeddable in dashboards.
3. **Safety**: The agent cannot modify production data — hard enforcement via read-only database, disabled tools, and tool allowlists.
4. **Audit**: Every insight is traceable to the exact SQL queries and data that produced it.
5. **Non-data fallback**: "What's 2+2?" → Conversational response without database tools.

## 4. Full Product Vision (North Star)

The MVP proves the core value chain. The full product extends it across four dimensions:

### 4.1 Multi-Database Support
- PostgreSQL, MySQL, and any database with an MCP server
- Architecture is already DB-agnostic: adding databases is configuration, not code
- Per-database access controls and schema isolation

### 4.2 Intelligence
- **Contextual schema injection**: Only inject schema for tables relevant to the question (critical for large databases — full schema injection doesn't scale past ~50 tables)
- **Conversation memory**: Follow-up questions that reference prior context ("now break that down by region")
- **Result caching**: Repeated questions return cached results without re-querying
- **Suggested explorations**: After answering, suggest related questions the user might find useful

### 4.3 Governance
- **Capability profiles**: Per-API-key access rules — which databases, which tables, query complexity limits
- **Budget enforcement**: Per-key spending caps via LiteLLM's virtual key system
- **Prompt sanitization hardening**: Pattern-based heuristics to detect injection attempts (soft guardrail, not a security boundary)
- **Structured audit storage**: Append-only audit database with retention policies

### 4.4 Observability
- **Action transparency**: Surface executed SQL queries in response metadata so users see how the insight was derived
- **Langfuse integration**: LLM observability — trace cost, latency, and quality per request
- **Cost dashboards**: Per-user, per-database cost attribution
- **Audit MCP server**: An MCP server that exposes the audit log — any MCP client (including Claude itself) becomes the audit browser

### 4.5 What This System Is NOT (at any stage)
- **Not a BI tool** — no charts, scheduled reports, or dashboards. Use Metabase/Looker for that.
- **Not an ETL pipeline** — reads data only.
- **Not deterministic** — the same question may produce different SQL or insights. Not suitable for compliance reporting.
- **Not secure against adversarial users** — hard enforcement prevents writes, but prompt injection could extract sensitive data. Internal-only deployment is the primary mitigation.

## 5. Architecture

### 5.1 Request Flow

1. Client sends chat completions request with natural language question
2. LiteLLM Proxy authenticates and routes to Claude-DA provider
3. Provider validates input (length limit) and constructs enhanced prompt (role + schema + rules)
4. Claude Agent SDK processes autonomously: reasons → writes SQL → executes via MCP → analyzes results → formulates insight
5. Provider logs session (question, queries, response) for audit
6. Response returns as OpenAI-compatible ChatCompletion (streaming or non-streaming)

### 5.2 Security Model

Three independent hard enforcement layers, each sufficient on its own:

| Layer | Enforcement | Bypass risk |
|---|---|---|
| Read-only database (filesystem permissions) | OS rejects writes | None (if configured) |
| Tool allowlist (`mcp__sqlite__*` only) | SDK blocks all non-MCP tools | None (SDK-enforced) |
| Dangerous tools disabled (Bash, Write, Edit) | SDK blocks sandbox escape | None (SDK-enforced) |

The system prompt includes read-only instructions as a supplementary soft guardrail. On startup, a write operation is attempted and verified to fail — if it succeeds, the system refuses to start.

### 5.3 Auditability

Every request produces a single structured JSON log entry containing: session ID, timestamp, user question, SQL queries executed (ordered), query results summary, final response, and metadata (model, tokens, cost, duration, tool call count).

Key properties:
- **Reproducible**: Anyone can re-run the exact SQL queries against the database
- **Configurable verbosity**: Summaries by default; full result sets in verbose mode
- **Non-blocking**: Logging failures never cause request failures

**Sensitivity note**: Audit logs contain query results. If a user asks "show all customer emails", the results are persisted. Treat audit logs with the same access controls as the database.

### 5.4 Cost & Latency

Each request involves an agentic loop (reason → query → analyze), so costs and latency are higher than simple API calls:

| Scenario | Latency | Cost (Sonnet) |
|---|---|---|
| Simple query ("total revenue last month") | 5–15s | ~$0.03 |
| Multi-step analysis ("MoM trends by segment") | 15–45s | ~$0.10 |
| Non-data chat ("what's 2+2?") | 3–8s | ~$0.01 |

`max_turns` (default: 10) and `max_budget_usd` (default: $0.50) provide hard caps on runaway loops. Timeout hierarchy: LiteLLM proxy (300s) > Agent SDK (240s) > MCP query (30s).

### 5.5 Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Data exfiltration via prompt injection | High | Read-only prevents writes, but sensitive data could be extracted. Internal-only deployment is primary mitigation. |
| Hallucinated insights | Medium | Claude may present plausible analysis not supported by data. Users must validate critical insights. |
| Agent SDK breaking changes (v0.1.x) | Medium | Pin version, integration tests, CLI subprocess fallback. |
| Non-deterministic responses | Medium | Acceptable for exploration. Not suitable for compliance. |

## 6. MVP Scope

### 6.1 Delivered

The MVP is the **minimal skeleton** that proves the value chain end-to-end: question → SQL → insight → audit.

| Component | What it does |
|---|---|
| **LiteLLM custom provider** | `CustomLLM` subclass registered as `claude-da/analyst`. Completion + streaming. |
| **Agent SDK integration** | New session per request via `query()`. Configurable `max_turns` and `max_budget_usd`. |
| **MCP SQLite** | E-commerce demo database (4 tables, realistic data). Zero-setup proof that the pattern works. |
| **System prompt + schema injection** | Role definition, auto-discovered schema, behavioral rules. Under 12K characters. |
| **Read-only safety** | Three hard layers: filesystem permissions, tool allowlist, tool blocklist. Startup validation. |
| **Audit logging** | Structured JSON per request. Configurable output (stdout/file/both). |
| **Env var config** | 9 variables with sensible defaults. Fail-fast validation at startup. |

### 6.2 Deferred

| Feature | Why deferred |
|---|---|
| PostgreSQL/MySQL | SQLite proves the pattern; adding DBs is configuration, not architecture |
| Docker Compose | MVP runs via `pip install`; Docker is a packaging convenience |
| Conversation memory | Agent SDK supports it; wiring is straightforward but time-consuming |
| Contextual schema injection | Full schema works for demo-sized DBs |
| Langfuse / action transparency | LiteLLM has these built-in; enabling is config, not code |

### 6.3 Key Tradeoffs

| Decision | Tradeoff | Rationale |
|---|---|---|
| MCP for DB access | Depends on MCP ecosystem quality | Zero custom DB code; Claude speaks MCP natively; future-proof |
| Agent SDK (not CLI subprocess) | v0.1.x, less battle-tested | Clean async API, typed responses; fallback documented |
| SQLite for demo | Not production-realistic | Zero setup, portable; architecture is DB-agnostic |
| Full schema in prompt | Doesn't scale past ~50 tables | Works for demo; contextual injection is the scaling solution |
| Structured logging | Less browsable than file artifacts | No extra infrastructure; audit MCP server is the full-vision solution |

## 7. Success Criteria

- [ ] Working demo: question in English → insight-driven answer from real data
- [ ] Any OpenAI-compatible client works without modification
- [ ] Every insight traceable to exact SQL queries via audit log
- [ ] Security model is honestly assessed (hard vs. soft enforcement)
- [ ] Clean codebase demonstrating engineering design thinking

## 8. Verified Technical Feasibility

All load-bearing assumptions verified against official documentation:

| Capability | Verified | Source |
|---|---|---|
| Agent SDK: MCP servers, tool control, async iteration, budget caps | Yes | [Agent SDK docs](https://platform.claude.com/docs/en/agent-sdk/python) |
| LiteLLM: CustomLLM subclass, proxy registration, streaming chunks | Yes | [CustomLLM docs](https://docs.litellm.ai/docs/providers/custom_llm_server) |
| Prior art: cabinlab/litellm-claude-code confirms pattern works E2E | Yes | [GitHub](https://github.com/cabinlab/litellm-claude-code) |
| MCP: SQLite, PostgreSQL, MySQL servers exist and are community-maintained | Yes | [MCP servers](https://github.com/modelcontextprotocol) |

**Pre-implementation gate**: Run an E2E smoke test (Agent SDK → MCP SQLite → query → response) before building the provider. If it fails, fall back to CLI subprocess.

## 9. Project Context

Claude-DA is the second deliverable in the VICI Claude Code 7-Day Challenge assessment. It lives in the `claude-litellm/` directory of the monorepo alongside the SubTerminator project. Separate package, no shared code — each demonstrates different aspects of AI engineering.
