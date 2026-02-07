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
github-claude-skills/    # Claude Code skill plugin
  .claude-plugin/        # Plugin manifest
  skills/                # Skill definitions (SKILL.md + references)
  tests/                 # Validation suite
```

## SubTerminator

CLI tool that automates subscription cancellation flows using LLM-driven browser orchestration via Playwright MCP. It navigates retention offers, exit surveys, and confusing dialogs while keeping the human in control of irreversible actions.

- **Product docs:** [subterminator/README.md](subterminator/README.md)
- **Developer guide:** [subterminator/README_FOR_DEV.md](subterminator/README_FOR_DEV.md)

## GitHub Claude Skills

Claude Code skill plugin that wraps GitHub CI/CD capabilities as AI-driven skills. The first skill, **GitHub CI/CD Guardian**, diagnoses pipeline failures and audits workflow security for GitHub Actions.

- **Skill docs:** [github-claude-skills/README.md](github-claude-skills/README.md)

## Tech Stack

- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- [Typer](https://typer.tiangolo.com/) CLI framework
- Claude API (LLM orchestration) via LangChain
- [Playwright MCP](https://github.com/anthropics/mcp) for browser control
- GitHub Actions CI/CD
