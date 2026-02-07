import numpy as np
import pandas as pd

from stock_backtester.engine import run_backtest
from stock_backtester.kelly import KellyError, compute_kelly
from stock_backtester.kelly import ruin_probability as kelly_ruin_prob
from stock_backtester.strategy import (
    AlwaysLongStrategy,
    EqualWeightStrategy,
    Strategy,
)
from stock_backtester.types import (
    BacktestConfig,
    OutputFormat,
    PriceData,
    SimulationConfig,
    SimulationResult,
    VerificationResult,
)


class SimulationError(Exception):
    pass


def calibrate_gbm(
    prices: dict[str, pd.DataFrame],
) -> dict[str, tuple[float, float]]:
    calibrations: dict[str, tuple[float, float]] = {}
    for sym, df in prices.items():
        close = df["close"]
        log_rets = np.log(close / close.shift(1)).dropna()
        mu_daily = float(log_rets.mean())
        sigma_daily = float(log_rets.std(ddof=1))
        mu_annual = mu_daily * 252
        sigma_annual = sigma_daily * np.sqrt(252)
        calibrations[sym] = (mu_annual, sigma_annual)
    return calibrations


def generate_gbm_paths(
    mu_annual: float,
    sigma_annual: float,
    n_paths: int,
    n_days: int,
    seed: int,
    s0: float = 100.0,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dt = 1.0 / 252.0
    z = rng.standard_normal((n_paths, n_days))
    drift = (mu_annual - 0.5 * sigma_annual**2) * dt
    diffusion = sigma_annual * np.sqrt(dt) * z
    log_increments = drift + diffusion
    log_prices = np.cumsum(log_increments, axis=1)
    paths = np.zeros((n_paths, n_days + 1))
    paths[:, 0] = s0
    paths[:, 1:] = s0 * np.exp(log_prices)
    return paths


def generate_multi_symbol_paths(
    calibrations: dict[str, tuple[float, float]],
    n_paths: int,
    n_days: int,
    seed: int,
) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for i, (sym, (mu, sigma)) in enumerate(calibrations.items()):
        result[sym] = generate_gbm_paths(mu, sigma, n_paths, n_days, seed + i)
    return result


def check_ruin(equity: pd.Series, drawdown_level: float) -> bool:  # type: ignore[type-arg]
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return bool(drawdown.min() < -drawdown_level)


def run_monte_carlo(
    prices: PriceData,
    strategy: Strategy,
    config: SimulationConfig,
) -> SimulationResult:
    # Step 1: Historical backtest
    backtest_config = BacktestConfig(
        symbols=config.symbols,
        start_date=config.start_date,
        end_date=config.end_date,
        strategy_name=config.strategy_name,
        strategy_params=config.strategy_params,
        commission_per_share=config.commission_per_share,
        slippage_k=config.slippage_k,
        ruin_threshold=config.ruin_threshold,
        drawdown_level=config.drawdown_level,
        output_format=config.output_format,
    )
    hist_result = run_backtest(backtest_config, prices, strategy)

    # Step 1b: Compute half-Kelly from historical net returns for ruin scaling
    try:
        kelly_result = compute_kelly(
            hist_result.net_returns,
            hist_result.warmup_end_idx,
            config.ruin_threshold,
            config.drawdown_level,
        )
        f_star = kelly_result.full_kelly
        half_kelly = kelly_result.half_kelly
    except KellyError:
        f_star = 0.0
        half_kelly = 0.0

    # Step 2: Calibrate GBM
    cals = calibrate_gbm(prices.prices)

    # Step 3: Generate paths
    n_days = len(prices.aligned_dates)
    multi_paths = generate_multi_symbol_paths(cals, config.n_paths, n_days, config.seed)

    # Step 4: Per-path backtest + ruin detection at half-Kelly sizing
    # If half_kelly <= 0, no capital would be allocated — ruin is trivially 0
    if half_kelly <= 0:
        empirical_ruin_rate = 0.0
        theoretical_ruin = 0.0
    else:
        # Synthetic dates for MC paths — value is arbitrary, only length matters
        dates = pd.bdate_range("2020-01-01", periods=n_days + 1)
        ruin_count = 0
        for path_idx in range(config.n_paths):
            prices_dict: dict[str, pd.DataFrame] = {}
            for sym in config.symbols:
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
            synth_prices = PriceData(
                prices=prices_dict,
                symbols=config.symbols,
                source="synthetic",
                adjusted=True,
                aligned_dates=dates,
            )
            path_result = run_backtest(backtest_config, synth_prices, strategy)
            scaled_returns = path_result.net_returns * half_kelly
            scaled_equity = np.exp(scaled_returns.cumsum())
            if check_ruin(scaled_equity, config.drawdown_level):
                ruin_count += 1

        empirical_ruin_rate = ruin_count / config.n_paths

        # Step 5: Theoretical ruin rate
        theoretical_ruin = kelly_ruin_prob(half_kelly, f_star, config.drawdown_level)

    return SimulationResult(
        n_paths=config.n_paths,
        seed=config.seed,
        per_symbol_calibrations=cals,
        empirical_ruin_rate=empirical_ruin_rate,
        theoretical_ruin_rate=theoretical_ruin,
        path_results=None,
    )


def run_verification_tests(seed: int = 42) -> list[VerificationResult]:
    results: list[VerificationResult] = []

    # AC-1: Deterministic returns
    try:
        closes = [100.0 * (1.01**i) for i in range(12)]
        dates = pd.bdate_range("2020-01-01", periods=12)
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
        price_data = PriceData(
            prices={"TEST": df},
            symbols=["TEST"],
            source="synthetic",
            adjusted=True,
            aligned_dates=dates,
        )
        config = BacktestConfig(
            symbols=["TEST"],
            start_date="2020-01-01",
            end_date="2025-01-01",
            strategy_name="always-long",
            strategy_params={},
            commission_per_share=0.0,
            slippage_k=0.0,
            ruin_threshold=0.01,
            drawdown_level=0.50,
            output_format=OutputFormat.TABLE,
        )
        result = run_backtest(config, price_data, AlwaysLongStrategy())
        total_return = (
            result.equity_curve.iloc[-1]
            / result.equity_curve.iloc[result.warmup_end_idx]
            - 1
        )
        expected = 1.01**10 - 1
        passed = abs(total_return - expected) < 1e-10
        results.append(
            VerificationResult(
                test_name="AC-1",
                passed=passed,
                expected=f"{expected:.10f}",
                actual=f"{total_return:.10f}",
                tolerance="1e-10",
                detail="Deterministic 1% daily returns",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-1",
                passed=False,
                expected="1.01^10 - 1",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-1b: Multi-symbol aggregation
    try:
        dates = pd.bdate_range("2020-01-01", periods=3)
        a_df = pd.DataFrame(
            {
                "open": [100, 105, 110],
                "high": [100, 105, 110],
                "low": [100, 105, 110],
                "close": [100.0, 105.0, 110.0],
                "volume": 1e6,
            },
            index=dates,
        )
        b_df = pd.DataFrame(
            {
                "open": [100, 95, 100],
                "high": [100, 95, 100],
                "low": [100, 95, 100],
                "close": [100.0, 95.0, 100.0],
                "volume": 1e6,
            },
            index=dates,
        )
        price_data = PriceData(
            prices={"A": a_df, "B": b_df},
            symbols=["A", "B"],
            source="synthetic",
            adjusted=True,
            aligned_dates=dates,
        )
        config = BacktestConfig(
            symbols=["A", "B"],
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
        result = run_backtest(config, price_data, EqualWeightStrategy())
        passed = abs(result.equity_curve.iloc[-1] - 1.050125) < 1e-4
        results.append(
            VerificationResult(
                test_name="AC-1b",
                passed=passed,
                expected="1.050125",
                actual=f"{result.equity_curve.iloc[-1]:.6f}",
                tolerance="1e-4",
                detail="Multi-symbol equal-weight aggregation",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-1b",
                passed=False,
                expected="1.050125",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-2: Look-ahead prevention
    try:
        from tests.conftest import PerfectForesightStrategy, make_synthetic_price_data

        prices = make_synthetic_price_data(["TEST"], 50, seed=123)
        config = BacktestConfig(
            symbols=["TEST"],
            start_date="2020-01-01",
            end_date="2025-01-01",
            strategy_name="always-long",
            strategy_params={},
            commission_per_share=0.0,
            slippage_k=0.0,
            ruin_threshold=0.01,
            drawdown_level=0.50,
            output_format=OutputFormat.TABLE,
        )
        strat = PerfectForesightStrategy()
        result = run_backtest(config, prices, strat)
        close = prices.prices["TEST"]["close"]
        simple_rets = close.pct_change().dropna()
        positive_rets = simple_rets[simple_rets > 0]
        perfect_return = (1 + positive_rets).prod() - 1
        backtest_return = (
            result.equity_curve.iloc[-1]
            / result.equity_curve.iloc[result.warmup_end_idx]
            - 1
        )
        passed = backtest_return < perfect_return
        results.append(
            VerificationResult(
                test_name="AC-2",
                passed=passed,
                expected=f"< {perfect_return:.6f}",
                actual=f"{backtest_return:.6f}",
                tolerance=None,
                detail="Backtest return < perfect foresight return",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-2",
                passed=False,
                expected="< perfect",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-3: Slippage invariant
    try:
        prices = make_synthetic_price_data(["A", "B"], 50, seed=seed)
        config = BacktestConfig(
            symbols=["A", "B"],
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
        result = run_backtest(config, prices, EqualWeightStrategy())
        net_total = result.net_returns.sum()
        gross_total = result.gross_returns.sum()
        passed = net_total < gross_total and result.commission_costs.sum() > 0
        results.append(
            VerificationResult(
                test_name="AC-3",
                passed=passed,
                expected="net < gross, commission > 0",
                actual=f"net={net_total:.6f}, gross={gross_total:.6f}",
                tolerance=None,
                detail="Slippage and commission invariant",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-3",
                passed=False,
                expected="net < gross",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-4: Kelly analytical
    try:
        from tests.conftest import make_deterministic_returns

        mu, sigma = 0.0005, 0.01
        rets = make_deterministic_returns(mu, sigma, 100)
        kelly = compute_kelly(rets, warmup_end_idx=0)
        passed = abs(kelly.full_kelly - 5.0) < 1e-6
        results.append(
            VerificationResult(
                test_name="AC-4",
                passed=passed,
                expected="5.0",
                actual=f"{kelly.full_kelly:.6f}",
                tolerance="1e-6",
                detail="Kelly f* = mu/sigma^2",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-4",
                passed=False,
                expected="5.0",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-5: Frontier consistency
    try:
        rets = make_deterministic_returns(0.0005, 0.01, 100)
        kelly = compute_kelly(rets, warmup_end_idx=0)
        row_1 = [r for r in kelly.frontier if r.fraction_of_fstar == 1.0][0]
        row_2 = [r for r in kelly.frontier if r.fraction_of_fstar == 2.0][0]
        ruin_vals = [r.ruin_probability for r in kelly.frontier]
        monotonic = all(
            ruin_vals[i] >= ruin_vals[i - 1] for i in range(1, len(ruin_vals))
        )
        passed = (
            abs(row_1.growth_pct_of_max - 100.0) < 1e-10
            and abs(row_2.growth_pct_of_max) < 1e-10
            and abs(row_2.ruin_probability - 1.0) < 1e-10
            and monotonic
        )
        results.append(
            VerificationResult(
                test_name="AC-5",
                passed=passed,
                expected="g(f*)=100%, g(2f*)=0%, ruin monotonic, ruin(2f*)=1.0",
                actual=(
                    f"g(f*)={row_1.growth_pct_of_max:.2f}%"
                    f", ruin(2f*)={row_2.ruin_probability:.4f}"
                ),
                tolerance="1e-10",
                detail="Frontier consistency checks",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-5",
                passed=False,
                expected="frontier consistent",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-6: GBM moments
    try:
        mu_ann, sigma_ann = 0.10, 0.20
        paths = generate_gbm_paths(mu_ann, sigma_ann, 200, 252, seed)
        log_rets = np.diff(np.log(paths), axis=1)
        dt = 1.0 / 252.0
        expected_mu_daily = (mu_ann - 0.5 * sigma_ann**2) * dt
        sample_mu = log_rets.mean()
        sample_sigma = log_rets.std(ddof=1)
        se_mu = sample_sigma / np.sqrt(200 * 252)
        mu_ok = abs(sample_mu - expected_mu_daily) < 2 * se_mu
        sigma_ok = (
            abs(sample_sigma - sigma_ann * np.sqrt(dt)) / (sigma_ann * np.sqrt(dt))
            < 0.05
        )
        passed = mu_ok and sigma_ok
        results.append(
            VerificationResult(
                test_name="AC-6",
                passed=passed,
                expected=(
                    f"mu_daily≈{expected_mu_daily:.6f}"
                    f", sigma_daily≈{sigma_ann * np.sqrt(dt):.6f}"
                ),
                actual=f"mu_daily={sample_mu:.6f}, sigma_daily={sample_sigma:.6f}",
                tolerance="2 SE / 5% rtol",
                detail="GBM moment matching",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-6",
                passed=False,
                expected="moments match",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    # AC-7: Zero-edge Sharpe
    try:
        symbols_7 = [f"SYM{i}" for i in range(4)]
        config = BacktestConfig(
            symbols=symbols_7,
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
        strategy = EqualWeightStrategy()
        # Use exact mu=0 calibrations to ensure true zero-edge
        cals_7 = {sym: (0.0, 0.20) for sym in symbols_7}
        multi_paths = generate_multi_symbol_paths(
            cals_7, n_paths=200, n_days=252, seed=seed
        )
        sharpes = []
        sim_dates = pd.bdate_range("2020-01-01", periods=253)
        for pidx in range(200):
            pd_dict: dict[str, pd.DataFrame] = {}
            for sym in symbols_7:
                pp = multi_paths[sym][pidx]
                pd_dict[sym] = pd.DataFrame(
                    {"open": pp, "high": pp, "low": pp, "close": pp, "volume": 1e6},
                    index=sim_dates,
                )
            synth = PriceData(
                prices=pd_dict,
                symbols=symbols_7,
                source="synthetic",
                adjusted=True,
                aligned_dates=sim_dates,
            )
            r = run_backtest(config, synth, strategy)
            rets = r.net_returns.iloc[r.warmup_end_idx :]
            mr, sr = rets.mean(), rets.std(ddof=1)
            sharpes.append(mr * 252 / (sr * np.sqrt(252)) if sr > 0 else 0.0)
        sharpes_arr = np.array(sharpes)
        mean_s = sharpes_arr.mean()
        se_s = sharpes_arr.std(ddof=1) / np.sqrt(len(sharpes_arr))
        passed = abs(mean_s) < 2 * se_s
        results.append(
            VerificationResult(
                test_name="AC-7",
                passed=passed,
                expected="mean Sharpe ≈ 0",
                actual=f"mean={mean_s:.4f}, SE={se_s:.4f}",
                tolerance="2 SE",
                detail="Zero-edge Sharpe within statistical noise",
            )
        )
    except Exception as e:
        results.append(
            VerificationResult(
                test_name="AC-7",
                passed=False,
                expected="mean Sharpe ≈ 0",
                actual=f"ERROR: {e}",
                tolerance=None,
                detail=str(e),
            )
        )

    return results
