import json
import math

from stock_backtester.types import (
    BacktestConfig,
    KellyResult,
    MetricsResult,
    OutputFormat,
    SimulationResult,
    VerificationResult,
)

SURVIVORSHIP_WARNING = (
    "WARNING: This analysis uses survivorship-biased data (yfinance). "
    "Results may overstate historical performance."
)


def _safe_float(v: float) -> float | None:
    if math.isinf(v):
        return None
    if math.isnan(v):
        return None
    return v


def format_backtest_report(
    metrics: MetricsResult,
    kelly: KellyResult,
    config: BacktestConfig,
    output_format: OutputFormat,
) -> str:
    if output_format == OutputFormat.JSON:
        data = {
            "warning": SURVIVORSHIP_WARNING,
            "config": {
                "symbols": config.symbols,
                "start_date": config.start_date,
                "end_date": config.end_date,
                "strategy": config.strategy_name,
                "commission_per_share": config.commission_per_share,
                "slippage_k": config.slippage_k,
            },
            "metrics": {
                "sharpe": _safe_float(metrics.sharpe),
                "sortino": _safe_float(metrics.sortino),
                "max_drawdown": metrics.max_drawdown,
                "max_drawdown_duration_days": metrics.max_drawdown_duration_days,
                "annualized_return": metrics.annualized_return,
                "annualized_volatility": metrics.annualized_volatility,
                "win_rate": metrics.win_rate,
                "gross_return_total": metrics.gross_return_total,
                "net_return_total": metrics.net_return_total,
                "cost_drag": metrics.cost_drag,
            },
            "kelly": {
                "full_kelly": kelly.full_kelly,
                "half_kelly": kelly.half_kelly,
                "critical_kelly": kelly.critical_kelly,
                "mu_daily": kelly.mu_daily,
                "sigma_daily": kelly.sigma_daily,
            },
            "frontier": [
                {
                    "label": row.fraction_label,
                    "fraction_of_fstar": row.fraction_of_fstar,
                    "growth_pct_of_max": row.growth_pct_of_max,
                    "ruin_probability": row.ruin_probability,
                }
                for row in kelly.frontier
            ],
        }
        return json.dumps(data, indent=2)

    # TABLE format
    lines = [
        SURVIVORSHIP_WARNING,
        "",
        "=" * 60,
        f"  Portfolio: {', '.join(config.symbols)}",
        f"  Strategy:  {config.strategy_name}",
        f"  Period:    {config.start_date} to {config.end_date}",
        "=" * 60,
        "",
        "--- Performance Metrics ---",
        f"  Sharpe Ratio:          {metrics.sharpe:>10.4f}",
        f"  Sortino Ratio:         "
        f"{'inf' if math.isinf(metrics.sortino) else f'{metrics.sortino:>10.4f}'}",
        f"  Max Drawdown:          {metrics.max_drawdown:>10.4f}",
        f"  Max Drawdown Duration: {metrics.max_drawdown_duration_days:>10d} days",
        f"  Annualized Return:     {metrics.annualized_return:>10.4f}",
        f"  Annualized Volatility: {metrics.annualized_volatility:>10.4f}",
        f"  Win Rate:              {metrics.win_rate:>10.4f}",
        f"  Gross Return Total:    {metrics.gross_return_total:>10.4f}",
        f"  Net Return Total:      {metrics.net_return_total:>10.4f}",
        f"  Cost Drag:             {metrics.cost_drag:>10.4f}",
        "",
        "--- Kelly Analysis ---",
        f"  Full Kelly (f*):       {kelly.full_kelly:>10.4f}",
        f"  Half Kelly (f*/2):     {kelly.half_kelly:>10.4f}",
        f"  Critical Kelly:        "
        f"{kelly.critical_kelly if kelly.critical_kelly is not None else 'N/A':>10}",
        f"  Mu Daily:              {kelly.mu_daily:>10.6f}",
        f"  Sigma Daily:           {kelly.sigma_daily:>10.6f}",
        "",
        "--- Capital Efficiency Frontier ---",
        f"  {'Fraction':<12} {'Growth %':<12} {'Ruin Prob':<12}",
        f"  {'-' * 12} {'-' * 12} {'-' * 12}",
    ]
    for row in kelly.frontier:
        growth = f"{row.growth_pct_of_max:<12.2f}"
        ruin = f"{row.ruin_probability:<12.4f}"
        lines.append(f"  {row.fraction_label:<12} {growth} {ruin}")
    return "\n".join(lines)


def format_simulation_report(
    result: SimulationResult,
    output_format: OutputFormat,
) -> str:
    if output_format == OutputFormat.JSON:
        data = {
            "n_paths": result.n_paths,
            "seed": result.seed,
            "calibrations": {
                sym: {"mu_annual": mu, "sigma_annual": sigma}
                for sym, (mu, sigma) in result.per_symbol_calibrations.items()
            },
            "empirical_ruin_rate": result.empirical_ruin_rate,
            "theoretical_ruin_rate": result.theoretical_ruin_rate,
        }
        return json.dumps(data, indent=2)

    lines = [
        "=" * 60,
        "  Monte Carlo Simulation Results",
        "=" * 60,
        "",
        f"  Paths:               {result.n_paths}",
        f"  Seed:                {result.seed}",
        "",
        "--- Calibrations ---",
    ]
    for sym, (mu, sigma) in result.per_symbol_calibrations.items():
        lines.append(f"  {sym}: mu={mu:.4f}, sigma={sigma:.4f}")
    lines.extend(
        [
            "",
            "--- Ruin Analysis ---",
            f"  Empirical Ruin Rate:   {result.empirical_ruin_rate:.4f}",
            f"  Theoretical Ruin Rate: {result.theoretical_ruin_rate:.4f}",
        ]
    )
    return "\n".join(lines)


def format_verification_report(
    results: list[VerificationResult],
    output_format: OutputFormat,
) -> str:
    if output_format == OutputFormat.JSON:
        data = [
            {
                "test_name": r.test_name,
                "passed": r.passed,
                "expected": r.expected,
                "actual": r.actual,
                "tolerance": r.tolerance,
                "detail": r.detail,
            }
            for r in results
        ]
        return json.dumps(data, indent=2)

    lines = [
        "=" * 60,
        "  Verification Test Results",
        "=" * 60,
        "",
    ]
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"  {r.test_name}: {status} - {r.detail}")
        if not r.passed:
            lines.append(f"    Expected: {r.expected}")
            lines.append(f"    Actual:   {r.actual}")
    all_pass = all(r.passed for r in results)
    lines.extend(
        [
            "",
            f"  Total: {len(results)} tests, "
            f"{'ALL PASSED' if all_pass else 'SOME FAILED'}",
        ]
    )
    return "\n".join(lines)
