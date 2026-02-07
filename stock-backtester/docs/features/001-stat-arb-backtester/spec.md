# Specification: Statistical Arbitrage Backtesting System

**Feature:** 001-stat-arb-backtester
**PRD Version:** v6
**Spec Version:** v4

---

## 1. Module Decomposition

The system is organized into nine modules (plus a shared types file) with well-defined boundaries. Each module corresponds to a node (or group of nodes) in the PRD's Mermaid diagram.

```
stock_backtester/
  __init__.py
  cli.py              # Module 1: CLI (Typer entry points)
  data.py             # Module 2: Data Layer
  engine.py           # Module 3: Backtesting Engine
  execution.py        # Module 4: Execution Model
  strategy.py         # Module 5: Strategy Layer
  kelly.py            # Module 6: Kelly/Ruin Analyzer
  simulation.py       # Module 7: Monte Carlo Simulation
  metrics.py          # Module 8: Performance Metrics
  report.py           # Module 9: Report Generator
  types.py            # Shared type definitions
```

### Dependency Graph (imports flow downward)

```
cli (orchestrator)
 ├── data        → fetch multi-symbol prices, align dates
 ├── strategy    → create strategy (EqualWeight / AlwaysLong)
 ├── engine      → run multi-asset backtest → portfolio returns
 ├── metrics     → compute metrics from portfolio returns
 ├── kelly       → compute Kelly from portfolio returns
 ├── simulation  → run multi-symbol Monte Carlo
 └── report      → format output (takes result types, no computation)

engine
 ├── execution   → compute simple returns, per-symbol costs, aggregate to portfolio
 └── strategy    → call compute_weights → weight DataFrame

simulation
 ├── data        → calibrate per-symbol from historical
 └── engine      → reuse backtest logic per path set
```

**Invariant**: No circular imports. `types.py` is imported by all modules but imports none. `report.py` depends only on `types.py` — it formats data but never calls computation modules.

---

## 2. Shared Types (`types.py`)

```python
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from numpy.typing import NDArray


class OutputFormat(Enum):
    TABLE = "table"
    JSON = "json"


@dataclass(frozen=True)
class BacktestConfig:
    """Immutable configuration for a single backtest run."""
    symbols: list[str]                 # e.g. ["AAPL", "MSFT", "GOOG", "AMZN"]
    start_date: str                    # ISO format YYYY-MM-DD
    end_date: str                      # ISO format YYYY-MM-DD
    strategy_name: str                 # e.g. "equal-weight"
    strategy_params: dict[str, float]  # strategy-specific params (empty for EqualWeight)
    commission_per_share: float        # default 0.001
    slippage_k: float                  # default 0.5
    ruin_threshold: float              # default 0.01
    drawdown_level: float              # default 0.50
    output_format: OutputFormat        # default TABLE


@dataclass(frozen=True)
class SimulationConfig:
    """Immutable configuration for Monte Carlo simulation."""
    symbols: list[str]
    start_date: str
    end_date: str
    strategy_name: str
    strategy_params: dict[str, float]
    n_paths: int                       # default 200
    seed: int                          # default 42
    commission_per_share: float
    slippage_k: float
    ruin_threshold: float
    drawdown_level: float
    output_format: OutputFormat


@dataclass(frozen=True)
class PriceData:
    """Validated multi-symbol OHLCV data. Immutable after construction."""
    prices: dict[str, pd.DataFrame]  # {symbol: DataFrame} each with date(index), open, high, low, close, volume
    symbols: list[str]               # ordered list of symbols
    source: str                      # "yfinance"
    adjusted: bool                   # Always True in MVP (auto_adjust=True hardcoded)
    aligned_dates: pd.DatetimeIndex  # common trading dates (inner join)


@dataclass(frozen=True)
class BacktestResult:
    """Complete result of a single backtest run."""
    config: BacktestConfig
    gross_returns: pd.Series       # daily gross PORTFOLIO returns (post-shift, pre-cost)
    net_returns: pd.Series         # daily net PORTFOLIO returns (post-cost)
    weights: pd.DataFrame          # daily weight matrix (dates × symbols, after shift)
    slippage_costs: pd.Series      # daily total slippage cost (summed across symbols)
    commission_costs: pd.Series    # daily total commission cost (summed across symbols)
    equity_curve: pd.Series        # cumulative portfolio value
    warmup_end_idx: int            # positional index (iloc) of first active trading bar


@dataclass(frozen=True)
class KellyResult:
    """Complete Kelly/Ruin analysis output."""
    mu_daily: float                # estimated daily mean return (net)
    sigma_daily: float             # estimated daily return std dev
    full_kelly: float              # f* = mu/sigma^2
    half_kelly: float              # f*/2
    critical_kelly: float | None   # max safe fraction (None if no safe fraction)
    frontier: list["FrontierRow"]
    ruin_threshold: float          # from config
    drawdown_level: float          # from config


@dataclass(frozen=True)
class FrontierRow:
    """One row of the capital efficiency frontier."""
    fraction_label: str       # e.g. "0.50 f*"
    fraction_of_fstar: float  # e.g. 0.50
    growth_pct_of_max: float  # e.g. 75.0
    ruin_probability: float   # e.g. 0.125


@dataclass(frozen=True)
class MetricsResult:
    """Standard performance metrics."""
    sharpe: float
    sortino: float
    max_drawdown: float            # negative value, e.g. -0.187
    max_drawdown_duration_days: int
    annualized_return: float
    annualized_volatility: float
    win_rate: float
    gross_return_total: float
    net_return_total: float
    cost_drag: float               # gross - net


@dataclass(frozen=True)
class SimulationResult:
    """Monte Carlo simulation output."""
    n_paths: int
    seed: int
    per_symbol_calibrations: dict[str, tuple[float, float]]  # {sym: (mu_annual, sigma_annual)}
    empirical_ruin_rate: float     # at half-Kelly
    theoretical_ruin_rate: float   # from formula (using portfolio-level mu/sigma)
    path_results: list[BacktestResult] | None  # None if not stored


@dataclass(frozen=True)
class VerificationResult:
    """Known-answer test output."""
    test_name: str
    passed: bool
    expected: str
    actual: str
    tolerance: str | None
    detail: str
```

---

## 3. Module Interfaces

### 3.1 Data Layer (`data.py`)

**Responsibility**: Fetch, validate, and align multi-symbol OHLCV price data.

