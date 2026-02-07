import numpy as np
import pandas as pd

from stock_backtester.strategy import AlwaysLongStrategy, EqualWeightStrategy
from stock_backtester.types import BacktestConfig, OutputFormat, PriceData
from tests.conftest import PerfectForesightStrategy, make_synthetic_price_data


def _make_config(symbols: list[str], **kwargs) -> BacktestConfig:
    defaults = dict(
        symbols=symbols,
        start_date="2020-01-01",
        end_date="2025-01-01",
        strategy_name="equal-weight",
        strategy_params={},
        commission_per_share=0.0,
        slippage_k=0.0,
        ruin_threshold=0.01,
        drawdown_level=0.50,
        output_format=OutputFormat.TABLE,
    )
    defaults.update(kwargs)
    return BacktestConfig(**defaults)


def _make_price_data(prices_dict: dict[str, pd.DataFrame]) -> PriceData:
    symbols = list(prices_dict.keys())
    dates = next(iter(prices_dict.values())).index
    return PriceData(
        prices=prices_dict,
        symbols=symbols,
        source="synthetic",
        adjusted=True,
        aligned_dates=pd.DatetimeIndex(dates),
    )


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


class TestAC1:
    def test_ac1_correct_returns(self):
        from stock_backtester.engine import run_backtest

        # 12 prices → 11 returns → 10 active after shift(1) → 1.01^10
        closes = [100.0 * (1.01**i) for i in range(12)]
        prices = _make_price_data({"TEST": _make_price_df(closes)})
        config = _make_config(
            ["TEST"],
            commission_per_share=0.0,
            slippage_k=0.0,
        )
        result = run_backtest(config, prices, AlwaysLongStrategy())
        total_return = (
            result.equity_curve.iloc[-1]
            / result.equity_curve.iloc[result.warmup_end_idx]
            - 1
        )
        expected = 1.01**10 - 1
        np.testing.assert_allclose(total_return, expected, atol=1e-10)


class TestAC1b:
    def test_ac1b_multi_symbol_aggregation(self):
        from stock_backtester.engine import run_backtest

        prices = _make_price_data(
            {
                "A": _make_price_df([100.0, 105.0, 110.0]),
                "B": _make_price_df([100.0, 95.0, 100.0]),
            }
        )
        config = _make_config(
            ["A", "B"],
            commission_per_share=0.0,
            slippage_k=0.0,
        )
        result = run_backtest(config, prices, EqualWeightStrategy())
        # Expected: equity at end ≈ 1.050125
        np.testing.assert_allclose(result.equity_curve.iloc[-1], 1.050125, atol=1e-4)


class TestAC2:
    def test_ac2_look_ahead_prevention(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["TEST"], 50, seed=123)
        config = _make_config(
            ["TEST"],
            commission_per_share=0.0,
            slippage_k=0.0,
        )
        strategy = PerfectForesightStrategy()
        result = run_backtest(config, prices, strategy)

        # Compute compounded perfect foresight return (no shift)
        close = prices.prices["TEST"]["close"]
        simple_rets = close.pct_change().dropna()
        positive_rets = simple_rets[simple_rets > 0]
        perfect_return = (1 + positive_rets).prod() - 1

        backtest_return = (
            result.equity_curve.iloc[-1]
            / result.equity_curve.iloc[result.warmup_end_idx]
            - 1
        )
        assert backtest_return < perfect_return


class TestAC3:
    def test_ac3_slippage_invariant(self):
        from stock_backtester.engine import run_backtest

        prices = make_synthetic_price_data(["A", "B"], 50, seed=42)
        config = _make_config(["A", "B"], commission_per_share=0.001, slippage_k=0.5)
        result = run_backtest(config, prices, EqualWeightStrategy())

        # Global: net < gross
        total_net = result.net_returns.sum()
        total_gross = result.gross_returns.sum()
        assert total_net < total_gross

        # Commission > 0 (always nonzero for initial trade)
        assert result.commission_costs.sum() > 0
        # Slippage >= 0 (may be 0 if trailing vol insufficient at initial trade)
        assert result.slippage_costs.sum() >= 0


class TestAC4:
    def test_ac4_kelly_analytical(self):
        from stock_backtester.kelly import compute_kelly
        from tests.conftest import make_deterministic_returns

        mu, sigma = 0.0005, 0.01
        rets = make_deterministic_returns(mu, sigma, 100)
        result = compute_kelly(rets, warmup_end_idx=0)
        np.testing.assert_allclose(result.full_kelly, 5.0, atol=1e-6)


