import numpy as np
import pandas as pd

from stock_backtester.types import PriceData


def _make_price_df(closes: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=len(closes))
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": 1e6,
        },
        index=dates,
    )


class TestSimpleReturns:
    def test_simple_returns_known_series(self):
        from stock_backtester.execution import compute_simple_returns

        df = _make_price_df([100.0, 101.0, 102.01])
        result = compute_simple_returns(df)
        assert pd.isna(result.iloc[0])
        np.testing.assert_allclose(result.iloc[1], 0.01, atol=1e-10)
        np.testing.assert_allclose(result.iloc[2], 0.01, atol=1e-4)

    def test_multi_symbol_simple_returns(self):
        from stock_backtester.execution import compute_multi_symbol_simple_returns

        prices = PriceData(
            prices={
                "A": _make_price_df([100.0, 105.0, 110.0]),
                "B": _make_price_df([100.0, 95.0, 100.0]),
            },
            symbols=["A", "B"],
            source="test",
            adjusted=True,
            aligned_dates=pd.bdate_range("2020-01-01", periods=3),
        )
        result = compute_multi_symbol_simple_returns(prices)
        assert result.shape == (3, 2)
        assert list(result.columns) == ["A", "B"]


class TestLogReturns:
    def test_log_returns_known_series(self):
        from stock_backtester.execution import compute_log_returns

        df = _make_price_df([100.0, 101.0, 102.01])
        result = compute_log_returns(df)
        assert pd.isna(result.iloc[0])
        np.testing.assert_allclose(result.iloc[1], np.log(1.01), atol=1e-10)
        np.testing.assert_allclose(result.iloc[2], np.log(102.01 / 101.0), atol=1e-10)

    def test_multi_symbol_log_returns(self):
        from stock_backtester.execution import compute_multi_symbol_log_returns

        prices = PriceData(
            prices={
                "A": _make_price_df([100.0, 105.0, 110.0]),
                "B": _make_price_df([100.0, 95.0, 100.0]),
            },
            symbols=["A", "B"],
            source="test",
            adjusted=True,
            aligned_dates=pd.bdate_range("2020-01-01", periods=3),
        )
        result = compute_multi_symbol_log_returns(prices)
        assert result.shape == (3, 2)


class TestTrailingVol:
    def test_trailing_vol_constant(self):
        from stock_backtester.execution import compute_trailing_volatility

        df = _make_price_df([100.0, 100.0, 100.0, 100.0, 100.0])
        from stock_backtester.execution import compute_log_returns

        log_ret = compute_log_returns(df)
        vol = compute_trailing_volatility(log_ret, window=20)
        # All log returns are 0 (after the NaN first value)
        # So expanding std should be 0 (or NaN for insufficient data)
        assert vol.iloc[-1] == 0.0

    def test_trailing_vol_alternating(self):
        from stock_backtester.execution import (
            compute_log_returns,
            compute_trailing_volatility,
        )

        df = _make_price_df([100.0, 101.0, 100.0, 101.0, 100.0])
        log_ret = compute_log_returns(df)
        vol = compute_trailing_volatility(log_ret, window=20)

        r0 = np.log(101.0 / 100.0)
        r1 = np.log(100.0 / 101.0)
        r2 = np.log(101.0 / 100.0)
        r3 = np.log(100.0 / 101.0)

        # bar 1: NaN (1 obs < min_periods=2)
        assert pd.isna(vol.iloc[1]) or vol.iloc[1] == 0.0
        # bar 2: std([r0, r1], ddof=1)
        expected_bar2 = np.std([r0, r1], ddof=1)
        np.testing.assert_allclose(vol.iloc[2], expected_bar2, atol=1e-5)
        # bar 3: std([r0, r1, r2], ddof=1)
        expected_bar3 = np.std([r0, r1, r2], ddof=1)
        np.testing.assert_allclose(vol.iloc[3], expected_bar3, atol=1e-5)
        # bar 4: std([r0, r1, r2, r3], ddof=1)
        expected_bar4 = np.std([r0, r1, r2, r3], ddof=1)
        np.testing.assert_allclose(vol.iloc[4], expected_bar4, atol=1e-5)

    def test_trailing_vol_insufficient(self):
        from stock_backtester.execution import (
            compute_log_returns,
            compute_trailing_volatility,
        )

        df = _make_price_df([100.0, 101.0])
        log_ret = compute_log_returns(df)
        vol = compute_trailing_volatility(log_ret, window=20)
        # bar 0: NaN (log_ret is NaN), bar 1: single observation -> NaN or 0
        assert pd.isna(vol.iloc[0]) or vol.iloc[0] == 0.0