```python
def fetch_prices(symbols: list[str], start_date: str, end_date: str) -> PriceData:
    """
    Fetch daily OHLCV data for multiple symbols from yfinance.

    Fetches each symbol individually via yf.download(symbol, start, end,
    auto_adjust=True). Individual downloads are used (not batch) to avoid
    the MultiIndex column structure that yfinance returns for multi-ticker
    batch downloads, which complicates column access.

    With auto_adjust=True (the yfinance default), ALL OHLCV columns
    are split- and dividend-adjusted. There is NO separate 'Adj Close'
    column — the 'Close' column IS the adjusted close.

    After fetching all symbols, aligns on inner join of trading dates
    (only dates where ALL symbols have data). This handles different
    IPO dates, halts, and delistings by keeping only common dates.

    Default date range: if start is None, defaults to 5 years before end.
    If end is None, defaults to today. If both None, (today - 5yr, today).

    Args:
        symbols: list of US stock tickers (e.g., ["AAPL", "MSFT", "GOOG"])
        start_date: ISO date string "YYYY-MM-DD" or None
        end_date: ISO date string "YYYY-MM-DD" or None

    Returns:
        PriceData with validated per-symbol DataFrames and aligned dates

    Raises:
        DataError("No symbols provided")
            if symbols list is empty
        DataError("No data for ticker {symbol}. Check symbol and date range")
            if yfinance returns empty DataFrame for any symbol
        DataError("No common trading days across symbols")
            if inner join of dates produces zero rows
        DataError("Invalid prices: NaN detected in {symbol} at {dates}")
            if any close prices are NaN after fetch
        DataError("Invalid prices: non-positive values in {symbol} at {dates}")
            if any close prices are <= 0
        DataError("Insufficient data for reliable estimation. Need at least 30 trading days")
            if fewer than 30 aligned bars

    Contract:
        - Column names normalized to lowercase after fetch:
          df.columns = df.columns.str.lower()
          (yfinance returns capitalized: Open, High, Low, Close, Volume)
        - Each per-symbol DataFrame index is DatetimeIndex, sorted ascending
        - Columns: open, high, low, close, volume (all float64)
        - ALL OHLCV columns are adjusted (auto_adjust=True)
        - No NaN values in close column for any symbol
        - All close values > 0 for all symbols
        - aligned_dates = inner join of all symbols' trading dates
        - All per-symbol DataFrames are reindexed to aligned_dates
        - source = "yfinance", adjusted = True
    """


def validate_prices(df: pd.DataFrame, symbol: str) -> None:
    """
    Validate price DataFrame for a single symbol. Raises DataError on failure.

    Checks:
        1. No NaN in close column
        2. All close > 0
        3. At least 30 bars (minimum for reliable estimation)
    """


def align_dates(price_dfs: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """
    Compute inner join of trading dates across all symbols.

    Returns:
        DatetimeIndex of dates present in ALL symbol DataFrames.

    Raises:
        DataError("No common trading days across symbols")
            if intersection is empty
    """


class DataError(Exception):
    """Raised for data fetching or validation failures."""
    pass
```

### 3.2 Strategy Layer (`strategy.py`)

**Responsibility**: Compute target weight vectors from multi-symbol price data. Strategies are stateless functions of price history.

```python
from abc import ABC, abstractmethod


class Strategy(ABC):
    """
    Base class for all strategies.

    Contract:
        - compute_weights() receives COPIES of price data (not views)
        - Returns DataFrame of target weights: dates × symbols
        - Weights are intentions: {AAPL: 0.25, MSFT: 0.25, ...}
        - Weights should sum to <= 1.0 per bar (unlevered)
        - NaN weight rows in the warmup period are acceptable —
          the engine will identify and skip them
        - Strategy must NOT apply shift — the engine handles temporal alignment
    """

    @abstractmethod
    def compute_weights(
        self, prices: dict[str, pd.DataFrame], symbols: list[str]
    ) -> pd.DataFrame:
        """
        Compute target position weight vectors for each date.

        Args:
            prices: {symbol: DataFrame} each with columns
                    [open, high, low, close, volume].
                    These are COPIES — mutations do not affect the original.
            symbols: ordered list of symbols

        Returns:
            DataFrame indexed by date, columns = symbols, values = float weights.
            NaN rows in the warmup period are acceptable.

        Raises:
            StrategyError if computation fails
        """

    @property
    @abstractmethod
    def warmup_bars(self) -> int:
        """Number of initial bars needed before first valid signal."""


class EqualWeightStrategy(Strategy):
    """
    Equal-weight (1/N) allocation across all symbols.

    The DeMiguel et al. (2009) benchmark. No signal computation —
    always holds equal weight in every symbol.

    warmup_bars = 0 (immediate signal)
    """

    def compute_weights(
        self, prices: dict[str, pd.DataFrame], symbols: list[str]
    ) -> pd.DataFrame:
        """
        Returns:
            DataFrame where every cell = 1/N (N = number of symbols).
            No NaN values. Index = aligned dates from any symbol's DataFrame.

        Implementation:
            n = len(symbols)
            dates = next(iter(prices.values())).index
            return pd.DataFrame(1.0 / n, index=dates, columns=symbols)
        """

    @property
    def warmup_bars(self) -> int:
        return 0


class AlwaysLongStrategy(Strategy):
    """
    Always hold equal weight in all symbols. Functionally identical to
    EqualWeightStrategy — exists as a named alias for semantic clarity:
    - "equal-weight" is the user-facing strategy name (CLI default)
    - "always-long" is the test fixture name (AC-1, AC-2)
    This avoids a single class serving dual roles with confusing naming.

    warmup_bars = 0 (immediate signal)

    Note: For single-symbol use, this degenerates to weight=1.0.
    """

    def compute_weights(
        self, prices: dict[str, pd.DataFrame], symbols: list[str]
    ) -> pd.DataFrame:
        """
        Returns:
            DataFrame where every cell = 1/N.
            Identical to EqualWeightStrategy.
        """

    @property
    def warmup_bars(self) -> int:
        return 0


def get_strategy(name: str, params: dict[str, float]) -> Strategy:
    """
    Factory function. Returns strategy instance.

    Args:
        name: "equal-weight" or "always-long" (MVP options)
        params: strategy-specific params (empty dict for both MVP strategies)

    Raises:
        StrategyError(f"Unknown strategy: {name}")
    """


class StrategyError(Exception):
    pass
```

### 3.3 Backtesting Engine (`engine.py`)

**Responsibility**: Orchestrate the multi-asset backtest pipeline. Enforces shift(1) as the single temporal alignment point. Computes portfolio returns from weight vectors.

