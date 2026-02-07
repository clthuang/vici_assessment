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
stock-backtester/        # Stock Backtester project
  src/stock_backtester/  # Source code
    types.py             # Dataclasses (BacktestConfig, SimulationConfig)
    data.py              # Price data fetching (yfinance)
    strategy.py          # Strategy definitions (equal-weight)
    execution.py         # Transaction cost modeling
    engine.py            # Vectorized backtesting engine
    metrics.py           # Performance metrics (Sharpe, drawdown)
    kelly.py             # Kelly criterion & ruin analysis
    simulation.py        # Monte Carlo simulation
    report.py            # Output formatting (table/JSON)
    cli.py               # CLI entry point (Typer)
  tests/                 # Test suite (88 tests, 93% coverage)
  pyproject.toml         # Project config
```

## Development Guidelines

- Focus on engineering design over flashiness
- Prioritize code quality and maintainability
- Demonstrate practical AI tool integration
