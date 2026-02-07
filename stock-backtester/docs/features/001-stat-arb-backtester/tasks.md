# Tasks: Statistical Arbitrage Backtesting System

**Feature:** 001-stat-arb-backtester
**Plan Version:** v2
**Tasks Version:** v3

---

## Phase 0: Project Scaffold

### Task 0.1: Create pyproject.toml
- **File:** `stock-backtester/pyproject.toml`
- **Do:** Copy pyproject.toml from design Section 6 verbatim. Includes: build-system, project metadata, dependencies (pandas, numpy, scipy, yfinance, typer), dev deps (pytest, pytest-cov, ruff, pyright), entry point `backtest = "stock_backtester.cli:app"`, tool configs (ruff, pyright basic, pytest).
- **Done when:** File exists with all sections from design.
- **Est:** ~5 min

### Task 0.2: Create package files
- **Files:** `stock-backtester/src/stock_backtester/__init__.py`, `__main__.py`, `tests/__init__.py`, `tests/conftest.py`
- **Do:**
  - `__init__.py`: `__version__ = "0.1.0"`
  - `__main__.py`: Deferred stub: `try: from .cli import app; app() except ImportError: print("CLI not yet implemented")`
  - `tests/__init__.py`: empty
  - `tests/conftest.py`: empty (will grow)
- **Done when:** All 4 files exist with correct content.
- **Est:** ~5 min

### Task 0.3: Install and verify toolchain
- **Do:** Run `cd stock-backtester && uv sync`, then `uv run pytest --co` (0 tests collected), then `uv run ruff check src/` (clean).
- **Done when:** All 3 commands succeed with no errors.
- **Est:** ~5 min

---

## Phase 1: Shared Types

### Task 1.1: Implement types.py
- **File:** `src/stock_backtester/types.py`
- **Do:** Implement all 10 dataclasses/enums from spec Section 2: `OutputFormat`, `BacktestConfig`, `SimulationConfig`, `PriceData`, `BacktestResult`, `KellyResult`, `FrontierRow`, `MetricsResult`, `SimulationResult`, `VerificationResult`. All result types `@dataclass(frozen=True)`.
- **Note:** Exception classes (`DataError`, `StrategyError`, `KellyError`, `SimulationError`) are NOT in types.py — they are co-located in their respective domain modules (data.py, strategy.py, kelly.py, simulation.py) per design TD-3.
- **Done when:** `from stock_backtester.types import BacktestConfig, PriceData, ...` works for all 10 types.
- **Est:** ~10 min

### Task 1.2: Write test_types.py
- **File:** `tests/test_types.py`
- **Do:** Tests: (a) frozen dataclasses reject `setattr`, (b) `BacktestConfig` defaults match spec (commission=0.001, slippage_k=0.5, etc.), (c) `OutputFormat.TABLE` and `OutputFormat.JSON` exist.
- **Note:** Phase 1 is implementation-before-tests (inverted TDD) because types.py defines data structures with no logic — tests validate the schema rather than drive behavior. All subsequent phases follow RED-GREEN-REGRESSION.
- **Done when:** `uv run pytest tests/test_types.py` passes.
- **Est:** ~5 min

### Task 1.3: Pyright check types.py
- **Do:** Run `uv run pyright src/stock_backtester/types.py` — 0 errors.
- **Done when:** Exit code 0, no type errors.
- **Est:** ~2 min

---

## Phase 2: Execution Model

### Task 2.1: Add make_constant_price_series fixture
- **File:** `tests/conftest.py`
- **Do:** Add `make_constant_price_series(price, n)` — returns DataFrame with constant close=price for n bars, DatetimeIndex, lowercase columns (open, high, low, close, volume).
- **Done when:** Fixture importable and returns correctly shaped DataFrame.
- **Est:** ~5 min

