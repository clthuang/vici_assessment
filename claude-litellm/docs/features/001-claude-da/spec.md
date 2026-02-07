# Specification: Claude-DA — Natural Language Data Analysis API

**Feature**: 001-claude-da
**Phase**: specify
**PRD**: [prd.md](./prd.md)

---

## 1. Scope

This spec covers the MVP as defined in the PRD (Section 6.1). It specifies **7 deliverables**:

1. LiteLLM custom provider (completion + streaming)
2. Claude Agent SDK integration
3. MCP SQLite connectivity
4. Data analyst system prompt with schema injection
5. Read-only safety (tool allowlist + disabled Bash + read-only DB user)
6. Structured audit logging
7. Environment variable configuration

Anything listed in PRD Section 6.2 (deferred) is explicitly **out of scope**.

---

## 2. Requirements

### REQ-01: LiteLLM Custom Provider

**Description**: Implement a `CustomLLM` subclass that registers as `claude-da/analyst` and handles chat completion requests.

**Acceptance Criteria**:
- [ ] AC-01.1: Subclasses `litellm.CustomLLM` and implements `acompletion()` and `astreaming()` (async variants used by proxy)
- [ ] AC-01.2: Sync variants (`completion()`, `streaming()`) delegate to async implementations or raise `NotImplementedError` with a clear message
- [ ] AC-01.3: Registered via `litellm.custom_provider_map` as provider `"claude-da"`
- [ ] AC-01.4: Accessible as model `"claude-da/analyst"` through LiteLLM proxy's `/v1/chat/completions` endpoint
- [ ] AC-01.5: Non-streaming requests return a valid OpenAI `ChatCompletion` response with `choices[0].message.content` as a non-empty string containing a natural language response
- [ ] AC-01.6: Streaming requests (`stream=true`) return SSE-formatted chunks, each a valid `GenericStreamingChunk` with `text`, `is_finished`, `finish_reason`, `index` fields
- [ ] AC-01.7: Final streaming chunk has `is_finished=true` and `finish_reason="stop"`
- [ ] AC-01.8: Full conversation history from the `messages` parameter is forwarded to the Agent SDK (not just the latest message)
- [ ] AC-01.9: Errors from the Agent SDK are caught and returned according to the error mapping in Section 4 (400, 429, 503, 504 with descriptive messages)

**Out of scope**: `/v1/completions`, `/v1/embeddings`, `/v1/models` endpoints.

---

### REQ-02: Claude Agent SDK Integration

**Description**: The provider invokes Claude Code via the Agent SDK to process each request.

**Acceptance Criteria**:
- [ ] AC-02.1: Uses `claude-agent-sdk` Python package, pinned to `>=0.1.30`
- [ ] AC-02.2: Each request creates a new Agent SDK session via `query()` with `ClaudeAgentOptions`
- [ ] AC-02.3: The `system_prompt` option is set to the data analyst prompt (see REQ-04)
- [ ] AC-02.4: The `max_turns` option is set to a configurable value (default: 10) to cap agentic loops
- [ ] AC-02.5: The `max_budget_usd` option is set to a configurable value (default: 0.50) to cap spend per request
- [ ] AC-02.6: Agent SDK responses are iterated via `async for message in query(...)` and collected into the final response
- [ ] AC-02.7: For streaming requests, text content from Agent SDK messages is yielded as `GenericStreamingChunk` as it arrives
- [ ] AC-02.8: Agent SDK exceptions are caught and mapped to provider errors (e.g., rate limit → 429, timeout → 504)
- [ ] AC-02.9: The `query()` call is wrapped in `asyncio.wait_for()` with a 240-second timeout (the Agent SDK does not expose a native timeout parameter). If the timeout fires, a 504 error is returned. This is less than LiteLLM proxy's 300s default, allowing graceful error propagation.

---

### REQ-03: MCP SQLite Connectivity

**Description**: The Agent SDK is configured with an MCP SQLite server that provides database access to the demo dataset.

**Acceptance Criteria**:
- [ ] AC-03.1: MCP server is configured via `ClaudeAgentOptions(mcp_servers={...})` using `McpStdioServerConfig`
- [ ] AC-03.2: The MCP server command launches `@modelcontextprotocol/server-sqlite` via `npx -y` with the database file path as an argument. **Prerequisite**: Node.js (with npx) must be available in the runtime environment.
- [ ] AC-03.3: The database file path is configurable via environment variable `CLAUDE_DA_DB_PATH`
- [ ] AC-03.4: A demo SQLite database is provided with an e-commerce schema:
  - `customers` (id, name, email, tier, created_at)
  - `products` (id, name, category, price)
  - `orders` (id, customer_id, status, created_at)
  - `order_items` (id, order_id, product_id, quantity, unit_price)
