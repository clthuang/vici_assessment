# Tasks: Statistical Arbitrage Backtesting System

**Feature:** 001-stat-arb-backtester
**Plan Version:** v2
**Tasks Version:** v1

---

## Phase 0: Project Scaffold

### Task 0.1: Create pyproject.toml
- **File:** `stock-backtester/pyproject.toml`
- **Do:** Copy pyproject.toml from design Section 6 verbatim. Includes: build-system, project metadata, dependencies (pandas, numpy, scipy, yfinance, typer), dev deps (pytest, pytest-cov, ruff, pyright), entry point `backtest = "stock_backtester.cli:app"`, tool configs (ruff, pyright basic, pytest).
- **Done when:** File exists with all sections from design.

### Task 0.2: Create package files
- **Files:** `stock-backtester/src/stock_backtester/__init__.py`, `__main__.py`, `tests/__init__.py`, `tests/conftest.py`
- **Do:**
  - `__init__.py`: `__version__ = "0.1.0"`
  - `__main__.py`: Deferred stub: `try: from .cli import app; app() except ImportError: print("CLI not yet implemented")`
  - `tests/__init__.py`: empty
  - `tests/conftest.py`: empty (will grow)
- **Done when:** All 4 files exist with correct content.

### Task 0.3: Install and verify toolchain
- **Do:** Run `cd stock-backtester && uv sync`, then `uv run pytest --co` (0 tests collected), then `uv run ruff check src/` (clean).
- **Done when:** All 3 commands succeed with no errors.

---

## Phase 1: Shared Types

### Task 1.1: Implement types.py
- **File:** `src/stock_backtester/types.py`
- **Do:** Implement all 10 dataclasses/enums from spec Section 2: `OutputFormat`, `BacktestConfig`, `SimulationConfig`, `PriceData`, `BacktestResult`, `KellyResult`, `FrontierRow`, `MetricsResult`, `SimulationResult`, `VerificationResult`. All result types `@dataclass(frozen=True)`.
- **Done when:** `from stock_backtester.types import BacktestConfig, PriceData, ...` works for all 10 types.

### Task 1.2: Write test_types.py
- **File:** `tests/test_types.py`
- **Do:** Tests: (a) frozen dataclasses reject `setattr`, (b) `BacktestConfig` defaults match spec (commission=0.001, slippage_k=0.5, etc.), (c) `OutputFormat.TABLE` and `OutputFormat.JSON` exist.
- **Done when:** `uv run pytest tests/test_types.py` passes.

### Task 1.3: Pyright check types.py
- **Do:** Run `uv run pyright src/stock_backtester/types.py` — 0 errors.
- **Done when:** Exit code 0, no type errors.

---

## Phase 2: Execution Model

### Task 2.1: Add make_constant_price_series fixture
- **File:** `tests/conftest.py`
- **Do:** Add `make_constant_price_series(price, n)` — returns DataFrame with constant close=price for n bars, DatetimeIndex, lowercase columns (open, high, low, close, volume).
- **Done when:** Fixture importable and returns correctly shaped DataFrame.

### Task 2.2: Write test_execution.py (RED)
- **File:** `tests/test_execution.py`
- **Do:** Write failing tests:
  - `test_simple_returns_known_series`: `[100, 101, 102.01]` → `[NaN, 0.01, 0.01]`
  - `test_log_returns_known_series`: same series → `[NaN, ln(1.01), ln(1.01)]`
  - `test_multi_symbol_simple_returns`: 2-symbol DataFrame → correct shapes
  - `test_multi_symbol_log_returns`: 2-symbol DataFrame → correct shapes
  - `test_trailing_vol_constant`: constant series → 0
  - `test_trailing_vol_alternating`: known alternating → exact std
  - `test_trailing_vol_insufficient`: < 2 observations → NaN
  - `test_costs_zero_delta`: zero delta_w → zero cost
  - `test_costs_known_slippage`: known delta_w, k, sigma → exact value
  - `test_commission_dimensionless`: `($/share) / ($/share)` = dimensionless
  - `test_nan_trailing_vol_zero_slippage`: NaN vol → 0 slippage
