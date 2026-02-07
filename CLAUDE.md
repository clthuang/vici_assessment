# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a VICI Claude Code 7-Day Challenge assessment project. The goal is to demonstrate engineering design thinking, code quality, and AI tool integration.

## Project Structure

```
.github/workflows/      # CI/CD (lint, test, build, auto-PR)
subterminator/           # SubTerminator CLI project
  src/subterminator/     # Source code
    cli/                 # CLI layer (Typer)
    mcp_orchestrator/    # AI orchestration engine
    services/            # Service registry & configs
    utils/               # Configuration & logging
  tests/                 # Test suite (unit + integration)
  docs/                  # Architecture, features, PRDs
  pyproject.toml         # Project config
claude-litellm/          # Claude-DA data analysis project
  src/claude_da/         # Source code (agent, provider, schema, config, audit, prompt)
  tests/                 # Test suite (unit + integration)
  docs/                  # Technical guide, feature specs, brainstorms
  scripts/               # Database seeder
  pyproject.toml         # Project config
```

## Development Guidelines

- Focus on engineering design over flashiness
- Prioritize code quality and maintainability
- Demonstrate practical AI tool integration
