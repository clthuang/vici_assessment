# Implementation Plan: Statistical Arbitrage Backtesting System

**Feature:** 001-stat-arb-backtester
**Spec Version:** v4
**Design Version:** v1
**Plan Version:** v2

---

## Build Order & Dependencies

The plan follows the design's dependency graph (Section 10). Each phase builds on the previous, enabling incremental testing. **TDD ordering: each phase writes tests first, then implements to pass them.** After completing each phase, run the full test suite (not just the new phase's tests) to catch regressions.

```
Phase 0: Scaffold           (no deps)
Phase 1: types.py           (no deps)
Phase 2: execution.py       (types)
Phase 3: data.py            (types)
Phase 4: strategy.py        (types)
Phase 5: engine.py          (types, execution, strategy)  → AC-1, AC-1b, AC-2, AC-3
Phase 6: metrics.py         (types)
Phase 7: kelly.py           (types)                       → AC-4, AC-5
Phase 8: simulation.py      (types, execution, strategy, data, engine, metrics, kelly)  → AC-6, AC-7
Phase 9: report.py          (types)
Phase 10: cli.py            (all modules)                 → CLI e2e tests
Phase 11: Integration & NFR (all modules)                 → full AC suite, performance
```

### AC Test Readiness Map

| AC | Requires (Phases) | Earliest Runnable |
|----|-------------------|-------------------|
| AC-1 (correct returns) | types + execution + strategy + engine | After Phase 5 |
| AC-1b (multi-symbol aggregation) | types + execution + strategy + engine | After Phase 5 |
| AC-2 (look-ahead prevention) | types + execution + strategy + engine + conftest (PerfectForesight) | After Phase 5 |
| AC-3 (slippage invariant) | types + execution + strategy + engine | After Phase 5 |
| AC-4 (Kelly analytical) | types + kelly + conftest (make_deterministic_returns) | After Phase 7 |
| AC-5 (frontier consistency) | types + kelly | After Phase 7 |
| AC-6 (GBM moments) | types + execution + simulation | After Phase 8 |
| AC-7 (zero-edge Sharpe) | types + execution + strategy + engine + simulation + metrics | After Phase 8 |

---

## Phase 0: Project Scaffold

**Goal:** Working project structure with dependencies installable.

**Steps:**
1. Create `stock-backtester/pyproject.toml` (from design Section 6)
2. Create `stock-backtester/src/stock_backtester/__init__.py` (version string)
3. Create `stock-backtester/src/stock_backtester/__main__.py` (deferred stub: `try: from .cli import app; app() except ImportError: print("CLI not yet implemented")`) — replaced with real import in Phase 10
4. Create `stock-backtester/tests/__init__.py`
5. Create `stock-backtester/tests/conftest.py` (empty, will grow)
6. Run `cd stock-backtester && uv sync` to install dependencies
7. Run `uv run pytest --co` to confirm test collection works (0 tests)
8. Run `uv run ruff check src/` to confirm linter works

**Outputs:** Installable package, empty test suite passes, linter runs clean.

**Risks:** None. Pure scaffolding.

---

## Phase 1: Shared Types (`types.py`)

**Goal:** All dataclass types from spec Section 2 implemented and importable.

**Steps:**
1. Implement all 10 dataclasses/enums from spec: `OutputFormat`, `BacktestConfig`, `SimulationConfig`, `PriceData`, `BacktestResult`, `KellyResult`, `FrontierRow`, `MetricsResult`, `SimulationResult`, `VerificationResult`
2. Write `test_types.py`:
   - All frozen dataclasses reject field assignment
   - Config defaults match spec values
   - OutputFormat enum has TABLE and JSON
3. Run `uv run pyright src/stock_backtester/types.py` — 0 errors

**Outputs:** `types.py` importable by all subsequent modules.

**Risks:** None. Pure data definitions.

---

## Phase 2: Execution Model (`execution.py`)

**Goal:** Return computation utilities and cost model.

