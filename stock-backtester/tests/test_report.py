import json

from stock_backtester.types import (
    BacktestConfig,
    FrontierRow,
    KellyResult,
    MetricsResult,
    OutputFormat,
    SimulationResult,
    VerificationResult,
)


def _make_metrics(**overrides) -> MetricsResult:
    defaults = dict(
        sharpe=1.5,
        sortino=2.0,
        max_drawdown=-0.15,
        max_drawdown_duration_days=30,
        annualized_return=0.12,
        annualized_volatility=0.18,
        win_rate=0.55,
        gross_return_total=0.50,
        net_return_total=0.45,
        cost_drag=0.05,
    )
    defaults.update(overrides)
    return MetricsResult(**defaults)


def _make_kelly(**overrides) -> KellyResult:
    defaults = dict(
        mu_daily=0.0005,
        sigma_daily=0.01,
        full_kelly=5.0,
        half_kelly=2.5,
        critical_kelly=3.0,
        frontier=[
            FrontierRow("0.25 f*", 0.25, 43.75, 0.015),
            FrontierRow("0.50 f*", 0.50, 75.00, 0.062),
            FrontierRow("0.75 f*", 0.75, 93.75, 0.177),
            FrontierRow("1.00 f*", 1.00, 100.00, 0.500),
            FrontierRow("1.50 f*", 1.50, 75.00, 0.841),
            FrontierRow("2.00 f*", 2.00, 0.00, 1.000),
        ],
        ruin_threshold=0.01,
        drawdown_level=0.50,
    )
    defaults.update(overrides)
    return KellyResult(**defaults)


def _make_config() -> BacktestConfig:
    return BacktestConfig(
        symbols=["AAPL", "MSFT"],
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


class TestSurvivorshipWarning:
    def test_survivorship_warning(self):
        from stock_backtester.report import format_backtest_report

        output = format_backtest_report(
            _make_metrics(), _make_kelly(), _make_config(), OutputFormat.TABLE
        )
        assert "survivorship" in output.lower()


class TestJsonValid:
    def test_json_valid(self):
        from stock_backtester.report import format_backtest_report

        output = format_backtest_report(
            _make_metrics(), _make_kelly(), _make_config(), OutputFormat.JSON
        )
        parsed = json.loads(output)
        assert isinstance(parsed, dict)


class TestMetricsFields:
    def test_metrics_fields_in_table(self):
        from stock_backtester.report import format_backtest_report

        output = format_backtest_report(
            _make_metrics(), _make_kelly(), _make_config(), OutputFormat.TABLE
        )
        output_lower = output.lower()
        for field in [
            "sharpe",
            "sortino",
            "max_drawdown",
            "win_rate",
            "annualized_return",
            "annualized_volatility",
            "cost_drag",
        ]:
            assert field.replace("_", " ") in output_lower or field in output_lower, (
                f"Missing field: {field}"
            )


class TestKellyFields:
    def test_kelly_fields_in_table(self):
        from stock_backtester.report import format_backtest_report

        output = format_backtest_report(
            _make_metrics(), _make_kelly(), _make_config(), OutputFormat.TABLE
        )
        output_lower = output.lower()
        assert "full kelly" in output_lower or "full_kelly" in output_lower
        assert "half kelly" in output_lower or "half_kelly" in output_lower


class TestFrontierRows:
    def test_frontier_six_rows(self):
        from stock_backtester.report import format_backtest_report

        output = format_backtest_report(
            _make_metrics(), _make_kelly(), _make_config(), OutputFormat.TABLE
        )
        # Count frontier data rows: lines matching "N.NN f*" pattern
        import re

        fstar_lines = [
            line for line in output.split("\n") if re.search(r"\d+\.\d+\s+f\*", line)
        ]
        assert len(fstar_lines) == 6


class TestSimulationReport:
    def test_simulation_report_ruin_rate(self):
        from stock_backtester.report import format_simulation_report

        sim = SimulationResult(
            n_paths=200,
            seed=42,
            per_symbol_calibrations={"AAPL": (0.10, 0.20)},
            empirical_ruin_rate=0.15,
            theoretical_ruin_rate=0.12,
            path_results=None,
        )
        output = format_simulation_report(sim, OutputFormat.TABLE)
        assert "ruin" in output.lower()


class TestVerificationReport:
    def test_verification_report_all_acs(self):
        from stock_backtester.report import format_verification_report

        results = [
            VerificationResult(f"AC-{i}", True, "x", "x", None, "ok")
            for i in range(1, 8)
        ] + [VerificationResult("AC-1b", True, "x", "x", None, "ok")]
        output = format_verification_report(results, OutputFormat.TABLE)
        for r in results:
            assert r.test_name in output
            assert "PASS" in output


class TestInfSortino:
    def test_inf_sortino_table_display(self):
        from stock_backtester.report import format_backtest_report

        metrics = _make_metrics(sortino=float("inf"))
        output = format_backtest_report(
            metrics, _make_kelly(), _make_config(), OutputFormat.TABLE
        )
        assert "inf" in output.lower()

    def test_inf_sortino_json_display(self):
        from stock_backtester.report import format_backtest_report

        metrics = _make_metrics(sortino=float("inf"))
        output = format_backtest_report(
            metrics, _make_kelly(), _make_config(), OutputFormat.JSON
        )
        # Must be valid JSON (float('inf') is not valid JSON)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
