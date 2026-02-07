# Claude-DA

Ask questions about your data in plain English. Get SQL-backed insights via any OpenAI-compatible client.

Claude-DA is a LiteLLM custom provider that wraps a Claude-powered data analyst agent behind an OpenAI-compatible API. You send a natural language question, and an autonomous agent writes SQL, executes it against a SQLite database through the Model Context Protocol (MCP), and returns an answer in plain language. Any tool that speaks the OpenAI chat completions format -- curl, the OpenAI Python SDK, LangChain, etc. -- works without modification.


## What Claude-DA Does

### How It Works

1. You send a question to the `/v1/chat/completions` endpoint (e.g., "What are the top 5 products by revenue?").
2. The Claude agent interprets your question, generates one or more SQL queries, and decides the right analytical approach.
3. Each SQL query is executed read-only against the SQLite database through the MCP sqlite server.
4. The agent synthesizes the query results into a natural language answer with formatting, trends, and context.

The agent is autonomous: it can run multiple queries in sequence, refine its approach based on intermediate results, and ask clarifying follow-up queries against the database -- all within a single request.

### Example Questions

- "How many customers are in each tier?"
- "What are the top 5 products by revenue?"
- "Show me the monthly order trend for 2024."
- "Which product category has the highest average order value?"
- "Compare the cancellation rate across customer tiers."

### Architecture

Claude-DA has three layers. The **LiteLLM proxy** provides the OpenAI-compatible API surface and handles request routing, streaming, and error formatting. The **Claude Agent SDK** manages the reasoning loop: it receives the user question plus a system prompt with the database schema, decides which queries to run, and synthesizes the final answer. The **MCP SQLite server** (`@modelcontextprotocol/server-sqlite`) provides the actual database access tools -- the agent calls these tools and never touches the filesystem directly.


## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required for the Agent SDK |
| Node.js | 18+ | Provides `npx`, used to launch the MCP sqlite server |
| uv | latest | Python package manager |
| Anthropic API key | -- | Obtain from [console.anthropic.com](https://console.anthropic.com) |

The MCP SQLite server is installed automatically via `npx` on first request. No manual npm install is needed.

### Setup

```bash
# Navigate to the claude-litellm directory
cd claude-litellm

# Install Python dependencies
uv sync

# Seed the demo database (creates demo.db with read-only permissions)
uv run python scripts/seed_demo_db.py

# Copy the environment template and add your API key
cp .env.template .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### Start the Server

```bash
uv run litellm --config litellm_config.yaml
```

The server starts on `http://localhost:4000`. The Claude agent and MCP server initialize lazily on the first request, so the first query will take longer than subsequent ones while the MCP sqlite server starts up.

### Usage Examples

#### curl (non-streaming)

Request:

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-da/analyst",
    "messages": [{"role": "user", "content": "How many customers are in each tier?"}]
  }'
```

Response:

```json
{
  "id": "chatcmpl-a1b2c3d4e5f6",
  "object": "chat.completion",
  "created": 1706900000,
  "model": "claude-da/analyst",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Here's the breakdown of customers by tier:\n\n| Tier | Count |\n|------|-------|\n| Free | 30 |\n| Pro | 17 |\n| Enterprise | 8 |\n\nThe free tier has the most customers (55% of total), followed by pro (31%) and enterprise (15%). This distribution is typical for a freemium model where the majority of users are on the free plan."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1850,
    "completion_tokens": 210,
    "total_tokens": 2060
  }
}
```

#### Python (OpenAI SDK)

```python
from openai import OpenAI

# LiteLLM proxy does not require client auth by default.
# api_key is required by the SDK but its value is not checked.
client = OpenAI(base_url="http://localhost:4000/v1", api_key="unused")

# Non-streaming
response = client.chat.completions.create(
    model="claude-da/analyst",
    messages=[{"role": "user", "content": "What are the top 5 products by revenue?"}],
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="claude-da/analyst",
    messages=[{"role": "user", "content": "Show me the monthly order trend for 2024."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

#### curl (streaming)

Request:

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-da/analyst",
    "messages": [{"role": "user", "content": "What is the average order value?"}],
    "stream": true
  }'
```

Response (SSE excerpt):

```
data: {"id":"chatcmpl-a1b2c3d4e5f6","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Based on the completed orders"},"finish_reason":null}]}

