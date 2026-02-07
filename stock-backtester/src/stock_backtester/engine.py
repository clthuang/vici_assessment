import numpy as np

from stock_backtester.execution import (
    compute_costs,
    compute_multi_symbol_simple_returns,
)
from stock_backtester.strategy import Strategy
from stock_backtester.types import BacktestConfig, BacktestResult, PriceData


def run_backtest(
    config: BacktestConfig,
    prices: PriceData,
    strategy: Strategy,
) -> BacktestResult:
    # Step 1: Copy prices, pass to strategy
    prices_copy = {sym: df.copy() for sym, df in prices.prices.items()}
    raw_weights = strategy.compute_weights(prices_copy, prices.symbols)

    # Step 2: Shift(1) weights — single temporal alignment point
    shifted_weights = raw_weights.shift(1).fillna(0.0)

    # Step 3: Simple returns per symbol
    simple_returns = compute_multi_symbol_simple_returns(prices)

    # Step 4: Portfolio simple return R_p = sum(w_i * R_i)
    # Fill NaN returns (first bar has no prior price) with 0 to avoid NaN propagation
    portfolio_simple_return = (shifted_weights * simple_returns.fillna(0.0)).sum(axis=1)

    # Step 5: Convert to log-return r_p = ln(1 + R_p)
    portfolio_log_return = np.log(1 + portfolio_simple_return)

    # Step 6: Costs per symbol -> aggregate
    slippage_costs, commission_costs = compute_costs(
        prices, shifted_weights, config.slippage_k, config.commission_per_share
    )

    # Step 7: Net returns = gross - costs
    gross_returns = portfolio_log_return
    net_returns = gross_returns - slippage_costs - commission_costs

    # Warmup: first bar where shifted weights are not all 0 (positional index)
    weight_sums = shifted_weights.abs().sum(axis=1)
    nonzero_mask = weight_sums.ne(0)
    first_active_date = nonzero_mask.idxmax()
    warmup_end_idx = int(shifted_weights.index.get_loc(first_active_date))

    # Step 8: Equity curve = exp(cumsum(net_returns))
    cumulative = net_returns.cumsum()
    # Normalize so equity at warmup_end_idx = 1.0
    cumulative = cumulative - cumulative.iloc[warmup_end_idx]
    equity_curve = np.exp(cumulative)

    return BacktestResult(
        config=config,
        gross_returns=gross_returns,
        net_returns=net_returns,
        weights=shifted_weights,
        slippage_costs=slippage_costs,
        commission_costs=commission_costs,
        equity_curve=equity_curve,
        warmup_end_idx=warmup_end_idx,
    )
