from dataclasses import dataclass
from enum import Enum

import pandas as pd


class OutputFormat(Enum):
    TABLE = "table"
    JSON = "json"


@dataclass(frozen=True)
class BacktestConfig:
    symbols: list[str]
    start_date: str
    end_date: str
    strategy_name: str
    strategy_params: dict[str, float]
    commission_per_share: float
    slippage_k: float
    ruin_threshold: float
    drawdown_level: float
    output_format: OutputFormat


@dataclass(frozen=True)
class SimulationConfig:
    symbols: list[str]
    start_date: str
    end_date: str
    strategy_name: str
    strategy_params: dict[str, float]
    n_paths: int
    seed: int
    commission_per_share: float
    slippage_k: float
    ruin_threshold: float
    drawdown_level: float
    output_format: OutputFormat


@dataclass(frozen=True)
class PriceData:
    prices: dict[str, pd.DataFrame]
    symbols: list[str]
    source: str
    adjusted: bool
    aligned_dates: pd.DatetimeIndex


@dataclass(frozen=True)
class BacktestResult:
    config: BacktestConfig
    gross_returns: pd.Series  # type: ignore[type-arg]
    net_returns: pd.Series  # type: ignore[type-arg]
    weights: pd.DataFrame
    slippage_costs: pd.Series  # type: ignore[type-arg]
    commission_costs: pd.Series  # type: ignore[type-arg]
    equity_curve: pd.Series  # type: ignore[type-arg]
    warmup_end_idx: int


@dataclass(frozen=True)
class KellyResult:
    mu_daily: float
    sigma_daily: float
    full_kelly: float
    half_kelly: float
    critical_kelly: float | None
    frontier: list["FrontierRow"]
    ruin_threshold: float
    drawdown_level: float


@dataclass(frozen=True)
class FrontierRow:
    fraction_label: str
    fraction_of_fstar: float
    growth_pct_of_max: float
    ruin_probability: float


@dataclass(frozen=True)
class MetricsResult:
    sharpe: float
    sortino: float
    max_drawdown: float
    max_drawdown_duration_days: int
    annualized_return: float
    annualized_volatility: float
    win_rate: float
    gross_return_total: float
    net_return_total: float
    cost_drag: float


@dataclass(frozen=True)
class SimulationResult:
    n_paths: int
    seed: int
    per_symbol_calibrations: dict[str, tuple[float, float]]
    empirical_ruin_rate: float
    theoretical_ruin_rate: float
    path_results: list[BacktestResult] | None


@dataclass(frozen=True)
class VerificationResult:
    test_name: str
    passed: bool
    expected: str
    actual: str
    tolerance: str | None
    detail: str
