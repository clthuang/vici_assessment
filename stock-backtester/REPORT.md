# Stock Backtester: Consulting Case Report

**Project:** Statistical Arbitrage Backtesting System
**Author:** Terry
**Date:** February 2026
**Assessment:** VICI Holdings (HFT Prop Shop) — 7-Day Challenge

---

## I. Executive Summary

### The Problem

Backtesting systems answer the wrong question. Every mainstream framework — Zipline, VectorBT, Backtrader — produces the same output: "Your strategy had a Sharpe of 1.4." This tells the quant researcher what happened. It does not tell them whether they should trade this strategy, how much capital to allocate, or under what conditions the strategy breaks.

The gap is not technical — it is conceptual. Standard backtest output treats returns as the final answer. But returns without capital allocation context are incomplete: a strategy with Sharpe 1.4 at 2x leverage has a 100% probability of ruin. The same strategy at 0.5x leverage retains 75% of its maximum growth rate while reducing ruin probability to 12.5%. This analysis is absent from every major open-source backtester.

### The Solution

A three-pillar architecture that answers the complete question:

1. **Engine** — Vectorized backtesting with architectural look-ahead prevention. A single `shift(1)` at `engine.py:21` enforces temporal correctness; a perfect-foresight strategy proves it works (AC-2).

2. **Kelly/Ruin Analysis** — Capital allocation as a first-class feature, not post-processing. The capital efficiency frontier maps the entire risk/return surface: growth rate, ruin probability, and critical fraction at every leverage level.

3. **Monte Carlo Simulation** — Synthetic price paths via Geometric Brownian Motion to stress-test strategy survival. Empirical ruin rates compared against theoretical predictions to surface model inadequacy.

### Scope Calibration

This is a daily-bar MVP with an equal-weight strategy. It is not HFT infrastructure. This is a deliberate engineering decision, not a limitation.

An HFT backtester requires order-book modeling, queue-priority simulation (FIFO vs. pro-rata, with 81-89% adverse fill rates on limit orders per arXiv:2409.12721v2), microsecond replay with realistic network topology, and typically C++/Rust with FPGA acceleration. It is a systems engineering problem requiring co-located Level 2/3 data feeds, calibration against live fills, and months of work. Building a toy version in Python for a 7-day challenge would lack credibility with a firm that runs production systems at this level.

Instead, this project demonstrates the statistical rigor and engineering design thinking that transfers to any strategy class — including HFT — at the appropriate abstraction level for a time-boxed assessment.

### Differentiator

No mainstream backtesting framework ships a capital efficiency frontier or closed-form ruin probability solver. The combination of Kelly criterion analysis, ruin probability curves, and the critical Kelly solver (the maximum fraction where ruin probability stays below a user-defined threshold) is genuinely novel as a first-class backtester feature.

### Delivery Metrics

| Metric | Value |
|--------|-------|
| Tests | 88 |
| Coverage | 93% |
| Acceptance criteria | 8 (AC-1 through AC-7 + AC-1b) |
| Review iterations | 5 (converging: 1 blocker, 0, 0, 0, APPROVED) |
| Design decisions | 7 (each documented with trade-offs) |
| Acknowledged limitations | 14 (each with mitigation + North Star resolution) |
| Specification artifacts | 5 (PRD v5, Spec v4, Design v1, Plan v2, Tasks v5) |
| Total tasks | 51 across 12 phases |

---

## II. Problem Decomposition

### Industry Failure Modes

Backtesting is one of the most dangerous tools in quantitative finance. It appears to answer questions with precision while systematically producing wrong answers. The failure modes are well-documented but rarely prevented at the architectural level.

**Look-ahead bias.** Knight Capital lost $440 million in 45 minutes (August 2012) partly due to dead code reuse that inadvertently introduced look-ahead logic. In backtesting, look-ahead manifests subtly: a strategy that uses today's closing price to decide today's position appears profitable in backtest but is physically impossible to execute. The standard mitigation — "be careful" — is a process solution to a structural problem. Our mitigation is architectural: a single `shift(1)` enforced by the engine, verified by a perfect-foresight acceptance test (AC-2) where the wrong answer is qualitatively different from the correct one.

**Overfitting and multiple testing.** Lopez de Prado demonstrates that after only 7 independent trials, the expected maximum Sharpe ratio from pure noise exceeds 1.0. The Quantopian platform (founded by Tucker Balch) saw strategies with Sharpe 7.0 in-sample that produced flat returns in production — the backtest was fitting noise, not signal. Bailey & Lopez de Prado's Deflated Sharpe Ratio (DSR) corrects for this, but requires a trial registry that most frameworks lack. We document this as L7 in our acknowledged limitations and specify the DSR formula and trial-counting rules for the North Star.

**Survivorship bias.** Free data sources like Yahoo Finance only contain stocks that currently exist. Failed companies, delisted stocks, and acquisition targets are absent. Strategies backtested on survivor-only data systematically overstate performance. Our mitigation: a non-suppressible warning on every report — "Data source: yfinance (survivorship-biased). Results may overstate performance." This is a design choice, not a limitation. The warning cannot be turned off because intellectual honesty about data quality is not optional.

**Transaction cost misestimation.** Research on limit order fills in futures (ES, NQ, CL, ZN) shows 81-89% adverse fill rates (arXiv:2409.12721v2) — the market moves against the maker immediately after fill. Naive backtests that assume 100% fill probability at the resting price flip the sign of PnL when adverse selection is properly modeled. Ernest Chan documents specific look-ahead bugs where backtests use the day's high/low for open-day signals. As QuantConnect forums advise: "slippage model should be the first lines of code you write."

### HFT vs. Daily-Bar Framing

VICI Holdings operates HFT infrastructure. The assignment says "美股回測系統" without specifying frequency. It is worth being explicit about what an HFT backtester actually requires and why it is out of scope:

