# VICI Claude Code 7-Day Challenge

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The [VICI Claude Code 7-Day Challenge](subterminator/docs/prds/VICI%20Claude%20Code%207-Day%20Challenge_%20Jan%202026.pdf) evaluates engineering design thinking, code quality, and AI tool integration. The challenge offers four tasks at varying difficulty levels — this project attempts **all four**.

## Task Overview

| # | Task | Difficulty | Status |
|---|------|------------|--------|
| 4 | [SubTerminator (Browser Automation)](#task-4-subterminator-browser-automation) | Hard | Completed |
| 1 | [US Stock Backtesting System](#task-1-us-stock-backtesting-system) | Easy | Not Started |
| 2 | [Claude CLI → LiteLLM Endpoint](#task-2-claude-cli--litellm-endpoint) | Medium | Not Started |
| 3 | [GitHub CI/CD → Claude Skills](#task-3-github-cicd--claude-skills) | Medium | Not Started |

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

## Task 1: US Stock Backtesting System

US stock backtesting system (美股回測系統) for evaluating trading strategies against historical market data.

**Status:** Not Started

---

## Task 2: Claude CLI → LiteLLM Endpoint

Wrap the Claude CLI as a LiteLLM-compatible endpoint (封裝 Claude CLI 變成 LiteLLM endpoint), enabling Claude Code to be used as a backend through the OpenAI-compatible API.

**Status:** Not Started

---

## Task 3: GitHub CI/CD → Claude Skills

Wrap GitHub CI/CD pipelines as Claude Skills (封裝 GitHub CI/CD 成為 Claude Skills), allowing CI/CD workflows to be triggered and managed through Claude.

**Status:** Not Started

---

## Project Structure

```
subterminator/           # Task 4: Browser automation tool
  src/subterminator/     #   Source code
  tests/                 #   Test suite
  docs/                  #   Architecture, features, PRDs
  pyproject.toml         #   Project config
.github/workflows/       # CI/CD (lint, test, build)
```

## Tech Stack

- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- [Typer](https://typer.tiangolo.com/) CLI framework
- Claude API (LLM orchestration) via LangChain
- [Playwright MCP](https://github.com/anthropics/mcp) for browser control
- GitHub Actions CI/CD

## License

MIT License — see LICENSE file for details.