```python
def run_backtest(
    config: BacktestConfig,
    prices: PriceData,
    strategy: Strategy,
    slippage_k: float = 0.5,
    commission_per_share: float = 0.001,
) -> BacktestResult:
    """
    Run a vectorized multi-asset backtest with enforced look-ahead prevention.

    Pipeline:
        1. Pass {sym: df.copy()} to strategy.compute_weights()
           → returns DataFrame of weights (dates × symbols)
        2. Apply shift(1) to raw weight DataFrame → executed weights
        3. Compute per-symbol daily SIMPLE returns: R_{t,i} = P_{t,i}/P_{t-1,i} - 1
           → returns DataFrame (dates × symbols)
        4. Compute gross portfolio SIMPLE return per bar:
           R_p,t = sum_i(w_{t,i} * R_{t,i})
           (weighted sum of simple returns is exact for portfolio aggregation)
        5. Convert to portfolio LOG-return:
           r_p,t = ln(1 + R_p,t)
           NOTE: Weighted sum of log-returns ≠ portfolio log-return. Cross-sectional
           aggregation MUST use simple returns. This is a well-known mathematical
           property: ln(sum(w_i * exp(r_i))) ≠ sum(w_i * r_i) due to Jensen's
           inequality. The error is always negative and compounds over time.
        6. Compute slippage and commission costs via execution model
           (per-symbol weight changes, summed to portfolio-level cost)
        7. Compute net returns: net_t = r_p,t - slippage_t - commission_t
           (costs are small enough that subtracting from log-returns is a valid
           first-order approximation; for costs > 1% per bar, this breaks down)
        8. Build equity curve: equity = exp(cumsum(net_returns)), normalized to 1.0
           Since net_returns are log-returns, exp(cumsum) correctly compounds.

    Shift(1) contract:
        - Raw weight DataFrame from strategy represents "what I want to hold tomorrow"
        - shift(1) makes it "what I hold today based on yesterday's signal"
        - This is applied ONCE, HERE, in the engine — nowhere else
        - The first row after shift has NaN weights → treated as 0 (flat in all symbols)

    Warmup handling:
        - Identify warmup_end_idx: first bar where shifted weights are not NaN
        - All bars before warmup_end_idx have all positions = 0, return = 0
        - The transition from 0 to first target weights IS a trade
          (incurs slippage and commission per symbol)

    Args:
        config: BacktestConfig (embedded in BacktestResult for provenance)
        prices: Validated PriceData (multi-symbol)
        strategy: Strategy instance
        slippage_k: multiplier for volatility-based slippage
        commission_per_share: flat per-share commission

    Returns:
        BacktestResult with portfolio return series and weight matrix

    Invariants:
        - len(gross_returns) == len(net_returns) == len(prices.aligned_dates)
        - net_returns[i] <= gross_returns[i] for all i where trading occurs
        - weights are always the SHIFTED weight matrix (no look-ahead)
    """
```

### 3.4 Execution Model (`execution.py`)

**Responsibility**: Apply transaction costs to per-symbol weight changes, aggregated to portfolio level. Also provides return computation utilities (simple and log) used by the engine and simulation modules. These live here rather than in a separate utils module because they are tightly coupled to the execution/cost model (trailing volatility needs log-returns, portfolio aggregation needs simple returns).

```python
def compute_costs(
    prices: PriceData,
    weights: pd.DataFrame,
    slippage_k: float,
    commission_per_share: float,
) -> tuple[pd.Series, pd.Series]:
    """
    Compute slippage and commission costs for each bar, summed across symbols.

    All costs are expressed as FRACTIONAL costs (dimensionless, same
    units as log-returns) so they can be directly subtracted from
    gross returns: net_return_t = gross_return_t - slippage_t - commission_t.

    For each symbol i on each bar t:

    Slippage model:
        slippage_{t,i} = k * sigma_trailing_i(20) * |delta_w_{t,i}|

        where:
            k = slippage multiplier (default 0.5, dimensionless)
            sigma_trailing_i(20) = std of symbol i's most recent 20 daily
                                   log-returns (dimensionless, NOT annualized)
            delta_w_{t,i} = w_{t,i} - w_{t-1,i} (weight change for symbol i)

        This is a first-order approximation valid when:
            - Individual slippage terms are small (< 0.5% per bar)
            - Weight changes are modest (typical for daily rebalance)
        For large weight swings (e.g., 0→1 on first trade), the linear
        model overstates cost vs a square-root impact model. Accepted for MVP.

    Commission model:
        commission_{t,i} = commission_rate_i * |delta_w_{t,i}|

        where commission_rate_i = commission_per_share / close_price_{t,i}.
        This converts the per-share cost into a fractional cost.

        Dimensional analysis:
            commission_per_share: $/share
            close_price_{t,i}: $/share
            commission_rate = ($/share) / ($/share) = dimensionless ✓

        Economic mapping: commission_per_share is a user-facing parameter
        (e.g., $0.001/share for IBKR Pro). The division by close_price
        converts it to a fractional cost so it can be applied to
        weight-based position changes. For a $100 stock with $0.001/share
        commission, the fractional rate is 0.001% per unit weight change.

    Portfolio-level aggregation:
        slippage_t = sum_i(slippage_{t,i})
        commission_t = sum_i(commission_{t,i})

    Trailing volatility edge cases:
        - If fewer than 20 bars available, use all available bars (min 2)
        - If trailing vol is 0 (halted stock, constant price), slippage = 0
          for that symbol

    Args:
        prices: PriceData with per-symbol DataFrames
        weights: DataFrame of position weights (dates × symbols, already shifted)
        slippage_k: multiplier (default 0.5)
        commission_per_share: per-share cost (default 0.001)

    Returns:
        (slippage_costs, commission_costs) — both non-negative Series
        indexed by date, in fractional units (same as log-returns).
        These are portfolio-level totals (summed across symbols).

    Invariants:
        - slippage_costs >= 0 for all bars
        - commission_costs >= 0 for all bars
        - costs are 0 when no position changes in any symbol
    """


def compute_simple_returns(prices: pd.DataFrame) -> pd.Series:
    """
    Compute daily simple returns for a single symbol: R_t = P_t/P_{t-1} - 1.

    Used by engine for cross-sectional portfolio aggregation (Step 3-4).

    Returns Series with first value = NaN (no prior price).
    """


def compute_multi_symbol_simple_returns(prices: PriceData) -> pd.DataFrame:
    """
    Compute daily simple returns for all symbols.

    Used by engine for portfolio return computation:
        R_p,t = sum_i(w_{t,i} * R_{t,i})

    Returns DataFrame (dates × symbols) with first row = NaN.
    """


def compute_log_returns(prices: pd.DataFrame) -> pd.Series:
    """
    Compute daily log-returns for a single symbol: r_t = ln(P_t / P_{t-1}).

    Used by execution model (trailing volatility) and simulation (calibration).

    Returns Series with first value = NaN (no prior price).
    """


def compute_multi_symbol_log_returns(prices: PriceData) -> pd.DataFrame:
    """
    Compute daily log-returns for all symbols.

    Used by simulation for per-symbol GBM calibration.

    Returns DataFrame (dates × symbols) with first row = NaN.
    """


def compute_trailing_volatility(
    log_returns: pd.Series, window: int = 20
) -> pd.Series:
    """
    Rolling standard deviation of log-returns for a single symbol.

    If fewer than `window` bars available at the start,
    uses expanding window with minimum 2 observations.
    """
```

