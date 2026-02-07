from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from stock_backtester.strategy import Strategy

if TYPE_CHECKING:
    from stock_backtester.types import PriceData


def make_constant_price_series(price: float, n: int) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 1e6,
        },
        index=dates,
    )


def make_synthetic_price_data(
    symbols: list[str], n_days: int, seed: int
) -> PriceData:
    from stock_backtester.types import PriceData

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    prices_dict: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        log_returns = rng.normal(0.0003, 0.015, n_days)
        close = 100.0 * np.exp(np.cumsum(log_returns))
        df = pd.DataFrame(
            {
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1e6,
            },
            index=dates,
        )
        prices_dict[sym] = df
    return PriceData(
        prices=prices_dict,
        symbols=symbols,
        source="synthetic",
        adjusted=True,
        aligned_dates=dates,
    )


class PerfectForesightStrategy(Strategy):
    def compute_weights(
        self, prices: dict[str, pd.DataFrame], symbols: list[str]
    ) -> pd.DataFrame:
        if len(symbols) != 1:
            raise ValueError("PerfectForesightStrategy supports single-symbol only")
        sym = symbols[0]
        close = prices[sym]["close"]
        simple_ret = close.pct_change()
        # Peek at next-day return: weight=1.0 if positive, else 0.0
        # Last bar: no next-day return -> weight=0.0
        future_ret = simple_ret.shift(-1)
        weights_series = (future_ret > 0).astype(float)
        weights_series.iloc[-1] = 0.0
        return pd.DataFrame({sym: weights_series}, index=close.index)

    @property
    def warmup_bars(self) -> int:
        return 0


def make_deterministic_returns(mu: float, sigma: float, n: int) -> pd.Series:  # type: ignore[type-arg]
    values = []
    for i in range(n):
        if i % 2 == 0:
            values.append(mu + sigma)
        else:
            values.append(mu - sigma)
    return pd.Series(values)


def make_multi_symbol_zero_edge(
    n_symbols: int, n_days: int, sigma: float, seed: int
) -> PriceData:
    from stock_backtester.types import PriceData

    dates = pd.bdate_range("2020-01-01", periods=n_days)
    symbols = [f"SYM{i}" for i in range(n_symbols)]
    prices_dict: dict[str, pd.DataFrame] = {}
    dt = 1.0 / 252.0
    for i, sym in enumerate(symbols):
        sub_rng = np.random.default_rng(seed + i)
        z = sub_rng.standard_normal(n_days)
        log_increments = -0.5 * sigma**2 * dt + sigma * np.sqrt(dt) * z
        close = 100.0 * np.exp(np.cumsum(log_increments))
        df = pd.DataFrame(
            {
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1e6,
            },
            index=dates,
        )
        prices_dict[sym] = df
    return PriceData(
        prices=prices_dict,
        symbols=symbols,
        source="synthetic",
        adjusted=True,
        aligned_dates=dates,
    )
