from abc import ABC, abstractmethod

import pandas as pd


class StrategyError(Exception):
    pass


class Strategy(ABC):
    @abstractmethod
    def compute_weights(
        self, prices: dict[str, pd.DataFrame], symbols: list[str]
    ) -> pd.DataFrame: ...

    @property
    @abstractmethod
    def warmup_bars(self) -> int: ...


class EqualWeightStrategy(Strategy):
    def compute_weights(
        self, prices: dict[str, pd.DataFrame], symbols: list[str]
    ) -> pd.DataFrame:
        n = len(symbols)
        dates = next(iter(prices.values())).index
        return pd.DataFrame(1.0 / n, index=dates, columns=symbols)

    @property
    def warmup_bars(self) -> int:
        return 0


class AlwaysLongStrategy(EqualWeightStrategy):
    """Always-long strategy: equal-weight allocation across all symbols."""

    pass


def get_strategy(name: str, params: dict[str, float]) -> Strategy:
    if name == "equal-weight":
        return EqualWeightStrategy()
    elif name == "always-long":
        return AlwaysLongStrategy()
    else:
        raise StrategyError(f"Unknown strategy: {name}")
