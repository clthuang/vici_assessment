# VICI Claude Code 7-Day Challenge

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The [VICI Claude Code 7-Day Challenge](subterminator/docs/prds/VICI%20Claude%20Code%207-Day%20Challenge_%20Jan%202026.pdf) evaluates engineering design thinking, code quality, and AI tool integration. The challenge offers four tasks at varying difficulty levels — this project attempts **all four**.

## Task Overview

| # | Task | Difficulty | Status |
|---|------|------------|--------|
| 4 | [SubTerminator (Browser Automation)](#task-4-subterminator-browser-automation) | Hard | Completed |
| 1 | [US Stock Backtesting System](#task-1-us-stock-backtesting-system) | Easy | Not Started |
| 2 | [Claude CLI → LiteLLM Endpoint](#task-2-claude-cli--litellm-endpoint) | Medium | Completed |
| 3 | [GitHub CI/CD → Claude Skills](#task-3-github-cicd--claude-skills) | Medium | Completed |

---

## Task 4: SubTerminator (Browser Automation)

**CLI tool for automating subscription cancellations.** SubTerminator uses LLM-driven browser orchestration via Playwright MCP to navigate cancellation flows — handling retention offers, exit surveys, and confusing dialogs — while keeping you in control of the final decision.

> **Warning:** This tool automates browser interactions with subscription services. Many services prohibit automation in their Terms of Service. **Use at your own risk.**

### Key Features

- LLM-driven browser orchestration via Playwright MCP
- Human checkpoints for authentication and final confirmation
- Interactive service selection menu
- Browser session persistence via persistent profiles
- Full session logging with screenshots at every step

### Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd subterminator && uv sync && uv run playwright install chromium

# Run with dry-run mode (safe, stops at final confirmation)
uv run subterminator cancel --service netflix --dry-run
```

- **Product docs:** [subterminator/README.md](subterminator/README.md)
- **Developer guide:** [subterminator/README_FOR_DEV.md](subterminator/README_FOR_DEV.md)

---

## Task 3: GitHub CI/CD → Claude Skills

Claude Code skill plugin that wraps GitHub CI/CD capabilities as AI-driven skills. The first skill, **GitHub CI/CD Guardian**, diagnoses pipeline failures and audits workflow security for GitHub Actions.

- **Skill docs:** [github-claude-skills/README.md](github-claude-skills/README.md)

---

## Task 2: Claude CLI → LiteLLM Endpoint

LiteLLM custom provider that wraps the Claude Agent SDK to expose a natural language data analysis API via any OpenAI-compatible endpoint. Point it at a read-only SQLite database and query it in plain English through `/v1/chat/completions`.

- **Product docs:** [claude-litellm/README.md](claude-litellm/README.md)
- **Assessment report:** [claude-litellm/REPORT.md](claude-litellm/REPORT.md)
- **Technical guide:** [claude-litellm/docs/TECHNICAL_GUIDE.md](claude-litellm/docs/TECHNICAL_GUIDE.md)

---

## Task 1: US Stock Backtesting System

US stock backtesting system (美股回測系統) for evaluating trading strategies against historical market data.

**Status:** Not Started

---

## Project Structure

```
subterminator/           # Task 4: Browser automation tool
  src/subterminator/     #   Source code
  tests/                 #   Test suite
  docs/                  #   Architecture, features, PRDs
  pyproject.toml         #   Project config
github-claude-skills/    # Task 3: Claude Code skill plugin
  .claude-plugin/        #   Plugin manifest
  skills/                #   Skill definitions (SKILL.md + references)
  tests/                 #   Validation suite
claude-litellm/          # Task 2: Claude-DA data analysis
  src/claude_da/         #   Source code
  tests/                 #   Test suite (unit + integration)
  docs/                  #   Technical guide, features, brainstorms
  scripts/               #   Database seeder
  pyproject.toml         #   Project config
.github/workflows/       # CI/CD (lint, test, build)
```

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

## License

MIT License — see LICENSE file for details.
