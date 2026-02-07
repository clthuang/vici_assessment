# Claude-DA: Database Analyst LiteLLM Provider

Claude-DA wraps a Claude-powered database analyst agent as a LiteLLM custom provider, exposing it through an OpenAI-compatible API. The agent uses the Model Context Protocol (MCP) to execute read-only SQLite queries and answer natural language questions about your data.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Seed the demo database
uv run python scripts/seed_demo_db.py

# 3. Start the LiteLLM server
ANTHROPIC_API_KEY=your-key uv run litellm --config litellm_config.yaml
```

The server runs on `http://localhost:4000` and is compatible with any OpenAI SDK or curl.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| ANTHROPIC_API_KEY | (required) | Anthropic API key |
| CLAUDE_DA_DB_PATH | ./demo.db | Path to SQLite database |
| CLAUDE_DA_MODEL | claude-sonnet-4-5-20250929 | Claude model identifier |
| CLAUDE_DA_MAX_TURNS | 10 | Maximum agent conversation turns |
| CLAUDE_DA_MAX_BUDGET_USD | 0.50 | Maximum spend per session |
| CLAUDE_DA_INPUT_MAX_CHARS | 10000 | Maximum user input length |
| CLAUDE_DA_LOG_OUTPUT | stdout | Audit log destination (stdout/file/both) |
| CLAUDE_DA_LOG_FILE | ./claude-da-audit.jsonl | JSONL audit log path |
| CLAUDE_DA_LOG_VERBOSE | false | Include full query results in audit |

## Example Usage

### Non-streaming

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-da/analyst",
    "messages": [{"role": "user", "content": "How many customers are in each tier?"}]
  }'
```

### Streaming

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-da/analyst",
    "messages": [{"role": "user", "content": "What are the top 5 products by revenue?"}],
    "stream": true
  }'
```

## Architecture

Claude-DA implements a LiteLLM custom provider that wraps the Claude Agent SDK with an MCP SQLite server for read-only database access. The architecture includes three layers of safety:

1. **Tool allowlist**: Only the SQLite MCP server is registered with the agent
2. **Tool blocklist**: Database write operations are explicitly denied at the prompt level
3. **Filesystem permissions**: The SQLite connection is opened in read-only mode with URI parameters

The agent uses Claude Sonnet 4.5 by default to interpret user questions, generate SQL queries, and synthesize natural language responses. All database interactions and cost metrics are logged to a JSONL audit trail for compliance and debugging.
