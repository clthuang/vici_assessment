import numpy as np
import pandas as pd
import pytest

from tests.conftest import make_deterministic_returns


class TestFullKelly:
    def test_full_kelly_known(self):
        from stock_backtester.kelly import compute_kelly

        mu, sigma = 0.0005, 0.01
        rets = make_deterministic_returns(mu, sigma, 100)
        result = compute_kelly(rets, warmup_end_idx=0)
        expected_fstar = mu / sigma**2  # = 5.0
        np.testing.assert_allclose(result.full_kelly, expected_fstar, atol=1e-6)

    def test_negative_edge(self):
        from stock_backtester.kelly import compute_kelly

        rets = make_deterministic_returns(-0.001, 0.01, 100)
        result = compute_kelly(rets, warmup_end_idx=0)
        assert result.full_kelly < 0
        assert result.critical_kelly is None

    def test_insufficient_data(self):
        from stock_backtester.kelly import KellyError, compute_kelly

        rets = pd.Series([0.001] * 10)
        with pytest.raises(KellyError, match="Insufficient"):
            compute_kelly(rets, warmup_end_idx=0)


class TestRuin:
    def test_ruin_monotonic(self):
        from stock_backtester.kelly import ruin_probability

        f_star = 5.0
        d = 0.5
        prev = 0.0
        for alpha in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75]:
            f = alpha * f_star
            p = ruin_probability(f, f_star, d)
            assert p >= prev
            prev = p

    def test_ruin_at_2fstar(self):
        from stock_backtester.kelly import ruin_probability

        p = ruin_probability(10.0, 5.0, 0.5)  # f = 2*f_star
        assert p == 1.0

    def test_ruin_at_zero(self):
        from stock_backtester.kelly import ruin_probability

        p = ruin_probability(0.0, 5.0, 0.5)
        assert p == 0.0

    def test_ruin_probability_known(self):
        from stock_backtester.kelly import ruin_probability

        # At f = f_star (alpha=1), ruin = D^(2/1 - 1) = D^1 = D = 0.5
        p = ruin_probability(5.0, 5.0, 0.5)
        np.testing.assert_allclose(p, 0.5, atol=1e-10)


class TestFrontier:
    def test_frontier_growth_at_fstar(self):
        from stock_backtester.kelly import growth_rate_fraction

        g = growth_rate_fraction(1.0)  # alpha=1 -> 100%
        np.testing.assert_allclose(g, 1.0, atol=1e-10)

    def test_frontier_growth_at_2fstar(self):
        from stock_backtester.kelly import growth_rate_fraction

        g = growth_rate_fraction(2.0)  # alpha=2 -> 0%
        np.testing.assert_allclose(g, 0.0, atol=1e-10)


class TestCriticalKelly:
    def test_critical_kelly_plugback(self):
        from stock_backtester.kelly import (
            critical_kelly_fraction,
            ruin_probability,
        )

        mu, sigma = 0.0005, 0.01
        f_star = mu / sigma**2
        threshold = 0.01
        d = 0.5
        f_crit = critical_kelly_fraction(mu, sigma, threshold, d)
        assert f_crit is not None
        p = ruin_probability(f_crit, f_star, d)
        np.testing.assert_allclose(p, threshold, atol=1e-4)