### 3.5 Performance Metrics (`metrics.py`)

**Responsibility**: Compute standard performance metrics from return series.

```python
def compute_metrics(
    net_returns: pd.Series,
    gross_returns: pd.Series,
    warmup_end_idx: int,
) -> MetricsResult:
    """
    Compute all MVP performance metrics.

    All computations use post-warmup returns ONLY.
    The warmup period (bars 0..warmup_end_idx-1) is excluded.

    Metric definitions (all use ARITHMETIC mean/std of daily log net returns):

    Sharpe (arithmetic, ex-post):
        annualized_return / annualized_volatility
        where annualized_return = mean(net_daily) * 252  (arithmetic mean of log-returns)
              annualized_volatility = std(net_daily, ddof=1) * sqrt(252)

        NOTE: Sharpe uses ddof=1 (sample std) because it is an inferential
        statistic estimating population Sharpe. Kelly uses ddof=0 (population
        std) because the continuous Kelly formula uses population parameters.
        NOTE: The Sharpe numerator (mean * 252) differs from the displayed
        Annualized Return metric (exp(mean*252) - 1). The former is standard
        for log-return-based Sharpe; the latter converts to percentage for
        user readability. They are equivalent for small daily returns.

    Sortino:
        annualized_return / annualized_downside_deviation
        where downside_deviation = sqrt((1/N) * sum(min(r_t, 0)^2))
              MAR = 0
              N = total bar count (full-count convention per Sortino 2001,
                  NOT just downside observations)
              annualized_DD = DD_daily * sqrt(252)

    Max Drawdown:
        max peak-to-trough decline in equity curve (negative value)
        max_drawdown_duration = longest period (in trading days) from
        peak to recovery (or to end of series if no recovery)

    Win Rate:
        count(net_daily > 0) / count(net_daily != 0)
        Excludes days with zero return (no position)

    Annualized Return (geometric):
        exp(mean(net_daily_log) * 252) - 1
        This converts from log-return space to percentage for display.
        More intuitive than raw log-return for reporting.

    Annualized Volatility:
        std(net_daily) * sqrt(252)

    Returns:
        MetricsResult dataclass
    """
```

### 3.6 Kelly/Ruin Analyzer (`kelly.py`)

**Responsibility**: Kelly fraction estimation, ruin probability, capital efficiency frontier.

```python
def compute_kelly(
    net_returns: pd.Series,
    warmup_end_idx: int,
    ruin_threshold: float = 0.01,
    drawdown_level: float = 0.50,
) -> KellyResult:
    """
    Full Kelly/Ruin analysis from NET return series (post slippage+commission).

    Uses post-warmup returns only. Using net returns is critical — computing
    Kelly from gross returns overstates the optimal fraction because it
    ignores friction that scales with leverage.

    Step 1 — Estimate parameters:
        mu_daily = mean(net_returns[warmup_end_idx:])
        sigma_daily = std(net_returns[warmup_end_idx:], ddof=0)

        Convention: use population std (ddof=0), NOT sample std (ddof=1).
        Rationale: the continuous Kelly formula f* = mu/sigma^2 uses
        population parameters. Using ddof=1 would bias f* downward
        for small samples. Both AC-4 test fixture and this estimator
        MUST use the same ddof=0 convention.

    Step 2 — Full Kelly:
        f_star = mu_daily / sigma_daily^2

        If f_star <= 0:
            Return KellyResult with full_kelly=f_star,
            critical_kelly=None, empty frontier.
            Report: "Strategy has negative expected return."

    Step 3 — Critical Kelly solver (closed-form):
        f_critical = 2*mu / (sigma^2 * (ln(P_target)/ln(D) + 1))

        Validity check:
            if f_critical >= 2*f_star:
                critical_kelly = None
                (no safe fraction exists at given drawdown level)
            else:
                Verify by plugging back: P(ruin|f_critical, D) ≈ P_target
                within tolerance 1e-6

    Step 4 — Capital efficiency frontier:
        For each alpha in [0.25, 0.50, 0.75, 1.00, 1.50, 2.00]:
            f = alpha * f_star
            growth_pct = (2*alpha - alpha^2) * 100
            ruin = D^(2/alpha - 1)  if alpha < 2.0
            ruin = 1.0              if alpha >= 2.0

    Args:
        net_returns: daily net return series
        warmup_end_idx: first active trading bar index
        ruin_threshold: max acceptable ruin probability (default 0.01)
        drawdown_level: drawdown fraction (default 0.50)

    Returns:
        KellyResult

    Raises:
        KellyError("Insufficient data for Kelly estimation. Need >= 30 bars")
            if post-warmup returns have fewer than 30 observations
    """


def ruin_probability(f: float, f_star: float, D: float) -> float:
    """
    P(ruin | f, D) = D^(2*mu/(sigma^2*f) - 1)

    Simplified using alpha = f/f_star:
        P = D^(2/alpha - 1)

    Domain:
        if alpha >= 2.0: return 1.0
        if alpha <= 0.0: return 0.0 (no position, no ruin)
        if D <= 0 or D >= 1: raise ValueError
    """


def growth_rate_fraction(alpha: float) -> float:
    """
    Growth rate as fraction of maximum: 2*alpha - alpha^2

    Domain:
        alpha >= 0
        Returns 0.0 at alpha=0, 1.0 at alpha=1, 0.0 at alpha=2
    """


def critical_kelly_fraction(
    mu: float,
    sigma: float,
    ruin_threshold: float,
    drawdown_level: float,
) -> float | None:
    """
    Closed-form critical Kelly solver.

    f_critical = 2*mu / (sigma^2 * (ln(P_target)/ln(D) + 1))

    Returns None if:
        - mu <= 0 (no edge)
        - f_critical >= 2*f_star (no safe fraction exists)
    """


class KellyError(Exception):
    pass
```

### 3.7 Monte Carlo Simulation (`simulation.py`)

**Responsibility**: Multi-symbol GBM path generation, moment-matching calibration, Monte Carlo backtest loop.