**Steps (TDD: tests first):**
1. **RED — Write `test_execution.py`** with failing tests:
   - Simple returns: known 3-bar series `[100, 101, 102.01]` → `[NaN, 0.01, 0.01]`
   - Log returns: known series → `[NaN, ln(1.01), ln(1.01)]`
   - Multi-symbol simple/log returns: 2-symbol DataFrame → correct shapes
   - Trailing vol: constant series → 0, known alternating → exact std
   - Trailing vol: fewer than 2 observations → NaN
   - Costs: zero delta_w → zero cost
   - Costs: known delta_w, k, sigma → exact slippage value
   - Commission dimensional check: `($/share) / ($/share)` = dimensionless
   - NaN trailing vol → 0 slippage (explicit test)
   - Add `make_constant_price_series(price, n)` fixture to conftest.py
2. **GREEN — Implement** to pass all tests:
   - `compute_simple_returns(prices_df)` — `close.pct_change()`
   - `compute_log_returns(prices_df)` — `np.log(close / close.shift(1))`
   - `compute_multi_symbol_simple_returns(prices)` — iterate symbols
   - `compute_multi_symbol_log_returns(prices)` — iterate symbols
   - `compute_trailing_volatility(log_returns, window=20)` — `rolling(20).std()` with `expanding(min_periods=2)` fallback. NaN → fillna(0)
   - `compute_costs(prices, weights, slippage_k, commission_per_share)` — per-symbol, sum to portfolio
3. **Regression** — Run `uv run pytest` (all prior tests still pass)

**Outputs:** All return utilities and cost model working with unit tests.

**Risks:** Trailing volatility NaN at early bars — tested explicitly in Step 1.

---

## Phase 3: Data Layer (`data.py`)

**Goal:** yfinance fetch, validation, alignment.

**Steps (TDD: tests first):**
1. **RED — Write `test_data.py`** with failing tests (all mock `yfinance.download`):
   - Valid fetch: mock returns capitalized DataFrame → PriceData with lowercase columns
   - Column normalization: verify `Open` → `open`, `Close` → `close`
   - Empty response: raises DataError with "No data for ticker"
   - NaN prices: raises DataError
   - Non-positive prices: raises DataError
   - < 30 bars: raises DataError with "Insufficient data"
   - Multi-symbol alignment: 2 symbols with different date ranges → inner join
   - No common dates: raises DataError
2. **GREEN — Implement:**
   - `DataError` exception class
   - `validate_prices(df, symbol)` — NaN check, positivity, min 30 bars
   - `align_dates(price_dfs)` — inner join of DatetimeIndex
   - `fetch_prices(symbols, start_date, end_date)`:
     - Individual `yf.download(symbol, start=start, end=end, auto_adjust=True, multi_level_index=False)` per symbol
     - **Critical:** `multi_level_index=False` prevents MultiIndex columns (yfinance >= 0.2.51 defaults to True)
     - `df.columns = df.columns.str.lower()` immediately after fetch
     - Validate each symbol, align dates, build PriceData
3. **Regression** — Run `uv run pytest`

**Outputs:** Data layer complete with full error handling.

**Risks:**
- yfinance `multi_level_index` default: mitigated by explicit `multi_level_index=False`
- yfinance mock fidelity: mocks return capitalized flat DataFrames matching real behavior

---

## Phase 4: Strategy Layer (`strategy.py`)

**Goal:** Strategy ABC, EqualWeight, AlwaysLong, factory function.

**Steps (TDD: tests first):**
1. **RED — Write `test_strategy.py`** with failing tests:
   - EqualWeight: single symbol → all 1.0
   - EqualWeight: 4 symbols → all 0.25
   - AlwaysLong: identical to EqualWeight
   - Factory: "equal-weight" → EqualWeightStrategy
   - Factory: "always-long" → AlwaysLongStrategy
   - Factory: "unknown" → StrategyError
   - warmup_bars: both return 0
   - Weight sum <= 1.0 per row