class TestAC5:
    def test_ac5_frontier_consistency(self):
        from stock_backtester.kelly import compute_kelly
        from tests.conftest import make_deterministic_returns

        mu, sigma = 0.0005, 0.01
        rets = make_deterministic_returns(mu, sigma, 100)
        result = compute_kelly(rets, warmup_end_idx=0)

        # Growth at 1.0 is 100%
        row_1 = [r for r in result.frontier if r.fraction_of_fstar == 1.0][0]
        np.testing.assert_allclose(row_1.growth_pct_of_max, 100.0, atol=1e-10)

        # Growth at 2.0 is 0%
        row_2 = [r for r in result.frontier if r.fraction_of_fstar == 2.0][0]
        np.testing.assert_allclose(row_2.growth_pct_of_max, 0.0, atol=1e-10)

        # Ruin monotonically increasing
        ruin_vals = [r.ruin_probability for r in result.frontier]
        for i in range(1, len(ruin_vals)):
            assert ruin_vals[i] >= ruin_vals[i - 1]

        # Ruin at 2.0 is 1.0
        np.testing.assert_allclose(row_2.ruin_probability, 1.0, atol=1e-10)


class TestAC6:
    def test_ac6_gbm_moments(self):
        from stock_backtester.simulation import generate_gbm_paths

        mu, sigma = 0.10, 0.20
        n_paths = 200
        n_days = 252
        seed = 42
        paths = generate_gbm_paths(mu, sigma, n_paths, n_days, seed)

        # Compute daily log returns from paths
        dt = 1.0 / 252.0
        log_rets = np.diff(np.log(paths), axis=1)  # (n_paths, n_days)

        # Expected daily moments
        expected_mu_daily = (mu - 0.5 * sigma**2) * dt
        expected_sigma_daily = sigma * np.sqrt(dt)

        # Sample moments across all paths and days
        sample_mu = log_rets.mean()
        sample_sigma = log_rets.std(ddof=1)

        # Check within 2 SE
        n_total = n_paths * n_days
        se_mu = sample_sigma / np.sqrt(n_total)
        assert abs(sample_mu - expected_mu_daily) < 2 * se_mu
        np.testing.assert_allclose(sample_sigma, expected_sigma_daily, rtol=0.05)


class TestAC7:
    def test_ac7_zero_edge_sharpe(self):
        from stock_backtester.engine import run_backtest
        from stock_backtester.simulation import generate_multi_symbol_paths

        symbols = ["SYM0", "SYM1", "SYM2", "SYM3"]
        config = _make_config(
            symbols,
            commission_per_share=0.0,
            slippage_k=0.0,
        )
        strategy = EqualWeightStrategy()

        # Generate paths with exact mu=0 for each symbol (sigma=0.20 annual)
        # mu_annual=0 means GBM drift is -sigma^2/2 (Ito correction)
        # But for Sharpe of simple returns, E[simple_ret] ≈ 0 when mu_annual=0
        cals = {sym: (0.0, 0.20) for sym in symbols}
        multi_paths = generate_multi_symbol_paths(
            cals, n_paths=200, n_days=252, seed=42
        )

        sharpes = []
        dates = pd.bdate_range("2020-01-01", periods=253)
        for path_idx in range(200):
            prices_dict = {}
            for sym in symbols:
                path_prices = multi_paths[sym][path_idx]
                df = pd.DataFrame(
                    {
                        "open": path_prices,
                        "high": path_prices,
                        "low": path_prices,
                        "close": path_prices,
                        "volume": 1e6,
                    },
                    index=dates,
                )
                prices_dict[sym] = df
            synth = PriceData(
                prices=prices_dict,
                symbols=symbols,
                source="synthetic",
                adjusted=True,
                aligned_dates=dates,
            )
            result = run_backtest(config, synth, strategy)
            rets = result.net_returns.iloc[result.warmup_end_idx :]
            mean_r = rets.mean()
            std_r = rets.std(ddof=1)
            if std_r > 0:
                sharpe_p = mean_r * 252 / (std_r * np.sqrt(252))
            else:
                sharpe_p = 0.0
            sharpes.append(sharpe_p)

        sharpes = np.array(sharpes)
        mean_sharpe = sharpes.mean()
        se = sharpes.std(ddof=1) / np.sqrt(len(sharpes))
        # With mu=0, mean Sharpe should be near 0 within 2 SE
        assert abs(mean_sharpe) < 2 * se
