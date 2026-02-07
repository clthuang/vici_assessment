import time
import tracemalloc

from stock_backtester.engine import run_backtest
from stock_backtester.strategy import EqualWeightStrategy
from stock_backtester.types import BacktestConfig, OutputFormat
from tests.conftest import make_synthetic_price_data


def _make_config(symbols):
    return BacktestConfig(
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


class TestBacktestTiming:
    def test_single_backtest_under_5s(self):
        """Single 4-symbol, 5-year backtest completes in < 5 seconds."""
        prices = make_synthetic_price_data(["A", "B", "C", "D"], 1260, seed=42)
        config = _make_config(prices.symbols)
        strategy = EqualWeightStrategy()

        start = time.perf_counter()
        run_backtest(config, prices, strategy)
        elapsed = time.perf_counter() - start

        assert elapsed < 5.0, f"Backtest took {elapsed:.2f}s (limit: 5s)"


class TestMemory:
    def test_backtest_memory_under_500mb(self):
        """Memory usage stays under 500 MB for a standard backtest."""
        prices = make_synthetic_price_data(["A", "B", "C", "D"], 1260, seed=42)
        config = _make_config(prices.symbols)
        strategy = EqualWeightStrategy()

        tracemalloc.start()
        run_backtest(config, prices, strategy)
        _, peak_mb = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb_val = peak_mb / 1e6

        assert peak_mb_val < 500, f"Memory peak {peak_mb_val:.1f} MB (limit: 500 MB)"


class TestSimulationTiming:
    def test_simulation_completes_under_120s(self):
        """Monte Carlo simulation (200 paths) completes in < 120 seconds."""
        from stock_backtester.simulation import run_monte_carlo
        from stock_backtester.types import SimulationConfig

        prices = make_synthetic_price_data(["A", "B"], 252, seed=42)
        config = SimulationConfig(
            symbols=prices.symbols,
            start_date="2020-01-01",
            end_date="2025-01-01",
            strategy_name="equal-weight",
            strategy_params={},
            n_paths=200,
            seed=42,
            commission_per_share=0.001,
            slippage_k=0.5,
            ruin_threshold=0.01,
            drawdown_level=0.50,
            output_format=OutputFormat.TABLE,
        )
        strategy = EqualWeightStrategy()

        start = time.perf_counter()
        run_monte_carlo(prices, strategy, config)
        elapsed = time.perf_counter() - start

        assert elapsed < 120.0, f"Simulation took {elapsed:.2f}s (limit: 120s)"


class TestVerificationTiming:
    def test_verification_completes_under_30s(self):
        """Verification test suite completes in < 30 seconds."""
        from stock_backtester.simulation import run_verification_tests

        start = time.perf_counter()
        run_verification_tests(seed=42)
        elapsed = time.perf_counter() - start

        assert elapsed < 30.0, f"Verification took {elapsed:.2f}s (limit: 30s)"


class TestNoCircularImports:
    def test_types_imports_nothing_from_package(self):
        """types.py should not import from stock_backtester modules."""
        import ast
        import pathlib

        types_path = (
            pathlib.Path(__file__).parent.parent
            / "src"
            / "stock_backtester"
            / "types.py"
        )
        tree = ast.parse(types_path.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("stock_backtester"):
                    assert False, f"types.py imports from {node.module}"