```python
def calibrate_gbm(prices: PriceData) -> dict[str, tuple[float, float]]:
    """
    Method-of-moments calibration from historical data, per symbol.

    For each symbol:
        Compute daily log-returns: r_t = ln(P_t / P_{t-1})
        mu_daily = mean(r_t)
        sigma_daily = std(r_t, ddof=1)  # sample std for unbiased estimate

        Annualize:
            mu_annual = mu_daily * 252
            sigma_annual = sigma_daily * sqrt(252)

    Returns:
        {symbol: (mu_annual, sigma_annual)} for each symbol
    """


def generate_gbm_paths(
    mu_annual: float,
    sigma_annual: float,
    n_paths: int,
    n_days: int,
    seed: int,
    S0: float = 100.0,
) -> NDArray[np.float64]:
    """
    Generate GBM price paths for a single symbol.

    For each path i, each day t:
        S_{t+1} = S_t * exp((mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
    where dt = 1/252, Z ~ N(0,1)

    Args:
        mu_annual: annualized drift parameter
        sigma_annual: annualized volatility
        n_paths: number of paths to simulate
        n_days: trading days per path
        seed: random seed for reproducibility
        S0: initial price (default 100.0)

    Returns:
        ndarray of shape (n_paths, n_days+1) — price paths including S0

    Contract:
        - Setting the same seed produces identical output
        - All prices > 0 (GBM property)
    """


def generate_multi_symbol_paths(
    calibrations: dict[str, tuple[float, float]],
    n_paths: int,
    n_days: int,
    seed: int,
) -> dict[str, NDArray[np.float64]]:
    """
    Generate independent GBM paths for each symbol.

    Each symbol gets its own set of n_paths paths using deterministic
    sub-seeds derived from the master seed: sub_seed_i = seed + i.
    This ensures adding/removing a symbol doesn't change other symbols' paths.

    NOTE: Symbols are simulated independently (no correlation structure).
    This is a simplification — real assets are correlated. Accepted for
    MVP; the North Star adds factor model / copula correlation.

    Returns:
        {symbol: ndarray(n_paths, n_days+1)} for each symbol
    """


def run_monte_carlo(
    prices: PriceData,
    strategy: Strategy,
    config: SimulationConfig,
) -> SimulationResult:
    """
    Multi-symbol Monte Carlo backtest loop.

    Pipeline:
        1. Calibrate GBM per symbol from historical prices
        2. Generate n_paths synthetic price paths per symbol
        3. For each path index p:
           a. For each symbol, extract path p → construct per-symbol DataFrame
           b. Synthetic DataFrames: close=simulated price, open=high=low=close,
              volume=1e6 (constant placeholder), dates=pd.bdate_range(n_days)
              Columns are lowercase (matching data layer contract).
              Synthetic data is NOT passed through fetch_prices validation
              but conforms to the same DataFrame schema (Section 4.1).
           c. Assemble into PriceData with all symbols
           d. Run backtest with same strategy and cost parameters
           e. Check if equity curve hits drawdown_level at half-Kelly sizing
        4. Compute empirical ruin rate = count(ruin) / n_paths
        5. Compute theoretical ruin rate from formula at half-Kelly
           (using portfolio-level mu and sigma from historical backtest)

    Half-Kelly source:
        Before the Monte Carlo loop, run compute_kelly() on the HISTORICAL
        backtest's net returns to obtain half_kelly. This is the same value
        the user sees in the backtest report. The simulation tests whether
        the historical half-Kelly survives under GBM-simulated conditions.

    Ruin detection for each path:
        Scale net returns by (half_kelly / 1.0) to simulate leveraged returns.
        Check if equity curve ever drops below (1 - drawdown_level) * peak.

        NOTE: This is an approximation. Ruin detection scales returns
        linearly but does not re-run the backtest at the leveraged
        position size. Transaction costs at higher leverage would be
        proportionally higher, making this an optimistic estimate of
        empirical ruin rate. Accepted for MVP; the North Star
        cost-leverage interaction model addresses this.

        NOTE: Independent GBM per symbol ignores cross-asset correlation.
        This may underestimate tail risk for correlated portfolios.

    Returns:
        SimulationResult with empirical and theoretical ruin rates.
        theoretical_ruin_rate uses portfolio-level mu_daily and sigma_daily
        from the historical backtest's net returns (same values as compute_kelly),
        NOT from the per-symbol GBM calibration parameters.
    """


class SimulationError(Exception):
    """Raised for simulation failures (NaN/Inf in paths, invalid parameters)."""
    pass


def run_verification_tests(seed: int = 42) -> list[VerificationResult]:
    """
    Run all known-answer verification tests.

    Note: This function lives in simulation.py because it depends on
    GBM path generation (AC-6, AC-7) and the backtest engine. It is
    the only non-simulation function in this module — accepted because
    creating a separate verification module for one function adds
    unnecessary file count.

    AC-1: Deterministic 1% daily rise, single symbol, AlwaysLong, zero cost
        Expected total return: (1.01^10 - 1) = 10.4622...%

    AC-1b: Multi-symbol portfolio return (2 symbols, known simple returns)
        Validates simple-return aggregation vs incorrect log-return aggregation

    AC-2: Perfect foresight strategy with shift(1), single symbol
        Verify return < sum of all positive daily returns

    AC-3: Slippage invariant (net < gross)

    AC-4: Deterministic return series with mu=0.0005, sigma=0.01
        Expected f* = 0.0005/0.01^2 = 5.0

    AC-5: Frontier consistency (monotonic ruin, g(2f*)=0)

    AC-6: GBM moment matching (single symbol for moment test)
        mu=0.10/yr, sigma=0.20/yr, 200 paths, 252 days
        Check: mean log-return within 2 SE of (mu-sigma^2/2)*T
        Check: std of log-returns within 2 SE of sigma*sqrt(T)

    AC-7: Zero-edge GBM, multi-symbol (4 symbols, mu=0 each)
        Run EqualWeight strategy on 4-symbol zero-edge paths
        Check: portfolio Sharpe within 2 SE of zero

    Returns:
        List of VerificationResult, one per AC
    """
```

### 3.8 Report Generator (`report.py`)

**Responsibility**: Format and output results.

