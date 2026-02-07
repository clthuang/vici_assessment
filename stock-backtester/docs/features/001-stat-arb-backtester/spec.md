# Specification: Statistical Arbitrage Backtesting System

**Feature:** 001-stat-arb-backtester
**PRD Version:** v5
**Spec Version:** v2 (reviewer blockers addressed)

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
 ├── data        → fetch prices
 ├── strategy    → create strategy
 ├── engine      → run backtest
 ├── metrics     → compute metrics from returns
 ├── kelly       → compute Kelly from returns
 ├── simulation  → run Monte Carlo
 └── report      → format output (takes result types, no computation)

engine
 ├── execution   → compute costs
 └── strategy    → call compute_weights (protocol only)

simulation
 ├── data        → calibrate from historical
 └── engine      → reuse backtest logic per path
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
    symbol: str
    start_date: str                    # ISO format YYYY-MM-DD
    end_date: str                      # ISO format YYYY-MM-DD
    strategy_name: str                 # e.g. "sma"
    strategy_params: dict[str, float]  # e.g. {"fast": 20, "slow": 50}
    commission_per_share: float        # default 0.001
    slippage_k: float                  # default 0.5
    ruin_threshold: float              # default 0.01
    drawdown_level: float              # default 0.50
    output_format: OutputFormat        # default TABLE


@dataclass(frozen=True)
class SimulationConfig:
    """Immutable configuration for Monte Carlo simulation."""
    symbol: str
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
    """Validated OHLCV data. Immutable after construction."""
    df: pd.DataFrame  # columns: date(index), open, high, low, close, volume
    symbol: str
    source: str       # "yfinance"
    adjusted: bool    # True = split+dividend adjusted close


@dataclass(frozen=True)
class BacktestResult:
    """Complete result of a single backtest run."""
    config: BacktestConfig
    gross_returns: pd.Series       # daily gross returns (post-shift, pre-cost)
    net_returns: pd.Series         # daily net returns (post-cost)
    positions: pd.Series           # daily position weights (after shift)
    slippage_costs: pd.Series      # daily slippage cost
    commission_costs: pd.Series    # daily commission cost
    equity_curve: pd.Series        # cumulative portfolio value
    warmup_end_idx: int            # index of first active trading bar


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
    mu_calibrated: float           # annualized
    sigma_calibrated: float        # annualized
    empirical_ruin_rate: float     # at half-Kelly
    theoretical_ruin_rate: float   # from formula
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

**Responsibility**: Fetch and validate OHLCV price data.

```python
def fetch_prices(symbol: str, start_date: str, end_date: str) -> PriceData:
    """
    Fetch daily OHLCV data from yfinance.

    Uses yf.download(symbol, start, end, auto_adjust=True).
    With auto_adjust=True (the yfinance default), ALL OHLCV columns
    are split- and dividend-adjusted. There is NO separate 'Adj Close'
    column — the 'Close' column IS the adjusted close.

    Default date range: if start is None, defaults to 5 years before end.
    If end is None, defaults to today. If both None, (today - 5yr, today).

    Args:
        symbol: US stock ticker (e.g., "AAPL")
        start_date: ISO date string "YYYY-MM-DD" or None
        end_date: ISO date string "YYYY-MM-DD" or None

    Returns:
        PriceData with validated DataFrame

    Raises:
        DataError("No data for ticker {symbol}. Check symbol and date range")
            if yfinance returns empty DataFrame
        DataError("No trading days in range")
            if date range contains zero trading days
        DataError("Invalid prices: NaN detected at {dates}")
            if any close prices are NaN after fetch
        DataError("Invalid prices: non-positive values at {dates}")
            if any close prices are <= 0
        DataError("Insufficient data for reliable estimation. Need at least 30 trading days")
            if fewer than 30 bars returned

    Contract:
        - DataFrame index is DatetimeIndex, sorted ascending
        - Columns: open, high, low, close, volume (all float64)
        - ALL OHLCV columns are adjusted (auto_adjust=True)
        - No NaN values in close column
        - All close values > 0
        - source = "yfinance", adjusted = True

    Note: validate_prices checks total data length (>= 30 bars).
    The Kelly analyzer has a separate check for post-warmup bars
    (>= 30 active trading bars), which may require more total data
    depending on strategy warmup period.
    """


def validate_prices(df: pd.DataFrame) -> None:
    """
    Validate price DataFrame. Raises DataError on failure.

    Checks:
        1. No NaN in close column
        2. All close > 0
        3. At least 30 bars (minimum for reliable estimation)
    """


class DataError(Exception):
    """Raised for data fetching or validation failures."""
    pass
```