| Requirement | HFT Reality | This System |
|-------------|-------------|-------------|
| Data granularity | Microsecond Level 2/3 feeds | Daily bars (OHLCV) |
| Order book | Full limit order book as stochastic process | No order book |
| Queue priority | FIFO vs. pro-rata matching simulation | Not applicable |
| Adverse selection | 81-89% adverse fills on limit orders | Linear slippage model |
| Latency modeling | Feed + order entry + response (3 components) | No latency |
| Language | C++/Rust, FPGA for feed handling | Python |
| Data cost | Tens of thousands per year (co-located feeds) | Free (yfinance) |
| Calibration | Against live fills, production order flow | Method of moments |

This table is not an apology — it is a demonstration of deep awareness. Building a toy HFT backtester in Python would be worse than not building one: it would suggest ignorance of the problem's true complexity. Instead, we play to statistical strength and demonstrate engineering design thinking at the appropriate abstraction level.

### The Real Question

The real question is not "what was my Sharpe?" but "at what leverage does this strategy survive?" A Sharpe of 1.4 means nothing without context:

- At full Kelly (f*), the strategy achieves maximum growth but has a ~50% probability of hitting a 50% drawdown.
- At half Kelly (f*/2), the strategy retains 75% of maximum growth while reducing ruin probability to 12.5%.
- At 2x Kelly, the strategy has zero expected growth and certain ruin.

This is the analysis our system provides — and no mainstream backtester ships it.

---

## III. Strategic Design Decisions

Seven decisions shape the architecture. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

### Decision 1: Daily-Bar Focus, Not HFT

**Context.** The reviewer (VICI Holdings) operates HFT systems in C++ with FPGA acceleration. The assignment does not specify frequency.

**Analysis.** An HFT backtester is a systems engineering problem requiring: (a) order book modeling as a stochastic process, (b) queue priority simulation where resting and taking orders have fundamentally different adverse selection profiles, (c) microsecond replay with 3-component latency modeling, (d) co-located Level 2/3 data costing tens of thousands per year, and (e) calibration against live fills. This cannot be credibly demonstrated in Python in 7 days.

**Decision.** Focus on daily-bar statistical arbitrage strategies where the builder's strength — statistics, not market microstructure — creates the most value.

**Trade-off.** Does not directly showcase HFT infrastructure. Compensated by demonstrating statistical sophistication that transfers to any strategy class and by explicitly documenting HFT requirements (see Section II) to prove awareness, not ignorance.

**Evidence.** The three-pillar architecture (engine + Kelly/ruin + Monte Carlo) would not exist if scope had been diluted by HFT plumbing. Every hour not spent on order book simulation went into the capital efficiency frontier instead.

### Decision 2: Vectorized with shift(1), Not Event-Driven

**Context.** Event-driven architecture is the "gold standard" for production backtesting systems.

**Analysis.** Event-driven plumbing provides two advantages: (a) structural look-ahead prevention (the loop only sees past events) and (b) mirroring live trading (the same loop drives both). Advantage (b) is irrelevant — we are not building a live trading system. Advantage (a) can be replicated with a single `shift(1)` applied once in the engine, verified by a known-answer test.

**Decision.** Vectorized engine (pandas/numpy) with engine-controlled temporal shift.

**Trade-off.** Cannot extend to tick-level. Documented as architectural boundary.

**Evidence.** Vectorized execution is 100-1000x faster than Python event-driven. AC-2 (perfect foresight test) proves correctness: a strategy that knows the future still cannot achieve perfect returns because `shift(1)` delays its signal by one day. The implementation is a single line (`engine.py:21`):

```python
shifted_weights = raw_weights.shift(1).fillna(0.0)
```

This is the only temporal alignment point in the entire system. One line to audit, one test to verify. An event-driven architecture would distribute this logic across event handlers, making it harder to verify and easier to break.

### Decision 3: Kelly/Ruin as First-Class Feature

**Context.** Most backtesting frameworks stop at Sharpe and drawdown.

**Analysis.** The reverse Kelly question — "what is the maximum safe bet?" — is directly actionable. The capital efficiency frontier communicates risk/reward in ways a single Sharpe number cannot. While the Kelly-ruin relationship is well-established in the literature (Thorp 1962/2006, Vince "Leverage Space Trading Model"), packaging it as a first-class backtester output is genuinely differentiated.

**Decision.** Kelly criterion analysis and ruin probability are core features, not optional post-processing.

**Trade-off.** Time spent on Kelly is time not spent on additional strategies. Justified as primary differentiator: equal-weight is a sufficient vehicle to demonstrate the Kelly framework, while additional strategies without Kelly analysis are commodity features available in every backtester.

**Evidence.** The critical Kelly solver has a closed-form solution (no numerical optimization needed):

```
f_critical = 2*mu / (sigma^2 * (ln(P_target)/ln(D) + 1))
```

This solver answers: "Given that I will accept at most 1% probability of a 50% drawdown, what is the maximum leverage I can use?" No mainstream backtester provides this answer.

### Decision 4: Dual Return Types — Simple for Cross-Sectional, Log for Time-Series

**Context.** Portfolio return computation requires combining returns across multiple assets (cross-sectional) and compounding returns across time (time-series).

**Analysis.** These two operations require different return types. The weighted sum of simple returns IS the portfolio simple return (exact). The weighted sum of log-returns is NOT the portfolio log-return — Jensen's inequality guarantees the error is always negative and compounds over time. Using log-returns for cross-sectional aggregation would systematically understate portfolio returns.

However, log-returns are essential for time-series operations: `exp(cumsum(log_returns))` correctly compounds to portfolio value, and log-returns are additive over time (critical for the Kelly framework).