```python
def format_backtest_report(
    metrics: MetricsResult,
    kelly: KellyResult,
    config: BacktestConfig,
    output_format: OutputFormat,
) -> str:
    """
    Format complete backtest report.

    TABLE format:
        Survivorship warning (always first, non-suppressible)
        Portfolio summary: symbols, strategy name, weight allocation
        Historical Performance section:
            Sharpe, Sortino, Annual Return (annualized net),
            Max Drawdown (with duration in days),
            Annualized Vol, Win Rate,
            Gross Return, Net Return, Cost Drag
        Kelly Analysis section:
            Estimated edge (mu/day), Volatility (sigma/day),
            Full Kelly (f*), Half Kelly,
            Critical Kelly (with ruin threshold + drawdown level)
        Capital Efficiency Frontier table:
            6 rows at 0.25/0.50/0.75/1.00/1.50/2.00 f*

    JSON format:
        Identical data as nested dict, serialized to JSON.

    Survivorship warning (non-suppressible):
        "WARNING: Data source: yfinance (survivorship-biased).
         Results may overstate performance."

    Returns:
        Formatted string (CLI table or JSON)
    """


def format_simulation_report(
    result: SimulationResult,
    output_format: OutputFormat,
) -> str:
    """
    Format Monte Carlo simulation report.

    Includes:
        - Number of paths and seed
        - Calibrated mu and sigma
        - Empirical ruin rate at half-Kelly
        - Theoretical ruin rate
        - GBM limitation note
    """


def format_verification_report(
    results: list[VerificationResult],
    output_format: OutputFormat,
) -> str:
    """
    Format verification test report.

    Each test: AC-N (name): PASS/FAIL (expected: X, got: Y)
    """
```

### 3.9 CLI (`cli.py`)

**Responsibility**: Parse arguments, orchestrate pipeline, output results.

```python
import typer

app = typer.Typer()


@app.command()
def run(
    symbols: str = typer.Option(..., help="Comma-separated US stock tickers"),
    strategy: str = typer.Option("equal-weight", help="Strategy name"),
    start: str = typer.Option(None, help="Start date YYYY-MM-DD"),
    end: str = typer.Option(None, help="End date YYYY-MM-DD"),
    commission: float = typer.Option(0.001, help="Per-share commission"),
    slippage_k: float = typer.Option(0.5, help="Slippage multiplier"),
    ruin_threshold: float = typer.Option(0.01, help="Max ruin probability"),
    drawdown_level: float = typer.Option(0.50, help="Drawdown threshold"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Run multi-asset backtest on historical data with Kelly analysis."""
    # 1. Parse symbols: symbols.split(",") → list[str]
    # 2. Build config
    # 3. Fetch prices via data.fetch_prices(symbol_list, ...)
    # 4. Create strategy via strategy.get_strategy()
    # 5. Run backtest via engine.run_backtest()
    # 6. Compute metrics via metrics.compute_metrics()
    # 7. Compute Kelly via kelly.compute_kelly()
    # 8. Format and print report via report.format_backtest_report()


@app.command()
def simulate(
    symbols: str = typer.Option(..., help="Comma-separated US stock tickers"),
    strategy: str = typer.Option("equal-weight"),
    start: str = typer.Option(None),
    end: str = typer.Option(None),
    paths: int = typer.Option(200, help="Number of Monte Carlo paths"),
    seed: int = typer.Option(42, help="Random seed"),
    commission: float = typer.Option(0.001),
    slippage_k: float = typer.Option(0.5),
    ruin_threshold: float = typer.Option(0.01),
    drawdown_level: float = typer.Option(0.50),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Run strategy on GBM-simulated paths, compare empirical vs theoretical ruin."""


@app.command()
def verify(
    seed: int = typer.Option(42, help="Seed for stochastic tests"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """
    Run known-answer tests to verify engine correctness.

    The seed parameter affects only stochastic tests (AC-6, AC-7).
    Deterministic tests (AC-1, AC-1b, AC-2, AC-3, AC-4, AC-5) ignore the seed.
    """
```

---

## 4. Data Contracts

### 4.1 DataFrame Schema (per symbol)

| Column | dtype | Constraint | Source |
|--------|-------|-----------|--------|
| `date` | DatetimeIndex | sorted ascending, no duplicates, aligned across symbols | yfinance |
| `open` | float64 | > 0 | yfinance (adjusted via auto_adjust=True) |
| `high` | float64 | >= open, >= close | yfinance (adjusted via auto_adjust=True) |
| `low` | float64 | <= open, <= close | yfinance (adjusted via auto_adjust=True) |
| `close` | float64 | > 0, no NaN | yfinance (adjusted via auto_adjust=True) |
| `volume` | float64 | >= 0 | yfinance |

**Note**: With `auto_adjust=True`, all OHLC columns are split- and dividend-adjusted. There is no separate 'Adj Close' column. MVP uses only the `close` column for return computation. Open/High/Low are passed through for completeness but not used by EqualWeight/AlwaysLong strategies. Each symbol has its own DataFrame; all are reindexed to the same `aligned_dates` (inner join).

### 4.2 Immutability Contract

- `PriceData.prices` dict values are passed to strategies as `.copy()` — strategies cannot mutate engine data
- All `@dataclass(frozen=True)` types are immutable after construction
- `BacktestConfig` and `SimulationConfig` are frozen — no mid-run parameter changes

### 4.3 Return Convention

Two return types are used for mathematically distinct purposes:

- **Simple returns** for cross-sectional (multi-asset) aggregation:
  `R_t = P_t/P_{t-1} - 1`. Portfolio return: `R_p,t = sum_i(w_i * R_{t,i})`.
  Weighted sum of simple returns IS the portfolio simple return (exact).
- **Log-returns** for time-series operations:
  `r_t = ln(P_t / P_{t-1}) = ln(1 + R_t)`. Equity curve: `exp(cumsum(r_t))`.
  Additive over time, so cumulative sum gives total log-return.
- **Conversion** in engine pipeline (Step 5): `r_p,t = ln(1 + R_p,t)`.
  This bridges cross-sectional aggregation (simple) to time-series compounding (log).
- **Daily scale** for internal computation
- **Annualized** for reporting: `* 252` for mean, `* sqrt(252)` for std
- **Net returns** for Kelly estimation (post slippage and commission)
- **Sharpe/Sortino** use arithmetic mean and std of daily log net returns.
  This is the standard convention for daily-rebalanced portfolios.

---

## 5. Acceptance Criteria — Detailed Test Specifications

### AC-1: Historical backtest produces correct returns

```python
def test_ac1_correct_returns():
    """
    Construct: single symbol, 11-day price series starting at 100, rising 1%/day
        prices = {"TEST": DataFrame with close=[100, 101, 102.01, ..., 110.462...]}

    Strategy: AlwaysLongStrategy — returns weight={TEST: 1.0} for all bars
        (no warmup, NaN only for first bar from shift)

    Config: slippage_k=0, commission=0, symbols=["TEST"]

    Assert:
        total_return = equity_curve[-1] / equity_curve[warmup_end_idx] - 1
        abs(total_return - (1.01**10 - 1)) < 1e-10

    Note: 11 prices → 10 daily returns → 10 days of trading.
    AlwaysLongStrategy has warmup_bars=0. After shift(1), bar 0's
    weight is NaN (treated as 0), so first executed position is bar 1.
    Equity curve starts at bar 1 (warmup_end_idx=1).

    Single-symbol degenerate case validates basic engine correctness
    before multi-asset complexity.
    """
```