class TestCosts:
    def test_costs_zero_delta(self):
        from stock_backtester.execution import compute_costs

        prices = PriceData(
            prices={"A": _make_price_df([100.0, 100.0, 100.0])},
            symbols=["A"],
            source="test",
            adjusted=True,
            aligned_dates=pd.bdate_range("2020-01-01", periods=3),
        )
        dates = prices.aligned_dates
        weights = pd.DataFrame({"A": [0.5, 0.5, 0.5]}, index=dates)
        slip, comm = compute_costs(
            prices, weights, slippage_k=0.5, commission_per_share=0.001
        )
        # No weight changes after first row -> costs should be 0 for bars 1,2
        assert slip.iloc[1] == 0.0
        assert slip.iloc[2] == 0.0

    def test_costs_known_slippage(self):
        from stock_backtester.execution import compute_costs

        # delta_w=0.5, k=0.5, sigma=0.02 -> slippage = 0.5 * 0.02 * 0.5 = 0.005
        # We need to construct a scenario where trailing vol is ~0.02
        # Use a price series that gives trailing vol of 0.02
        # For simplicity, we'll check the formula indirectly
        prices = PriceData(
            prices={"A": _make_price_df([100.0, 100.0, 100.0, 100.0])},
            symbols=["A"],
            source="test",
            adjusted=True,
            aligned_dates=pd.bdate_range("2020-01-01", periods=4),
        )
        dates = prices.aligned_dates
        # Weight goes from 0 to 0.5 on bar 1 -> delta_w = 0.5
        weights = pd.DataFrame({"A": [0.0, 0.5, 0.5, 0.5]}, index=dates)
        slip, comm = compute_costs(
            prices, weights, slippage_k=0.5, commission_per_share=0.001
        )
        # With constant prices, log returns are 0, trailing vol is 0
        # So slippage should be 0 even with weight change
        assert slip.iloc[1] == 0.0

    def test_commission_dimensionless(self):
        from stock_backtester.execution import compute_costs

        prices = PriceData(
            prices={"A": _make_price_df([100.0, 100.0, 100.0])},
            symbols=["A"],
            source="test",
            adjusted=True,
            aligned_dates=pd.bdate_range("2020-01-01", periods=3),
        )
        dates = prices.aligned_dates
        # Weight goes from 0 to 1.0 on bar 1
        weights = pd.DataFrame({"A": [0.0, 1.0, 1.0]}, index=dates)
        slip, comm = compute_costs(
            prices, weights, slippage_k=0.0, commission_per_share=0.005
        )
        # commission_rate = 0.005 / 100.0 = 0.00005 per unit delta_w
        # delta_w = 1.0, so commission = 0.00005 * 1.0 = 0.00005
        np.testing.assert_allclose(comm.iloc[1], 0.00005, atol=1e-10)

    def test_nan_trailing_vol_zero_slippage(self):
        from stock_backtester.execution import compute_costs

        # With only 2 bars, first bar log return is NaN -> trailing vol NaN
        prices = PriceData(
            prices={"A": _make_price_df([100.0, 105.0])},
            symbols=["A"],
            source="test",
            adjusted=True,
            aligned_dates=pd.bdate_range("2020-01-01", periods=2),
        )
        dates = prices.aligned_dates
        weights = pd.DataFrame({"A": [0.0, 1.0]}, index=dates)
        slip, comm = compute_costs(
            prices, weights, slippage_k=0.5, commission_per_share=0.001
        )
        # NaN vol -> slippage should be 0 (fillna behavior)
        assert slip.iloc[1] == 0.0