**Decision.** Use simple returns for cross-sectional aggregation (engine Step 4), convert to log-returns for time-series operations (engine Step 5):

```python
# Step 4: R_p = sum(w_i * R_i)  [simple returns, exact]
portfolio_simple_return = (shifted_weights * simple_returns.fillna(0.0)).sum(axis=1)

# Step 5: r_p = ln(1 + R_p)    [convert to log for time-series]
portfolio_log_return = np.log(1 + portfolio_simple_return)
```

**Trade-off.** Two return types add conceptual complexity. Mitigated by clear documentation and AC-1b (a known-answer test where the wrong answer is qualitatively different: negative when correct is zero).

**Evidence.** AC-1b constructs a 2-symbol portfolio where on one day, stock A rises 5% and stock B falls 5%. The correct portfolio return (simple aggregation) is 0.0%. Log-return aggregation would give -0.125% — a negative return from a zero-return portfolio. This test catches the Jensen's inequality bug with maximum signal.

### Decision 5: ddof=0 for Kelly, ddof=1 for Sharpe

**Context.** The `ddof` parameter in standard deviation computation (population vs. sample) affects numerical results. Using the wrong convention silently corrupts calculations.

**Analysis.** Kelly and Sharpe serve different statistical purposes:

- **Kelly** (`ddof=0`, population std): The continuous Kelly formula `f* = mu/sigma^2` uses population parameters. It is an MLE estimator that computes the optimal fraction given the observed data. Using `ddof=1` would bias f* downward for small samples.

- **Sharpe** (`ddof=1`, sample std): Sharpe is an inferential statistic — we estimate the population Sharpe from a sample. The Bessel correction (`ddof=1`) provides an unbiased estimate of population variance.

**Decision.** Each convention is correct for its purpose. Both are explicitly documented and tested.

**Trade-off.** Having two conventions creates a source of confusion. Mitigated by AC-4 (Kelly analytical test) which would fail if `ddof=1` were used: the test constructs a deterministic series with exactly `mu=0.0005` and `sigma=0.01` (population std), expecting `f* = 5.0`. Any ddof mismatch between the test fixture and the estimator causes failure.

**Evidence.** The spec review (iteration 1) caught this as a blocker before any code was written. The ddof mismatch between test fixture and estimator would have been a silent runtime bug — AC-4 would have failed with no obvious explanation. Catching it during specification saved debugging time during implementation.

### Decision 6: GBM Only for MVP

**Context.** Heston stochastic volatility is the "right" model. Regime-switching is a practical middle ground. GBM is the simplest.

**Analysis.** GBM (Geometric Brownian Motion) assumes constant drift and volatility — no fat tails, no volatility clustering. These are significant limitations for real markets. However:

- GBM with method-of-moments calibration is implementable in a single day
- GBM serves a dual purpose: stress-test strategy via Monte Carlo AND verify engine via known-answer tests (AC-6: moment matching, AC-7: zero-edge Sharpe)
- Regime-switching adds 1-2 days for EM calibration and state management
- Heston adds 2+ days for 5-parameter optimization via characteristic function/FFT, with non-convex optimization and multiple local minima

**Decision.** GBM only for MVP. Regime-switching and Heston are documented in the North Star with specific implementation requirements.

**Trade-off.** Simulation underestimates tail risk. Compensated by: (a) documenting this prominently (L9), (b) comparing empirical vs. theoretical ruin to surface model inadequacy, and (c) every simulation report includes: "NOTE: GBM assumes no fat tails. Real ruin risk likely higher."

**Evidence.** AC-6 validates GBM correctness by checking that simulated log-returns match theoretical moments within 2 standard errors. AC-7 validates that zero-edge GBM produces zero expected Sharpe across 200 paths with 4 symbols. Both tests would be impossible with a more complex model where the correct answer is not analytically known.

### Decision 7: Half-Kelly Default

**Context.** Full Kelly maximizes long-run growth but has extreme variance. Practitioners universally use fractional Kelly.

**Analysis.** A common misconception is that half-Kelly retains "94% of return." This conflates expected arithmetic return with log growth rate. The correct analysis:

```
g(f*/2) = mu*(f*/2) - sigma^2*(f*/2)^2/2
        = mu^2/(2*sigma^2) - mu^2/(8*sigma^2)
        = 3*mu^2/(8*sigma^2)
        = 0.75 * mu^2/(2*sigma^2)
        = 0.75 * g(f*)
```

Half-Kelly retains **75% of maximum log growth rate**, not 94%. The 25% growth sacrifice buys dramatically lower variance and ruin probability. At 50% drawdown threshold:

| Fraction | Growth (% of max) | P(ruin) |
|----------|-------------------|---------|
| 0.25 f* | 43.8% | 0.8% |
| 0.50 f* | 75.0% | 12.5% |
| 1.00 f* | 100.0% | 50.0% |
| 1.50 f* | 75.0% | 79.4% |
| 2.00 f* | 0.0% | 100.0% |

**Decision.** Half-Kelly as default recommendation. The capital efficiency frontier shows all options.

**Trade-off.** None — this is strictly informational. The system presents the full frontier; the user decides.

**Evidence.** Note the symmetry: half-Kelly (0.50 f*) and 1.50 f* produce identical growth rates (75% of max), but ruin probabilities differ by 6x (12.5% vs. 79.4%). This asymmetry is the entire reason practitioners use fractional Kelly — and it is invisible without the capital efficiency frontier.

---

## IV. Architecture as Risk Mitigation

The architecture is not just a code organization scheme — it is a risk mitigation strategy. Each structural choice addresses a specific failure mode identified in the problem decomposition.

### Look-Ahead Prevention

**Risk.** Look-ahead bias silently inflates backtest returns. It is the most common and most dangerous backtesting bug.