### 3.2 Strategy Layer (`strategy.py`)

**Responsibility**: Compute target weights from price data. Strategies are stateless functions of price history.

```python
from abc import ABC, abstractmethod


class Strategy(ABC):
    """
    Base class for all strategies.

    Contract:
        - compute_weights() receives a COPY of price data (not a view)
        - Returns Series of target weights indexed by date
        - Weights are intentions: 1.0 = fully long, 0.0 = flat
        - NaN weights are forbidden — raise StrategyError
        - Strategy must NOT apply shift — the engine handles temporal alignment
    """

    @abstractmethod
    def compute_weights(self, prices: pd.DataFrame) -> pd.Series:
        """
        Compute target position weights for each date.

        Args:
            prices: DataFrame with columns [open, high, low, close, volume]
                    This is a COPY — mutations do not affect the original.

        Returns:
            Series indexed by date with float weights.
            NaN values in the warmup period are acceptable —
            the engine will identify and skip them.

        Raises:
            StrategyError if computation fails
        """

    @property
    @abstractmethod
    def warmup_bars(self) -> int:
        """Number of initial bars needed before first valid signal."""


class SMAStrategy(Strategy):
    """
    Simple Moving Average crossover strategy.

    Signal: fast_MA > slow_MA → long (weight=1.0), else flat (weight=0.0)

    Parameters:
        fast_period: int (default 20)
        slow_period: int (default 50)

    warmup_bars = slow_period (need slow_period bars for slow MA)
    """

    def __init__(self, fast_period: int = 20, slow_period: int = 50) -> None:
        """
        Raises:
            ValueError if fast_period >= slow_period
            ValueError if either period < 2
        """

    def compute_weights(self, prices: pd.DataFrame) -> pd.Series:
        """
        Returns:
            Series with NaN for first slow_period-1 bars (warmup),
            then 1.0 (long) or 0.0 (flat) for remaining bars.

        Implementation:
            fast_ma = prices["close"].rolling(fast_period).mean()
            slow_ma = prices["close"].rolling(slow_period).mean()
            signal = (fast_ma > slow_ma).astype(float)
            # First slow_period-1 values are NaN from rolling
        """

    @property
    def warmup_bars(self) -> int:
        """
        warmup_bars = slow_period means the strategy needs slow_period bars
        before producing a valid signal. The first valid (non-NaN) weight
        is at bar index slow_period-1. After engine shift(1), the first
        executed position is at bar index slow_period. Therefore,
        warmup_end_idx in BacktestResult = slow_period.
        """
        return self.slow_period


def get_strategy(name: str, params: dict[str, float]) -> Strategy:
    """
    Factory function. Returns strategy instance.

    Args:
        name: "sma" (only option in MVP)
        params: {"fast": 20, "slow": 50} (defaults if missing)

    Raises:
        StrategyError(f"Unknown strategy: {name}")
    """


class StrategyError(Exception):
    pass
```

### 3.3 Backtesting Engine (`engine.py`)

**Responsibility**: Orchestrate the backtest pipeline. Enforces shift(1) as the single temporal alignment point.

