# Stock Backtester

Statistical arbitrage backtesting system with Kelly criterion sizing and Monte Carlo simulation.

Given a pair (or basket) of stock symbols, the system runs a vectorized backtest over historical price data, computes risk-adjusted performance metrics, estimates optimal position sizing via the Kelly criterion, and evaluates ruin probability. Monte Carlo simulation stress-tests the strategy across synthetic return paths.

**VICI Challenge Task 1**

---

## Quick Start

```bash
cd stock-backtester
uv sync
backtest run --symbols AAPL,MSFT
```

## Installation

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/your-repo/vici_assessment-stock-backtester.git
cd vici_assessment-stock-backtester/stock-backtester

# Option A: uv (recommended)
uv sync

# Option B: pip
pip install -e ".[dev]"
```

## Usage

### `backtest run` -- Historical Backtest

Runs a backtest over real market data fetched via yfinance.

```bash
backtest run --symbols AAPL,MSFT
backtest run --symbols AAPL,MSFT --start 2021-01-01 --end 2024-01-01 --json
```

| Option | Default | Description |
|--------|---------|-------------|
| `--symbols` | (required) | Comma-separated stock symbols |
| `--start` | `2020-01-01` | Start date |
| `--end` | `2025-01-01` | End date |
| `--strategy` | `equal-weight` | Strategy name |
| `--commission` | `0.001` | Commission per share |
| `--slippage-k` | `0.5` | Slippage coefficient |
| `--ruin-threshold` | `0.01` | Ruin probability threshold |
| `--drawdown-level` | `0.50` | Drawdown level for ruin calculation |
| `--json` | `false` | Output as JSON |

### `backtest simulate` -- Monte Carlo Simulation

Generates synthetic return paths to stress-test the strategy.

```bash
backtest simulate --symbols AAPL,MSFT
backtest simulate --symbols AAPL,MSFT --paths 500 --seed 123
```

| Option | Default | Description |
|--------|---------|-------------|
| `--symbols` | (required) | Comma-separated stock symbols |
| `--start` | `2020-01-01` | Start date |
| `--end` | `2025-01-01` | End date |
| `--strategy` | `equal-weight` | Strategy name |
| `--paths` | `200` | Number of Monte Carlo paths |
| `--seed` | `42` | Random seed |
| `--commission` | `0.001` | Commission per share |
| `--slippage-k` | `0.5` | Slippage coefficient |
| `--ruin-threshold` | `0.01` | Ruin probability threshold |
| `--drawdown-level` | `0.50` | Drawdown level for ruin calculation |
| `--json` | `false` | Output as JSON |

### `backtest verify` -- Known-Answer Verification

Runs a built-in verification suite against deterministic test cases.

```bash
backtest verify
backtest verify --json
```

| Option | Default | Description |
|--------|---------|-------------|
| `--seed` | `42` | Random seed for verification |
| `--json` | `false` | Output as JSON |

## Architecture

The system is built on three pillars:

1. **Vectorized Backtesting Engine** -- Computes portfolio returns with transaction cost modeling (commission + slippage). Modules: `data.py`, `execution.py`, `strategy.py`, `engine.py`, `metrics.py`.

2. **Kelly Criterion & Ruin Analysis** -- Estimates optimal bet fraction and probability of drawdown-based ruin. Module: `kelly.py`.

3. **Monte Carlo Simulation** -- Bootstraps return paths from historical data to produce confidence intervals and ruin probability distributions. Module: `simulation.py`.

## Development

```bash
uv sync --group dev
uv run pytest                  # Run tests (88 tests, 93% coverage)
uv run ruff check src/         # Lint
uv run pyright src/             # Type check
```

## Dependencies

| Package | Purpose |
|---------|---------|
| pandas | Time series data handling |
| numpy | Vectorized numerical computation |
| scipy | Statistical functions |
| yfinance | Historical price data |
| typer | CLI framework |