**Mitigation.** A single `shift(1)` at `engine.py:21` enforces temporal alignment:

```python
shifted_weights = raw_weights.shift(1).fillna(0.0)
```

The strategy produces raw target weights (what it wants to hold tomorrow). The engine shifts them by one bar (yesterday's intention becomes today's execution). This is applied exactly once, in one place. The strategy cannot cause look-ahead because it never sees the shift — the engine owns temporal alignment.

**Verification.** AC-2 constructs a perfect-foresight strategy that knows the future. After `shift(1)`, the strategy's realized return is strictly less than the sum of all positive daily returns. If `shift(1)` were absent, the strategy would achieve perfect returns — a qualitatively different (and impossible) result.

### Cost Invariant

**Risk.** Transaction cost models with bugs can increase returns instead of reducing them — a silent corruption that makes bad strategies look good.

**Mitigation.** Costs are always non-negative and always reduce returns:

```
slippage_{t,i} = k * sigma_trailing(20) * |delta_w_{t,i}|    >= 0 always
commission_{t,i} = (commission_per_share / close_price) * |delta_w_{t,i}|  >= 0 always
net_return = gross_return - slippage - commission             <= gross always
```

**Verification.** AC-3 runs a strategy with positive slippage and asserts `net < gross` for every bar where trading occurs and `total_costs > 0`.

### Statistical Convention Rigor

**Risk.** Using the wrong ddof, the wrong return type, or the wrong warmup convention silently produces wrong numbers.

**Mitigation.** Every statistical computation has an explicit convention:

| Computation | Convention | Rationale |
|-------------|-----------|-----------|
| Kelly sigma | ddof=0 (population) | MLE estimator for continuous Kelly formula |
| Sharpe sigma | ddof=1 (sample) | Inferential statistic estimating population Sharpe |
| Cross-sectional aggregation | Simple returns | Exact for portfolio return |
| Time-series compounding | Log-returns | Additive, suitable for exp(cumsum) |
| Kelly estimation window | Post-warmup bars only | Warmup has zero position, would bias mu toward 0 |