### AC-1b: Multi-symbol portfolio return aggregation

```python
def test_ac1b_multi_symbol_portfolio_return():
    """
    Construct: 2 symbols ("A", "B"), 3-day price series
        A: close = [100, 105, 110]   → simple returns: [NaN, +5%, +4.76%]
        B: close = [100,  95, 100]   → simple returns: [NaN, -5%, +5.26%]

    Strategy: EqualWeightStrategy → weights = {A: 0.5, B: 0.5} for all bars

    Config: slippage_k=0, commission=0

    Expected portfolio simple returns (after shift(1)):
        Bar 0: NaN (shift)
        Bar 1: 0.5*(+0.05) + 0.5*(-0.05) = 0.0
        Bar 2: 0.5*(+0.0476...) + 0.5*(+0.0526...) = +0.0501...

    Expected portfolio log-returns:
        Bar 1: ln(1 + 0.0)     = 0.0
        Bar 2: ln(1 + 0.0501)  = 0.04889...

    Expected equity curve (from bar 1):
        exp(0.0) = 1.0
        exp(0.0 + 0.04889) = 1.0501...

    Assert:
        abs(equity_curve[-1] - 1.0501...) < 1e-6

    Why this test matters:
        If the engine incorrectly aggregates LOG-returns instead of
        simple returns, Bar 1 would give:
            0.5*ln(1.05) + 0.5*ln(0.95) = 0.5*(0.04879) + 0.5*(-0.05129) = -0.00125
        This is WRONG (negative when true portfolio return is zero).
        The error comes from Jensen's inequality and compounds over time.
    """
```

### AC-2: Look-ahead prevention verified

```python
def test_ac2_look_ahead_prevention():
    """
    Construct: single symbol, random price series with known up/down days (seeded)

    Strategy: PerfectForesightStrategy (single-symbol)
        - Knows future returns (implemented as: returns[t] > 0 → w={sym: 1.0}, else w={sym: 0.0})
        - This is the RAW signal — engine applies shift(1)

    Assert:
        After shift(1), the strategy's realized return is strictly less than
        sum of all positive daily returns.

        Specifically:
            perfect_return = sum(r_t for r_t in daily_returns if r_t > 0)
            backtest_return = total return from engine
            backtest_return < perfect_return

    Why: shift(1) means the foresight signal arrives one day late,
    so it sometimes goes long before a down day (stale signal).
    """
```

### AC-3: Slippage reduces returns

```python
def test_ac3_slippage_invariant():
    """
    Run: any strategy on any price data with slippage_k > 0

    Assert: For every bar where a trade occurs (position changes):
        net_return[t] <= gross_return[t]

    Also assert globally:
        total_net_return < total_gross_return
        sum(slippage_costs) > 0
        sum(commission_costs) > 0
    """
```

### AC-4: Kelly fraction matches analytical solution

```python
def test_ac4_kelly_analytical():
    """
    Construct: deterministic return series with exact moments
        mu = 0.0005 (0.05%/day)
        sigma = 0.01 (1.0%/day)

        Construction: 100 bars alternating between
            r_a = mu + sigma = 0.0105
            r_b = mu - sigma = -0.0095
        mean(r_a, r_b) = 0.0005 ✓
        std(r_a, r_b) = 0.01 ✓  (population std, use ddof=0 if needed)

    Note: Both test fixture and Kelly estimator use ddof=0 (population std).
    For an even-length alternating series:
        mean = (r_a+r_b)/2 = 0.0005 ✓
        std(ddof=0) = |r_a - r_b|/2 = 0.01 ✓

    Expected: f* = 0.0005 / 0.01^2 = 5.0

    Assert: abs(kelly_result.full_kelly - 5.0) < 1e-6
    """
```

### AC-5: Capital efficiency frontier is internally consistent

```python
def test_ac5_frontier_consistency():
    """
    Given: any KellyResult with full_kelly > 0

    Assert:
        1. growth at alpha=0 would be 0% (not in table, but formula)
        2. growth at alpha=1.0 is 100% (maximum)
        3. growth at alpha=2.0 is 0%
        4. Ruin probability is monotonically increasing across the table
        5. Ruin at alpha=2.0 is exactly 1.0

    Also verify formula consistency:
        For each row: growth_pct ≈ (2*alpha - alpha^2) * 100
        For each row: ruin ≈ D^(2/alpha - 1) where D = drawdown_level
    """
```

### AC-6: GBM moment matching

```python
def test_ac6_gbm_moments():
    """
    Config: mu=0.10/yr, sigma=0.20/yr, n_paths=200, n_days=252, seed=42

    Generate paths. For each path, compute terminal log-return:
        log_return = ln(S_T / S_0)

    Across all paths:
        mean_log_return = mean of terminal log-returns
        std_log_return = std of terminal log-returns

    Theoretical:
        expected_mean = (mu - sigma^2/2) * T = (0.10 - 0.02) * 1 = 0.08
        expected_std = sigma * sqrt(T) = 0.20

    Standard errors:
        SE_mean = std_log_return / sqrt(n_paths)
        SE_std = std_log_return / sqrt(2 * n_paths)  # approx

    Assert:
        abs(mean_log_return - expected_mean) < 2 * SE_mean
        abs(std_log_return - expected_std) < 2 * SE_std

    Determinism: fixed seed=42 ensures this test is deterministic in CI.
    """
```

### AC-7: Known-answer verification (zero-edge, multi-symbol)

```python
def test_ac7_zero_edge():
    """
    Config: 4 symbols, each with mu=0, sigma=0.20/yr,
            n_paths=200, n_days=252, seed=42,
            slippage_k=0, commission_per_share=0

    Run EqualWeight strategy on 4-symbol zero-edge GBM paths.
    Zero costs used so that only the return aggregation is tested
    (costs would create a negative bias obscuring the zero-edge test).

    For each path set, compute annualized Sharpe from the portfolio's
    daily net returns (= gross returns since costs are zero).
    Compute mean_sharpe = mean of all path-level Sharpes.
    Compute SE_sharpe = std(path_sharpes) / sqrt(n_paths).

    Expected: mean_sharpe ≈ 0 (no edge → no risk-adjusted return,
              even with diversification across 4 zero-edge symbols)

    Assert: abs(mean_sharpe) < 2 * SE_sharpe

    Note: This test validates that the multi-asset engine does not
    create phantom returns from portfolio construction. With equal-weight
    across 4 independent zero-edge assets, portfolio vol decreases by
    ~sqrt(4)=2x but expected return remains zero, so Sharpe ≈ 0.

    Note: Independent GBM per symbol means no cross-asset correlation.
    For zero-edge assets, this is acceptable — correlation affects
    portfolio variance but not expected return. However, ruin rate
    comparisons (empirical vs theoretical) may differ because the
    theoretical formula assumes a single-asset return stream, while
    the empirical rate comes from a diversified portfolio.

    Determinism: fixed seed=42.
    """
```