### Task 2.2: Write test_execution.py (RED)
- **File:** `tests/test_execution.py`
- **Do:** Write failing tests:
  - `test_simple_returns_known_series`: `[100, 101, 102.01]` → `[NaN, 0.01, 0.01]`
  - `test_log_returns_known_series`: same series → `[NaN, ln(1.01), ln(1.01)]` where `ln(1.01) ≈ 0.00995033`
  - `test_multi_symbol_simple_returns`: 2-symbol DataFrame → correct shapes
  - `test_multi_symbol_log_returns`: 2-symbol DataFrame → correct shapes
  - `test_trailing_vol_constant`: `[100, 100, 100, 100, 100]` (log returns all 0) → trailing vol = 0.0
  - `test_trailing_vol_alternating`: `[100, 101, 100, 101, 100]` → log returns alternate `[ln(1.01), ln(100/101), ln(1.01), ln(100/101)]`, expanding std(ddof=1) computable → assert exact values at each bar
  - `test_trailing_vol_insufficient`: single observation (bar 1) → NaN (< 2 observations for expanding std)
  - `test_costs_zero_delta`: zero delta_w → zero cost
  - `test_costs_known_slippage`: `delta_w=0.5, k=0.5, sigma=0.02` → slippage = `0.5 * 0.02 * 0.5 = 0.005`
  - `test_commission_dimensionless`: `commission_per_share=0.005, close=100.0` → `0.005/100 = 0.00005` per unit delta_w
  - `test_nan_trailing_vol_zero_slippage`: NaN vol → 0 slippage (fillna behavior)