```python
def run_backtest(
    prices: PriceData,
    strategy: Strategy,
    slippage_k: float = 0.5,
    commission_per_share: float = 0.001,
) -> BacktestResult:
    """
    Run a vectorized backtest with enforced look-ahead prevention.

    Pipeline:
        1. Pass prices.df.copy() to strategy.compute_weights()
        2. Apply shift(1) to raw weights → executed weights
        3. Compute daily log-returns: r_t = ln(P_t / P_{t-1})
        4. Compute gross returns: gross_t = position_t * r_t
        5. Compute slippage and commission costs via execution model
           (all costs in fractional units, same as log-returns)
        6. Compute net returns: net_t = gross_t - slippage_t - commission_t
        7. Build equity curve: equity = exp(cumsum(net_returns)), normalized to 1.0
           Since net_returns are log-returns, exp(cumsum) correctly compounds.

    Shift(1) contract:
        - Raw weights from strategy represent "what I want to hold tomorrow"
        - shift(1) makes them "what I hold today based on yesterday's signal"
        - This is applied ONCE, HERE, in the engine — nowhere else
        - The first bar after shift has NaN weight → treated as 0 (flat)

    Warmup handling:
        - Identify warmup_end_idx: first bar where shifted weight is not NaN
        - All bars before warmup_end_idx have position = 0, return = 0
        - The transition from 0 to first target weight IS a trade
          (incurs slippage and commission)

    Args:
        prices: Validated PriceData
        strategy: Strategy instance
        slippage_k: multiplier for volatility-based slippage
        commission_per_share: flat per-share commission

    Returns:
        BacktestResult with all return series and metadata

    Invariants:
        - len(gross_returns) == len(net_returns) == len(prices.df)
        - net_returns[i] <= gross_returns[i] for all i where trading occurs
        - positions are always the SHIFTED weights (no look-ahead)
    """
```

### 3.4 Execution Model (`execution.py`)

**Responsibility**: Apply transaction costs to weight changes.

