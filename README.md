# VICI Assessment

Monorepo for the [VICI Claude Code 7-Day Challenge](subterminator/docs/prds/VICI%20Claude%20Code%207-Day%20Challenge_%20Jan%202026.pdf) assessment. Demonstrates engineering design thinking, code quality, and AI tool integration through a real-world browser automation project.

## Repository Structure

```
.github/workflows/       # CI/CD (lint, test, build)
subterminator/           # SubTerminator CLI project
  src/subterminator/     # Source code
  tests/                 # Test suite
  docs/                  # Architecture, features, PRDs
  pyproject.toml         # Project config
claude-litellm/          # Claude-DA data analysis project
  src/claude_da/         # Source code
  tests/                 # Test suite (unit + integration)
  docs/                  # Technical guide, features, brainstorms
  scripts/               # Database seeder
  pyproject.toml         # Project config
```

## SubTerminator

CLI tool that automates subscription cancellation flows using LLM-driven browser orchestration via Playwright MCP. It navigates retention offers, exit surveys, and confusing dialogs while keeping the human in control of irreversible actions.

- **Product docs:** [subterminator/README.md](subterminator/README.md)
- **Developer guide:** [subterminator/README_FOR_DEV.md](subterminator/README_FOR_DEV.md)

## Claude-DA

LiteLLM custom provider that wraps the Claude Agent SDK to expose a natural language data analysis API via any OpenAI-compatible endpoint. Point it at a read-only SQLite database and query it in plain English through `/v1/chat/completions`.

- **Product docs:** [claude-litellm/README.md](claude-litellm/README.md)
- **Assessment report:** [claude-litellm/REPORT.md](claude-litellm/REPORT.md)
- **Technical guide:** [claude-litellm/docs/TECHNICAL_GUIDE.md](claude-litellm/docs/TECHNICAL_GUIDE.md)

## Tech Stack

### SubTerminator
- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- [Typer](https://typer.tiangolo.com/) CLI framework
- Claude API (LLM orchestration) via LangChain
- [Playwright MCP](https://github.com/anthropics/mcp) for browser control

### Claude-DA
- Python 3.11+, [uv](https://github.com/astral-sh/uv)
- [LiteLLM](https://github.com/BerriAI/litellm) custom provider
- [Claude Agent SDK](https://github.com/anthropics/claude-code-sdk-python) with MCP SQLite server
- Structured JSONL audit logging

### Shared
- GitHub Actions CI/CD
