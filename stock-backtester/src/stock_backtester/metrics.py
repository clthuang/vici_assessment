import numpy as np
import pandas as pd

from stock_backtester.types import MetricsResult


def compute_metrics(
    net_returns: pd.Series,  # type: ignore[type-arg]
    gross_returns: pd.Series,  # type: ignore[type-arg]
    warmup_end_idx: int,
) -> MetricsResult:
    net = net_returns.iloc[warmup_end_idx:]
    gross = gross_returns.iloc[warmup_end_idx:]

    mean_r = net.mean()
    std_r = net.std(ddof=1)

    # Sharpe
    if std_r == 0 or np.isnan(std_r):
        sharpe = 0.0
    else:
        sharpe = (mean_r * 252) / (std_r * np.sqrt(252))

    # Sortino (full-count convention, Sortino 2001)
    downside = net.clip(upper=0.0)
    dd_daily = np.sqrt((downside**2).sum() / len(net))
    dd_annual = dd_daily * np.sqrt(252)
    if dd_annual == 0:
        sortino = float("inf")
    else:
        ann_return_for_sortino = mean_r * 252
        sortino = ann_return_for_sortino / dd_annual

    # Max drawdown
    equity = np.exp(net.cumsum())
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    max_drawdown = drawdown.min()

    # Drawdown duration
    is_in_drawdown = drawdown < 0
    duration = 0
    max_duration = 0
    for dd_val in is_in_drawdown:
        if dd_val:
            duration += 1
            max_duration = max(max_duration, duration)
        else:
            duration = 0
    # If still in drawdown at end, count remaining bars
    max_drawdown_duration_days = max_duration

    # Win rate
    nonzero = net[net != 0]
    if len(nonzero) == 0:
        win_rate = 0.0
    else:
        win_rate = (nonzero > 0).sum() / len(nonzero)

    # Annualized return (geometric)
    annualized_return = np.exp(mean_r * 252) - 1

    # Annualized volatility
    annualized_volatility = std_r * np.sqrt(252)

    # Cost drag
    gross_total = gross.sum()
    net_total = net.sum()
    cost_drag = gross_total - net_total

    return MetricsResult(
        sharpe=float(sharpe),
        sortino=float(sortino),
        max_drawdown=float(max_drawdown),
        max_drawdown_duration_days=int(max_drawdown_duration_days),
        annualized_return=float(annualized_return),
        annualized_volatility=float(annualized_volatility),
        win_rate=float(win_rate),
        gross_return_total=float(gross_total),
        net_return_total=float(net_total),
        cost_drag=float(cost_drag),
    )