- [ ] AC-03.5: Demo database is populated with realistic sample data (minimum 50 customers, 200 orders, 500 order items) distributed across at least 6 calendar months with varied order counts per month to support meaningful trend analysis
- [ ] AC-03.6: The agent can successfully execute `SELECT` queries against the demo database and receive results

---

### REQ-04: Data Analyst System Prompt with Schema Injection

**Description**: The provider constructs a system prompt that gives Claude the role of a data analyst with knowledge of the connected database schema.

**Acceptance Criteria**:
- [ ] AC-04.1: System prompt defines the agent's role as a data analyst for internal use
- [ ] AC-04.2: System prompt includes the database schema (table names, column names, column types, primary/foreign key relationships)
- [ ] AC-04.3: Schema is discovered at startup by opening a separate read-only SQLite connection directly to `CLAUDE_DA_DB_PATH` and querying `sqlite_master` (not via MCP — avoids the complexity of running an Agent SDK session during initialization)
- [ ] AC-04.4: System prompt instructs the agent to: explain insights (not just raw data), note trends and anomalies, use read-only queries only, limit result sets
- [ ] AC-04.5: System prompt instructs the agent to respond conversationally to non-data questions without using database tools
- [ ] AC-04.6: Schema discovery failure at startup is a fatal error — the system refuses to start with a clear error message
- [ ] AC-04.7: System prompt total size (role + schema + rules) is under 12,000 characters for the demo schema (~3k tokens). This keeps the per-request baseline cost under $0.01 and leaves ample context window for the user's question and agent reasoning.

---

### REQ-05: Read-Only Safety

**Description**: Multiple hard enforcement layers prevent the agent from modifying data or escaping the MCP sandbox.

**Acceptance Criteria**:
- [ ] AC-05.1: `allowed_tools` restricts the agent to MCP database tools only (using wildcard pattern `mcp__sqlite__*` or equivalent)
- [ ] AC-05.2: `disallowed_tools` explicitly includes `Bash`, `Write`, `Edit` — these tools are never available to the agent
- [ ] AC-05.3: The demo SQLite database file is read-only enforced via filesystem permissions (`chmod 444`). The MCP SQLite server receives the plain file path. This is the primary mechanism; if the MCP server also supports URI parameters (`?mode=ro`), that is an additional layer.
- [ ] AC-05.4: On startup, the system attempts a write operation against the database and verifies it fails. If the write succeeds, startup aborts with error: "Database is not read-only. Refusing to start."
- [ ] AC-05.5: Input length limit: user messages exceeding a configurable character limit (default: 10,000 characters) are rejected with HTTP 400 before reaching the Agent SDK
- [ ] AC-05.6: System prompt includes read-only instructions as a soft guardrail (supplementary to hard enforcement)

---

### REQ-06: Structured Audit Logging

**Description**: Every request produces a structured log entry containing all information needed to trace an insight back to its source queries.

**Acceptance Criteria**:
- [ ] AC-06.1: Each request is assigned a unique session ID (UUID v4)
- [ ] AC-06.2: A single structured log entry (JSON) is emitted per request containing: session_id, timestamp, user_question, sql_queries_executed (ordered list), query_results_summary (row counts and column names per query), final_response, metadata (model, prompt_tokens, completion_tokens, cost_estimate_usd, duration_seconds, tool_call_count). Cost estimate is calculated as `(prompt_tokens * input_price + completion_tokens * output_price)` using published pricing for the configured model. If token counts are unavailable from the SDK, cost_estimate is set to `null`.
- [ ] AC-06.3: Log output destination is configurable via `CLAUDE_DA_LOG_OUTPUT` env var: `stdout` (default), `file`, or `both`
- [ ] AC-06.4: When output is `file` or `both`, logs are written to `CLAUDE_DA_LOG_FILE` (default: `./claude-da-audit.jsonl`) in JSON Lines format (one JSON object per line)
- [ ] AC-06.5: SQL queries are captured by inspecting Agent SDK messages during iteration — specifically, `AssistantMessage` objects containing tool use blocks where the tool name matches `mcp__sqlite__*`. The SQL text is extracted from the tool call arguments.
- [ ] AC-06.6: Default verbosity logs query summaries (row count, column names). When `CLAUDE_DA_LOG_VERBOSE=true`, full result sets are included.
- [ ] AC-06.7: Audit log is written after the response is sent to the client (non-blocking)
- [ ] AC-06.8: Logging failures do not cause request failures — errors are logged to stderr and the request completes normally

