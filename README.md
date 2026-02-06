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
```

## SubTerminator

CLI tool that automates subscription cancellation flows using LLM-driven browser orchestration via Playwright MCP. It navigates retention offers, exit surveys, and confusing dialogs while keeping the human in control of irreversible actions.

- **Product docs:** [subterminator/README.md](subterminator/README.md)
- **Developer guide:** [subterminator/README_FOR_DEV.md](subterminator/README_FOR_DEV.md)

## Tech Stack

- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- [Typer](https://typer.tiangolo.com/) CLI framework
- Claude API (LLM orchestration) via LangChain
- [Playwright MCP](https://github.com/anthropics/mcp) for browser control
- GitHub Actions CI/CD