**Verification.** AC-4 (Kelly analytical: ddof mismatch would cause failure), AC-1b (return type: Jensen's inequality would produce negative instead of zero), AC-1 (compounding: floating-point tolerance 1e-10).

### Immutability

**Risk.** Mutable state shared between modules leads to action-at-a-distance bugs — one module mutates data another module depends on.

**Mitigation.** All result types use `@dataclass(frozen=True)`. Prices are copied at module boundaries: `engine.run_backtest()` passes `{sym: df.copy() ...}` to `strategy.compute_weights()`. This is a shallow freeze (DataFrames inside frozen dataclasses are still technically mutable), but the copy-at-boundaries pattern prevents mutation bugs in practice.

---

## V. Validation Strategy

### Acceptance Criteria as Known-Answer Tests

The system has 8 acceptance criteria (AC-1 through AC-7, plus AC-1b). Each is a known-answer test where the correct answer is analytically computable and the wrong answer is qualitatively different from the correct one.

| AC | What It Tests | Expected | Wrong Answer |
|----|--------------|----------|--------------|
| AC-1 | Deterministic returns | 10.462% (1.01^10 - 1) | Any other value (off-by-one, NaN) |
| AC-1b | Multi-symbol aggregation | 0.0% on day 1 (zero portfolio return) | -0.125% (Jensen's inequality bug) |
| AC-2 | Look-ahead prevention | Return < perfect foresight | Return = perfect foresight (no shift) |
| AC-3 | Cost invariant | net < gross, costs > 0 | net >= gross (cost model bug) |
| AC-4 | Kelly analytical | f* = 5.0 | f* != 5.0 (ddof mismatch) |
| AC-5 | Frontier consistency | g(f*)=100%, g(2f*)=0%, ruin monotonic | Non-monotonic ruin, g(2f*)>0 |
| AC-6 | GBM moments | Mean within 2 SE of theory | Systematic bias (Ito correction bug) |
| AC-7 | Zero-edge Sharpe | Mean Sharpe within 2 SE of 0 | Nonzero Sharpe (phantom returns) |

### Test Design Philosophy

The key insight is that the wrong answer should be qualitatively different from the correct answer. This maximizes the signal-to-noise ratio of the test:

- **AC-1b:** If the engine incorrectly aggregates log-returns instead of simple returns, Bar 1 gives `0.5*ln(1.05) + 0.5*ln(0.95) = -0.00125` — a negative return when the true portfolio return is zero. The error is not a rounding issue; it is a conceptual bug that produces an answer of the wrong sign.

- **AC-2:** If `shift(1)` is absent, the perfect-foresight strategy achieves the sum of all positive daily returns — physically impossible in real trading. The error is not a small numerical discrepancy; it is a strategy achieving returns that violate causality.

- **AC-4:** If Kelly uses `ddof=1` instead of `ddof=0`, the alternating return series `[0.0105, -0.0095, 0.0105, ...]` gives `std(ddof=1) = 0.01005` instead of `std(ddof=0) = 0.01`, producing `f* = 4.95` instead of `5.0`. The tolerance is `1e-6`, so this fails clearly.

### Review Convergence

The system went through 5 implementation review iterations with decreasing severity:

| Iteration | Blockers | Warnings | Outcome |
|-----------|----------|----------|---------|
| 1 | (spec review) | (spec review) | Spec revised (3 blockers caught) |
| 2 | 1 | 3 | Half-Kelly scaling missing |
| 3 | 0 | 6 | Approved (warnings non-blocking) |
| 4 | 0 | 4 | Approved (4 false positives from stale cache) |
| 5 | 0 | 0 | Final approval, all issues resolved |

The convergence pattern is healthy: exactly one blocker in the first implementation review (the Monte Carlo ruin detection was not scaling returns by half-Kelly — a spec-implementation gap), zero blockers thereafter. The warnings decreased monotonically: survivorship warning text, CLI flag naming, AlwaysLongStrategy aliasing, and AC-7 parameter alignment — all addressed by iteration 5.

---

## VI. Acknowledged Limitations

Fourteen limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight. Presenting them here demonstrates intellectual honesty — the system's boundaries are known, quantified, and mapped to specific resolutions.

### Data Limitations

**L1: Survivorship Bias (yfinance)**
- **Impact:** Results overstate strategy performance. Strategies backtested on survivor-only data systematically avoid the worst outcomes (bankruptcy, delisting).
- **Current Mitigation:** Non-suppressible warning on every report. This forces every consumer to confront data quality before interpreting results.
- **North Star:** Pluggable data interface supporting CRSP (survivorship-bias-free), Parquet, CSV. Survivorship bias quantification via synthetic "delisted pair" scenarios.

**L13: No Data Caching**
- **Impact:** Repeated runs re-fetch from yfinance (slow, rate-limit risk).
- **Current Mitigation:** Acceptable for demo; yfinance rate limits are generous for single-stock daily data.
- **North Star:** Local Parquet cache keyed by (ticker, date_range). `--no-cache` flag to force refetch.

**L14: Minimal Data Validation**
- **Impact:** May miss subtle data issues (stock splits, large gaps, zero-volume days).
- **Current Mitigation:** NaN check + positive price check. Sufficient for adjusted close prices from yfinance.
- **North Star:** Full validation suite: >50% gap detection, zero-volume filtering, split adjustment verification.

### Strategy Limitations

**L2: No Pairs Trading (SMA Only)**
- **Impact:** Cannot demonstrate statistical arbitrage directly. The MVP uses equal-weight as a proof-of-concept vehicle.
- **Current Mitigation:** The architecture (target weights abstraction, `{symbol: weight}` interface, pluggable strategy base class) is designed for multi-asset stat arb from day one. Adding pairs trading requires only a new Strategy subclass, not engine changes.
- **North Star:** Pairs trading with cointegration, hedge ratio methods (OLS, Total Least Squares, Johansen procedure).

**L6: No Signal Half-Life or Factor Attribution**
- **Impact:** Cannot assess execution speed sensitivity or decompose alpha vs. beta.
- **Current Mitigation:** Not applicable for equal-weight strategy.
- **North Star:** Signal decay at shift(0..3), SPY regression for alpha/beta/R^2.

### Statistical Limitations

**L3: No Bootstrap CI on Kelly**
- **Impact:** Cannot quantify f* estimation uncertainty. Kelly fraction `f* = mu/sigma^2` is extremely sensitive to mu estimation — a factor-of-two error in mu doubles f*.
- **Current Mitigation:** Capital efficiency frontier shows consequences of over-betting. Half-Kelly as default provides buffer.
- **North Star:** Bootstrap CI (1,000 resamples) showing how sensitive Kelly is to mu estimation error.

**L4: No Walk-Forward Validation**
- **Impact:** Cannot detect overfitting or out-of-sample degradation.
- **Current Mitigation:** Known-answer tests prove engine correctness; Kelly analysis provides capital allocation guardrails.
- **North Star:** Rolling/anchored walk-forward with OOS degradation ratio.

**L7: No DSR or Trial Registry**
- **Impact:** Cannot correct for multiple testing bias. After only 7 trials, expect Sharpe > 1 from noise (Lopez de Prado).
- **Current Mitigation:** Documented awareness of the problem. The DSR formula and trial-counting rules are specified in the PRD for the North Star.
- **North Star:** Append-only trial log, DSR with V[SR-hat] (Bailey & Lopez de Prado 2014).

### Model Limitations

**L9: GBM Only (No Fat Tails, No Volatility Clustering)**
- **Impact:** Simulation underestimates tail risk. Real markets exhibit volatility clustering (GARCH), regime switching, and fat tails — all absent from GBM.
- **Current Mitigation:** Every simulation report notes "GBM assumes no fat tails. Real ruin risk likely higher." Empirical vs. theoretical ruin comparison surfaces model inadequacy.
- **North Star:** Regime-switching (2-state Markov with EM calibration), GARCH(1,1), Heston stochastic volatility, Merton Jump Diffusion.

**L10: Linear Slippage (No Order-Size Impact)**
- **Impact:** Underestimates costs for large positions. Slippage = k * sigma only; no square-root impact.
- **Current Mitigation:** At daily-bar scale with typical portfolio sizes, order-size impact is negligible. Configurable k allows pessimistic testing (k=2.0 simulates 4x normal slippage).
- **North Star:** Square-root impact model (Almgren-Chriss): Impact = sigma * sqrt(Q/V), verified across 8M institutional trades.

### Scope Limitations

**L5: No Regime-Switching Simulation**
- **Impact:** Cannot stress-test strategy across market regimes (bull, bear, crisis).
- **North Star:** 2-state Markov with EM calibration, regime-conditional Kelly.

**L8: No Turnover Reporting**
- **Impact:** Cannot assess friction drag at scale.
- **North Star:** Annualized turnover + turnover-adjusted return.

**L11: No Multi-Strategy Kelly**
- **Impact:** Cannot optimize across correlated strategies.
- **North Star:** Portfolio-level Kelly with correlation-aware sizing.

**L12: No Structural Break Detection**
- **Impact:** Cannot detect regime changes in historical data.
- **North Star:** CUSUM, Bai-Perron non-parametric tests.

---

## VII. Mathematical Foundation

### Kelly Criterion (Continuous Gaussian Approximation)

The Kelly criterion maximizes E[log(1 + f*r)]. For small returns (daily regime), the Taylor expansion yields:

**Growth rate as a function of fraction f:**

```
g(f) = mu*f - (sigma^2 * f^2) / 2
```

where mu = expected daily return, sigma = daily return standard deviation.

**Optimal (full Kelly) fraction** — set dg/df = 0:

```
f* = mu / sigma^2
```

**Growth rate at maximum:**

```
g(f*) = mu^2 / (2 * sigma^2)
```

**Growth rate as fraction of maximum (parametrized by alpha = f/f*):**

```
g(alpha * f*) / g(f*) = 2*alpha - alpha^2
```

This yields the capital efficiency frontier:

| alpha | Growth (% of max) |
|-------|-------------------|
| 0.25 | 43.75% |
| 0.50 | 75.00% |
| 0.75 | 93.75% |
| 1.00 | 100.00% |
| 1.50 | 75.00% |
| 2.00 | 0.00% |

### Half-Kelly Derivation

The commonly cited "half-Kelly retains 94% of return" is incorrect. The 94% figure refers to expected arithmetic return, not log growth rate. The correct calculation:

```
g(f*/2) / g(f*) = (2 * 0.5 - 0.5^2) / 1.0 = (1.0 - 0.25) / 1.0 = 0.75
```

**Half-Kelly retains 75% of maximum log growth rate.** Log growth rate, not arithmetic return, governs long-run compounding and ruin probability. This is the quantity that matters for capital allocation decisions.

### Ruin Probability

For a strategy with growth rate g(f) and portfolio volatility sigma_p = sigma*f, the probability of hitting drawdown D before any target profit is:

```
P(ruin | f, D) = D^(2*mu/(sigma^2*f) - 1)
```

The exponent simplifies using alpha = f/f*:

```
2*mu/(sigma^2*f) - 1 = 2/alpha - 1
```

So:

```
P(ruin | alpha, D) = D^(2/alpha - 1)
```

**Domain guards:**
- At alpha >= 2.0 (f >= 2f*): growth rate is zero or negative. Ruin probability = 1.0 (certain ruin).
- At alpha = 0: no position, no ruin. P = 0.0.
- At alpha = 1.0 (full Kelly): P = D. For D = 0.50, ruin probability is 50%.

### Critical Kelly Solver (Closed-Form)

Given target ruin probability P_target and drawdown level D, solve for the maximum safe fraction:

```
P_target = D^(2*mu/(sigma^2*f) - 1)

ln(P_target) = (2*mu/(sigma^2*f) - 1) * ln(D)

f_critical = 2*mu / (sigma^2 * (ln(P_target)/ln(D) + 1))
```

This has a closed-form solution — no numerical optimization required. The implementation verifies the solution by plugging f_critical back into the ruin formula and checking `P(ruin | f_critical, D) ≈ P_target`.

**Validity check:** If f_critical >= 2*f*, the requested ruin tolerance cannot be achieved. The system reports "no safe fraction exists" rather than returning a meaningless value.

### Slippage Model

```
slippage_per_side = k * sigma_trailing(20) * |delta_w|
```

All terms are dimensionless:
- k: slippage multiplier (default 0.5)
- sigma_trailing(20): std of 20 most recent daily log-returns (dimensionless)
- |delta_w|: absolute weight change (dimensionless)

The product represents a fractional cost on the same scale as log-returns, making it valid for direct subtraction: `net = gross - slippage`.

**Commission model** with dimensional analysis:

```
commission_rate = commission_per_share / close_price
                = ($/share) / ($/share) = dimensionless

commission = commission_rate * |delta_w|
```

---

## VIII. Process and Delivery Metrics

### Five-Stage Specification Pipeline

The system was built through a rigorous 5-stage specification pipeline. Each stage produced a versioned artifact with formal review.

| Stage | Artifact | Version | Key Output |
|-------|----------|---------|------------|
| Brainstorm/PRD | `prd.md` | v5 | 7 design decisions, 14 limitations, 7 ACs, North Star roadmap |
| Specification | `spec.md` | v4 | 9 module interfaces, 8 ACs (added AC-1b), data contracts, error taxonomy |
| Design | `design.md` | v1 | Architecture diagrams, interface contracts, 10 correctness invariants |
| Plan | `plan.md` | v2 | 12-phase build order, AC readiness map, TDD enforcement |
| Tasks | `tasks.md` | v5 | 51 tasks, 4 parallel groups, dependency graph |

### Front-Loaded Specification

The most important process insight: **front-loaded specification enabled approximately 3 hours of actual coding.** The spec review (iteration 1) caught 3 blockers before implementation began:

1. **Jensen's inequality** — The spec originally used log-return aggregation for portfolio returns. The reviewer identified that `ln(sum(w_i * exp(r_i))) != sum(w_i * r_i)` — a mathematical error that would have produced systematically wrong results. AC-1b was added specifically to catch this.

2. **ddof mismatch** — Kelly estimation used `ddof=0` (correct) but the test fixture implicitly assumed `ddof=1` (pandas default). The mismatch would have caused AC-4 to fail with no obvious explanation.

3. **Commission dimensional error** — The original formula `commission_per_share * |delta_w| * close_price` has units of `($/share) * dimensionless * ($/share) = $/share^2` — dimensionally incorrect. The fix: `commission_rate = commission_per_share / close_price` (dimensionless).

All three bugs would have been silent runtime errors — the system would produce wrong numbers without crashing. Catching them during specification saved hours of debugging during implementation.

### Plan Review Catches

The plan review (iteration 1) caught 3 additional issues:

1. **yfinance breaking change** — `multi_level_index=True` default in yfinance >= 0.2.51 breaks column normalization. Adding `multi_level_index=False` prevented a runtime failure.

2. **TDD ordering violation** — Phases 6-10 had implementation before tests. Forced to RED-GREEN-REGRESSION pattern.

3. **Phase 8 dependency error** — The dependency list was incomplete, which would have caused import errors.

### Task Review Convergence

The task breakdown required 5 review iterations (10 total reviews across task-reviewer and phase-reviewer). Issues caught:

- Missing pre-computed expected values in test descriptions
- Ambiguous function signatures (config object vs. explicit params)
- Off-by-one errors in drawdown duration counting
- AC-1b approximate expected value (0.0501) corrected to exact (20/399 ≈ 0.050125)

The convergence pattern: v1 had 7 warnings, v2 had 5, v3 had 6, v4 had 5, v5 had 0. The decreasing trajectory (with some noise from newly surfaced issues) indicates healthy convergence.

### Patterns Worth Documenting

These patterns emerged during the process and proved valuable:

1. **Spec every formula with units, ddof, and edge cases.** The commission dimensional error and ddof mismatch were both caught by requiring explicit dimensional analysis and ddof specification in the spec. Without this discipline, both would have been silent bugs.

2. **Design ACs where the wrong answer is qualitatively different from the correct one.** AC-1b produces a negative number when the correct answer is zero. AC-2 produces physically impossible returns when the bug is present. This maximizes bug detection signal — the test does not merely check a number within tolerance; it checks whether the answer makes physical sense.

3. **Single temporal alignment point.** Shift is applied once, in the engine, at one line. This prevents distributed look-ahead bugs and makes verification possible with a single test (AC-2).

4. **Frozen dataclasses + copy-at-boundaries.** Pragmatic Python immutability without deep copies. The dataclass itself is immutable; contained DataFrames are protected by explicit `.copy()` calls at module boundaries.

5. **Phase-level regression.** Every phase runs the full test suite after GREEN, catching cross-module breakage immediately rather than at integration time.

6. **AC readiness map.** The plan tracks when each acceptance criterion becomes testable (which phases must complete first). This prevents writing AC tests before their dependencies exist.

### Anti-Patterns to Avoid

1. **Implementing from memory instead of reading the spec.** Root cause of the half-Kelly scaling bug (iteration 2 blocker), AC-7 parameter drift, and survivorship warning text mismatch. The spec is the source of truth; the implementation is a transcription.

2. **DRY across semantic boundaries.** AlwaysLongStrategy was initially an alias for EqualWeightStrategy. While they are functionally identical (both return 1/N weights), they serve different semantic roles: "equal-weight" is user-facing, "always-long" is test-fixture-facing. The spec requires them as separate classes. DRY is a code organization principle, not a semantic one.

3. **Relaxing test parameters for stability.** AC-7 was initially implemented with 100 paths/3*SE instead of the spec's 200 paths/2*SE. Weakening test criteria without spec approval undermines the validation strategy.

4. **Accepting documentation drift.** After implementation changed `run_backtest` from 5 parameters to 3, the spec and design still referenced the 5-parameter signature. Either fix the docs or fix the code — never neither.

---

## IX. North Star Roadmap

The North Star represents where the system goes next. Each extension is mapped to a specific limitation it resolves and, where applicable, a research citation.

### Tier 1: Highest ROI

These extensions provide the most value relative to implementation effort.

**Bootstrap CI on Kelly (resolves L3)**
- **What:** 1,000 bootstrap resamples of the return series, computing f* for each resample to produce a confidence interval on the Kelly fraction.
- **Why:** f* = mu/sigma^2 is extremely sensitive to mu. A factor-of-two error in mu estimation (well within normal uncertainty for daily returns) doubles f*. Without CI, the point estimate of f* is unreliable for capital allocation decisions.
- **Effort:** 1 day. Self-contained module, no architectural changes.
- **Reference:** Thorp (2006), Section 9.4 (parameter uncertainty in Kelly).

**Walk-Forward Validation (resolves L4)**
- **What:** Rolling and anchored window variants with explicit stride. Train on window [t, t+W], test on [t+W, t+W+S], advance by stride S.
- **Why:** Detects overfitting by measuring out-of-sample degradation. Reports the distribution of OOS/IS Sharpe ratios.
- **Effort:** 2 days. Requires windowed backtest loop + metrics aggregation.
- **Reference:** Lopez de Prado (2018), Chapter 12 (Backtesting through Cross-Validation).

**Trial Registry + DSR (resolves L7)**
- **What:** Append-only trial log (JSON) storing parameters, metrics, and timestamp for every backtest run. DSR computation using V[SR-hat] formula (depends on skewness and kurtosis).
- **Why:** After only 7 trials, expect Sharpe > 1 from noise. Without correction, any "discovered" strategy is likely spurious.
- **Effort:** 2 days. Stateful JSON, V[SR-hat] formula, SR_0 computation.
- **Reference:** Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio," Eq. 3.

### Tier 2: Medium ROI

**Regime-Switching Simulation (resolves L5, L9)**
- **What:** 2-state Markov model (bull/bear) with distinct (mu, sigma) per state and stochastic transitions. EM calibration from historical data.
- **Why:** Markets exhibit regime behavior. GBM with constant parameters underestimates tail risk during regime transitions.
- **Effort:** 2-3 days. EM calibration, state management, regime-conditional Kelly.
- **Reference:** Hamilton (1989), "A New Approach to the Economic Analysis of Nonstationary Time Series."

**Square-Root Impact Model (resolves L10)**
- **What:** Impact = sigma * sqrt(Q/V) following Almgren-Chriss. Replaces linear slippage model.
- **Why:** Linear slippage understates costs for large positions. The square-root law has been verified across 8M institutional trades.
- **Effort:** 1 day. Drop-in replacement for slippage calculation in execution.py.
- **Reference:** Almgren & Chriss (2001), "Optimal Execution of Portfolio Transactions."

**Signal Half-Life (resolves L6)**
- **What:** Strategy PnL at shift(0), shift(1), shift(2), ... to quantify signal decay.
- **Why:** If shift(1) PnL < 50% of shift(0), the signal decays too rapidly for daily execution.
- **Effort:** 0.5 day. Parameterized shift in engine, metrics comparison.

### Tier 3: Long-Term

**Data Caching (resolves L13)**
- Local Parquet cache keyed by (ticker, date_range). `--no-cache` flag for refetch.

**Correlation Structure (resolves L11)**
- Factor model or copula for correlated multi-asset simulation. Enables portfolio-level Kelly with diversification benefit.

**Structural Break Tests (resolves L12)**
- CUSUM, Bai-Perron for non-parametric regime change detection without specifying number of regimes ex ante.

**Pairs Trading Strategy (resolves L2)**
- Cointegration-based pairs trading with Engle-Granger two-step (ADF on residuals), hedge ratio methods (OLS, Total Least Squares, Johansen procedure).
- Architecture is ready: adding a new strategy requires only implementing the `Strategy` base class with `compute_weights()`.

---

## X. Conclusion

### What Was Demonstrated

This project is an exercise in engineering design thinking applied to quantitative finance. The goal was never to build the most feature-rich backtester — it was to build the most thoughtful one.

**Statistical rigor.** Every formula has explicit units, ddof conventions, and edge cases. The commission dimensional error, Kelly ddof mismatch, and Jensen's inequality bug were all caught during specification — before a single line of code was written. The system uses dual return types (simple for cross-sectional, log for time-series) because mathematical correctness demands it, not because it is convenient.

**Validation discipline.** Eight acceptance criteria, each designed so the wrong answer is qualitatively different from the correct one. A negative number when zero is expected (AC-1b). Physically impossible returns when look-ahead prevention fails (AC-2). A ddof-sensitive number that breaks cleanly on mismatch (AC-4). These are not regression tests — they are proofs of correctness.

**Architectural prevention over process discipline.** Look-ahead bias is prevented by a single `shift(1)` at `engine.py:21`, not by asking strategy developers to be careful. The cost invariant (net <= gross) is guaranteed by the execution model's structure, not by code review. Survivorship warnings are non-suppressible by design, not by convention.

**Intellectual honesty.** Fourteen acknowledged limitations, each with impact assessment, current mitigation, and North Star resolution. The system does not pretend to solve problems it does not solve. GBM limitations are stated on every simulation report. Data quality warnings cannot be turned off. The capital efficiency frontier shows certain ruin at 2x Kelly — the system does not hide inconvenient truths.

### The System Answers the Right Question

Most backtesting tools answer: "Your strategy had a Sharpe of 1.4."

This system answers: "Your strategy had a Sharpe of 1.4. At half-Kelly sizing, your ruin probability is 12.5% at 50% drawdown. The capital efficiency frontier shows you retain 75% of maximum growth at half the risk. The critical Kelly fraction for 1% ruin probability is 0.42x. Data source is survivorship-biased — treat results with skepticism."

The second answer is useful. The first is not.

### Nothing Accidental

Every decision in this system is documented with its trade-off:

- Daily-bar focus trades HFT relevance for statistical depth.
- Vectorized engine trades tick-level extensibility for 100-1000x speed and auditability.
- Kelly as first-class feature trades strategy breadth for analytical uniqueness.
- GBM-only simulation trades model fidelity for dual-purpose verification.
- Half-Kelly default corrects a common misconception (75%, not 94%).
- Dual ddof conventions (0 for Kelly, 1 for Sharpe) are each correct for their purpose.
- 14 acknowledged limitations demonstrate awareness, not apology.

The depth of thought is the deliverable. The code is the proof.

---

## References

1. Bailey, D.H. & Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." *Journal of Portfolio Management*, 40(5), 94-107.

2. Bailey, D.H., Borwein, J.M., Lopez de Prado, M. & Zhu, Q.J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." *Notices of the AMS*, 61(5), 458-471.

3. Harvey, C.R., Liu, Y. & Zhu, H. (2016). "...and the Cross-Section of Expected Returns." *Review of Financial Studies*, 29(1), 5-68.

4. Thorp, E.O. (2006). "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market." In *Handbook of Asset and Liability Management*, Volume 1, Chapter 9.

5. Maier-Paape, S. (2015). "Correctness of Backtest Engines." arXiv:1509.08248.

6. Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.

7. Karatzas, I. & Shreve, S.E. (1991). *Brownian Motion and Stochastic Calculus*, 2nd ed. Springer.

8. Almgren, R. & Chriss, N. (2001). "Optimal Execution of Portfolio Transactions." *Journal of Risk*, 3(2), 5-39.

9. arXiv:2409.12721v2. Adverse selection in limit order fills (81-89% adverse fill rates in ES, NQ, CL, ZN futures).

10. DeMiguel, V., Garlappi, L. & Uppal, R. (2009). "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?" *Review of Financial Studies*, 22(5), 1915-1953.

---

## Appendix: Artifact Registry

| Artifact | Path | Version |
|----------|------|---------|
| PRD | `docs/brainstorms/2026-02-07-stat-arb-backtester.prd.md` | v5 |
| Specification | `docs/features/001-stat-arb-backtester/spec.md` | v4 |
| Design | `docs/features/001-stat-arb-backtester/design.md` | v1 |
| Plan | `docs/features/001-stat-arb-backtester/plan.md` | v2 |
| Tasks | `docs/features/001-stat-arb-backtester/tasks.md` | v5 |
| Retrospective | `docs/features/001-stat-arb-backtester/retro.md` | - |
| Review History | `docs/features/001-stat-arb-backtester/.review-history.md` | - |
| Source Code | `src/stock_backtester/*.py` | 9 modules + types |
| Tests | `tests/` | 88 tests, 93% coverage |
