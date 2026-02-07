import math

import pandas as pd

from stock_backtester.types import FrontierRow, KellyResult


class KellyError(Exception):
    pass


def ruin_probability(f: float, f_star: float, d: float) -> float:
    if f <= 0:
        return 0.0
    alpha = f / f_star
    if alpha >= 2.0:
        return 1.0
    return d ** (2.0 / alpha - 1.0)


def growth_rate_fraction(alpha: float) -> float:
    return 2.0 * alpha - alpha**2


def critical_kelly_fraction(
    mu: float,
    sigma: float,
    ruin_threshold: float,
    drawdown_level: float,
) -> float | None:
    if mu <= 0:
        return None
    f_star = mu / sigma**2
    ln_p = math.log(ruin_threshold)
    ln_d = math.log(drawdown_level)
    f_crit = 2 * mu / (sigma**2 * (ln_p / ln_d + 1))
    if f_crit >= 2 * f_star:
        return None
    return f_crit


def compute_kelly(
    net_returns: pd.Series,  # type: ignore[type-arg]
    warmup_end_idx: int,
    ruin_threshold: float = 0.01,
    drawdown_level: float = 0.50,
) -> KellyResult:
    rets = net_returns.iloc[warmup_end_idx:]
    if len(rets) < 30:
        raise KellyError(
            "Insufficient data for Kelly estimation. Need >= 30 active trading bars"
        )

    mu_daily = float(rets.mean())
    sigma_daily = float(rets.std(ddof=0))

    if sigma_daily == 0:
        f_star = 0.0
    else:
        f_star = mu_daily / sigma_daily**2

    half_kelly = f_star / 2.0

    if f_star <= 0:
        return KellyResult(
            mu_daily=mu_daily,
            sigma_daily=sigma_daily,
            full_kelly=f_star,
            half_kelly=half_kelly,
            critical_kelly=None,
            frontier=[],
            ruin_threshold=ruin_threshold,
            drawdown_level=drawdown_level,
        )

    crit = critical_kelly_fraction(
        mu_daily, sigma_daily, ruin_threshold, drawdown_level
    )

    frontier = []
    for alpha in [0.25, 0.50, 0.75, 1.00, 1.50, 2.00]:
        f = alpha * f_star
        g = growth_rate_fraction(alpha) * 100
        r = ruin_probability(f, f_star, drawdown_level)
        label = f"{alpha:.2f} f*"
        frontier.append(
            FrontierRow(
                fraction_label=label,
                fraction_of_fstar=alpha,
                growth_pct_of_max=g,
                ruin_probability=r,
            )
        )

    return KellyResult(
        mu_daily=mu_daily,
        sigma_daily=sigma_daily,
        full_kelly=f_star,
        half_kelly=half_kelly,
        critical_kelly=crit,
        frontier=frontier,
        ruin_threshold=ruin_threshold,
        drawdown_level=drawdown_level,
    )