2. **GREEN — Implement:**
   - `StrategyError` exception class
   - `Strategy` ABC with `compute_weights()` and `warmup_bars`
   - `EqualWeightStrategy` — returns `1/N` DataFrame
   - `AlwaysLongStrategy` — identical to EqualWeight
   - `get_strategy(name, params)` factory
3. **Regression** — Run `uv run pytest`

**Outputs:** Strategy layer complete. Ready for engine integration.

**Risks:** None. Trivial strategies.

---

## Phase 5: Backtesting Engine (`engine.py`)

**Goal:** Core 8-step pipeline producing BacktestResult. AC-1, AC-1b, AC-2, AC-3 pass.

**Steps (TDD: tests first):**
1. **Add test fixtures to `conftest.py`** (needed by tests):
   - `make_synthetic_price_data(symbols, n_days, seed)` — constructs PriceData directly (no data.py dependency — builds DataFrames and aligned_dates manually)
   - `PerfectForesightStrategy` — test-only Strategy subclass that peeks at next-day return
2. **RED — Write `test_engine.py`** with failing tests:
   - Shift(1) applied: first row weights all 0
   - Series lengths match aligned_dates
   - Net <= gross for all bars with trade
   - warmup_end_idx correct for EqualWeight (= 1)
   - Equity curve starts at 1.0 at warmup_end_idx
   - Cost approximation bound: first-trade cost < 1% of bar return (documents the approximation)
3. **RED — Write AC tests in `test_integration.py`:**
   - **AC-1**: 11-bar 1% daily rise, single symbol, AlwaysLong, zero cost → `(1.01^10 - 1)` within 1e-10
   - **AC-1b**: 2 symbols, 3-bar known prices, EqualWeight, zero cost → portfolio equity = 1.0501... within 1e-6
   - **AC-2**: PerfectForesight on random series → return < sum(positive returns)
   - **AC-3**: Any strategy with slippage_k > 0 → net < gross, costs > 0
4. **GREEN — Implement `run_backtest()`:**
   - Step 1: `{sym: df.copy() for sym, df in prices.prices.items()}` → strategy
   - Step 2: `weights.shift(1).fillna(0.0)`
   - Step 3: `compute_multi_symbol_simple_returns(prices)` via execution
   - Step 4: `(shifted_weights * simple_returns).sum(axis=1)` → portfolio simple return
   - Step 5: `np.log(1 + portfolio_simple_return)` → portfolio log-return
   - Step 6: `compute_costs(prices, shifted_weights, ...)` → slippage, commission
   - Step 7: `net = gross_log - slippage - commission`
   - Step 8: `equity = np.exp(np.cumsum(net_returns))`, normalize start to 1.0
   - Compute `warmup_end_idx`: first bar where shifted weights are not all 0
5. **Regression** — Run `uv run pytest` — all prior + new tests pass

**Outputs:** Working backtest pipeline. 4 acceptance criteria pass.

**Risks:**
- Jensen's inequality bug: AC-1b catches this
- Off-by-one in shift: AC-1 catches this
- Look-ahead: AC-2 catches this
- Cost approximation: first-trade cost explicitly tested for bound compliance

---

## Phase 6: Performance Metrics (`metrics.py`)

**Goal:** All MVP metrics from spec Section 3.5.

**Steps (TDD: tests first):**
1. **RED — Write `test_metrics.py`** with failing tests:
   - Known return series `[0.01, -0.005, 0.008, -0.002, 0.003]` → exact Sharpe (hand-computed)
   - All positive returns → Sortino numerator same as Sharpe, denominator uses full-count convention
   - Known drawdown series `[0.01, -0.03, -0.02, 0.05]` → exact max drawdown and duration
   - Win rate: 3 positive, 2 negative, 1 zero → 3/5 = 0.6
   - Zero returns → Sharpe = 0 (not NaN or error)
   - Annualized return: `exp(mean * 252) - 1` with known mean
   - Annualized vol: `std(ddof=1) * sqrt(252)` with known series
   - Cost drag: `gross_total - net_total` with known divergence
