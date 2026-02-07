# Stock Backtester

Statistical arbitrage backtesting with Kelly criterion sizing and Monte Carlo ruin analysis.

> **Disclaimer:** This tool uses survivorship-biased data from yfinance (only currently-listed tickers). Results may overstate historical performance. This is an educational/assessment tool, not investment advice.

## Table of Contents

- [Introduction](#introduction)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
  - [`backtest run`](#backtest-run)
  - [`backtest simulate`](#backtest-simulate)
  - [`backtest verify`](#backtest-verify)
- [Architecture](#architecture)
- [Limitations](#limitations)
- [Theoretical Appendix](#theoretical-appendix)
- [Development](#development)
- [Dependencies](#dependencies)

---

## Introduction

**What it does:** Runs vectorized backtests over historical price data, computes risk-adjusted performance metrics (Sharpe, Sortino, drawdown), estimates optimal position sizing via the Kelly criterion, and evaluates ruin probability through Monte Carlo simulation.

**Who it's for:** Quantitative finance students, code reviewers, and anyone exploring backtesting mechanics.

**What it is not:** Not a trading system. No real-time data, no order execution, no short-selling, no dynamic rebalancing. Output is CLI-only (TABLE or JSON).

---

## Quick Start

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv)

```bash
cd stock-backtester
uv sync
backtest run --symbols AAPL,MSFT
```

This fetches AAPL and MSFT price history from yfinance, runs an equal-weight backtest with default parameters, and prints performance metrics, Kelly analysis, and a capital efficiency frontier table.

---

## CLI Reference

### `backtest run`

Run a historical backtest over real market data.

```bash
backtest run --symbols AAPL,MSFT
backtest run --symbols AAPL,MSFT --start 2021-01-01 --end 2024-01-01 --json
```

| Option | Default | Description |
|--------|---------|-------------|
| `--symbols` | *(required)* | Comma-separated stock symbols |
| `--start` | `2020-01-01` | Start date |
| `--end` | `2025-01-01` | End date |
| `--strategy` | `equal-weight` | Strategy name (`equal-weight` or `always-long`) |
| `--commission` | `0.001` | Commission per share ($) |
| `--slippage-k` | `0.5` | Slippage coefficient (multiplied by trailing volatility) |
| `--ruin-threshold` | `0.01` | Ruin probability threshold for critical Kelly |
| `--drawdown-level` | `0.50` | Drawdown level (fraction) defining ruin |
| `--json` | `false` | Output as JSON instead of TABLE |

### `backtest simulate`

Run Monte Carlo simulation with GBM-generated synthetic paths.

```bash
backtest simulate --symbols AAPL,MSFT
backtest simulate --symbols AAPL,MSFT --paths 500 --seed 123
```

| Option | Default | Description |
|--------|---------|-------------|
| `--symbols` | *(required)* | Comma-separated stock symbols |
| `--start` | `2020-01-01` | Start date |
| `--end` | `2025-01-01` | End date |
| `--strategy` | `equal-weight` | Strategy name |
| `--paths` | `200` | Number of Monte Carlo paths |
| `--seed` | `42` | Random seed for reproducibility |
| `--commission` | `0.001` | Commission per share ($) |
| `--slippage-k` | `0.5` | Slippage coefficient |
| `--ruin-threshold` | `0.01` | Ruin probability threshold |
| `--drawdown-level` | `0.50` | Drawdown level for ruin |
| `--json` | `false` | Output as JSON |

### `backtest verify`

Run the built-in verification suite: 8 acceptance criteria tests against deterministic and synthetic data.

```bash
backtest verify
backtest verify --json
```

| Option | Default | Description |
|--------|---------|-------------|
| `--seed` | `42` | Random seed for stochastic tests |
| `--json` | `false` | Output as JSON |

**Acceptance criteria summary:**

| AC | Name | Verifies |
|----|------|----------|
| AC-1 | Deterministic returns | Equity from 1% daily return matches `1.01^10 - 1` (tol: 1e-10) |
| AC-1b | Multi-symbol aggregation | Cross-sectional simple-return aggregation (tol: 1e-4) |
| AC-2 | Look-ahead prevention | Perfect foresight strategy degraded by `shift(1)` |
| AC-3 | Slippage invariant | Net returns strictly less than gross when costs > 0 |
| AC-4 | Kelly analytical | f* = mu/sigma^2 = 5.0 for deterministic inputs (tol: 1e-6) |
| AC-5 | Frontier consistency | g(f*) = 100%, g(2f*) = 0%, ruin monotonic |
| AC-6 | GBM moments | Simulated mean/std match theory (2 SE / 5% rtol) |
| AC-7 | Zero-edge Sharpe | Mean Sharpe across 200 zero-drift paths ~ 0 (2 SE) |

---

## Architecture

The system is built on three pillars:

1. **Vectorized Backtesting Engine** — Computes portfolio returns with transaction cost modeling (slippage + commission). Modules: `data.py`, `execution.py`, `strategy.py`, `engine.py`, `metrics.py`.

2. **Kelly Criterion & Ruin Analysis** — Estimates optimal bet fraction (f*), half-Kelly sizing, and probability of drawdown-based ruin via continuous approximation. Module: `kelly.py`.

3. **Monte Carlo Simulation** — Calibrates GBM from historical data, generates synthetic paths, runs backtests per path at half-Kelly sizing, and compares empirical vs. theoretical ruin rates. Module: `simulation.py`.

For the full module dependency graph, sequence diagrams, and line-by-line reference, see [docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md).

---

## Limitations

### Data Quality

- **Survivorship bias:** yfinance only provides data for currently-listed tickers. Delisted stocks are excluded, which overstates historical portfolio performance.
- **Adjusted prices:** `auto_adjust=True` adjusts for splits and dividends. This is standard but hides the raw price series.
- **Minimum data:** Requires at least 30 trading days after date alignment (`data.py:20-23`, `data.py:59-62`).

### Model Assumptions

- **Equal-weight only:** No dynamic rebalancing, mean-variance optimization, or risk-parity. Two strategy names exist (`equal-weight`, `always-long`) but they produce identical behavior.
- **Linear slippage:** `slippage = k * trailing_vol * |delta_w|`. Real market impact is typically concave (square-root model), meaning this may understate costs for large trades.
- **Commission model:** `commission_per_share / close_price * |delta_w|` — a simplified fractional cost, not actual broker fee schedules.
- **GBM paths:** Constant drift and volatility, no regime switching, no jump-diffusion. Each symbol's paths are generated independently with `seed+i` — no cross-asset correlation.
- **Kelly assumes normality:** The `f* = mu/sigma^2` formula is optimal for normally distributed returns. Fat tails (which real returns exhibit) make full Kelly dangerously aggressive, which is why the system defaults to half-Kelly sizing.

### Ruin Analysis Caveats

- **Continuous approximation:** The ruin formula `P = D^(2/alpha - 1)` is a continuous-time result applied to discrete daily returns.
- **Drawdown-based:** Ruin is defined as max drawdown exceeding `drawdown_level`, not as absolute capital loss.
- **Half-Kelly sizing:** Monte Carlo paths are scaled by `half_kelly` (`simulation.py:153`), not full Kelly.

### Scope

- No short-selling, no streaming data, no web UI, no plots.
- CLI-only output: TABLE (fixed-width) or JSON.
- No portfolio optimization beyond equal weighting.

---

## Theoretical Appendix

### Return Conventions

Portfolio returns are aggregated **cross-sectionally using simple returns**, then converted to log-returns for time-series accumulation:

```
R_p = sum(w_i * R_i)        # simple-return aggregation (engine.py:28)
r_p = ln(1 + R_p)           # convert to log-return (engine.py:31)
```

**Why not log-return aggregation?** Jensen's inequality: `sum(ln(1+R_i))` != `ln(1 + sum(R_i))`. Summing log-returns across assets introduces systematic bias. AC-1b (`simulation.py:239-303`) explicitly tests that the engine handles this correctly.

### Sharpe Ratio

```
Sharpe = (mean(r) * 252) / (std(r) * sqrt(252))
```

- Uses **ddof=1** (sample standard deviation with Bessel's correction) — `metrics.py:16`
- Returns 0.0 if `std = 0` or `NaN` — `metrics.py:19-20`

### Sortino Ratio

```
dd_daily = sqrt(sum(min(r, 0)^2) / N)
dd_annual = dd_daily * sqrt(252)
Sortino = (mean(r) * 252) / dd_annual
```

- **Full-count convention:** `N` = total number of bars, not just negative bars — `metrics.py:26`
- Returns `inf` when `dd_annual = 0` (no downside) — `metrics.py:29`
- **Why full-count?** Using only negative-bar count inflates the denominator's sensitivity to sample composition. The full-count convention (Sortino & Price, 1994) provides a more stable estimate by anchoring the denominator to total observations.

### Kelly Criterion

```
f* = mu / sigma^2
half_kelly = f* / 2
```

- Uses **ddof=0** (population variance, MLE plug-in) — `kelly.py:55`
- **ddof=1 vs ddof=0:** Kelly is a plug-in estimator that needs the MLE (maximum likelihood) variance. Sharpe/Sortino are inferential statistics that need sample variance with Bessel correction. This is an intentional design choice, not a bug.
- Reference: `kelly.py:42-62`

### Ruin Probability & Critical Kelly

**Ruin probability** (continuous approximation):

```
P(ruin) = D^(2/alpha - 1)    where alpha = f / f*
```

- Special cases: `f <= 0` -> `P = 0.0`; `alpha >= 2` -> `P = 1.0` — `kelly.py:13-17`
- `D` = drawdown level (e.g., 0.50 for 50% drawdown)

**Critical Kelly fraction** — the largest `f` that keeps ruin probability below threshold:

```
f_crit = 2 * mu / (sigma^2 * (ln(P_threshold) / ln(D) + 1))
```

- Returns `None` if `mu <= 0` or `f_crit >= 2*f*` — `kelly.py:31-38`
- Reference: `kelly.py:25-39`

### Capital Efficiency Frontier

Growth rate as a fraction of the maximum (at full Kelly):

```
g(alpha) = (2 * alpha - alpha^2) * 100     # percentage of max growth
```

Evaluated at 6 points: `alpha = [0.25, 0.50, 0.75, 1.00, 1.50, 2.00]` of `f*`.

Key values:
- `g(1.0) = 100%` — full Kelly achieves maximum growth
- `g(0.50) = 75%` — half-Kelly captures 75% of growth with much lower ruin risk
- `g(2.0) = 0%` — twice Kelly produces zero long-run growth (certain ruin)

Reference: `kelly.py:80-93`

### GBM Simulation

Geometric Brownian Motion path generation:

```
S_t = S_0 * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)
```

- **Ito correction** (`-sigma^2/2`): ensures `E[S_T] = S_0 * exp(mu * T)` — `simulation.py:52`
- `s0 = 100.0` (arbitrary starting price) — `simulation.py:47`
- **Calibration:** log-return mean/std with ddof=1, annualized by `*252` and `*sqrt(252)` — `simulation.py:33-36`
- Reference: `simulation.py:41-59`

### Transaction Cost Model

**Slippage** (volatility-proportional):

```
slippage = k * trailing_vol(20, ddof=1) * |delta_w|
```

- `trailing_vol`: 20-bar rolling std with expanding fallback for early bars, NaN filled to 0.0 — `execution.py:30-37`
- `delta_w = weights.diff().fillna(weights)` — first bar's full weight counts as a trade — `execution.py:50`
- Reference: `execution.py:57-59`

**Commission** (per-share, converted to fractional):

```
commission = (commission_per_share / close_price) * |delta_w|
```

- Reference: `execution.py:61-63`

### Equity Curve & Other Metrics

- **Equity curve:** `exp(cumsum(net_log_returns))`, normalized to 1.0 at `warmup_end_idx` — `engine.py:49-52`
- **Max drawdown:** Negative fraction (e.g., -0.25 means 25% peak-to-trough decline) — `metrics.py:34-38`
- **Drawdown duration:** Consecutive bars where `equity < running_max` — `metrics.py:40-51`
- **Win rate:** `count(positive_bars) / count(nonzero_bars)` — excludes zero-return bars — `metrics.py:53-58`
- **Annualized return:** `exp(mean_r * 252) - 1` (geometric, continuous compounding) — `metrics.py:61`

---

## Development

```bash
uv sync --group dev
uv run pytest                  # 88 tests, 93% coverage
uv run ruff check src/         # Lint
uv run pyright src/             # Type check
```

For module-level reference, dependency graphs, and extension guides, see [docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md).

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | >= 2.0 | Time series data handling |
| numpy | >= 1.26 | Vectorized numerical computation |
| scipy | >= 1.12 | Statistical functions |
| yfinance | >= 0.2.36 | Historical price data from Yahoo Finance |
| typer[all] | >= 0.9 | CLI framework |