data: {"id":"chatcmpl-a1b2c3d4e5f6","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":", the average order value is **$127.43**."},"finish_reason":null}]}

data: {"id":"chatcmpl-a1b2c3d4e5f6","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Configuration

All settings are controlled through environment variables. Copy `.env.template` to `.env` to get started.

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `CLAUDE_DA_DB_PATH` | `./demo.db` | Path to SQLite database |
| `CLAUDE_DA_MODEL` | `claude-sonnet-4-5-20250929` | Claude model identifier |
| `CLAUDE_DA_MAX_TURNS` | `10` | Maximum agent conversation turns |
| `CLAUDE_DA_MAX_BUDGET_USD` | `0.50` | Maximum spend per session in USD |
| `CLAUDE_DA_INPUT_MAX_CHARS` | `10000` | Maximum user input length in characters |
| `CLAUDE_DA_LOG_OUTPUT` | `stdout` | Audit log destination (`stdout`, `file`, or `both`) |
| `CLAUDE_DA_LOG_FILE` | `./claude-da-audit.jsonl` | JSONL audit log file path |
| `CLAUDE_DA_LOG_VERBOSE` | `false` | Include full query results in audit output |


## Capabilities, Limitations, and Constraints

### Safety Model

Claude-DA enforces read-only database access through three independent layers, ordered from strongest to weakest:

1. **Filesystem permissions.** The seed script sets the SQLite file to `chmod 444` (read-only for all users). Even if the agent somehow issued a write statement, the operating system would reject it. This is the strongest guarantee because it operates below the application layer.

2. **Tool restrictions.** The agent is configured with an explicit tool allowlist (`mcp__sqlite__*` only) and a tool blocklist (`Bash`, `Write`, `Edit`). The Claude Agent SDK enforces these restrictions before any tool call reaches the MCP server.

3. **System prompt instructions.** The system prompt instructs the agent to execute only `SELECT` statements and to refuse data modification requests. This is a soft guardrail -- it relies on the model following instructions -- and is supplementary to the hard enforcement above.

### Demo Database

The seed script (`scripts/seed_demo_db.py`) creates a deterministic e-commerce database (seeded with `random.Random(42)`) with four tables:

| Table | Rows | Key Columns | Description |
|---|---|---|---|
| `customers` | 55 | id, name, email, tier, created_at | Customer accounts with tier distribution: 55% free, 30% pro, 15% enterprise |
| `products` | 25 | id, name, category, price | Products across 5 categories: Electronics, Accessories, Books, Furniture, Office Supplies |
| `orders` | 220 | id, customer_id, status, created_at | Orders spanning Jan--Oct 2024 with status distribution: 10% pending, 70% completed, 12% cancelled, 8% refunded |
| `order_items` | 550+ | id, order_id, product_id, quantity, unit_price | Line items (1--5 per order), minimum 550 guaranteed |

Relationships: `orders.customer_id` references `customers.id`; `order_items.order_id` references `orders.id`; `order_items.product_id` references `products.id`.

To use your own database, set `CLAUDE_DA_DB_PATH` to point to any SQLite file. The agent discovers the schema automatically at startup and embeds it in the system prompt.

### Performance and Cost

These are rough estimates based on the demo database with Claude Sonnet 4.5. Actual values depend on query complexity, database size, and model choice.

| Query Type | Typical Latency | Estimated Cost | Example |
|---|---|---|---|
| Simple aggregation | 5--15 seconds | ~$0.03 | "How many customers are in each tier?" |
| Multi-step analysis | 15--45 seconds | ~$0.10 | "Compare revenue by category and month" |
| Non-data question | 3--8 seconds | ~$0.01 | "What can you help me with?" |

Notes:
- **First request latency** is higher (add 5--10 seconds) because the MCP sqlite server starts via `npx` on the first request.
- The `CLAUDE_DA_MAX_BUDGET_USD` cap (default: $0.50) limits the total spend per session. The agent stops and returns a partial answer if it hits the budget limit.

### Error Handling

Errors are returned in OpenAI-compatible format:

```json
{
  "error": {
    "message": "Input length 12500 exceeds maximum 10000 characters",
    "type": "invalid_request_error",
    "code": "input_too_long"
  }
}
```

| HTTP Status | Error Code | Cause |
|---|---|---|
| 400 | `input_too_long` | Combined message content exceeds `CLAUDE_DA_INPUT_MAX_CHARS` (default: 10,000) |
| 429 | `rate_limited` | Anthropic API rate limit reached; retry after backoff |
| 503 | `database_unavailable` | MCP SQLite server failed to start or is unreachable |
| 504 | `agent_timeout` | Agent session exceeded 240-second timeout |

### Limitations

- **SQLite only.** The MCP server supports SQLite databases. PostgreSQL, MySQL, and other databases are not supported.
- **Stateless.** Each request starts a new agent session. There is no conversation memory across requests.
- **Read-only.** The agent cannot create tables, insert data, or modify the database in any way.
- **Not deterministic.** The same question can produce different SQL queries and different answers across requests. Users from deterministic API backgrounds should expect variation in phrasing, formatting, and analytical approach.
- **Fixed system prompt.** The system prompt (role definition, schema, behavioral rules) is assembled at startup and cannot be customized per-request.
- **50-row soft limit.** The system prompt instructs the agent to limit query results to 50 rows unless the user explicitly asks for more. This is a prompt-level instruction, not a hard database constraint.
- **Text-only responses.** The agent returns Markdown-formatted text. It does not generate charts, images, or file attachments.
- **Single-user oriented.** The LiteLLM proxy serves requests sequentially. It is designed for local development and demos, not production multi-tenant workloads.

### Configurable Constraints

Some constraints can be adjusted via environment variables; others are hardcoded.

**Environment variables (configurable):**

| Constraint | Variable | Default |
|---|---|---|
| Maximum input length | `CLAUDE_DA_INPUT_MAX_CHARS` | 10,000 characters |
| Maximum agent turns | `CLAUDE_DA_MAX_TURNS` | 10 turns |
| Maximum spend per session | `CLAUDE_DA_MAX_BUDGET_USD` | $0.50 |

**Hardcoded values:**

| Constraint | Value | Location |
|---|---|---|
| Agent timeout | 240 seconds | `src/claude_da/agent.py:34` |
| LiteLLM proxy timeout | Inherited from LiteLLM defaults | LiteLLM configuration |
| MCP query timeout | Inherited from MCP server defaults | MCP sqlite server |

The agent timeout (240s) is intentionally longer than typical query times to allow multi-step analysis chains to complete. If you need to adjust it, modify the `_AGENT_TIMEOUT_SECONDS` constant in `src/claude_da/agent.py`.

### Audit Logging

Every request produces a structured audit entry in JSONL format. The entry includes the user question, all SQL queries executed, the final response, and metadata (model, token counts, cost estimate, duration, tool call count).

Sample entry (with `CLAUDE_DA_LOG_VERBOSE=false`, the default):

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2024-10-15T14:30:00+00:00",
  "user_question": "How many customers are in each tier?",
  "sql_queries_executed": [
    "SELECT tier, COUNT(*) as count FROM customers GROUP BY tier ORDER BY count DESC"
  ],
  "final_response": "Here's the breakdown of customers by tier: ...",
  "metadata": {
    "model": "claude-sonnet-4-5-20250929",
    "prompt_tokens": 1850,
    "completion_tokens": 210,
    "cost_estimate_usd": 0.028,
    "duration_seconds": 8.4,
    "tool_call_count": 2
  }
}
```

Set `CLAUDE_DA_LOG_VERBOSE=true` to include full `query_results_summary` in the output. Use `CLAUDE_DA_LOG_OUTPUT=file` or `both` to write entries to `CLAUDE_DA_LOG_FILE` (default: `./claude-da-audit.jsonl`).