2. **GREEN — Implement `compute_metrics(net_returns, gross_returns, warmup_end_idx)`:**
   - Slice post-warmup: `returns.iloc[warmup_end_idx:]`
   - Sharpe: `mean * 252 / (std(ddof=1) * sqrt(252))`
   - Sortino: full-count convention (Sortino 2001), `DD = sqrt((1/N) * sum(min(r,0)^2))`
   - Max drawdown: peak-to-trough in equity curve, duration to recovery
   - Win rate: `count(r > 0) / count(r != 0)`
   - Annualized return: `exp(mean * 252) - 1`
   - Annualized vol: `std(ddof=1) * sqrt(252)`
   - Cost drag: `gross_total - net_total`
3. **Regression** — Run `uv run pytest` — all prior + new tests pass

**Outputs:** All metrics compute correctly.

**Risks:** Sortino full-count vs downside-only — test explicitly.

---

## Phase 7: Kelly/Ruin Analyzer (`kelly.py`)

**Goal:** Kelly estimation, ruin probability, frontier, critical solver. AC-4, AC-5 pass.

**Steps (TDD: tests first):**
1. **Add fixture to `conftest.py`:** `make_deterministic_returns(mu, sigma, n)` — alternating `mu+sigma`, `mu-sigma`
2. **RED — Write `test_kelly.py`** with failing tests:
   - Known mu/sigma → exact `f* = mu / sigma^2`
   - Ruin monotonicity: increasing in f for f > 0
   - Ruin at 2f* = 1.0 (certain ruin)
   - Ruin at f=0 = 0.0 (no risk)
   - Frontier growth: 100% at f*, 0% at 2f*
   - Critical Kelly: plug-back verification (ruin at critical_f ≈ threshold)
   - Negative edge: f* < 0, critical_kelly=None
   - < 30 bars: raises KellyError
   - Ruin detection unit test: verify `ruin_probability(f, f_star, D)` returns correct value for known inputs
3. **RED — Write AC tests in `test_integration.py`:**
   - **AC-4**: `mu=0.0005, sigma=0.01` → `f* = 5.0` within 1e-6 (ddof=0 required)
   - **AC-5**: frontier monotonic ruin, `g(2f*) = 0`
4. **GREEN — Implement:**
   - `KellyError` exception class
   - `ruin_probability(f, f_star, D)` with domain guards
   - `growth_rate_fraction(alpha)` — `2*alpha - alpha^2`
   - `critical_kelly_fraction(mu, sigma, ruin_threshold, drawdown_level)` — closed-form solver with validity check
   - `compute_kelly(net_returns, warmup_end_idx, ruin_threshold, drawdown_level)`:
     - Slice post-warmup
     - `mu = mean(returns)`, `sigma = std(returns, ddof=0)`
     - `f_star = mu / sigma^2`
     - Build frontier at `[0.25, 0.50, 0.75, 1.00, 1.50, 2.00]`
     - Compute critical_kelly
5. **Regression** — Run `uv run pytest` — all prior + new tests pass

**Outputs:** Kelly analysis complete. 6 of 8 acceptance criteria pass.

**Risks:** ddof=0 vs ddof=1 confusion — AC-4 catches this.

---

## Phase 8: Monte Carlo Simulation (`simulation.py`)

**Goal:** GBM paths, Monte Carlo loop, verification tests. AC-6, AC-7 pass.

**Steps (TDD: tests first):**
1. **Add fixture to `conftest.py`:** `make_multi_symbol_zero_edge(n_symbols, n_days, sigma, seed)` — zero-drift prices for AC-7
2. **RED — Write `test_simulation.py`** with failing tests:
   - GBM: all paths positive (no negative prices)
   - GBM: determinism (same seed → same output)
   - Calibration: known returns → known mu/sigma within tolerance
   - Multi-symbol: different sub-seeds per symbol (paths differ)
   - Ruin detection: known path breaching drawdown threshold → correctly detected
   - Ruin detection: path staying above threshold → not flagged
