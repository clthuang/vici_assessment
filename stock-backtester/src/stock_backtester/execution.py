import numpy as np
import pandas as pd

from stock_backtester.types import PriceData


def compute_simple_returns(prices_df: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    return prices_df["close"].pct_change()


def compute_log_returns(prices_df: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    close = prices_df["close"]
    return np.log(close / close.shift(1))


def compute_multi_symbol_simple_returns(prices: PriceData) -> pd.DataFrame:
    result: dict[str, pd.Series] = {}  # type: ignore[type-arg]
    for sym in prices.symbols:
        result[sym] = compute_simple_returns(prices.prices[sym])
    return pd.DataFrame(result, index=prices.aligned_dates)


def compute_multi_symbol_log_returns(prices: PriceData) -> pd.DataFrame:
    result: dict[str, pd.Series] = {}  # type: ignore[type-arg]
    for sym in prices.symbols:
        result[sym] = compute_log_returns(prices.prices[sym])
    return pd.DataFrame(result, index=prices.aligned_dates)


def compute_trailing_volatility(
    log_returns: pd.Series,
    window: int = 20,  # type: ignore[type-arg]
) -> pd.Series:  # type: ignore[type-arg]
    rolling = log_returns.rolling(window=window, min_periods=2).std(ddof=1)
    expanding = log_returns.expanding(min_periods=2).std(ddof=1)
    result = rolling.where(rolling.notna(), expanding)
    return result.fillna(0.0)


def compute_costs(
    prices: PriceData,
    weights: pd.DataFrame,
    slippage_k: float,
    commission_per_share: float,
) -> tuple[pd.Series, pd.Series]:  # type: ignore[type-arg]
    dates = prices.aligned_dates
    total_slippage = pd.Series(0.0, index=dates)
    total_commission = pd.Series(0.0, index=dates)

    delta_w = weights.diff().fillna(weights)

    for sym in prices.symbols:
        sym_df = prices.prices[sym]
        log_ret = compute_log_returns(sym_df)
        trailing_vol = compute_trailing_volatility(log_ret)

        abs_delta = delta_w[sym].abs()
        sym_slippage = slippage_k * trailing_vol * abs_delta
        total_slippage = total_slippage + sym_slippage.fillna(0.0)

        commission_rate = commission_per_share / sym_df["close"]
        sym_commission = commission_rate * abs_delta
        total_commission = total_commission + sym_commission.fillna(0.0)

    return total_slippage, total_commission
