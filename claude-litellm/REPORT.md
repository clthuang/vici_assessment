# Claude-DA: Report

This document explains the problem Claude-DA addresses, the proposed solution, the architecture and safety model, key design decisions with their tradeoffs, risks, and the boundary between the delivered MVP and the full product vision.

It is written for interviewers and technical evaluators. For setup and usage instructions, see [README.md](./README.md). For code-level architecture and module reference, see [docs/TECHNICAL_GUIDE.md](./docs/TECHNICAL_GUIDE.md).

---

## Problem Statement

Data analysis requires SQL fluency, schema knowledge, and the ability to translate business questions into technical queries. Non-technical stakeholders depend on analysts for every question, creating bottlenecks that slow decision-making across the organisation.

Three mature technologies each solve part of this problem independently:

- **Claude Code** reasons about data, writes SQL, executes queries, and explains results in natural language.
- **MCP servers** provide standardized, pluggable database access without custom connector code.
- **LiteLLM** provides an OpenAI-compatible API gateway that any existing client can call.

None of these, on their own, gives a non-technical user an end-to-end path from "English question" to "data-backed insight." Claude-DA connects them: point it at a database, and any OpenAI-compatible client becomes an AI data analyst.

| Audience | Value |
|---|---|
| Non-technical team members | Ask data questions in plain English via any chat UI |
| Developers | Standard OpenAI API -- no new SDK to learn, works with existing tools |
| Team leads | Centralised access with cost tracking via audit logs |
| Assessment reviewers | Demonstrates systems integration, security thinking, and product design |

---

## Proposed Solution

Claude-DA is a **LiteLLM custom provider** that wraps the Claude Agent SDK behind an OpenAI-compatible chat completions API. The provider injects the database schema into a system prompt, hands the user's question to an autonomous agent, and returns the agent's insight-driven response in standard OpenAI format.

```
Client  --->  LiteLLM Proxy  --->  Claude-DA Provider  --->  Claude Agent SDK  --->  MCP SQLite
```

- **Target audience**: internal teams, developers, and analysts who trust the deployment environment. Not designed for public-facing or adversarial use.
- **What a user sees**: send an English question (e.g., "What were our top 10 customers by revenue last month?"), receive a Markdown-formatted answer with trends, context, and the reasoning behind the analysis.
- **Protocol**: standard `POST /v1/chat/completions`. Any tool that speaks the OpenAI chat completions format -- curl, the OpenAI Python SDK, Open WebUI, LangChain -- works without modification.
- **Modes**: both non-streaming and streaming (Server-Sent Events) are supported.

---

## Architecture Overview

### Module Dependency Chain

The source code is organised into 6 modules plus a demo seeder script. Dependencies are acyclic:

```
provider  --->  agent  --->  prompt  --->  schema  --->  config  --->  exceptions
    |             |                                        ^
    +-- audit ----+----------------------------------------+
```

| Module | Responsibility |
|---|---|
| `provider.py` | LiteLLM CustomLLM interface, lazy init, error translation, audit dispatch |
| `agent.py` | Agent SDK session lifecycle, message iteration, SQL extraction |
| `prompt.py` | System prompt assembly (role + schema + rules) |
| `schema.py` | SQLite schema discovery via PRAGMA, read-only verification |
| `audit.py` | Structured JSONL audit logging (stdout, file, or both) |
| `config.py` | Environment variable parsing, validation, frozen dataclass |
| `exceptions.py` | Exception hierarchy with HTTP status codes |

### Request Lifecycle

A non-streaming request follows these steps:

1. **Route** -- LiteLLM Proxy receives `POST /v1/chat/completions` and routes to `claude-da/analyst`.
2. **Initialize** -- `provider.py` calls `_ensure_initialized()` on first request: loads config, discovers schema, verifies read-only access, builds system prompt, creates agent and audit logger.
3. **Validate** -- Input length is checked against `input_max_chars` (default: 10,000 characters). Rejects with HTTP 400 if exceeded.
4. **Run agent** -- `agent.py` converts messages to a prompt, builds `ClaudeAgentOptions` with MCP config and tool restrictions, and calls the Agent SDK's `query()` function wrapped in `asyncio.wait_for(timeout=240s)`.
5. **Iterate messages** -- The SDK returns an `AsyncIterator[Message]`. Text blocks are accumulated into the response; `ToolUseBlock` calls matching `mcp__sqlite__*` have their SQL extracted; `ResultMessage` provides token/cost metadata.
6. **Respond and audit** -- The provider formats a `ModelResponse`, fires an audit log task (fire-and-forget via `asyncio.create_task`), and returns the response.

For **streaming** requests, text chunks are yielded to the client as they arrive from the SDK. SQL queries and metadata are still accumulated in memory. The audit entry is written after the final chunk (`is_finished=True`).

---

## Safety Architecture

Claude-DA enforces read-only database access through three independent layers. Each is sufficient on its own; all three must fail simultaneously for a write to succeed.