3. **RED — Write AC tests in `test_integration.py`:**
   - **AC-6**: mu=0.10, sigma=0.20, 200 paths, seed=42 → mean and std within 2 SE
   - **AC-7**: 4 symbols, mu=0, EqualWeight, zero costs → Sharpe within 2 SE of 0
4. **GREEN — Implement:**
   - `SimulationError` exception class
   - `calibrate_gbm(prices)` — per-symbol method-of-moments, ddof=1
   - `generate_gbm_paths(mu, sigma, n_paths, n_days, seed, S0)`:
     - Vectorized: `log_increments = (mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z`
     - `paths = S0 * exp(cumsum(log_increments))`
   - `generate_multi_symbol_paths(calibrations, n_paths, n_days, seed)`:
     - Per-symbol sub-seed: `seed + i`
   - `run_monte_carlo(prices, strategy, config)`:
     - Internal: run historical backtest + compute_kelly → get half_kelly
     - Calibrate per-symbol GBM
     - Generate paths
     - Loop: construct synthetic PriceData per path, run backtest, check ruin at half_kelly
     - Compute empirical ruin rate and theoretical ruin rate (portfolio-level mu/sigma)
   - `run_verification_tests(seed)`:
     - AC-1 through AC-7 + AC-1b as VerificationResult list
5. **Regression** — Run `uv run pytest` — all prior + new tests pass

**Outputs:** Simulation complete. All 8 acceptance criteria pass.

**Risks:**
- GBM moment test: 5% expected false-failure rate → fixed seed makes deterministic
- Monte Carlo performance: N=200 × run_backtest should be < 120s

---

## Phase 9: Report Generator (`report.py`)

**Goal:** TABLE and JSON output formatting.

**Steps (TDD: tests first):**
1. **RED — Write `test_report.py`** with failing tests:
   - Survivorship warning present in TABLE output
   - JSON output is valid JSON (`json.loads()` succeeds)
   - All MetricsResult fields appear in TABLE output
   - All KellyResult fields appear in TABLE output
   - Frontier has 6 rows in TABLE output
   - Simulation report: ruin rate displayed
   - Verification report: all ACs listed with PASS/FAIL
2. **GREEN — Implement:**
   - `format_backtest_report(metrics, kelly, config, output_format)`:
     - TABLE: survivorship warning, portfolio summary, metrics section, Kelly section, frontier table
     - JSON: `json.dumps()` of equivalent nested dict
   - `format_simulation_report(result, output_format)`
   - `format_verification_report(results, output_format)`
3. **Regression** — Run `uv run pytest` — all prior + new tests pass

**Outputs:** All report functions working.

**Risks:** None. Pure string formatting.

---

## Phase 10: CLI (`cli.py`) & `__main__.py`

**Goal:** Working `backtest run`, `backtest simulate`, `backtest verify` commands. Replace `__main__.py` stub from Phase 0.

**Steps (TDD: tests first):**
1. **RED — Write `test_cli.py`** with failing tests:
   - `CliRunner` invokes `backtest verify` → exit code 0, all "PASS"
   - `CliRunner` invokes `backtest run --symbols TEST --json` (mocked data) → valid JSON
   - `CliRunner` with invalid symbol → exit code 1, error message
   - `CliRunner` with `--help` → shows usage without error
2. **GREEN — Implement:**
   - Typer app with 3 subcommands matching spec Section 3.9
   - `run` command: parse symbols → fetch prices → get strategy → run backtest → compute metrics → compute kelly → format report → print
   - `simulate` command: parse symbols → fetch → strategy → historical backtest → kelly → monte carlo → format report → print
   - `verify` command: run verification tests → format report → print
   - Error handling: catch `DataError`, `StrategyError`, `KellyError`, `SimulationError` → print message → `raise SystemExit(1)`
   - Update `__main__.py` to import from completed `cli.py` (replaces Phase 0 stub: `from .cli import app; app()`)
