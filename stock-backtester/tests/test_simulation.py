import numpy as np
import pandas as pd


class TestGBMPaths:
    def test_gbm_all_positive(self):
        from stock_backtester.simulation import generate_gbm_paths

        paths = generate_gbm_paths(
            mu_annual=0.10, sigma_annual=0.20, n_paths=50, n_days=252, seed=42
        )
        assert (paths > 0).all()

    def test_gbm_determinism(self):
        from stock_backtester.simulation import generate_gbm_paths

        p1 = generate_gbm_paths(0.10, 0.20, 20, 100, seed=99)
        p2 = generate_gbm_paths(0.10, 0.20, 20, 100, seed=99)
        np.testing.assert_array_equal(p1, p2)

    def test_gbm_shape(self):
        from stock_backtester.simulation import generate_gbm_paths

        paths = generate_gbm_paths(0.10, 0.20, 30, 252, seed=1)
        assert paths.shape == (30, 253)  # n_paths x (n_days + 1) including S0


class TestCalibration:
    def test_calibration_known_returns(self):
        from stock_backtester.simulation import calibrate_gbm

        # Use deterministic (constant) daily log returns for exact calibration
        n = 1000
        daily_log_ret = 0.0004  # constant
        # Prices: 100 * exp(0.0004 * t)
        closes = [100.0 * np.exp(daily_log_ret * t) for t in range(n)]
        dates = pd.bdate_range("2020-01-01", periods=n)
        df = pd.DataFrame(
            {
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "volume": 1e6,
            },
            index=dates,
        )
        cal = calibrate_gbm({"TEST": df})
        mu_ann, sigma_ann = cal["TEST"]
        # With constant returns, mean = daily_log_ret, std = 0
        np.testing.assert_allclose(mu_ann, daily_log_ret * 252, atol=1e-10)
        np.testing.assert_allclose(sigma_ann, 0.0, atol=1e-10)


class TestMultiSymbolSubseeds:
    def test_multi_symbol_different_subseeds(self):
        from stock_backtester.simulation import generate_multi_symbol_paths

        cals = {"A": (0.10, 0.20), "B": (0.10, 0.20)}
        result = generate_multi_symbol_paths(cals, n_paths=10, n_days=100, seed=42)
        # Different sub-seeds → different paths
        assert not np.array_equal(result["A"], result["B"])


class TestRuinDetection:
    def test_ruin_detection_breach(self):
        from stock_backtester.simulation import check_ruin

        # Peak=1.0, trough=0.40 → 60% drawdown > 50% threshold
        equity = pd.Series([1.0, 0.9, 0.7, 0.4, 0.5])
        assert check_ruin(equity, drawdown_level=0.50) is True

    def test_ruin_detection_no_breach(self):
        from stock_backtester.simulation import check_ruin

        # Peak=1.0, min=0.60 → 40% drawdown < 50% threshold
        equity = pd.Series([1.0, 0.95, 0.8, 0.6, 0.7])
        assert check_ruin(equity, drawdown_level=0.50) is False