- **Done when:** All tests exist and fail (ImportError — execution.py doesn't exist yet).
- **Est:** ~15 min

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
- **Est:** ~15 min

### Task 2.4: Regression check Phase 2
- **Do:** Run `uv run pytest` — all tests from Phase 1 + Phase 2 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 3: Data Layer

### Task 3.1: Write test_data.py (RED)
- **File:** `tests/test_data.py`
- **Note:** Phase 3 (data.py) is not a code dependency for Phase 5 (engine.py) — engine.py receives PriceData directly, not via data.py. Phase 3 can run in parallel with Phases 2 and 4.
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
- **Est:** ~10 min

### Task 3.2: Implement data.py (GREEN)
- **File:** `src/stock_backtester/data.py`
- **Do:** Implement:
  - `DataError` exception class
  - `validate_prices(df, symbol)` — NaN check, positivity, min 30 bars
  - `align_dates(price_dfs)` — inner join of DatetimeIndex
  - `fetch_prices(symbols, start_date, end_date)` — per-symbol `yf.download(symbol, start=start, end=end, auto_adjust=True, multi_level_index=False)`, then `df.columns = df.columns.str.lower()`, validate, align, build PriceData
- **Done when:** `uv run pytest tests/test_data.py` all pass.
- **Est:** ~10 min

### Task 3.3: Regression check Phase 3
- **Do:** Run `uv run pytest` — all tests from Phases 1-3 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

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
- **Est:** ~10 min

### Task 4.2: Implement strategy.py (GREEN)
- **File:** `src/stock_backtester/strategy.py`
- **Do:** Implement:
  - `StrategyError` exception class
  - `Strategy` ABC with `compute_weights(prices, symbols)` and `warmup_bars` property
  - `EqualWeightStrategy` — returns `1/N` DataFrame
  - `AlwaysLongStrategy` — identical to EqualWeight
  - `get_strategy(name, params)` factory
- **Done when:** `uv run pytest tests/test_strategy.py` all pass.
- **Est:** ~10 min

### Task 4.3: Regression check Phase 4
- **Do:** Run `uv run pytest` — all tests from Phases 1-4 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 5: Backtesting Engine

### Task 5.1: Add engine fixtures to conftest.py
- **File:** `tests/conftest.py`
- **Do:** Add:
  - `make_synthetic_price_data(symbols, n_days, seed)` — constructs PriceData directly (builds DataFrames with random walk close prices, open=high=low=close, volume=1e6, DatetimeIndex, lowercase columns, aligned_dates = full date range)
  - `PerfectForesightStrategy` — test-only Strategy subclass: for each bar t, peeks at next-day simple return, sets weight=1.0 if positive else 0.0. **Last-bar behavior:** weight=0.0 (no next-day return to peek at). **Multi-symbol:** raises `ValueError("PerfectForesightStrategy supports single-symbol only")`. warmup_bars=0.
- **Done when:** Both fixtures importable and return correct types. PerfectForesight raises on multi-symbol input. Last bar weight is 0.0.
- **Est:** ~10 min

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
- **Est:** ~10 min

### Task 5.3: Write AC integration tests (RED)
- **File:** `tests/test_integration.py`
- **Do:** Write failing AC tests:
  - `test_ac1_correct_returns`: 11-bar 1% daily rise, single symbol, AlwaysLong, zero cost → `(1.01^10 - 1) ≈ 0.10462212541` within 1e-10
  - `test_ac1b_multi_symbol_aggregation`: 2 symbols, 3-bar known prices per spec AC-1b: sym_A=[100, 105, 110] (+5%, +4.76%), sym_B=[100, 95, 100] (-5%, +5.26%). EqualWeight (w=0.5 each), zero cost. Portfolio simple return: bar 1 = `0.5*(0.05) + 0.5*(-0.05) = 0.0`, bar 2 = `0.5*(5/105) + 0.5*(5/95) = 20/399 ≈ 0.050125`. Equity = `(1.0)*(1 + 20/399) ≈ 1.050125` → total return `≈ 0.050125` within 1e-4
  - `test_ac2_look_ahead_prevention`: PerfectForesight on random series → return < sum(positive returns)
  - `test_ac3_slippage_invariant`: slippage_k > 0 → net < gross, costs > 0
- **Done when:** All 4 AC tests exist and fail.
- **Est:** ~10 min

### Task 5.4: Implement engine.py (GREEN)
- **File:** `src/stock_backtester/engine.py`
- **Do:** Implement `run_backtest(config, prices, strategy, slippage_k, commission_per_share)` following design's 8-step pipeline (Section 1.3):
  1. **Copy prices, pass to strategy** — `{sym: df.copy() ...}`, call `strategy.compute_weights()`
  2. **Shift(1) weights** — `weights.shift(1).fillna(0.0)` (single temporal alignment point)
  3. **Simple returns per symbol** — via `compute_multi_symbol_simple_returns(prices)`
  4. **Portfolio simple return** — `R_p = (shifted_weights * simple_returns).sum(axis=1)`
  5. **Convert to log-return** — `r_p = np.log(1 + R_p)`
  6. **Costs per symbol → aggregate** — via `compute_costs(prices, shifted_weights, ...)`
  7. **Net returns** — `net = r_p - slippage - commission`
  8. **Equity curve** — `exp(cumsum(net))`, normalize to 1.0 at `warmup_end_idx`
  - Also: compute `warmup_end_idx` (first bar where shifted weights not all 0), build BacktestResult
- **Done when:** `uv run pytest tests/test_engine.py tests/test_integration.py` all pass. AC-1, AC-1b, AC-2, AC-3 green.
- **Est:** ~15 min

### Task 5.5: Regression check Phase 5
- **Do:** Run `uv run pytest` — all tests from Phases 1-5 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 6: Performance Metrics

### Task 6.1: Write test_metrics.py (RED)
- **File:** `tests/test_metrics.py`
- **Do:** Write failing tests:
  - `test_sharpe_known_series`: `[0.01, -0.005, 0.008, -0.002, 0.003]` → mean=0.0028, std(ddof=1)=0.006181, Sharpe = `(0.0028*252) / (0.006181*sqrt(252)) ≈ 7.19` within 0.01
  - `test_sortino_all_positive`: all positive returns → Sortino uses full-count convention (DD denominator = `sqrt((1/N)*sum(min(r,0)^2))` = 0 → Sortino = inf or capped)
  - `test_max_drawdown_known`: `[0.01, -0.03, -0.02, 0.05]` → equity peaks at bar 0: `exp(0.01)=1.01005`, drops at bar 1: `exp(0.01-0.03)=0.98020`, trough at bar 2: `exp(0.01-0.03-0.02)=0.96079`. Max DD = `1 - 0.96079/1.01005 ≈ 0.04877`. Duration = 3 trading days (peak at bar 0, recovery at bar 3 where equity `exp(0.01-0.03-0.02+0.05)=1.01005` returns to peak; per spec: "longest period from peak to recovery" = bars 1, 2, 3 elapsed).
  - `test_win_rate`: 3 positive, 2 negative, 1 zero → 3/5 = 0.6 (zero excluded from count)
  - `test_sharpe_zero_returns`: all zero returns → Sharpe = 0 (not NaN)
  - `test_annualized_return`: known mean=0.001 → `exp(0.001 * 252) - 1 ≈ 0.28668` within 1e-4
  - `test_annualized_vol`: known series → `std(ddof=1) * sqrt(252)`
  - `test_cost_drag`: gross total = 0.10, net total = 0.08 → cost_drag = 0.02
- **Done when:** All tests exist and fail.
- **Est:** ~15 min

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
- **Est:** ~15 min

### Task 6.3: Regression check Phase 6
- **Do:** Run `uv run pytest` — all tests from Phases 1-6 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 7: Kelly/Ruin Analyzer

### Task 7.1: Add make_deterministic_returns fixture
- **File:** `tests/conftest.py`
- **Do:** Add `make_deterministic_returns(mu, sigma, n)` — generates pd.Series of n alternating values: `mu+sigma`, `mu-sigma`. Mean = mu, std(ddof=0) = sigma exactly.
- **Done when:** Fixture returns Series with verified moments.
- **Est:** ~5 min

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
- **Est:** ~10 min

### Task 7.3: Write AC-4 and AC-5 integration tests (RED)
- **File:** `tests/test_integration.py` (append)
- **Do:** Add:
  - `test_ac4_kelly_analytical`: `mu=0.0005, sigma=0.01` → `f* = 5.0` within 1e-6
  - `test_ac5_frontier_consistency`: monotonic ruin, `g(2f*) = 0`
- **Done when:** Both tests exist and fail.
- **Est:** ~5 min

### Task 7.4: Implement kelly.py (GREEN)
- **File:** `src/stock_backtester/kelly.py`
- **Do:** Implement:
  - `KellyError` exception class
  - `ruin_probability(f, f_star, D)` — `D^(2/alpha - 1)` with domain guards (f>=2f* → 1.0, f<=0 → 0.0)
  - `growth_rate_fraction(alpha)` — `2*alpha - alpha^2`
  - `critical_kelly_fraction(mu, sigma, ruin_threshold, drawdown_level)` — closed-form `2*mu / (sigma^2 * (ln(P)/ln(D) + 1))`, returns None if f_crit >= 2*f* or mu <= 0
  - `compute_kelly(net_returns, warmup_end_idx, ruin_threshold, drawdown_level)` — slice post-warmup, mu=mean, sigma=std(ddof=0), f*=mu/sigma^2, build frontier at [0.25, 0.50, 0.75, 1.00, 1.50, 2.00], compute critical_kelly
- **Done when:** `uv run pytest tests/test_kelly.py tests/test_integration.py -k "ac4 or ac5"` all pass.
- **Est:** ~15 min

### Task 7.5: Regression check Phase 7
- **Do:** Run `uv run pytest` — all tests from Phases 1-7 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 8: Monte Carlo Simulation

### Task 8.1: Add make_multi_symbol_zero_edge fixture
- **File:** `tests/conftest.py`
- **Do:** Add `make_multi_symbol_zero_edge(n_symbols, n_days, sigma, seed)` — generates PriceData for n symbols with mu=0, given sigma. Uses GBM-like construction: `S_t = S_0 * exp(cumsum(-sigma^2/2*dt + sigma*sqrt(dt)*Z))`.
- **Done when:** Fixture returns PriceData with correct number of symbols and shapes.
- **Est:** ~5 min

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
- **Est:** ~10 min

### Task 8.3: Write AC-6 and AC-7 integration tests (RED)
- **File:** `tests/test_integration.py` (append)
- **Do:** Add:
  - `test_ac6_gbm_moments`: mu=0.10, sigma=0.20, 200 paths, seed=42 → mean and std within 2 SE
  - `test_ac7_zero_edge_sharpe`: 4 symbols, mu=0, EqualWeight, zero costs → Sharpe within 2 SE of 0
- **Done when:** Both tests exist and fail.
- **Est:** ~10 min

### Task 8.4: Implement simulation.py — GBM functions (GREEN part 1)
- **File:** `src/stock_backtester/simulation.py`
- **Do:** Implement:
  - `SimulationError` exception class
  - `calibrate_gbm(prices)` — per-symbol method-of-moments, ddof=1, annualize
  - `generate_gbm_paths(mu_annual, sigma_annual, n_paths, n_days, seed, S0=100.0)` — vectorized: `log_increments = (mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z`, `paths = S0 * exp(cumsum(log_increments))`
  - `generate_multi_symbol_paths(calibrations, n_paths, n_days, seed)` — per-symbol sub-seed: `seed + i`
- **Done when:** `uv run pytest tests/test_simulation.py -k "gbm or calibration or subseed"` pass.
- **Est:** ~15 min

### Task 8.5: Implement simulation.py — Monte Carlo loop (GREEN part 2)
- **File:** `src/stock_backtester/simulation.py`
- **Do:** Implement `run_monte_carlo(prices, strategy, config)`:
  - Run historical backtest + compute_kelly → get half_kelly
  - Calibrate per-symbol GBM
  - Generate paths
  - Loop: construct synthetic PriceData per path, run backtest, check ruin at half_kelly
  - Compute empirical and theoretical ruin rate (portfolio-level mu/sigma)
- **Done when:** `uv run pytest tests/test_simulation.py tests/test_integration.py -k "ac6 or ac7 or ruin_detection"` all pass.
- **Est:** ~15 min

### Task 8.5b: Implement run_verification_tests (GREEN part 3)
- **File:** `src/stock_backtester/simulation.py`
- **Do:** Implement `run_verification_tests(seed)` — runs AC-1 through AC-7 + AC-1b using the real engine pipeline with synthetic data. Returns `list[VerificationResult]`.
- **Note:** `run_verification_tests` is tested indirectly through CLI `verify` command (Task 10.1: `test_cli_verify`) and by the AC integration tests themselves (test_integration.py) which exercise the same pipeline.
- **Done when:** `uv run python -c "from stock_backtester.simulation import run_verification_tests; r = run_verification_tests(42); assert len(r) == 8; assert all(v.passed for v in r)"` succeeds. Function returns 8 VerificationResult objects, all passing.
- **Est:** ~10 min

### Task 8.6: Regression check Phase 8
- **Do:** Run `uv run pytest` — all tests from Phases 1-8 pass. All 8 ACs green.
- **Done when:** Full suite green.
- **Est:** ~2 min

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
- **Est:** ~10 min

### Task 9.2: Implement report.py (GREEN)
- **File:** `src/stock_backtester/report.py`
- **Do:** Implement:
  - `format_backtest_report(metrics, kelly, config, output_format)` — TABLE: survivorship warning + portfolio summary + metrics + Kelly + frontier. JSON: `json.dumps()` of nested dict
  - `format_simulation_report(result, output_format)` — paths, seed, calibrations, ruin rates
  - `format_verification_report(results, output_format)` — AC-N: PASS/FAIL with expected/actual
- **Done when:** `uv run pytest tests/test_report.py` all pass.
- **Est:** ~10 min

### Task 9.3: Regression check Phase 9
- **Do:** Run `uv run pytest` — all tests from Phases 1-9 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 10: CLI

### Task 10.1: Write test_cli.py (RED)
- **File:** `tests/test_cli.py`
- **Do:** Write failing tests using `typer.testing.CliRunner`:
  - `test_cli_verify`: `backtest verify` → exit code 0, all "PASS" in output
  - `test_cli_run_json`: `backtest run --symbols TEST --json` (mock yfinance) → valid JSON
  - `test_cli_simulate`: `backtest simulate --symbols TEST --paths 10 --seed 42` (mock yfinance) → exit code 0, "ruin" in output (tests Task 10.2b's simulate command)
  - `test_cli_invalid_symbol`: invalid symbol → exit code 1, error message
  - `test_cli_help`: `--help` → shows usage without error
- **Done when:** All tests exist and fail.
- **Est:** ~10 min

### Task 10.2a: Implement cli.py — run and verify commands (GREEN part 1)
- **File:** `src/stock_backtester/cli.py`
- **Do:** Implement Typer app with two commands:
  - `run` command: parse `--symbols` → split(",") → fetch_prices → get_strategy → run_backtest → compute_metrics → compute_kelly → format_backtest_report → print
  - `verify` command: run_verification_tests → format_verification_report → print
  - Error handling: catch DataError, StrategyError, KellyError, SimulationError → print message → `raise SystemExit(1)`
- **Done when:** `uv run pytest tests/test_cli.py -k "verify or run_json or help"` pass.
- **Est:** ~10 min

### Task 10.2b: Implement cli.py — simulate command (GREEN part 2)
- **File:** `src/stock_backtester/cli.py`
- **Do:** Add `simulate` command: parse → fetch → strategy → run_monte_carlo → format_simulation_report → print
- **Note:** `simulate` calls `run_monte_carlo()` which internally runs a historical backtest + compute_kelly to get half_kelly, then calibrates GBM and runs the Monte Carlo loop. The CLI does NOT separately call run_backtest/compute_kelly — that redundancy is encapsulated inside run_monte_carlo.
- **Done when:** `uv run pytest tests/test_cli.py` all pass.
- **Est:** ~10 min

### Task 10.3: Update __main__.py
- **File:** `src/stock_backtester/__main__.py`
- **Do:** Replace deferred stub with: `from .cli import app; app()`
- **Done when:** `uv run python -m stock_backtester --help` shows Typer help.
- **Est:** ~2 min

### Task 10.4: Regression check Phase 10
- **Do:** Run `uv run pytest` — all tests from Phases 1-10 pass.
- **Done when:** Full suite green.
- **Est:** ~2 min

---

## Phase 11: Integration & NFR Polish

### Task 11.1: Run full AC suite
- **Do:** `uv run pytest tests/test_integration.py -v` — all 8 ACs pass.
- **Done when:** All AC-1, AC-1b, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 green.
- **Est:** ~2 min

### Task 11.2: Write test_nfr.py (RED)
- **File:** `tests/test_nfr.py`
- **Do:** Write performance tests:
  - `test_backtest_timing`: 4 symbols, 1260 bars, assert < 5s. Construct test data using `make_synthetic_price_data` fixture (do NOT call yfinance).
  - `test_simulation_timing`: 200 paths, 4 symbols, assert < 120s. Use synthetic PriceData.
  - `test_memory_usage`: tracemalloc peak < 500 MB
  - `test_verification_timing`: all ACs < 30s
- **Done when:** Tests exist. May pass or fail depending on performance.
- **Est:** ~10 min

### Task 11.3: Optimize if NFR fails (GREEN)
- **Do:** If test_nfr.py fails, profile and fix:
  1. Run `uv run python -m cProfile -s cumulative -c "from stock_backtester.simulation import run_monte_carlo; ..."` to identify hot functions
  2. **GBM generation:** Ensure `generate_gbm_paths` uses `np.random.default_rng(seed).standard_normal((n_paths, n_days))` matrix, not per-path loops
  3. **Monte Carlo loop:** Ensure PriceData construction per path uses direct DataFrame creation, not row-by-row
  4. **Engine vectorization:** Confirm `(shifted_weights * simple_returns).sum(axis=1)` is vectorized pandas, no Python loops
  5. **Memory:** If peak > 500MB, process paths in chunks of 50 instead of all at once
- **Done when:** `uv run pytest tests/test_nfr.py` all pass.
- **Est:** ~15 min (if optimization needed; ~2 min if already passing)

### Task 11.4: Pyright validation
- **Do:** Run `uv run pyright src/` — 0 errors on basic mode.
- **Done when:** Exit code 0, no type errors.
- **Est:** ~5 min (fix any type errors)

### Task 11.5: Lint check
- **Do:** Run `uv run ruff check src/` — clean.
- **Done when:** Exit code 0, no lint errors.
- **Est:** ~5 min (fix any lint errors)

### Task 11.6: Coverage report
- **Do:** Run `uv run pytest --cov=stock_backtester` — all green.
- **Done when:** Coverage report generated, no test failures.
- **Est:** ~2 min

**Note:** Tasks 11.4, 11.5, and 11.6 can run in parallel — they are independent validation checks.

### Task 11.7: Final CLI verification
- **Do:** Run `uv run backtest verify` from command line.
- **Done when:** All ACs show "PASS", exit code 0.
- **Est:** ~2 min

---

## Task Dependencies

```
0.1 → 0.2 → 0.3 → 1.1
1.1 → 1.2 → 1.3

# Phase 2, 3, 4 can run in parallel after Phase 1
1.3 → 2.1 → 2.2 → 2.3 → 2.4
1.3 → 3.1 → 3.2 → 3.3
1.3 → 4.1 → 4.2 → 4.3

# Phase 5 requires 2 and 4 (engine.py imports execution.py and strategy.py, NOT data.py)
2.4 + 4.3 → 5.1 → 5.2 → 5.3 → 5.4 → 5.5

# Phase 6, 7 can run in parallel after Phase 5
5.5 → 6.1 → 6.2 → 6.3
5.5 → 7.1 → 7.2 → 7.3 → 7.4 → 7.5

# Phase 8 requires 6, 7 (simulation.py does NOT import data.py — it receives PriceData directly; data.py is called by CLI in Phase 10)
6.3 + 7.5 → 8.1 → 8.2 → 8.3 → 8.4 → 8.5 → 8.5b → 8.6

# Phase 9 can run in parallel with 8 (depends only on types)
1.3 → 9.1 → 9.2 → 9.3

# Phase 10 requires 8, 9
8.6 + 9.3 → 10.1 → 10.2a → 10.2b → 10.3 → 10.4

# Phase 11 requires 10
10.4 → 11.1 → 11.2 → 11.3
11.3 → 11.4 ─┐
11.3 → 11.5 ─┼─ (parallel) → 11.7
11.3 → 11.6 ─┘
```

### Parallel Groups

| Group | Tasks | Can Run Simultaneously |
|-------|-------|----------------------|
| A | 2.1-2.4, 3.1-3.3, 4.1-4.3 | Yes (all depend only on Phase 1) |
| B | 6.1-6.3, 7.1-7.5 | Yes (both depend only on Phase 5) |
| C | 8.1-8.6, 9.1-9.3 | Partial (Phase 9 depends only on types, can start earlier) |
| D | 11.4, 11.5, 11.6 | Yes (independent validation checks after 11.3) |

---

## References

| Artifact | Path |
|----------|------|
| PRD | `stock-backtester/docs/brainstorms/2026-02-07-stat-arb-backtester.prd.md` |
| Spec | `stock-backtester/docs/features/001-stat-arb-backtester/spec.md` |
| Design | `stock-backtester/docs/features/001-stat-arb-backtester/design.md` |
| Plan | `stock-backtester/docs/features/001-stat-arb-backtester/plan.md` |

---

## Summary

- **Total tasks:** 51 (12 phases × ~4 tasks avg; includes split tasks 8.5/8.5b and 10.2a/10.2b)
- **Phases:** 12 (0-11)
- **Parallel groups:** 4 (A: Phases 2/3/4, B: Phases 6/7, C: Phases 8/9, D: Phase 11 validation checks)
- **AC coverage:** All 8 ACs mapped to specific tasks (5.3, 7.3, 8.3)
- **Fixture tasks:** 4 (2.1, 5.1, 7.1, 8.1)
- **README:** Deferred to post-implementation buffer (not required by spec or design)