```python
def compute_costs(
    prices: pd.DataFrame,
    positions: pd.Series,
    slippage_k: float,
    commission_per_share: float,
) -> tuple[pd.Series, pd.Series]:
    """
    Compute slippage and commission costs for each bar.

    All costs are expressed as FRACTIONAL costs (dimensionless, same
    units as log-returns) so they can be directly subtracted from
    gross returns: net_return_t = gross_return_t - slippage_t - commission_t.

    Slippage model:
        slippage_t = k * sigma_trailing(20) * |delta_w_t|

        where:
            k = slippage multiplier (default 0.5, dimensionless)
            sigma_trailing(20) = std of most recent 20 daily log-returns
                                 (dimensionless fraction, NOT annualized)
            delta_w_t = w_t - w_{t-1} (weight change, dimensionless)

        Result: dimensionless fraction of portfolio value.

    Trailing volatility edge cases:
        - If fewer than 20 bars available, use all available bars (min 2)
        - If trailing vol is 0 (halted stock, constant price), slippage = 0
          (acceptable for MVP; no artificial floor needed since k*0 = 0
           and constant-price stocks have no return to distort)

    Commission model:
        commission_t = commission_rate * |delta_w_t|

        where commission_rate = commission_per_share / close_price_t.
        This converts the per-share cost into a fractional cost.

        Dimensional analysis:
            commission_per_share: $/share
            close_price_t: $/share
            commission_rate = ($/share) / ($/share) = dimensionless
            commission_t = dimensionless * dimensionless = dimensionless ✓

        Example: commission=$0.001/share, close=$150 → rate=0.00067%
        With |delta_w|=1.0 (full position change): cost = 0.00067%

    Args:
        prices: DataFrame with 'close' column
        positions: Series of position weights (already shifted)
        slippage_k: multiplier (default 0.5)
        commission_per_share: per-share cost (default 0.001)

    Returns:
        (slippage_costs, commission_costs) — both non-negative Series,
        in fractional units (same as log-returns)

    Invariants:
        - slippage_costs >= 0 for all bars
        - commission_costs >= 0 for all bars
        - costs are 0 when position does not change
    """


def compute_log_returns(prices: pd.DataFrame) -> pd.Series:
    """
    Compute daily log-returns: r_t = ln(P_t / P_{t-1}).

    Returns Series with first value = NaN (no prior price).
    """


def compute_trailing_volatility(
    log_returns: pd.Series, window: int = 20
) -> pd.Series:
    """
    Rolling standard deviation of log-returns.

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

    Metric definitions:

    Sharpe:
        annualized_return / annualized_volatility
        where annualized_return = mean(net_daily) * 252
              annualized_volatility = std(net_daily) * sqrt(252)

    Sortino:
        annualized_return / annualized_downside_deviation
        where downside_deviation = sqrt((1/N) * sum(min(r_t, 0)^2))
              MAR = 0
              N = total bar count (all returns, not just negative)
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

**Responsibility**: GBM path generation, moment-matching calibration, Monte Carlo backtest loop.

```python
def calibrate_gbm(prices: PriceData) -> tuple[float, float]:
    """
    Method-of-moments calibration from historical data.

    Compute daily log-returns: r_t = ln(P_t / P_{t-1})
    mu_daily = mean(r_t)
    sigma_daily = std(r_t)

    Annualize:
        mu_annual = mu_daily * 252
        sigma_annual = sigma_daily * sqrt(252)

    Returns:
        (mu_annual, sigma_annual)
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
    Generate GBM price paths.

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


def run_monte_carlo(
    prices: PriceData,
    strategy: Strategy,
    config: SimulationConfig,
) -> SimulationResult:
    """
    Monte Carlo backtest loop.

    Pipeline:
        1. Calibrate GBM from historical prices
        2. Generate n_paths synthetic price paths
        3. For each path:
           a. Convert ndarray to PriceData-compatible DataFrame
           b. Synthetic DataFrames: close=simulated price, open=high=low=close,
              volume=1e6 (constant placeholder), dates=pd.bdate_range(n_days)
           c. Run backtest with same strategy and cost parameters
           c. Check if equity curve hits drawdown_level at half-Kelly sizing
        4. Compute empirical ruin rate = count(ruin) / n_paths
        5. Compute theoretical ruin rate from formula at half-Kelly

    Ruin detection for each path:
        Scale net returns by (half_kelly / 1.0) to simulate leveraged returns.
        Check if equity curve ever drops below (1 - drawdown_level) * peak.

        NOTE: This is an approximation. Ruin detection scales returns
        linearly but does not re-run the backtest at the leveraged
        position size. Transaction costs at higher leverage would be
        proportionally higher, making this an optimistic estimate of
        empirical ruin rate. Accepted for MVP; the North Star
        cost-leverage interaction model addresses this.

    Returns:
        SimulationResult with empirical and theoretical ruin rates
    """


def run_verification_tests(seed: int = 42) -> list[VerificationResult]:
    """
    Run all known-answer verification tests.

    AC-1: Deterministic 1% daily rise, always-long, zero cost
        Expected total return: (1.01^10 - 1) = 10.4622...%

    AC-2: Perfect foresight strategy with shift(1)
        Verify return < sum of all positive daily returns

    AC-3: Slippage invariant (net < gross)

    AC-4: Deterministic return series with mu=0.0005, sigma=0.01
        Expected f* = 0.0005/0.01^2 = 5.0

    AC-5: Frontier consistency (monotonic ruin, g(2f*)=0)

    AC-6: GBM moment matching
        mu=0.10/yr, sigma=0.20/yr, 200 paths, 252 days
        Check: mean log-return within 2 SE of (mu-sigma^2/2)*T
        Check: std of log-returns within 2 SE of sigma*sqrt(T)

    AC-7: Zero-edge GBM (mu=0, sigma=0.20)
        Check: Sharpe within 2 SE of zero

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
    strategy: str = typer.Option("sma", help="Strategy name"),
    symbol: str = typer.Option(..., help="US stock ticker"),
    start: str = typer.Option(None, help="Start date YYYY-MM-DD"),
    end: str = typer.Option(None, help="End date YYYY-MM-DD"),
    fast: int = typer.Option(20, help="SMA fast period"),
    slow: int = typer.Option(50, help="SMA slow period"),
    commission: float = typer.Option(0.001, help="Per-share commission"),
    slippage_k: float = typer.Option(0.5, help="Slippage multiplier"),
    ruin_threshold: float = typer.Option(0.01, help="Max ruin probability"),
    drawdown_level: float = typer.Option(0.50, help="Drawdown threshold"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Run SMA backtest on historical data with Kelly analysis."""
    # 1. Build config
    # 2. Fetch prices via data.fetch_prices()
    # 3. Create strategy via strategy.get_strategy()
    # 4. Run backtest via engine.run_backtest()
    # 5. Compute metrics via metrics.compute_metrics()
    # 6. Compute Kelly via kelly.compute_kelly()
    # 7. Format and print report via report.format_backtest_report()


@app.command()
def simulate(
    strategy: str = typer.Option("sma"),
    symbol: str = typer.Option(...),
    start: str = typer.Option(None),
    end: str = typer.Option(None),
    fast: int = typer.Option(20),
    slow: int = typer.Option(50),
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
    """Run known-answer tests to verify engine correctness."""
```

---

## 4. Data Contracts

### 4.1 DataFrame Schema

| Column | dtype | Constraint | Source |
|--------|-------|-----------|--------|
| `date` | DatetimeIndex | sorted ascending, no duplicates | yfinance |
| `open` | float64 | > 0 | yfinance (adjusted via auto_adjust=True) |
| `high` | float64 | >= open, >= close | yfinance (adjusted via auto_adjust=True) |
| `low` | float64 | <= open, <= close | yfinance (adjusted via auto_adjust=True) |
| `close` | float64 | > 0, no NaN | yfinance (adjusted via auto_adjust=True) |
| `volume` | float64 | >= 0 | yfinance |

**Note**: With `auto_adjust=True`, all OHLC columns are split- and dividend-adjusted. There is no separate 'Adj Close' column. MVP uses only the `close` column for signal generation and return computation. Open/High/Low are passed through for completeness but not used by the SMA strategy.

### 4.2 Immutability Contract

- `PriceData.df` is passed to strategies as `.copy()` — strategies cannot mutate engine data
- All `@dataclass(frozen=True)` types are immutable after construction
- `BacktestConfig` and `SimulationConfig` are frozen — no mid-run parameter changes

### 4.3 Return Convention

- **Log-returns** throughout: `r_t = ln(P_t / P_{t-1})`
- **Daily scale** for internal computation
- **Annualized** for reporting: `* 252` for mean, `* sqrt(252)` for std
- **Net returns** for Kelly estimation (post slippage and commission)

---

## 5. Acceptance Criteria — Detailed Test Specifications

### AC-1: Historical backtest produces correct returns

```python
def test_ac1_correct_returns():
    """
    Construct: 11-day price series starting at 100, rising 1%/day
        prices = [100, 101, 102.01, ..., 110.462...]

    Strategy: AlwaysLongStrategy — returns weight=1.0 for all bars
        (no warmup, NaN only for first bar from shift)

    Config: slippage_k=0, commission=0

    Assert:
        total_return = equity_curve[-1] / equity_curve[warmup_end_idx] - 1
        abs(total_return - (1.01**10 - 1)) < 1e-10

    Note: 11 prices → 10 daily returns → 10 days of trading.
    AlwaysLongStrategy has warmup_bars=0. After shift(1), bar 0's
    position is NaN (treated as 0), so first executed position is bar 1.
    Equity curve starts at bar 1 (warmup_end_idx=1).
    """
```

### AC-2: Look-ahead prevention verified

```python
def test_ac2_look_ahead_prevention():
    """
    Construct: random price series with known up/down days (seeded)

    Strategy: PerfectForesightStrategy
        - Knows future returns (implemented as: returns[t] > 0 → w=1, else w=0)
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

### AC-7: Known-answer verification (zero-edge)

```python
def test_ac7_zero_edge():
    """
    Config: mu=0, sigma=0.20/yr, n_paths=200, n_days=252, seed=42

    Run SMA strategy on each generated path.
    For each path, compute annualized Sharpe from the path's daily net returns.
    Compute mean_sharpe = mean of all path-level Sharpes.
    Compute SE_sharpe = std(path_sharpes) / sqrt(n_paths).

    Expected: mean_sharpe ≈ 0 (no edge → no risk-adjusted return)

    Assert: abs(mean_sharpe) < 2 * SE_sharpe

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
| Historical backtest (1 stock, 5yr) | < 2 seconds | `time` in test, assert < 2.0 |
| Monte Carlo (200 paths, 5yr) | < 1 minute | `time` in test, assert < 60.0 |
| Memory usage | < 500 MB | Monitor via `tracemalloc` in test |
| All verification tests | < 30 seconds | `time` in test suite |

**Performance strategy**: Vectorize with numpy/pandas. The Monte Carlo loop should vectorize across days within a path. Across paths, a simple Python loop is acceptable for N=200 — vectorizing across paths (3D array) is an optimization if needed.

---

## 8. Scope Boundary

### In Scope (MVP)

- Single symbol, single strategy (SMA), single data source (yfinance)
- Vectorized engine with shift(1) enforcement
- Slippage = k * trailing vol, flat commission
- Kelly f*, half-Kelly, critical Kelly (closed-form), capital efficiency frontier
- GBM simulation with method-of-moments calibration
- 7 acceptance criteria as verification tests
- CLI with `run`, `simulate`, `verify` subcommands
- CLI table + JSON output
- Survivorship warning (non-suppressible)
- Fixed seed for reproducibility

### Deferred to North Star (not L1-L14)

- **Reproducibility metadata** (git hash, dependency versions, CLI invocation): PRD lists this in North Star Output & Reporting. MVP includes seed for simulation but not full reproducibility envelope. This is a polish item, not a correctness item.

### Out of Scope (see PRD Acknowledged Limitations L1-L14)

- Multiple data sources, caching, PIT data
- Pairs trading, multi-asset, portfolio optimization
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
| `test_data.py` | Fetch + validation, error cases |
| `test_strategy.py` | SMA weights, warmup, edge cases |
| `test_engine.py` | Shift(1) correctness, warmup handling |
| `test_execution.py` | Slippage calculation, commission, edge cases |
| `test_metrics.py` | Sharpe, Sortino, drawdown formulas |
| `test_kelly.py` | f*, ruin probability, frontier, critical solver |
| `test_simulation.py` | GBM generation, moment matching |
| `test_report.py` | Output formatting, JSON schema |
| `test_nfr.py` | Performance: backtest < 2s, simulation < 60s, memory < 500MB, verification < 30s |

### Integration Tests

| Test | Description |
|------|------------|
| `test_ac1` through `test_ac7` | Acceptance criteria (see Section 5) |
| `test_cli_run` | End-to-end `backtest run` produces valid output |
| `test_cli_simulate` | End-to-end `backtest simulate` completes |
| `test_cli_verify` | All verification tests pass |
| `test_cli_json` | `--json` flag produces valid JSON |

### Test Fixtures

- `AlwaysLongStrategy`: weight=1.0 for all bars (for AC-1)
- `PerfectForesightStrategy`: uses future returns as signal (for AC-2)
- `make_deterministic_returns(mu, sigma, n)`: generates alternating series with exact moments (for AC-4)
- `make_constant_price_series(price, n)`: constant price (edge case testing)