---

### REQ-07: Environment Variable Configuration

**Description**: All configurable values are set via environment variables with sensible defaults.

**Acceptance Criteria**:
- [ ] AC-07.1: The following environment variables are supported:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key for Claude |
| `CLAUDE_DA_DB_PATH` | `./demo.db` | Path to SQLite database file |
| `CLAUDE_DA_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `CLAUDE_DA_MAX_TURNS` | `10` | Max agentic loop iterations per request |
| `CLAUDE_DA_MAX_BUDGET_USD` | `0.50` | Max spend per request |
| `CLAUDE_DA_INPUT_MAX_CHARS` | `10000` | Max user input length |
| `CLAUDE_DA_LOG_OUTPUT` | `stdout` | Audit log destination: stdout, file, both |
| `CLAUDE_DA_LOG_FILE` | `./claude-da-audit.jsonl` | Audit log file path (when output=file/both) |
| `CLAUDE_DA_LOG_VERBOSE` | `false` | Include full query results in audit log |

- [ ] AC-07.2: Missing `ANTHROPIC_API_KEY` causes startup failure with clear error message
- [ ] AC-07.3: Invalid values for numeric variables (e.g., `CLAUDE_DA_MAX_TURNS=abc`) cause startup failure with clear error message
- [ ] AC-07.4: All defaults are documented in a README section

---

## 3. E-Commerce Demo Dataset Schema

```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL CHECK(tier IN ('free', 'pro', 'enterprise')),
    created_at TEXT NOT NULL  -- ISO 8601
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL CHECK(status IN ('pending', 'completed', 'cancelled', 'refunded')),
    created_at TEXT NOT NULL  -- ISO 8601
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
```

This schema supports natural business questions like:
- "What were our top 10 customers by revenue last month?"
- "Which product category has the highest growth?"
- "What's our monthly revenue trend over the past 6 months?"
- "How many enterprise customers ordered last quarter?"

---

## 4. Error Response Format

All error responses follow OpenAI's error format:

```json
{
  "error": {
    "message": "descriptive error message",
    "type": "invalid_request_error | server_error | rate_limit_error",
    "code": "input_too_long | database_unavailable | query_timeout | agent_timeout | rate_limited"
  }
}
```

| Scenario | HTTP Status | Type | Code |
|---|---|---|---|
| Input exceeds length limit | 400 | `invalid_request_error` | `input_too_long` |
| MCP database unreachable | 503 | `server_error` | `database_unavailable` |
| Query timeout (30s) | 504 | `server_error` | `query_timeout` |
| Agent SDK timeout (240s) | 504 | `server_error` | `agent_timeout` |
| Anthropic API rate limited | 429 | `rate_limit_error` | `rate_limited` |
| Agent exhausts max_turns | 200 | (normal response) | (best-effort answer) |

---

## 5. Boundaries & Exclusions

### In Scope
- Single SQLite database
- Single model (configurable via env var)
- Stateless requests (no conversation memory between requests)
- Text-only responses (no charts, files, or structured data formats)
- Single-user / low-concurrency

### Out of Scope (per PRD Section 6.2)
- PostgreSQL, MySQL, or other database types
- YAML configuration files
- Docker Compose packaging
- Hardened prompt sanitization
- Health endpoints
- Capability profiles / virtual API keys
- Contextual schema injection
- Conversation memory / sessions
- Result caching, Langfuse integration, action transparency

---

## 6. Testing Strategy

### Unit Tests
- Provider registration: verify `claude-da/analyst` model is routable
- Input validation: verify length limit enforcement and error response format
- Config loading: verify env var parsing, defaults, and validation errors
- Audit log formatting: verify JSON structure, field presence, JSONL format

### Integration Tests (require ANTHROPIC_API_KEY)
- Smoke test: Agent SDK → MCP SQLite → query execution → response (PRD Section 10 pre-implementation gate)
- End-to-end: `POST /v1/chat/completions` → data question → response contains insight referencing real data
- Streaming: `POST /v1/chat/completions` with `stream=true` → valid SSE chunks → final chunk has `finish_reason=stop`
- Non-data question: send "what's 2+2?" → response does not invoke database tools
- Read-only enforcement: verify agent cannot execute write operations

### Tests That Cannot Run in CI
- Integration tests require a live `ANTHROPIC_API_KEY` and will be skipped if the key is not set
- All unit tests run without external dependencies