| Layer | Mechanism | Enforcement Level | Code Reference |
|---|---|---|---|
| Tool allowlist | `allowed_tools=["mcp__sqlite__*"]` | SDK-enforced; blocks all non-MCP tools | `agent.py:208` |
| Tool blocklist | `disallowed_tools=["Bash", "Write", "Edit"]` | SDK-enforced; explicitly blocks the three most dangerous tools | `agent.py:209` |
| Filesystem permissions | `chmod 444` on the database file | OS-enforced; rejects writes below the application layer | `seed_demo_db.py:266` |

**Startup validation**: on first request, `verify_read_only()` at `schema.py:222` attempts a write operation against the database. If the write succeeds, the system refuses to start. If it fails (the expected case), initialisation continues.

**Why three layers?** The `allowed_tools` wildcard alone should be sufficient. However, a bug in early Agent SDK versions (v0.1.5--v0.1.9, issue #361) caused `allowed_tools` to be silently ignored. The tool blocklist would have caught the critical paths. Filesystem permissions protect regardless of any application-level bug.

**Honest assessment**: hard enforcement prevents writes, but prompt injection could extract sensitive data via crafted read queries. Internal-only deployment is the primary mitigation. The system prompt includes read-only instructions as a supplementary soft guardrail, but this depends on the model following instructions and is not a security boundary.

---

## Key Design Decisions and Tradeoffs

| Decision | Tradeoff | Rationale |
|---|---|---|
| MCP for DB access (not custom connectors) | Depends on MCP ecosystem quality | Zero custom DB code; Claude speaks MCP natively; adding new databases is configuration, not code |
| Agent SDK (not CLI subprocess) | v0.1.x, less battle-tested | Clean async API with typed responses; CLI subprocess fallback is documented |
| SQLite for demo | Not production-realistic | Zero setup, portable; architecture is DB-agnostic by design |
| Env vars (not YAML config) | Less structured than a config file | MVP has 9 settings; env vars are simpler, Docker-native, zero parsing code |
| Structured logging (not file-per-session) | Less browsable than file artifacts | No extra infrastructure needed; configurable verbosity; audit MCP server is the full-vision solution |
| Full schema in system prompt | Doesn't scale past ~50 tables | Works for demo-sized databases; contextual injection is the documented scaling path |
| Lazy initialisation | First request is slower | Avoids import-time failures when env vars are not yet set (e.g., during test collection or LiteLLM provider scanning) |

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Data exfiltration via prompt injection** | High | Read-only prevents writes, but sensitive data could be extracted through crafted read queries. Internal-only deployment is the primary mitigation. Audit logs capture all executed SQL for post-hoc review. |
| **Hallucinated insights** | Medium | Claude may present plausible analysis not supported by the data. Users must validate critical insights independently. Audit logs provide the exact SQL for verification. |
| **Agent SDK breaking changes** (v0.1.x) | Medium | Version pinned to `>=0.1.30,<0.2.0`. Integration tests catch breaks. CLI subprocess is a documented fallback. |
| **Non-deterministic responses** | Medium | The same question may produce different SQL or different phrasing. Acceptable for exploratory analysis; not suitable for compliance or financial reporting. |

---

## MVP vs. Full Vision

The MVP proves the core value chain end-to-end: English question in, SQL-backed insight out, audit trail recorded.

| Dimension | MVP (Delivered) | Full Vision (Deferred) |
|---|---|---|
| **Database** | SQLite via MCP | PostgreSQL, MySQL, and any MCP-supported database |
| **Schema handling** | Full schema injected into system prompt at startup | Contextual injection: only tables relevant to the question |
| **Memory** | Stateless; each request is independent | Conversation memory for follow-up questions |
| **Governance** | Single API key, env var config | Per-key capability profiles, budget enforcement via LiteLLM virtual keys |
| **Audit** | Structured JSONL to stdout/file | Append-only audit database, retention policies, audit MCP server |
| **Observability** | Token/cost metadata in audit entries | Langfuse integration, cost dashboards, action transparency in response metadata |
| **Caching** | None | Result caching for repeated questions |

Why each was deferred:

- **Multi-database**: SQLite proves the pattern; adding databases is configuration, not architecture.
- **Contextual schema injection**: full schema works for demo-sized databases; optimisation adds complexity without demo benefit.
- **Conversation memory**: Agent SDK supports sessions; wiring through is straightforward but time-consuming.
- **Governance and observability**: LiteLLM has built-in support for virtual keys, Langfuse, and budget enforcement; enabling them is configuration, not code.
- **Audit storage**: structured logging is sufficient for MVP; an audit MCP server is the full-vision solution.

---

## Success Criteria

- Working demo: ask a question in English, get an insight-driven answer from real data
- Any OpenAI-compatible client works without modification
- Every insight is traceable to the exact SQL queries via the audit log
- Security model is honestly assessed (hard vs. soft enforcement, with known limitations documented)
- Clean codebase demonstrating engineering design thinking
