import pandas as pd
import pytest

from tests.conftest import make_constant_price_series


def _make_multi_prices(symbols: list[str], n: int) -> dict[str, pd.DataFrame]:
    return {sym: make_constant_price_series(100.0, n) for sym in symbols}


class TestEqualWeight:
    def test_equal_weight_single_symbol(self):
        from stock_backtester.strategy import EqualWeightStrategy

        s = EqualWeightStrategy()
        prices = _make_multi_prices(["A"], 10)
        w = s.compute_weights(prices, ["A"])
        assert (w["A"] == 1.0).all()

    def test_equal_weight_four_symbols(self):
        from stock_backtester.strategy import EqualWeightStrategy

        syms = ["A", "B", "C", "D"]
        s = EqualWeightStrategy()
        prices = _make_multi_prices(syms, 10)
        w = s.compute_weights(prices, syms)
        for sym in syms:
            assert (w[sym] == 0.25).all()


class TestAlwaysLong:
    def test_always_long_identical(self):
        from stock_backtester.strategy import AlwaysLongStrategy, EqualWeightStrategy

        syms = ["A", "B"]
        prices = _make_multi_prices(syms, 10)
        eq = EqualWeightStrategy().compute_weights(prices, syms)
        al = AlwaysLongStrategy().compute_weights(prices, syms)
        pd.testing.assert_frame_equal(eq, al)


class TestFactory:
    def test_factory_equal_weight(self):
        from stock_backtester.strategy import EqualWeightStrategy, get_strategy

        s = get_strategy("equal-weight", {})
        assert isinstance(s, EqualWeightStrategy)

    def test_factory_always_long(self):
        from stock_backtester.strategy import AlwaysLongStrategy, get_strategy

        s = get_strategy("always-long", {})
        assert isinstance(s, AlwaysLongStrategy)

    def test_factory_unknown(self):
        from stock_backtester.strategy import StrategyError, get_strategy

        with pytest.raises(StrategyError, match="Unknown strategy"):
            get_strategy("unknown", {})


class TestWarmup:
    def test_warmup_bars_zero(self):
        from stock_backtester.strategy import AlwaysLongStrategy, EqualWeightStrategy

        assert EqualWeightStrategy().warmup_bars == 0
        assert AlwaysLongStrategy().warmup_bars == 0


class TestWeightSum:
    def test_weight_sum_constraint(self):
        from stock_backtester.strategy import EqualWeightStrategy

        syms = ["A", "B", "C", "D"]
        s = EqualWeightStrategy()
        prices = _make_multi_prices(syms, 10)
        w = s.compute_weights(prices, syms)
        row_sums = w.sum(axis=1)
        assert (row_sums <= 1.0 + 1e-10).all()