3. **Regression** — Run `uv run pytest` — all prior + new tests pass

**Note:** `__main__.py` from Phase 0 uses a deferred import stub (`try: from .cli import app; app() except ImportError: ...`) to avoid ImportError before cli.py exists. This phase replaces that stub with the real import once cli.py is implemented.

**Outputs:** CLI complete. Full end-to-end pipeline works.

**Risks:** Typer argument parsing edge cases — test with CliRunner.

---

## Phase 11: Integration & NFR Polish

**Goal:** Full AC suite, NFR tests, pyright validation, final cleanup.

**Steps:**
1. **Run full AC suite:** `uv run pytest tests/test_integration.py -v` — all 8 pass
2. **RED — Write `test_nfr.py`** with performance tests:
   - Backtest timing: 4 symbols, 1260 bars < 5s
   - Simulation timing: 200 paths, 4 symbols < 120s
   - Memory: < 500 MB via tracemalloc
   - Verification: all ACs < 30s
3. **GREEN — Optimize if needed:** Profile and vectorize hot paths in engine/simulation
4. **Pyright validation:** `uv run pyright src/` — 0 errors on basic mode (per design's pyproject.toml)
5. **Lint:** `uv run ruff check src/` — clean
6. **Coverage:** `uv run pytest --cov=stock_backtester` — all green, coverage report
7. **Final verification:** `uv run backtest verify` from command line → all PASS

**Outputs:** All tests pass. Linter and type checker clean. Ready for demo.

**Risks:** NFR failures → profile and optimize hot paths (vectorization in engine/simulation).

---

## Timeline Mapping

Mapping phases to the PRD's 7-day timeline:

| Day | Phases | Key Deliverables |
|-----|--------|-----------------|
| 1 | 0, 1, 2, 3 | Scaffold, types, execution, data layer (all with tests) |
| 2 | 4, 5 | Strategy, engine core. AC-1, AC-1b, AC-2, AC-3 pass |
| 3 | 6, 7 | Metrics, Kelly. AC-4, AC-5 pass |
| 4 | 8 | Simulation (GBM, Monte Carlo, verification). AC-6, AC-7 pass |
| 5 | 9, 10 | Report, CLI. End-to-end `backtest run/simulate/verify` work |
| 6 | 11 | Integration, NFR, polish. Full test suite green |
| 7 | Buffer | Bug fixes, README, demo on real data |

---

## Risk Mitigations by Phase

| Risk (Design Section 9) | Mitigated In | How |
|--------------------------|-------------|-----|
| Jensen's inequality | Phase 5 (AC-1b) | 2-symbol known-answer test catches log-return aggregation |
| Look-ahead bias | Phase 5 (AC-2) | PerfectForesight strategy + shift(1) verification |
| yfinance API changes | Phase 3 (data tests) | Column normalization + mocked integration tests |
| Float accumulation | Phase 5 (AC-1) | Deterministic 10-bar compounding within 1e-10 |
| Kelly noise | Phase 7 (AC-4) | Deterministic series with exact moments |
| Independent GBM | Phase 8 (docs) | Documented limitation in SimulationResult |

---

## Test Fixture Locations

| Fixture | Location | First Used |
|---------|----------|-----------|
| `make_deterministic_returns(mu, sigma, n)` | `conftest.py` | Phase 7 (AC-4) |
| `make_constant_price_series(price, n)` | `conftest.py` | Phase 2 (execution tests) |
| `make_synthetic_price_data(symbols, n_days, seed)` | `conftest.py` | Phase 5 (engine tests) |
| `make_multi_symbol_zero_edge(n_symbols, n_days, sigma, seed)` | `conftest.py` | Phase 8 (AC-7) |
| `PerfectForesightStrategy` | `conftest.py` | Phase 5 (AC-2) |