---

## 6. Error Taxonomy

| Error Class | Module | Trigger | User-Facing Message |
|------------|--------|---------|-------------------|
| `DataError` | data | Empty ticker response | "No data for ticker X. Check symbol and date range" |
| `DataError` | data | No trading days | "No trading days in range" |
| `DataError` | data | NaN prices | "Invalid prices: NaN detected at {dates}" |
| `DataError` | data | Non-positive prices | "Invalid prices: non-positive values at {dates}" |
| `DataError` | data | < 30 bars | "Insufficient data for reliable estimation. Need at least 30 trading days" |
| `StrategyError` | strategy | Unknown strategy name | "Unknown strategy: {name}" |
| `StrategyError` | strategy | NaN weights produced | "Strategy produced NaN weights on date X. Check strategy logic or data quality" |
| `KellyError` | kelly | < 30 post-warmup bars | "Insufficient data for Kelly estimation. Need >= 30 active trading bars" |
| `SimulationError` | simulation | NaN/Inf in paths | "Simulation produced invalid values. Check model parameters" |

**Error handling principle**: Fail fast with clear messages. No silent NaN propagation. No fallback to defaults — if data is bad, stop and tell the user.

---

## 7. Non-Functional Requirements

| Requirement | Target | Verification Method |
|-------------|--------|-------------------|
| Historical backtest (4 stocks, 5yr) | < 5 seconds | `time` in test, assert < 5.0 |
| Monte Carlo (200 paths, 4 stocks, 5yr) | < 2 minutes | `time` in test, assert < 120.0 |
| Memory usage | < 500 MB | Monitor via `tracemalloc` in test |
| All verification tests | < 30 seconds | `time` in test suite |

**Performance strategy**: Vectorize with numpy/pandas. Per-symbol operations (returns, trailing vol) vectorize naturally. Portfolio return is a dot product of weight and return vectors per bar. The Monte Carlo loop should vectorize across days within a path. Across paths, a simple Python loop is acceptable for N=200 — vectorizing across paths is an optimization if needed.

---

## 8. Scope Boundary

### In Scope (MVP)

- Multi-symbol portfolio engine with `{symbol: weight}` interface
- Two built-in strategies (EqualWeight, AlwaysLong), single data source (yfinance)
- Multi-symbol data fetch with date alignment (inner join)
- Vectorized engine with shift(1) enforcement and portfolio return computation
- Per-symbol slippage = k * trailing vol, per-symbol flat commission
- Kelly f*, half-Kelly, critical Kelly (closed-form), capital efficiency frontier on portfolio returns
- Multi-symbol GBM simulation (independent per symbol) with method-of-moments calibration
- 8 acceptance criteria as verification tests (AC-1 through AC-7, plus AC-1b for multi-symbol aggregation)
- CLI with `run`, `simulate`, `verify` subcommands
- CLI table + JSON output
- Survivorship warning (non-suppressible)
- Fixed seed for reproducibility

### Deferred to North Star (not L1-L14)

- **Reproducibility metadata** (git hash, dependency versions, CLI invocation): PRD lists this in North Star Output & Reporting. MVP includes seed for simulation but not full reproducibility envelope. This is a polish item, not a correctness item.
- **Correlated simulation**: MVP simulates symbols independently. North Star adds factor model / copula correlation structure.

### Out of Scope (see PRD Acknowledged Limitations L1-L14)

- Multiple data sources, caching, PIT data
- Signal-driven strategies (SMA, momentum, pairs trading, cointegration)
- Portfolio optimization (mean-variance, risk parity, Black-Litterman)
- Bootstrap CI on Kelly, walk-forward, DSR/trial registry
- Regime-switching, GARCH, Heston, Merton models
- Signal half-life, factor attribution, turnover reporting
- Square-root impact model, per-asset-class slippage calibration
- Structural break detection
- Live trading, broker integration

---

## 9. Testing Strategy

### Unit Tests

Each module has its own test file:

| Test File | Tests |
|-----------|-------|
| `test_data.py` | Multi-symbol fetch, validation, date alignment, error cases |
| `test_strategy.py` | EqualWeight/AlwaysLong weights, multi-symbol, edge cases |
| `test_engine.py` | Shift(1) correctness, multi-symbol portfolio returns, warmup |
| `test_execution.py` | Per-symbol slippage, commission, multi-symbol aggregation |
| `test_metrics.py` | Sharpe, Sortino, drawdown formulas |
| `test_kelly.py` | f*, ruin probability, frontier, critical solver |
| `test_simulation.py` | GBM generation, moment matching |
| `test_report.py` | Output formatting, JSON schema |
| `test_nfr.py` | Performance: backtest < 5s, simulation < 120s, memory < 500MB, verification < 30s |

### Integration Tests

| Test | Description |
|------|------------|
| `test_ac1` through `test_ac7` + `test_ac1b` | Acceptance criteria (see Section 5) |
| `test_cli_run` | End-to-end `backtest run` produces valid output for multi-symbol portfolio |
| `test_cli_simulate` | End-to-end `backtest simulate` completes for multi-symbol |
| `test_cli_verify` | All verification tests pass |
| `test_cli_json` | `--json` flag produces valid JSON |

### Test Fixtures

- `AlwaysLongStrategy`: weight={sym: 1/N} for all bars (for AC-1, single-symbol degenerates to 1.0)
- `PerfectForesightStrategy`: test-only Strategy subclass (not in production module).
  Receives full price history including future dates. For each bar t, peeks at
  next-day simple return: if R_{t+1} > 0 → weight={sym: 1.0}, else weight={sym: 0.0}.
  Single-symbol only (symbols list must contain exactly 1). warmup_bars=0.
  The engine's shift(1) delays this signal, so it is NOT actually profitable (for AC-2)
- `make_deterministic_returns(mu, sigma, n)`: generates alternating series with exact moments (for AC-4)
- `make_constant_price_series(price, n)`: constant price (edge case testing)
- `make_synthetic_price_data(symbols, n_days, seed)`: generates multi-symbol PriceData with independent random walks (for multi-symbol engine tests)
- `make_multi_symbol_zero_edge(n_symbols, n_days, sigma, seed)`: generates PriceData for n symbols with mu=0 each (for AC-7)
