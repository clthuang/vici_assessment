import numpy as np
import pandas as pd

from stock_backtester.metrics import compute_metrics


class TestSharpe:
    def test_sharpe_known_series(self):
        rets = pd.Series([0.01, -0.005, 0.008, -0.002, 0.003])
        result = compute_metrics(rets, rets, warmup_end_idx=0)
        mean_r = rets.mean()
        std_r = rets.std(ddof=1)
        expected_sharpe = (mean_r * 252) / (std_r * np.sqrt(252))
        np.testing.assert_allclose(result.sharpe, expected_sharpe, atol=0.01)

    def test_sharpe_zero_returns(self):
        rets = pd.Series([0.0, 0.0, 0.0, 0.0, 0.0])
        result = compute_metrics(rets, rets, warmup_end_idx=0)
        assert result.sharpe == 0.0


class TestSortino:
    def test_sortino_all_positive(self):
        rets = pd.Series([0.01, 0.02, 0.005, 0.015, 0.008])
        result = compute_metrics(rets, rets, warmup_end_idx=0)
        assert result.sortino == float("inf")


class TestMaxDrawdown:
    def test_max_drawdown_known(self):
        # Log returns: [0.01, -0.03, -0.02, 0.05]
        rets = pd.Series([0.01, -0.03, -0.02, 0.05])
        gross = rets.copy()
        result = compute_metrics(rets, gross, warmup_end_idx=0)
        # Equity: exp(cumsum) = [exp(0.01), exp(-0.02), exp(-0.04), exp(0.01)]
        # Peak at bar 0: exp(0.01) = 1.01005
        # Trough at bar 2: exp(-0.04) = 0.96079
        # DD = -(1 - 0.96079/1.01005) ≈ -0.04877
        np.testing.assert_allclose(result.max_drawdown, -0.04877, atol=1e-4)
        assert result.max_drawdown < 0  # Must be negative
        # Duration: bars 1, 2 in drawdown (peak at 0, recovery at 3)
        assert result.max_drawdown_duration_days == 2


class TestWinRate:
    def test_win_rate(self):
        rets = pd.Series([0.01, -0.005, 0.008, -0.002, 0.003, 0.0])
        result = compute_metrics(rets, rets, warmup_end_idx=0)
        # 3 positive, 2 negative, 1 zero (excluded)
        np.testing.assert_allclose(result.win_rate, 3 / 5, atol=1e-10)


class TestAnnualized:
    def test_annualized_return(self):
        rets = pd.Series([0.001] * 100)
        result = compute_metrics(rets, rets, warmup_end_idx=0)
        expected = np.exp(0.001 * 252) - 1
        np.testing.assert_allclose(result.annualized_return, expected, atol=1e-4)

    def test_annualized_vol(self):
        rets = pd.Series([0.01, -0.005, 0.008, -0.002, 0.003])
        result = compute_metrics(rets, rets, warmup_end_idx=0)
        expected = rets.std(ddof=1) * np.sqrt(252)
        np.testing.assert_allclose(result.annualized_volatility, expected, atol=1e-10)


class TestCostDrag:
    def test_cost_drag(self):
        net = pd.Series([0.08] * 10)
        gross = pd.Series([0.10] * 10)
        result = compute_metrics(net, gross, warmup_end_idx=0)
        expected_drag = gross.sum() - net.sum()
        np.testing.assert_allclose(result.cost_drag, expected_drag, atol=1e-10)
