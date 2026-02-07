import sys

import typer

from stock_backtester.types import BacktestConfig, OutputFormat, SimulationConfig

app = typer.Typer(help="Stock backtesting system with Kelly/ruin analysis")


@app.command()
def run(
    symbols: str = typer.Option(..., help="Comma-separated stock symbols"),
    start: str = typer.Option("2020-01-01", help="Start date"),
    end: str = typer.Option("2025-01-01", help="End date"),
    strategy: str = typer.Option("equal-weight", help="Strategy name"),
    commission: float = typer.Option(0.001, help="Commission per share"),
    slippage_k: float = typer.Option(0.5, "--slippage-k", help="Slippage coefficient"),
    ruin_threshold: float = typer.Option(0.01, help="Ruin probability threshold"),
    drawdown_level: float = typer.Option(0.50, help="Drawdown level for ruin"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run a historical backtest."""
    from stock_backtester.data import DataError, fetch_prices
    from stock_backtester.engine import run_backtest
    from stock_backtester.kelly import KellyError, compute_kelly
    from stock_backtester.metrics import compute_metrics
    from stock_backtester.report import format_backtest_report
    from stock_backtester.strategy import StrategyError, get_strategy

    symbol_list = [s.strip() for s in symbols.split(",")]
    output_format = OutputFormat.JSON if json else OutputFormat.TABLE

    config = BacktestConfig(
        symbols=symbol_list,
        start_date=start,
        end_date=end,
        strategy_name=strategy,
        strategy_params={},
        commission_per_share=commission,
        slippage_k=slippage_k,
        ruin_threshold=ruin_threshold,
        drawdown_level=drawdown_level,
        output_format=output_format,
    )

    try:
        prices = fetch_prices(symbol_list, start, end)
        strat = get_strategy(strategy, {})
        result = run_backtest(config, prices, strat)
        metrics = compute_metrics(
            result.net_returns, result.gross_returns, result.warmup_end_idx
        )
        kelly = compute_kelly(
            result.net_returns,
            result.warmup_end_idx,
            ruin_threshold,
            drawdown_level,
        )
        report = format_backtest_report(metrics, kelly, config, output_format)
        print(report)
    except (DataError, StrategyError, KellyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


@app.command()
def simulate(
    symbols: str = typer.Option(..., help="Comma-separated stock symbols"),
    start: str = typer.Option("2020-01-01", help="Start date"),
    end: str = typer.Option("2025-01-01", help="End date"),
    strategy: str = typer.Option("equal-weight", help="Strategy name"),
    paths: int = typer.Option(200, help="Number of Monte Carlo paths"),
    seed: int = typer.Option(42, help="Random seed"),
    commission: float = typer.Option(0.001, help="Commission per share"),
    slippage_k: float = typer.Option(0.5, "--slippage-k", help="Slippage coefficient"),
    ruin_threshold: float = typer.Option(0.01, help="Ruin probability threshold"),
    drawdown_level: float = typer.Option(0.50, help="Drawdown level for ruin"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run Monte Carlo simulation."""
    from stock_backtester.data import DataError, fetch_prices
    from stock_backtester.report import format_simulation_report
    from stock_backtester.simulation import SimulationError, run_monte_carlo
    from stock_backtester.strategy import StrategyError, get_strategy

    symbol_list = [s.strip() for s in symbols.split(",")]
    output_format = OutputFormat.JSON if json else OutputFormat.TABLE

    config = SimulationConfig(
        symbols=symbol_list,
        start_date=start,
        end_date=end,
        strategy_name=strategy,
        strategy_params={},
        n_paths=paths,
        seed=seed,
        commission_per_share=commission,
        slippage_k=slippage_k,
        ruin_threshold=ruin_threshold,
        drawdown_level=drawdown_level,
        output_format=output_format,
    )

    try:
        prices = fetch_prices(symbol_list, start, end)
        strat = get_strategy(strategy, {})
        result = run_monte_carlo(prices, strat, config)
        report = format_simulation_report(result, output_format)
        print(report)
    except (DataError, StrategyError, SimulationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


@app.command()
def verify(
    seed: int = typer.Option(42, help="Random seed for verification"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run built-in verification tests."""
    from stock_backtester.report import format_verification_report
    from stock_backtester.simulation import run_verification_tests

    output_format = OutputFormat.JSON if json else OutputFormat.TABLE
    results = run_verification_tests(seed)
    report = format_verification_report(results, output_format)
    print(report)