- **Done when:** All tests exist and fail (ImportError — execution.py doesn't exist yet).

### Task 2.3: Implement execution.py (GREEN)
- **File:** `src/stock_backtester/execution.py`
- **Do:** Implement to pass all tests from 2.2:
  - `compute_simple_returns(prices_df)` — `close.pct_change()`
  - `compute_log_returns(prices_df)` — `np.log(close / close.shift(1))`
  - `compute_multi_symbol_simple_returns(prices)` — iterate symbols
  - `compute_multi_symbol_log_returns(prices)` — iterate symbols
  - `compute_trailing_volatility(log_returns, window=20)` — `rolling(20).std()` + `expanding(min_periods=2)` fallback, NaN → `fillna(0)`
  - `compute_costs(prices, weights, slippage_k, commission_per_share)` — per-symbol costs, sum to portfolio
- **Done when:** `uv run pytest tests/test_execution.py` all pass.

### Task 2.4: Regression check Phase 2
- **Do:** Run `uv run pytest` — all tests from Phase 1 + Phase 2 pass.
- **Done when:** Full suite green.

---

## Phase 3: Data Layer

### Task 3.1: Write test_data.py (RED)
- **File:** `tests/test_data.py`
- **Do:** Write failing tests (all mock `yfinance.download` via `@patch`):
  - `test_fetch_valid_single_symbol`: mock returns capitalized DataFrame → PriceData with lowercase columns
  - `test_column_normalization`: `Open` → `open`, `Close` → `close`
  - `test_fetch_empty_response`: raises `DataError` with "No data for ticker"
  - `test_fetch_nan_prices`: raises `DataError`
  - `test_fetch_non_positive_prices`: raises `DataError`
  - `test_fetch_insufficient_bars`: < 30 bars → `DataError` "Insufficient data"
  - `test_multi_symbol_alignment`: 2 symbols with different date ranges → inner join
  - `test_no_common_dates`: raises `DataError`
- **Done when:** All tests exist and fail (ImportError).

### Task 3.2: Implement data.py (GREEN)
- **File:** `src/stock_backtester/data.py`
- **Do:** Implement:
  - `DataError` exception class
  - `validate_prices(df, symbol)` — NaN check, positivity, min 30 bars
  - `align_dates(price_dfs)` — inner join of DatetimeIndex
  - `fetch_prices(symbols, start_date, end_date)` — per-symbol `yf.download(symbol, start=start, end=end, auto_adjust=True, multi_level_index=False)`, then `df.columns = df.columns.str.lower()`, validate, align, build PriceData
- **Done when:** `uv run pytest tests/test_data.py` all pass.

### Task 3.3: Regression check Phase 3
- **Do:** Run `uv run pytest` — all tests from Phases 1-3 pass.
- **Done when:** Full suite green.

---

## Phase 4: Strategy Layer

### Task 4.1: Write test_strategy.py (RED)
- **File:** `tests/test_strategy.py`
- **Do:** Write failing tests:
  - `test_equal_weight_single_symbol`: 1 symbol → all weights 1.0
  - `test_equal_weight_four_symbols`: 4 symbols → all weights 0.25
  - `test_always_long_identical`: AlwaysLong produces same weights as EqualWeight
  - `test_factory_equal_weight`: `get_strategy("equal-weight", {})` → EqualWeightStrategy
  - `test_factory_always_long`: `get_strategy("always-long", {})` → AlwaysLongStrategy
  - `test_factory_unknown`: `get_strategy("unknown", {})` → StrategyError
  - `test_warmup_bars_zero`: both strategies return warmup_bars=0
  - `test_weight_sum_constraint`: weight sum <= 1.0 per row
- **Done when:** All tests exist and fail (ImportError).

### Task 4.2: Implement strategy.py (GREEN)
- **File:** `src/stock_backtester/strategy.py`
- **Do:** Implement:
  - `StrategyError` exception class
  - `Strategy` ABC with `compute_weights(prices, symbols)` and `warmup_bars` property
  - `EqualWeightStrategy` — returns `1/N` DataFrame
  - `AlwaysLongStrategy` — identical to EqualWeight
  - `get_strategy(name, params)` factory
- **Done when:** `uv run pytest tests/test_strategy.py` all pass.

### Task 4.3: Regression check Phase 4
- **Do:** Run `uv run pytest` — all tests from Phases 1-4 pass.
- **Done when:** Full suite green.

---

## Phase 5: Backtesting Engine

### Task 5.1: Add engine fixtures to conftest.py
- **File:** `tests/conftest.py`
- **Do:** Add:
  - `make_synthetic_price_data(symbols, n_days, seed)` — constructs PriceData directly (builds DataFrames with random walk close prices, open=high=low=close, volume=1e6, DatetimeIndex, lowercase columns, aligned_dates = full date range)
  - `PerfectForesightStrategy` — test-only Strategy subclass: for each bar t, peeks at next-day simple return, sets weight=1.0 if positive else 0.0. Single-symbol only. warmup_bars=0.
- **Done when:** Both fixtures importable and return correct types.

### Task 5.2: Write test_engine.py (RED)
- **File:** `tests/test_engine.py`
- **Do:** Write failing tests:
  - `test_shift_applied`: first row of shifted weights is all 0
  - `test_series_lengths`: gross_returns, net_returns lengths == len(aligned_dates)
  - `test_net_leq_gross`: net <= gross for all bars with trade
  - `test_warmup_end_idx_equal_weight`: warmup_end_idx == 1 for EqualWeight
  - `test_equity_starts_at_one`: equity_curve.iloc[warmup_end_idx] == 1.0
  - `test_cost_approximation_bound`: first-trade cost < 1% of bar return
- **Done when:** All tests exist and fail.

### Task 5.3: Write AC integration tests (RED)
- **File:** `tests/test_integration.py`
- **Do:** Write failing AC tests:
  - `test_ac1_correct_returns`: 11-bar 1% daily rise, single symbol, AlwaysLong, zero cost → `(1.01^10 - 1)` within 1e-10
  - `test_ac1b_multi_symbol_aggregation`: 2 symbols, 3-bar known prices, EqualWeight, zero cost → equity = 1.0501... within 1e-6
  - `test_ac2_look_ahead_prevention`: PerfectForesight on random series → return < sum(positive returns)
  - `test_ac3_slippage_invariant`: slippage_k > 0 → net < gross, costs > 0
- **Done when:** All 4 AC tests exist and fail.

### Task 5.4: Implement engine.py (GREEN)
- **File:** `src/stock_backtester/engine.py`
- **Do:** Implement `run_backtest(config, prices, strategy, slippage_k, commission_per_share)`:
  1. Copy prices: `{sym: df.copy() for sym, df in prices.prices.items()}`
  2. Compute raw weights via `strategy.compute_weights()`
  3. Shift: `weights.shift(1).fillna(0.0)`
  4. Simple returns via `compute_multi_symbol_simple_returns(prices)`
  5. Portfolio simple return: `(shifted_weights * simple_returns).sum(axis=1)`
  6. Convert to log: `np.log(1 + portfolio_simple_return)`
  7. Costs via `compute_costs(prices, shifted_weights, ...)`
  8. Net: `gross_log - slippage - commission`
  9. Equity: `np.exp(np.cumsum(net_returns))`, normalize to 1.0 at warmup_end_idx
  10. Compute warmup_end_idx: first bar where shifted weights not all 0
  11. Build and return BacktestResult
- **Done when:** `uv run pytest tests/test_engine.py tests/test_integration.py` all pass. AC-1, AC-1b, AC-2, AC-3 green.

### Task 5.5: Regression check Phase 5
- **Do:** Run `uv run pytest` — all tests from Phases 1-5 pass.
- **Done when:** Full suite green.

---

## Phase 6: Performance Metrics

### Task 6.1: Write test_metrics.py (RED)
- **File:** `tests/test_metrics.py`
- **Do:** Write failing tests:
  - `test_sharpe_known_series`: `[0.01, -0.005, 0.008, -0.002, 0.003]` → hand-computed Sharpe
  - `test_sortino_all_positive`: all positive returns → Sortino uses full-count convention
  - `test_max_drawdown_known`: `[0.01, -0.03, -0.02, 0.05]` → exact max drawdown and duration
  - `test_win_rate`: 3 positive, 2 negative, 1 zero → 3/5 = 0.6
  - `test_sharpe_zero_returns`: all zero returns → Sharpe = 0 (not NaN)
  - `test_annualized_return`: known mean → `exp(mean * 252) - 1`
  - `test_annualized_vol`: known series → `std(ddof=1) * sqrt(252)`
  - `test_cost_drag`: gross and net with known divergence → exact cost_drag
- **Done when:** All tests exist and fail.

### Task 6.2: Implement metrics.py (GREEN)
- **File:** `src/stock_backtester/metrics.py`
- **Do:** Implement `compute_metrics(net_returns, gross_returns, warmup_end_idx)`:
  - Slice post-warmup: `returns.iloc[warmup_end_idx:]`
  - Sharpe: `mean * 252 / (std(ddof=1) * sqrt(252))`
  - Sortino: full-count (Sortino 2001): `DD = sqrt((1/N) * sum(min(r,0)^2))`, annualize `* sqrt(252)`
  - Max drawdown: peak-to-trough in equity curve, duration to recovery (or end)
  - Win rate: `count(r > 0) / count(r != 0)`
  - Annualized return: `exp(mean * 252) - 1`
  - Annualized vol: `std(ddof=1) * sqrt(252)`
  - Cost drag: `gross_total - net_total`
  - Return MetricsResult
- **Done when:** `uv run pytest tests/test_metrics.py` all pass.

### Task 6.3: Regression check Phase 6
- **Do:** Run `uv run pytest` — all tests from Phases 1-6 pass.
- **Done when:** Full suite green.

---

## Phase 7: Kelly/Ruin Analyzer

### Task 7.1: Add make_deterministic_returns fixture
- **File:** `tests/conftest.py`
- **Do:** Add `make_deterministic_returns(mu, sigma, n)` — generates pd.Series of n alternating values: `mu+sigma`, `mu-sigma`. Mean = mu, std(ddof=0) = sigma exactly.
- **Done when:** Fixture returns Series with verified moments.

### Task 7.2: Write test_kelly.py (RED)
- **File:** `tests/test_kelly.py`
- **Do:** Write failing tests:
  - `test_full_kelly_known`: mu/sigma → exact `f* = mu / sigma^2`
  - `test_ruin_monotonic`: ruin probability increasing in f
  - `test_ruin_at_2fstar`: ruin = 1.0 at 2f*
  - `test_ruin_at_zero`: ruin = 0.0 at f=0
  - `test_frontier_growth_at_fstar`: growth = 100% at f*
  - `test_frontier_growth_at_2fstar`: growth = 0% at 2f*
  - `test_critical_kelly_plugback`: ruin at critical_f ≈ threshold
  - `test_negative_edge`: f* < 0 → critical_kelly=None
  - `test_insufficient_data`: < 30 bars → KellyError
  - `test_ruin_probability_known`: `ruin_probability(f, f_star, D)` returns exact value for known inputs
- **Done when:** All tests exist and fail.

### Task 7.3: Write AC-4 and AC-5 integration tests (RED)
- **File:** `tests/test_integration.py` (append)
- **Do:** Add:
  - `test_ac4_kelly_analytical`: `mu=0.0005, sigma=0.01` → `f* = 5.0` within 1e-6
  - `test_ac5_frontier_consistency`: monotonic ruin, `g(2f*) = 0`
- **Done when:** Both tests exist and fail.

### Task 7.4: Implement kelly.py (GREEN)
- **File:** `src/stock_backtester/kelly.py`
- **Do:** Implement:
  - `KellyError` exception class
  - `ruin_probability(f, f_star, D)` — `D^(2/alpha - 1)` with domain guards (f>=2f* → 1.0, f<=0 → 0.0)
  - `growth_rate_fraction(alpha)` — `2*alpha - alpha^2`
  - `critical_kelly_fraction(mu, sigma, ruin_threshold, drawdown_level)` — closed-form `2*mu / (sigma^2 * (ln(P)/ln(D) + 1))`, returns None if f_crit >= 2*f* or mu <= 0
  - `compute_kelly(net_returns, warmup_end_idx, ruin_threshold, drawdown_level)` — slice post-warmup, mu=mean, sigma=std(ddof=0), f*=mu/sigma^2, build frontier at [0.25, 0.50, 0.75, 1.00, 1.50, 2.00], compute critical_kelly
- **Done when:** `uv run pytest tests/test_kelly.py tests/test_integration.py -k "ac4 or ac5"` all pass.

### Task 7.5: Regression check Phase 7
- **Do:** Run `uv run pytest` — all tests from Phases 1-7 pass.
- **Done when:** Full suite green.

---

## Phase 8: Monte Carlo Simulation

### Task 8.1: Add make_multi_symbol_zero_edge fixture
- **File:** `tests/conftest.py`
- **Do:** Add `make_multi_symbol_zero_edge(n_symbols, n_days, sigma, seed)` — generates PriceData for n symbols with mu=0, given sigma. Uses GBM-like construction: `S_t = S_0 * exp(cumsum(-sigma^2/2*dt + sigma*sqrt(dt)*Z))`.
- **Done when:** Fixture returns PriceData with correct number of symbols and shapes.

### Task 8.2: Write test_simulation.py (RED)
- **File:** `tests/test_simulation.py`
- **Do:** Write failing tests:
  - `test_gbm_all_positive`: all paths > 0
  - `test_gbm_determinism`: same seed → same output
  - `test_calibration_known_returns`: known returns → known mu/sigma within tolerance
  - `test_multi_symbol_different_subseeds`: different sub-seeds per symbol (paths differ)
  - `test_ruin_detection_breach`: known path breaching drawdown → detected
  - `test_ruin_detection_no_breach`: path above threshold → not flagged
- **Done when:** All tests exist and fail.

### Task 8.3: Write AC-6 and AC-7 integration tests (RED)
- **File:** `tests/test_integration.py` (append)
- **Do:** Add:
  - `test_ac6_gbm_moments`: mu=0.10, sigma=0.20, 200 paths, seed=42 → mean and std within 2 SE
  - `test_ac7_zero_edge_sharpe`: 4 symbols, mu=0, EqualWeight, zero costs → Sharpe within 2 SE of 0
- **Done when:** Both tests exist and fail.

### Task 8.4: Implement simulation.py — GBM functions (GREEN part 1)
- **File:** `src/stock_backtester/simulation.py`
- **Do:** Implement:
  - `SimulationError` exception class
  - `calibrate_gbm(prices)` — per-symbol method-of-moments, ddof=1, annualize
  - `generate_gbm_paths(mu_annual, sigma_annual, n_paths, n_days, seed, S0=100.0)` — vectorized: `log_increments = (mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z`, `paths = S0 * exp(cumsum(log_increments))`
  - `generate_multi_symbol_paths(calibrations, n_paths, n_days, seed)` — per-symbol sub-seed: `seed + i`
- **Done when:** `uv run pytest tests/test_simulation.py -k "gbm or calibration or subseed"` pass.

### Task 8.5: Implement simulation.py — Monte Carlo loop (GREEN part 2)
- **File:** `src/stock_backtester/simulation.py`
- **Do:** Implement:
  - `run_monte_carlo(prices, strategy, config)`:
    - Run historical backtest + compute_kelly → get half_kelly
    - Calibrate per-symbol GBM
    - Generate paths
    - Loop: construct synthetic PriceData per path, run backtest, check ruin at half_kelly
    - Compute empirical and theoretical ruin rate (portfolio-level mu/sigma)
  - `run_verification_tests(seed)` — runs AC-1 through AC-7 + AC-1b, returns list[VerificationResult]
- **Done when:** `uv run pytest tests/test_simulation.py tests/test_integration.py -k "ac6 or ac7 or ruin_detection"` all pass.

### Task 8.6: Regression check Phase 8
- **Do:** Run `uv run pytest` — all tests from Phases 1-8 pass. All 8 ACs green.
- **Done when:** Full suite green.

---

## Phase 9: Report Generator

### Task 9.1: Write test_report.py (RED)
- **File:** `tests/test_report.py`
- **Do:** Write failing tests (construct MetricsResult, KellyResult, etc. manually):
  - `test_survivorship_warning`: "survivorship" in TABLE output
  - `test_json_valid`: `json.loads(output)` succeeds
  - `test_metrics_fields_in_table`: all MetricsResult field names appear in TABLE
  - `test_kelly_fields_in_table`: all KellyResult field names appear in TABLE
  - `test_frontier_six_rows`: frontier section has 6 data rows
  - `test_simulation_report_ruin_rate`: ruin rate appears in simulation report
  - `test_verification_report_all_acs`: all AC names listed with PASS/FAIL
- **Done when:** All tests exist and fail.

### Task 9.2: Implement report.py (GREEN)
- **File:** `src/stock_backtester/report.py`
- **Do:** Implement:
  - `format_backtest_report(metrics, kelly, config, output_format)` — TABLE: survivorship warning + portfolio summary + metrics + Kelly + frontier. JSON: `json.dumps()` of nested dict
  - `format_simulation_report(result, output_format)` — paths, seed, calibrations, ruin rates
  - `format_verification_report(results, output_format)` — AC-N: PASS/FAIL with expected/actual
- **Done when:** `uv run pytest tests/test_report.py` all pass.

### Task 9.3: Regression check Phase 9
- **Do:** Run `uv run pytest` — all tests from Phases 1-9 pass.
- **Done when:** Full suite green.

---

## Phase 10: CLI

### Task 10.1: Write test_cli.py (RED)
- **File:** `tests/test_cli.py`
- **Do:** Write failing tests using `typer.testing.CliRunner`:
  - `test_cli_verify`: `backtest verify` → exit code 0, all "PASS" in output
  - `test_cli_run_json`: `backtest run --symbols TEST --json` (mock yfinance) → valid JSON
  - `test_cli_invalid_symbol`: invalid symbol → exit code 1, error message
  - `test_cli_help`: `--help` → shows usage without error
- **Done when:** All tests exist and fail.

### Task 10.2: Implement cli.py (GREEN)
- **File:** `src/stock_backtester/cli.py`
- **Do:** Implement Typer app:
  - `run` command: parse `--symbols` → split(",") → fetch_prices → get_strategy → run_backtest → compute_metrics → compute_kelly → format_backtest_report → print
  - `simulate` command: parse → fetch → strategy → run_backtest (historical) → compute_kelly → run_monte_carlo → format_simulation_report → print
  - `verify` command: run_verification_tests → format_verification_report → print
  - Error handling: catch DataError, StrategyError, KellyError, SimulationError → print message → `raise SystemExit(1)`
- **Done when:** `uv run pytest tests/test_cli.py` all pass.

### Task 10.3: Update __main__.py
- **File:** `src/stock_backtester/__main__.py`
- **Do:** Replace deferred stub with: `from .cli import app; app()`
- **Done when:** `uv run python -m stock_backtester --help` shows Typer help.

### Task 10.4: Regression check Phase 10
- **Do:** Run `uv run pytest` — all tests from Phases 1-10 pass.
- **Done when:** Full suite green.

---

## Phase 11: Integration & NFR Polish

### Task 11.1: Run full AC suite
- **Do:** `uv run pytest tests/test_integration.py -v` — all 8 ACs pass.
- **Done when:** All AC-1, AC-1b, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 green.

### Task 11.2: Write test_nfr.py (RED)
- **File:** `tests/test_nfr.py`
- **Do:** Write performance tests:
  - `test_backtest_timing`: 4 symbols, 1260 bars, assert < 5s
  - `test_simulation_timing`: 200 paths, 4 symbols, assert < 120s
  - `test_memory_usage`: tracemalloc peak < 500 MB
  - `test_verification_timing`: all ACs < 30s
- **Done when:** Tests exist. May pass or fail depending on performance.

### Task 11.3: Optimize if NFR fails (GREEN)
- **Do:** If test_nfr.py fails, profile hot paths (engine loop, GBM generation). Vectorize numpy operations. Ensure GBM uses matrix operations not Python loops.
- **Done when:** `uv run pytest tests/test_nfr.py` all pass.

### Task 11.4: Pyright validation
- **Do:** Run `uv run pyright src/` — 0 errors on basic mode.
- **Done when:** Exit code 0, no type errors.

### Task 11.5: Lint check
- **Do:** Run `uv run ruff check src/` — clean.
- **Done when:** Exit code 0, no lint errors.

### Task 11.6: Coverage report
- **Do:** Run `uv run pytest --cov=stock_backtester` — all green.
- **Done when:** Coverage report generated, no test failures.

### Task 11.7: Final CLI verification
- **Do:** Run `uv run backtest verify` from command line.
- **Done when:** All ACs show "PASS", exit code 0.

---

## Task Dependencies

```
0.1 → 0.2 → 0.3 → 1.1
1.1 → 1.2 → 1.3

# Phase 2, 3, 4 can run in parallel after Phase 1
1.3 → 2.1 → 2.2 → 2.3 → 2.4
1.3 → 3.1 → 3.2 → 3.3
1.3 → 4.1 → 4.2 → 4.3

# Phase 5 requires 2, 3 (for data tests), 4
2.4 + 4.3 → 5.1 → 5.2 → 5.3 → 5.4 → 5.5

# Phase 6, 7 can run in parallel after Phase 5
5.5 → 6.1 → 6.2 → 6.3
5.5 → 7.1 → 7.2 → 7.3 → 7.4 → 7.5

# Phase 8 requires 6, 7
6.3 + 7.5 → 8.1 → 8.2 → 8.3 → 8.4 → 8.5 → 8.6

# Phase 9 can run in parallel with 8 (depends only on types)
1.3 → 9.1 → 9.2 → 9.3

# Phase 10 requires 8, 9
8.6 + 9.3 → 10.1 → 10.2 → 10.3 → 10.4

# Phase 11 requires 10
10.4 → 11.1 → 11.2 → 11.3 → 11.4 → 11.5 → 11.6 → 11.7
```

### Parallel Groups

| Group | Tasks | Can Run Simultaneously |
|-------|-------|----------------------|
| A | 2.1-2.4, 3.1-3.3, 4.1-4.3 | Yes (all depend only on Phase 1) |
| B | 6.1-6.3, 7.1-7.5 | Yes (both depend only on Phase 5) |
| C | 8.1-8.6, 9.1-9.3 | Partial (Phase 9 depends only on types, can start earlier) |

---

## Summary

- **Total tasks:** 45
- **Phases:** 12 (0-11)
- **Parallel groups:** 3
- **AC coverage:** All 8 ACs mapped to specific tasks (5.3, 7.3, 8.3)
- **Fixture tasks:** 4 (2.1, 5.1, 7.1, 8.1)
