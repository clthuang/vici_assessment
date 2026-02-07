import numpy as np

from stock_backtester.strategy import EqualWeightStrategy
from stock_backtester.types import BacktestConfig, OutputFormat
from tests.conftest import make_synthetic_price_data


def _make_config(symbols: list[str], **kwargs) -> BacktestConfig:
    defaults = dict(
        symbols=symbols,
        start_date="2020-01-01",
        end_date="2025-01-01",
        strategy_name="equal-weight",
        strategy_params={},
        commission_per_share=0.001,
        slippage_k=0.5,
        ruin_threshold=0.01,
        drawdown_level=0.50,
        output_format=OutputFormat.TABLE,
    )
    defaults.update(kwargs)
    return BacktestConfig(**defaults)


class TestEngineBasics:
    def test_shift_applied(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A", "B"], 50, seed=42)
        config = _make_config(["A", "B"])
        strategy = EqualWeightStrategy()
        result = run_backtest(config, prices, strategy)
        # First row of shifted weights should be all 0
        assert (result.weights.iloc[0] == 0.0).all()

    def test_series_lengths(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A"], 50, seed=42)
        config = _make_config(["A"])
        result = run_backtest(config, prices, EqualWeightStrategy())
        n = len(prices.aligned_dates)
        assert len(result.gross_returns) == n
        assert len(result.net_returns) == n

    def test_net_leq_gross(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A", "B"], 50, seed=42)
        config = _make_config(["A", "B"])
        result = run_backtest(config, prices, EqualWeightStrategy())
        # Where trading occurs (bar 1+), net <= gross
        for i in range(result.warmup_end_idx, len(result.net_returns)):
            assert result.net_returns.iloc[i] <= result.gross_returns.iloc[i] + 1e-15

    def test_warmup_end_idx_equal_weight(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A"], 50, seed=42)
        config = _make_config(["A"])
        result = run_backtest(config, prices, EqualWeightStrategy())
        # EqualWeight warmup_bars=0, shift(1) makes bar 0 NaN -> warmup_end_idx = 1
        assert result.warmup_end_idx == 1

    def test_equity_starts_at_one(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A"], 50, seed=42)
        config = _make_config(["A"])
        result = run_backtest(config, prices, EqualWeightStrategy())
        np.testing.assert_allclose(
            result.equity_curve.iloc[result.warmup_end_idx], 1.0, atol=1e-10
        )

    def test_cost_approximation_bound(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A", "B", "C"], 50, seed=42)
        config = _make_config(["A", "B", "C"])
        result = run_backtest(config, prices, EqualWeightStrategy())
        # First-trade cost should be < 0.01 (< 1% per bar)
        idx = result.warmup_end_idx
        cost = result.slippage_costs.iloc[idx] + result.commission_costs.iloc[idx]
        assert cost < 0.01
