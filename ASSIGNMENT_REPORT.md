# VICI Holdings — Claude Code 7-Day Challenge: Assignment Report

**Author:** Terry
**Date:** February 2026
**Assessment:** VICI Holdings (HFT Prop Shop) — 7-Day Challenge

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Task 1: Stock Backtester — Simple](#task-1-stock-backtester) — Vectorized backtesting with Kelly criterion and Monte Carlo simulation
- [Task 2: Claude-DA LiteLLM Provider — Medium](#task-2-claude-da-litellm-provider) — Claude Agent SDK wrapped as OpenAI-compatible data analysis endpoint
- [Task 3: GitHub CI/CD Guardian — Medium](#task-3-github-cicd-guardian) — Claude Code skill plugin for pipeline diagnosis and security audit
- [Task 4: SubTerminator — Hard](#task-4-subterminator) — AI-orchestrated browser automation for subscription cancellation

---

## Executive Summary

### Overview

All four tasks in the VICI 7-Day Challenge have been completed. Each project was built through a structured specification pipeline (PRD, Spec, Design, Plan, Tasks) with formal review at every stage. The projects span four distinct engineering domains — quantitative finance, systems integration, prompt engineering, and AI browser orchestration — but share common themes: engineering design thinking, safety-first architecture, review-driven development, and honest limitation disclosure.

### Per-Project Summary

**Task 1: Stock Backtester (Simple).** The problem: mainstream backtesting frameworks answer the wrong question — "what was my Sharpe?" instead of "at what leverage does this strategy survive?" The solution: a three-pillar architecture (vectorized engine + Kelly/ruin analysis + Monte Carlo simulation) that produces a capital efficiency frontier mapping growth rate, ruin probability, and critical fraction at every leverage level. No mainstream backtester ships this. 88 tests, 93% coverage, 8 acceptance criteria each designed so the wrong answer is qualitatively different from the correct one.

**Task 2: Claude-DA LiteLLM Provider (Medium).** The problem: data analysis requires SQL fluency, creating bottlenecks between stakeholders and analysts. The solution: a LiteLLM custom provider wrapping the Claude Agent SDK behind an OpenAI-compatible API, with MCP SQLite for database access. Three-layer read-only safety (tool allowlist, tool blocklist, filesystem permissions) ensures the agent cannot write to the database. 152 tests, 41/41 tasks completed, 10 review blockers caught before they became runtime failures.

**Task 3: GitHub CI/CD Guardian (Medium).** The problem: AI agents modify CI/CD config in only 3.25% of file changes, yet pipeline failures remain the top bottleneck after code generation. The solution: a Claude Code skill plugin — 238 lines of structured markdown, not code — providing pipeline failure diagnosis (6 categories) and security audit (8 anti-patterns). 67 automated validation checks, 100% passing. Demonstrates that prompt engineering is software engineering.

**Task 4: SubTerminator (Hard).** The problem: subscription services weaponize UX friction against cancellation; every production cancellation service uses human operators. The solution: LLM-driven browser orchestration via Playwright MCP, with predicate-based service configs and mandatory human checkpoints for irreversible actions. Mock-first architecture enabled 337 tests and 89% coverage instead of 1-2 cautious attempts against real Netflix. Four architectural pivots documented with evidence.

### Cross-Cutting Themes

1. **Engineering design thinking over flashiness.** Every project prioritizes depth of thought over feature count. The stock backtester has one strategy (equal-weight) but a complete capital efficiency frontier. SubTerminator supports one service (Netflix) but has a fully extensible predicate-based config system.

2. **Safety as architecture, not afterthought.** Look-ahead prevention via a single `shift(1)` (stock backtester). Three-layer read-only enforcement (Claude-DA). Behavioral triaging contracts (CI/CD Guardian). Human checkpoints evaluated before every tool execution (SubTerminator). Safety is structural in every project.

3. **Review-driven development.** Front-loaded specification caught critical bugs before implementation: Jensen's inequality error, ddof mismatch, commission dimensional error (stock backtester); wrong SDK package name, permission mode hang (Claude-DA); plugin.json location, frontmatter format (CI/CD Guardian). Review is cheaper than debugging.

4. **Honest limitations.** 14 limitations (stock backtester) + 8 (Claude-DA) + 6 (CI/CD Guardian) + 10 (SubTerminator) = 38 acknowledged limitations across all projects, each with impact assessment, current mitigation, and North Star resolution.

### Consolidated Delivery Metrics

| Metric | Stock Backtester | Claude-DA | CI/CD Guardian | SubTerminator | Total |
|--------|-----------------|-----------|----------------|---------------|-------|
| Tests | 88 | 152 | 67 (validation) | 337 | 644 |
| Coverage | 93% | — | 100% (checks) | 89% | — |
| Tasks completed | 51 | 41 | 10 | ~15 | ~117 |
| Review iterations | 5 | 7 | 6 | — | ~18 |
| Blockers caught | 3 (spec) | 10 | — | — | 13+ |
| Acknowledged limitations | 14 | 8 | 6 | 10 | 38 |
| Specification artifacts | 5 | 5 | 5+ | 5 | 20+ |
| Design decisions documented | 7 | 7 | 7 | 7 | 28 |

---

## Task 1: Stock Backtester

**Difficulty:** Simple
**Challenge prompt:** 美股回測系統 (US Stock Backtesting System)
**Project directory:** `stock-backtester/`
**Detailed report:** [`stock-backtester/REPORT.md`](stock-backtester/REPORT.md)

---

### I. Executive Summary

#### The Problem

Backtesting systems answer the wrong question. Every mainstream framework — Zipline, VectorBT, Backtrader — produces the same output: "Your strategy had a Sharpe of 1.4." This tells the quant researcher what happened. It does not tell them whether they should trade this strategy, how much capital to allocate, or under what conditions the strategy breaks.

The gap is not technical — it is conceptual. Standard backtest output treats returns as the final answer. But returns without capital allocation context are incomplete: a strategy with Sharpe 1.4 at 2x leverage has a 100% probability of ruin. The same strategy at 0.5x leverage retains 75% of its maximum growth rate while reducing ruin probability to 12.5%. This analysis is absent from every major open-source backtester.

#### The Solution

A three-pillar architecture that answers the complete question:

1. **Engine** — Vectorized backtesting with architectural look-ahead prevention. A single `shift(1)` at `engine.py:21` enforces temporal correctness; a perfect-foresight strategy proves it works (AC-2).

2. **Kelly/Ruin Analysis** — Capital allocation as a first-class feature, not post-processing. The capital efficiency frontier maps the entire risk/return surface: growth rate, ruin probability, and critical fraction at every leverage level.

3. **Monte Carlo Simulation** — Synthetic price paths via Geometric Brownian Motion to stress-test strategy survival. Empirical ruin rates compared against theoretical predictions to surface model inadequacy.

#### Scope Calibration

This is a daily-bar MVP with an equal-weight strategy. It is not HFT infrastructure. This is a deliberate engineering decision, not a limitation.

An HFT backtester requires order-book modeling, queue-priority simulation (FIFO vs. pro-rata, with 81-89% adverse fill rates on limit orders per arXiv:2409.12721v2), microsecond replay with realistic network topology, and typically C++/Rust with FPGA acceleration. It is a systems engineering problem requiring co-located Level 2/3 data feeds, calibration against live fills, and months of work. Building a toy version in Python for a 7-day challenge would lack credibility with a firm that runs production systems at this level.

Instead, this project demonstrates the statistical rigor and engineering design thinking that transfers to any strategy class — including HFT — at the appropriate abstraction level for a time-boxed assessment.

#### Differentiator

No mainstream backtesting framework ships a capital efficiency frontier or closed-form ruin probability solver. The combination of Kelly criterion analysis, ruin probability curves, and the critical Kelly solver (the maximum fraction where ruin probability stays below a user-defined threshold) is genuinely novel as a first-class backtester feature.

#### Delivery Metrics

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

### II. Problem Decomposition

#### Industry Failure Modes

Backtesting is one of the most dangerous tools in quantitative finance. It appears to answer questions with precision while systematically producing wrong answers. The failure modes are well-documented but rarely prevented at the architectural level.

**Look-ahead bias.** Knight Capital lost $440 million in 45 minutes (August 2012) partly due to dead code reuse that inadvertently introduced look-ahead logic. In backtesting, look-ahead manifests subtly: a strategy that uses today's closing price to decide today's position appears profitable in backtest but is physically impossible to execute. The standard mitigation — "be careful" — is a process solution to a structural problem. Our mitigation is architectural: a single `shift(1)` enforced by the engine, verified by a perfect-foresight acceptance test (AC-2) where the wrong answer is qualitatively different from the correct one.

**Overfitting and multiple testing.** Lopez de Prado demonstrates that after only 7 independent trials, the expected maximum Sharpe ratio from pure noise exceeds 1.0. The Quantopian platform (founded by Tucker Balch) saw strategies with Sharpe 7.0 in-sample that produced flat returns in production — the backtest was fitting noise, not signal. Bailey & Lopez de Prado's Deflated Sharpe Ratio (DSR) corrects for this, but requires a trial registry that most frameworks lack. We document this as L7 in our acknowledged limitations and specify the DSR formula and trial-counting rules for the North Star.

**Survivorship bias.** Free data sources like Yahoo Finance only contain stocks that currently exist. Failed companies, delisted stocks, and acquisition targets are absent. Strategies backtested on survivor-only data systematically overstate performance. Our mitigation: a non-suppressible warning on every report — "Data source: yfinance (survivorship-biased). Results may overstate performance." This is a design choice, not a limitation. The warning cannot be turned off because intellectual honesty about data quality is not optional.

**Transaction cost misestimation.** Research on limit order fills in futures (ES, NQ, CL, ZN) shows 81-89% adverse fill rates (arXiv:2409.12721v2) — the market moves against the maker immediately after fill. Naive backtests that assume 100% fill probability at the resting price flip the sign of PnL when adverse selection is properly modeled. Ernest Chan documents specific look-ahead bugs where backtests use the day's high/low for open-day signals. As QuantConnect forums advise: "slippage model should be the first lines of code you write."

#### HFT vs. Daily-Bar Framing

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

#### The Real Question

The real question is not "what was my Sharpe?" but "at what leverage does this strategy survive?" A Sharpe of 1.4 means nothing without context:

- At full Kelly (f*), the strategy achieves maximum growth but has a ~50% probability of hitting a 50% drawdown.
- At half Kelly (f*/2), the strategy retains 75% of maximum growth while reducing ruin probability to 12.5%.
- At 2x Kelly, the strategy has zero expected growth and certain ruin.

This is the analysis our system provides — and no mainstream backtester ships it.

---

### III. Strategic Design Decisions

Seven decisions shape the architecture. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

#### Decision 1: Daily-Bar Focus, Not HFT

**Context.** The reviewer (VICI Holdings) operates HFT systems in C++ with FPGA acceleration. The assignment does not specify frequency.

**Analysis.** An HFT backtester is a systems engineering problem requiring: (a) order book modeling as a stochastic process, (b) queue priority simulation where resting and taking orders have fundamentally different adverse selection profiles, (c) microsecond replay with 3-component latency modeling, (d) co-located Level 2/3 data costing tens of thousands per year, and (e) calibration against live fills. This cannot be credibly demonstrated in Python in 7 days.

**Decision.** Focus on daily-bar statistical arbitrage strategies where the builder's strength — statistics, not market microstructure — creates the most value.

**Trade-off.** Does not directly showcase HFT infrastructure. Compensated by demonstrating statistical sophistication that transfers to any strategy class and by explicitly documenting HFT requirements (see Section II) to prove awareness, not ignorance.

**Evidence.** The three-pillar architecture (engine + Kelly/ruin + Monte Carlo) would not exist if scope had been diluted by HFT plumbing. Every hour not spent on order book simulation went into the capital efficiency frontier instead.

#### Decision 2: Vectorized with shift(1), Not Event-Driven

**Context.** Event-driven architecture is the "gold standard" for production backtesting systems.

**Analysis.** Event-driven plumbing provides two advantages: (a) structural look-ahead prevention (the loop only sees past events) and (b) mirroring live trading (the same loop drives both). Advantage (b) is irrelevant — we are not building a live trading system. Advantage (a) can be replicated with a single `shift(1)` applied once in the engine, verified by a known-answer test.

**Decision.** Vectorized engine (pandas/numpy) with engine-controlled temporal shift.

**Trade-off.** Cannot extend to tick-level. Documented as architectural boundary.

**Evidence.** Vectorized execution is 100-1000x faster than Python event-driven. AC-2 (perfect foresight test) proves correctness: a strategy that knows the future still cannot achieve perfect returns because `shift(1)` delays its signal by one day. The implementation is a single line (`engine.py:21`):

```python
shifted_weights = raw_weights.shift(1).fillna(0.0)
```

This is the only temporal alignment point in the entire system. One line to audit, one test to verify. An event-driven architecture would distribute this logic across event handlers, making it harder to verify and easier to break.

#### Decision 3: Kelly/Ruin as First-Class Feature

**Context.** Most backtesting frameworks stop at Sharpe and drawdown.

**Analysis.** The reverse Kelly question — "what is the maximum safe bet?" — is directly actionable. The capital efficiency frontier communicates risk/reward in ways a single Sharpe number cannot. While the Kelly-ruin relationship is well-established in the literature (Thorp 1962/2006, Vince "Leverage Space Trading Model"), packaging it as a first-class backtester output is genuinely differentiated.

**Decision.** Kelly criterion analysis and ruin probability are core features, not optional post-processing.

**Trade-off.** Time spent on Kelly is time not spent on additional strategies. Justified as primary differentiator: equal-weight is a sufficient vehicle to demonstrate the Kelly framework, while additional strategies without Kelly analysis are commodity features available in every backtester.

**Evidence.** The critical Kelly solver has a closed-form solution (no numerical optimization needed):

```
f_critical = 2*mu / (sigma^2 * (ln(P_target)/ln(D) + 1))
```

This solver answers: "Given that I will accept at most 1% probability of a 50% drawdown, what is the maximum leverage I can use?" No mainstream backtester provides this answer.

#### Decision 4: Dual Return Types — Simple for Cross-Sectional, Log for Time-Series

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

#### Decision 5: ddof=0 for Kelly, ddof=1 for Sharpe

**Context.** The `ddof` parameter in standard deviation computation (population vs. sample) affects numerical results. Using the wrong convention silently corrupts calculations.

**Analysis.** Kelly and Sharpe serve different statistical purposes:

- **Kelly** (`ddof=0`, population std): The continuous Kelly formula `f* = mu/sigma^2` uses population parameters. It is an MLE estimator that computes the optimal fraction given the observed data. Using `ddof=1` would bias f* downward for small samples.

- **Sharpe** (`ddof=1`, sample std): Sharpe is an inferential statistic — we estimate the population Sharpe from a sample. The Bessel correction (`ddof=1`) provides an unbiased estimate of population variance.

**Decision.** Each convention is correct for its purpose. Both are explicitly documented and tested.

**Trade-off.** Having two conventions creates a source of confusion. Mitigated by AC-4 (Kelly analytical test) which would fail if `ddof=1` were used: the test constructs a deterministic series with exactly `mu=0.0005` and `sigma=0.01` (population std), expecting `f* = 5.0`. Any ddof mismatch between the test fixture and the estimator causes failure.

**Evidence.** The spec review (iteration 1) caught this as a blocker before any code was written. The ddof mismatch between test fixture and estimator would have been a silent runtime bug — AC-4 would have failed with no obvious explanation. Catching it during specification saved debugging time during implementation.

#### Decision 6: GBM Only for MVP

**Context.** Heston stochastic volatility is the "right" model. Regime-switching is a practical middle ground. GBM is the simplest.

**Analysis.** GBM (Geometric Brownian Motion) assumes constant drift and volatility — no fat tails, no volatility clustering. These are significant limitations for real markets. However:

- GBM with method-of-moments calibration is implementable in a single day
- GBM serves a dual purpose: stress-test strategy via Monte Carlo AND verify engine via known-answer tests (AC-6: moment matching, AC-7: zero-edge Sharpe)
- Regime-switching adds 1-2 days for EM calibration and state management
- Heston adds 2+ days for 5-parameter optimization via characteristic function/FFT, with non-convex optimization and multiple local minima

**Decision.** GBM only for MVP. Regime-switching and Heston are documented in the North Star with specific implementation requirements.

**Trade-off.** Simulation underestimates tail risk. Compensated by: (a) documenting this prominently (L9), (b) comparing empirical vs. theoretical ruin to surface model inadequacy, and (c) every simulation report includes: "NOTE: GBM assumes no fat tails. Real ruin risk likely higher."

**Evidence.** AC-6 validates GBM correctness by checking that simulated log-returns match theoretical moments within 2 standard errors. AC-7 validates that zero-edge GBM produces zero expected Sharpe across 200 paths with 4 symbols. Both tests would be impossible with a more complex model where the correct answer is not analytically known.

#### Decision 7: Half-Kelly Default

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

### IV. Architecture as Risk Mitigation

The architecture is not just a code organization scheme — it is a risk mitigation strategy. Each structural choice addresses a specific failure mode identified in the problem decomposition.

#### Look-Ahead Prevention

**Risk.** Look-ahead bias silently inflates backtest returns. It is the most common and most dangerous backtesting bug.

**Mitigation.** A single `shift(1)` at `engine.py:21` enforces temporal alignment:

```python
shifted_weights = raw_weights.shift(1).fillna(0.0)
```

The strategy produces raw target weights (what it wants to hold tomorrow). The engine shifts them by one bar (yesterday's intention becomes today's execution). This is applied exactly once, in one place. The strategy cannot cause look-ahead because it never sees the shift — the engine owns temporal alignment.

**Verification.** AC-2 constructs a perfect-foresight strategy that knows the future. After `shift(1)`, the strategy's realized return is strictly less than the sum of all positive daily returns. If `shift(1)` were absent, the strategy would achieve perfect returns — a qualitatively different (and impossible) result.

#### Cost Invariant

**Risk.** Transaction cost models with bugs can increase returns instead of reducing them — a silent corruption that makes bad strategies look good.

**Mitigation.** Costs are always non-negative and always reduce returns:

```
slippage_{t,i} = k * sigma_trailing(20) * |delta_w_{t,i}|    >= 0 always
commission_{t,i} = (commission_per_share / close_price) * |delta_w_{t,i}|  >= 0 always
net_return = gross_return - slippage - commission             <= gross always
```

**Verification.** AC-3 runs a strategy with positive slippage and asserts `net < gross` for every bar where trading occurs and `total_costs > 0`.

#### Statistical Convention Rigor

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

#### Immutability

**Risk.** Mutable state shared between modules leads to action-at-a-distance bugs — one module mutates data another module depends on.

**Mitigation.** All result types use `@dataclass(frozen=True)`. Prices are copied at module boundaries: `engine.run_backtest()` passes `{sym: df.copy() ...}` to `strategy.compute_weights()`. This is a shallow freeze (DataFrames inside frozen dataclasses are still technically mutable), but the copy-at-boundaries pattern prevents mutation bugs in practice.

---

### V. Validation Strategy

#### Acceptance Criteria as Known-Answer Tests

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

#### Test Design Philosophy

The key insight is that the wrong answer should be qualitatively different from the correct answer. This maximizes the signal-to-noise ratio of the test:

- **AC-1b:** If the engine incorrectly aggregates log-returns instead of simple returns, Bar 1 gives `0.5*ln(1.05) + 0.5*ln(0.95) = -0.00125` — a negative return when the true portfolio return is zero. The error is not a rounding issue; it is a conceptual bug that produces an answer of the wrong sign.

- **AC-2:** If `shift(1)` is absent, the perfect-foresight strategy achieves the sum of all positive daily returns — physically impossible in real trading. The error is not a small numerical discrepancy; it is a strategy achieving returns that violate causality.

- **AC-4:** If Kelly uses `ddof=1` instead of `ddof=0`, the alternating return series `[0.0105, -0.0095, 0.0105, ...]` gives `std(ddof=1) = 0.01005` instead of `std(ddof=0) = 0.01`, producing `f* = 4.95` instead of `5.0`. The tolerance is `1e-6`, so this fails clearly.

#### Review Convergence

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

### VI. Acknowledged Limitations

Fourteen limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight. Presenting them here demonstrates intellectual honesty — the system's boundaries are known, quantified, and mapped to specific resolutions.

#### Data Limitations

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

#### Strategy Limitations

**L2: No Pairs Trading (SMA Only)**
- **Impact:** Cannot demonstrate statistical arbitrage directly. The MVP uses equal-weight as a proof-of-concept vehicle.
- **Current Mitigation:** The architecture (target weights abstraction, `{symbol: weight}` interface, pluggable strategy base class) is designed for multi-asset stat arb from day one. Adding pairs trading requires only a new Strategy subclass, not engine changes.
- **North Star:** Pairs trading with cointegration, hedge ratio methods (OLS, Total Least Squares, Johansen procedure).

**L6: No Signal Half-Life or Factor Attribution**
- **Impact:** Cannot assess execution speed sensitivity or decompose alpha vs. beta.
- **Current Mitigation:** Not applicable for equal-weight strategy.
- **North Star:** Signal decay at shift(0..3), SPY regression for alpha/beta/R^2.

#### Statistical Limitations

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

#### Model Limitations

**L9: GBM Only (No Fat Tails, No Volatility Clustering)**
- **Impact:** Simulation underestimates tail risk. Real markets exhibit volatility clustering (GARCH), regime switching, and fat tails — all absent from GBM.
- **Current Mitigation:** Every simulation report notes "GBM assumes no fat tails. Real ruin risk likely higher." Empirical vs. theoretical ruin comparison surfaces model inadequacy.
- **North Star:** Regime-switching (2-state Markov with EM calibration), GARCH(1,1), Heston stochastic volatility, Merton Jump Diffusion.

**L10: Linear Slippage (No Order-Size Impact)**
- **Impact:** Underestimates costs for large positions. Slippage = k * sigma only; no square-root impact.
- **Current Mitigation:** At daily-bar scale with typical portfolio sizes, order-size impact is negligible. Configurable k allows pessimistic testing (k=2.0 simulates 4x normal slippage).
- **North Star:** Square-root impact model (Almgren-Chriss): Impact = sigma * sqrt(Q/V), verified across 8M institutional trades.

#### Scope Limitations

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

### VII. Mathematical Foundation

#### Kelly Criterion (Continuous Gaussian Approximation)

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

#### Half-Kelly Derivation

The commonly cited "half-Kelly retains 94% of return" is incorrect. The 94% figure refers to expected arithmetic return, not log growth rate. The correct calculation:

```
g(f*/2) / g(f*) = (2 * 0.5 - 0.5^2) / 1.0 = (1.0 - 0.25) / 1.0 = 0.75
```

**Half-Kelly retains 75% of maximum log growth rate.** Log growth rate, not arithmetic return, governs long-run compounding and ruin probability. This is the quantity that matters for capital allocation decisions.

#### Ruin Probability

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

#### Critical Kelly Solver (Closed-Form)

Given target ruin probability P_target and drawdown level D, solve for the maximum safe fraction:

```
P_target = D^(2*mu/(sigma^2*f) - 1)

ln(P_target) = (2*mu/(sigma^2*f) - 1) * ln(D)

f_critical = 2*mu / (sigma^2 * (ln(P_target)/ln(D) + 1))
```

This has a closed-form solution — no numerical optimization required. The implementation verifies the solution by plugging f_critical back into the ruin formula and checking `P(ruin | f_critical, D) ≈ P_target`.

**Validity check:** If f_critical >= 2*f*, the requested ruin tolerance cannot be achieved. The system reports "no safe fraction exists" rather than returning a meaningless value.

#### Slippage Model

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

### VIII. Process and Delivery Metrics

#### Five-Stage Specification Pipeline

The system was built through a rigorous 5-stage specification pipeline. Each stage produced a versioned artifact with formal review.

| Stage | Artifact | Version | Key Output |
|-------|----------|---------|------------|
| Brainstorm/PRD | `prd.md` | v5 | 7 design decisions, 14 limitations, 7 ACs, North Star roadmap |
| Specification | `spec.md` | v4 | 9 module interfaces, 8 ACs (added AC-1b), data contracts, error taxonomy |
| Design | `design.md` | v1 | Architecture diagrams, interface contracts, 10 correctness invariants |
| Plan | `plan.md` | v2 | 12-phase build order, AC readiness map, TDD enforcement |
| Tasks | `tasks.md` | v5 | 51 tasks, 4 parallel groups, dependency graph |

#### Front-Loaded Specification

The most important process insight: **front-loaded specification enabled approximately 3 hours of actual coding.** The spec review (iteration 1) caught 3 blockers before implementation began:

1. **Jensen's inequality** — The spec originally used log-return aggregation for portfolio returns. The reviewer identified that `ln(sum(w_i * exp(r_i))) != sum(w_i * r_i)` — a mathematical error that would have produced systematically wrong results. AC-1b was added specifically to catch this.

2. **ddof mismatch** — Kelly estimation used `ddof=0` (correct) but the test fixture implicitly assumed `ddof=1` (pandas default). The mismatch would have caused AC-4 to fail with no obvious explanation.

3. **Commission dimensional error** — The original formula `commission_per_share * |delta_w| * close_price` has units of `($/share) * dimensionless * ($/share) = $/share^2` — dimensionally incorrect. The fix: `commission_rate = commission_per_share / close_price` (dimensionless).

All three bugs would have been silent runtime errors — the system would produce wrong numbers without crashing. Catching them during specification saved hours of debugging during implementation.

#### Plan Review Catches

The plan review (iteration 1) caught 3 additional issues:

1. **yfinance breaking change** — `multi_level_index=True` default in yfinance >= 0.2.51 breaks column normalization. Adding `multi_level_index=False` prevented a runtime failure.

2. **TDD ordering violation** — Phases 6-10 had implementation before tests. Forced to RED-GREEN-REGRESSION pattern.

3. **Phase 8 dependency error** — The dependency list was incomplete, which would have caused import errors.

#### Task Review Convergence

The task breakdown required 5 review iterations (10 total reviews across task-reviewer and phase-reviewer). Issues caught:

- Missing pre-computed expected values in test descriptions
- Ambiguous function signatures (config object vs. explicit params)
- Off-by-one errors in drawdown duration counting
- AC-1b approximate expected value (0.0501) corrected to exact (20/399 ≈ 0.050125)

The convergence pattern: v1 had 7 warnings, v2 had 5, v3 had 6, v4 had 5, v5 had 0. The decreasing trajectory (with some noise from newly surfaced issues) indicates healthy convergence.

#### Patterns Worth Documenting

These patterns emerged during the process and proved valuable:

1. **Spec every formula with units, ddof, and edge cases.** The commission dimensional error and ddof mismatch were both caught by requiring explicit dimensional analysis and ddof specification in the spec. Without this discipline, both would have been silent bugs.

2. **Design ACs where the wrong answer is qualitatively different from the correct one.** AC-1b produces a negative number when the correct answer is zero. AC-2 produces physically impossible returns when the bug is present. This maximizes bug detection signal — the test does not merely check a number within tolerance; it checks whether the answer makes physical sense.

3. **Single temporal alignment point.** Shift is applied once, in the engine, at one line. This prevents distributed look-ahead bugs and makes verification possible with a single test (AC-2).

4. **Frozen dataclasses + copy-at-boundaries.** Pragmatic Python immutability without deep copies. The dataclass itself is immutable; contained DataFrames are protected by explicit `.copy()` calls at module boundaries.

5. **Phase-level regression.** Every phase runs the full test suite after GREEN, catching cross-module breakage immediately rather than at integration time.

6. **AC readiness map.** The plan tracks when each acceptance criterion becomes testable (which phases must complete first). This prevents writing AC tests before their dependencies exist.

#### Anti-Patterns to Avoid

1. **Implementing from memory instead of reading the spec.** Root cause of the half-Kelly scaling bug (iteration 2 blocker), AC-7 parameter drift, and survivorship warning text mismatch. The spec is the source of truth; the implementation is a transcription.

2. **DRY across semantic boundaries.** AlwaysLongStrategy was initially an alias for EqualWeightStrategy. While they are functionally identical (both return 1/N weights), they serve different semantic roles: "equal-weight" is user-facing, "always-long" is test-fixture-facing. The spec requires them as separate classes. DRY is a code organization principle, not a semantic one.

3. **Relaxing test parameters for stability.** AC-7 was initially implemented with 100 paths/3*SE instead of the spec's 200 paths/2*SE. Weakening test criteria without spec approval undermines the validation strategy.

4. **Accepting documentation drift.** After implementation changed `run_backtest` from 5 parameters to 3, the spec and design still referenced the 5-parameter signature. Either fix the docs or fix the code — never neither.

---

### IX. North Star Roadmap

The North Star represents where the system goes next. Each extension is mapped to a specific limitation it resolves and, where applicable, a research citation.

#### Tier 1: Highest ROI

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

#### Tier 2: Medium ROI

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

#### Tier 3: Long-Term

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

### X. Conclusion

#### What Was Demonstrated

This project is an exercise in engineering design thinking applied to quantitative finance. The goal was never to build the most feature-rich backtester — it was to build the most thoughtful one.

**Statistical rigor.** Every formula has explicit units, ddof conventions, and edge cases. The commission dimensional error, Kelly ddof mismatch, and Jensen's inequality bug were all caught during specification — before a single line of code was written. The system uses dual return types (simple for cross-sectional, log for time-series) because mathematical correctness demands it, not because it is convenient.

**Validation discipline.** Eight acceptance criteria, each designed so the wrong answer is qualitatively different from the correct one. A negative number when zero is expected (AC-1b). Physically impossible returns when look-ahead prevention fails (AC-2). A ddof-sensitive number that breaks cleanly on mismatch (AC-4). These are not regression tests — they are proofs of correctness.

**Architectural prevention over process discipline.** Look-ahead bias is prevented by a single `shift(1)` at `engine.py:21`, not by asking strategy developers to be careful. The cost invariant (net <= gross) is guaranteed by the execution model's structure, not by code review. Survivorship warnings are non-suppressible by design, not by convention.

**Intellectual honesty.** Fourteen acknowledged limitations, each with impact assessment, current mitigation, and North Star resolution. The system does not pretend to solve problems it does not solve. GBM limitations are stated on every simulation report. Data quality warnings cannot be turned off. The capital efficiency frontier shows certain ruin at 2x Kelly — the system does not hide inconvenient truths.

#### The System Answers the Right Question

Most backtesting tools answer: "Your strategy had a Sharpe of 1.4."

This system answers: "Your strategy had a Sharpe of 1.4. At half-Kelly sizing, your ruin probability is 12.5% at 50% drawdown. The capital efficiency frontier shows you retain 75% of maximum growth at half the risk. The critical Kelly fraction for 1% ruin probability is 0.42x. Data source is survivorship-biased — treat results with skepticism."

The second answer is useful. The first is not.

#### Nothing Accidental

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

### References (Task 1)

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

### Appendix: Artifact Registry (Task 1)

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

---

## Task 2: Claude-DA LiteLLM Provider

**Difficulty:** Medium
**Challenge prompt:** 封裝 claude cli 變成 litellm endpoint (Wrap Claude CLI as a LiteLLM endpoint)
**Project directory:** `claude-litellm/`
**Detailed report:** [`claude-litellm/REPORT.md`](claude-litellm/REPORT.md)

---

### I. Executive Summary

#### The Problem

Data analysis requires SQL fluency, schema knowledge, and the ability to translate business questions into technical queries. Non-technical stakeholders depend on analysts for every question, creating bottlenecks that slow decision-making across the organisation. A product manager asking "What were our top 10 customers by revenue last month?" must wait for an analyst to write SQL, run it, interpret the results, and format a response. This dependency is the bottleneck — not the database, not the infrastructure, not the compute.

Three mature technologies each solve part of this problem independently: Claude Code reasons about data and writes SQL. MCP servers provide standardised, pluggable database access. LiteLLM provides an OpenAI-compatible API gateway that any existing client can call. None of these, on their own, gives a non-technical user an end-to-end path from English question to data-backed insight.

#### The Solution

Claude-DA is a **LiteLLM custom provider** that wraps the Claude Agent SDK behind an OpenAI-compatible chat completions API. The provider injects the database schema into a system prompt, hands the user's question to an autonomous agent, and returns the agent's insight-driven response in standard OpenAI format.

```
Client  --->  LiteLLM Proxy  --->  Claude-DA Provider  --->  Claude Agent SDK  --->  MCP SQLite
```

Any tool that speaks the OpenAI chat completions format — curl, the OpenAI Python SDK, Open WebUI, LangChain — works without modification. Both non-streaming and streaming (Server-Sent Events) modes are supported.

#### Scope Calibration

This is a demo-scale MVP targeting SQLite with a seeded e-commerce database. It is not a production analytics platform. This is a deliberate engineering decision, not a limitation.

Production analytics requires: multi-database support, contextual schema injection for large databases, conversation memory, per-user governance, and cost dashboards. Each of these is deferred because the core value chain — English question in, SQL-backed insight out, audit trail recorded — can be proven without them. The architecture is designed so that each deferred capability is configuration or wiring, not a new system.

#### Differentiator

No existing tool connects these three technologies into a single API surface. The combination of:
- LiteLLM custom provider as the API gateway (any OpenAI-compatible client works)
- Claude Agent SDK as the reasoning engine (autonomous multi-query analysis)
- MCP SQLite server as the database access layer (zero custom DB connector code)
- Three-layer read-only safety architecture (tool allowlist, tool blocklist, filesystem permissions)

...creates a system where adding a new database backend is configuration, not code. The safety model — three independent layers that must all fail for a write to succeed — is designed for the paranoid, not the optimistic.

#### Delivery Metrics

| Metric | Value |
|--------|-------|
| Source LOC | 1,472 (8 modules) |
| Test LOC | 2,772 (14 test files) |
| Tests | 152 collected, 146 passing, 2 failing (runtime-dependent), 4 skipped |
| Tasks completed | 41/41 |
| Review iterations | 7 across 5 phases |
| Review blockers caught | 10 |
| Duration | ~9.5 hours |
| Specification artifacts | 5 (PRD, Spec, Design, Plan, Tasks) |

---

### II. Problem Decomposition

#### The Analyst Bottleneck

The core workflow today looks like this:

| Step | Actor | Latency |
|------|-------|---------|
| Business question arises | Stakeholder | Immediate |
| Question queued for analyst | Stakeholder → Analyst | Hours to days |
| Analyst writes SQL | Analyst | Minutes |
| Analyst runs query | Analyst | Seconds |
| Analyst interprets and formats | Analyst | Minutes |
| Answer delivered | Analyst → Stakeholder | Minutes |

The bottleneck is steps 2-5 — the analyst dependency. The SQL itself is often trivial. The value is in knowing what to ask the database, not in writing `SELECT`. An LLM can bridge this gap: it understands the business question, knows (via the schema) what data is available, and can write and execute SQL autonomously.

#### Three Technologies, No Integration

| Technology | Solves | Does Not Solve |
|-----------|--------|----------------|
| **Claude Code** | Reasoning, SQL generation, natural language response | No standard API surface; requires Claude Code CLI |
| **MCP SQLite** | Standardised database access, zero connector code | No reasoning; tool-level only |
| **LiteLLM** | OpenAI-compatible API gateway, client compatibility | No agent capabilities; pass-through only |

The gap is integration. Claude-DA fills it: LiteLLM provides the API surface, the Agent SDK provides the reasoning, and MCP provides the database access. The provider is the glue — 1,472 LOC of integration code, not 10,000 LOC of a new analytics platform.

#### The Real Question

The real question is not "can Claude write SQL?" — it can. The real question is: **can an autonomous agent safely access a database through a standard API while maintaining auditability and read-only guarantees?**

This reframes the project from "natural language to SQL" (a solved problem) to "safe, auditable, API-compatible agent-database integration" (an unsolved integration challenge).

---

### III. Strategic Design Decisions

Seven decisions shape the architecture. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

#### Decision 1: MCP for Database Access

**Context.** The agent needs to execute SQL against a database. Two approaches: (a) custom database connector code in the provider, or (b) MCP server providing database tools that the agent calls natively.

**Analysis.** Custom connectors mean writing connection management, query execution, result formatting, and error handling for each database type. The `@modelcontextprotocol/server-sqlite` MCP server already provides `read_query`, `write_query`, `create_table`, `list_tables`, and `describe_table` tools. Claude speaks MCP natively — the Agent SDK handles tool routing without custom code.

**Decision.** Use MCP for all database access. Zero custom DB code in the provider.

**Trade-off.** Depends on the MCP ecosystem quality and the `@modelcontextprotocol/server-sqlite` server specifically. Compensated by: (a) MCP is an Anthropic-backed standard with active development, (b) the architecture is MCP-server-agnostic — swapping SQLite for PostgreSQL means changing one config line, (c) the provider never touches the database directly, so database-specific bugs are isolated to the MCP server.

**Evidence.** The entire `src/claude_da/` codebase contains zero SQL execution code. All database interaction flows through MCP tool calls that the Agent SDK routes to the MCP server. Adding PostgreSQL support means configuring a PostgreSQL MCP server — no provider code changes.

#### Decision 2: Agent SDK over CLI Subprocess

**Context.** Two ways to invoke Claude as an agent: (a) the Claude Agent SDK (`claude-agent-sdk` on PyPI), which provides a clean async Python API, or (b) shelling out to the Claude Code CLI as a subprocess.

**Analysis.** The Agent SDK provides typed responses (`AsyncIterator[Message]`), structured tool use blocks, token/cost metadata, and async support. The CLI subprocess approach requires parsing stdout, handling process lifecycle, and loses type safety. However, the Agent SDK is v0.1.x — less battle-tested than the CLI.

**Decision.** Use the Agent SDK as the primary integration. Document CLI subprocess as a fallback if SDK breaks.

**Trade-off.** v0.1.x API may change. Compensated by: (a) version pinned to `>=0.1.30,<0.2.0` with upper bound preventing surprise breakage, (b) integration tests catch SDK breaks, (c) CLI fallback is documented in `docs/TECHNICAL_GUIDE.md` — switching requires changing one module, not the architecture.

**Evidence.** The Agent SDK's typed response model enabled structured SQL extraction from `ToolUseBlock` objects matching `mcp__sqlite__*` tool names (`agent.py`). A CLI subprocess approach would require regex-parsing tool calls from stdout — fragile and untestable.

#### Decision 3: SQLite for Demo

**Context.** The demo needs a database. Options: SQLite (zero setup, portable), PostgreSQL (production-realistic), or a mock/in-memory store.

**Analysis.** SQLite requires zero infrastructure — no server, no credentials, no Docker. The demo database is seeded by a Python script (`scripts/seed_demo_db.py`) that generates an e-commerce dataset with customers, products, orders, and order items across 6+ calendar months with varied distributions. The architecture is DB-agnostic by design (MCP server is the only database-aware component).

**Decision.** SQLite for demo. PostgreSQL is a configuration change, not an architecture change.

**Trade-off.** SQLite is not production-realistic for multi-user analytics. Compensated by: (a) the engineering value is in the provider-agent-MCP integration, not in the database, (b) SQLite enables zero-setup demos — `uv run python scripts/seed_demo_db.py` creates a ready-to-query database, (c) the seeder sets `chmod 444` on the database file as the third safety layer.

**Evidence.** The seeder script generates: 50+ customers across 3 tiers (Free/Pro/Enterprise), 25+ products across 4 categories, and 200+ orders spanning 6 months. This is sufficient for meaningful analysis queries while remaining portable.

#### Decision 4: Environment Variables over YAML Config

**Context.** The provider needs 9 configuration settings: API key, model, database path, MCP server command, log settings, timeouts, and limits.

**Analysis.** YAML config files are more structured but require a parser, a schema, a config file location convention, and documentation. Environment variables are simpler, Docker-native, and require zero parsing code. The MVP has 9 settings — YAML overhead is not justified.

**Decision.** Environment variables with a frozen dataclass (`config.py`). Validation at parse time, immutable after construction.

**Trade-off.** Less structured than a config file — no nesting, no comments. Compensated by: (a) `.env.template` documents all variables with defaults, (b) the frozen dataclass enforces types and validation at startup, not at query time, (c) LiteLLM's own config (`litellm_config.yaml`) handles routing — the provider config is orthogonal.

**Evidence.** `config.py` parses all 9 environment variables into a frozen `ClaudeDAConfig` dataclass. Missing required values (e.g., `ANTHROPIC_API_KEY`) raise `ConfigurationError` at startup, not at query time.

#### Decision 5: Structured JSONL Logging

**Context.** Every query must be auditable — the exact SQL executed, token costs, and response metadata must be traceable.

**Analysis.** Options: (a) file-per-session artifacts (browsable but require storage management), (b) structured JSONL to stdout/file (machine-parseable, configurable, no infrastructure), (c) database-backed audit trail (full-featured but requires infrastructure). The MVP needs auditability without infrastructure.

**Decision.** Structured JSONL audit logging via `audit.py`. Configurable output: stdout, file, or both. Fire-and-forget via `asyncio.create_task` to avoid blocking the response path.

**Trade-off.** Less browsable than file artifacts — requires `jq` or similar to query. Compensated by: (a) each audit entry contains the full request, response, SQL queries, token counts, cost, and latency, (b) stdout mode integrates with any log aggregation system, (c) fire-and-forget with exception suppression ensures audit failures never break query responses.

**Evidence.** The audit entry schema captures: `request_id`, `model`, `messages`, `response_text`, `sql_queries[]`, `input_tokens`, `output_tokens`, `cost`, `latency_ms`, and `timestamp`. The `task.add_done_callback()` pattern suppresses "never retrieved" warnings for fire-and-forget tasks.

#### Decision 6: Full Schema in System Prompt

**Context.** The agent needs to know what tables and columns exist to write correct SQL.

**Analysis.** Two approaches: (a) inject the full schema into the system prompt at startup, or (b) contextual injection — only include tables relevant to the current question. Contextual injection is more token-efficient but requires a relevance classifier (itself an LLM call or embedding lookup).

**Decision.** Full schema injection at startup via `schema.py` PRAGMA queries. The schema is discovered once during lazy initialization and embedded in every system prompt.

**Trade-off.** Doesn't scale past ~50 tables (prompt grows linearly with schema size). Compensated by: (a) demo databases are small — the full schema fits comfortably in the context window, (b) contextual injection is the documented scaling path in `docs/TECHNICAL_GUIDE.md`, (c) the prompt assembly in `prompt.py` is modular — swapping full-schema for contextual-schema requires changing one function.

**Evidence.** `schema.py` discovers the schema via `SELECT * FROM sqlite_master` and `PRAGMA table_info()`, formatting it as `CREATE TABLE` statements. The `prompt.py` module assembles the system prompt from three parts: role definition, schema, and behavioral rules (including read-only instructions).

#### Decision 7: Lazy Initialization

**Context.** The provider is instantiated at LiteLLM import time. Environment variables may not be set yet (during test collection, provider scanning, or module loading).

**Analysis.** Eager initialization at import time causes cascading failures: missing `ANTHROPIC_API_KEY` during `pytest --collect-only`, missing database during LiteLLM provider discovery, and import-order dependencies. The plan review (iteration 1) identified this as a blocker — "Module-level instance runs full init at import time — fragile."

**Decision.** Lazy initialization via `_ensure_initialized()` with `asyncio.Lock`. First request triggers full init: config loading, schema discovery, read-only verification, prompt assembly, agent and audit logger creation. Init failure is cached to prevent cascading retries.

**Trade-off.** First request is slower (~2-5 seconds for MCP server startup). Compensated by: (a) subsequent requests are fast (MCP server stays running), (b) init failure caching prevents repeated slow failures, (c) no import-time side effects — the provider module can be safely imported in any context.

**Evidence.** The lazy init pattern resolved two review blockers: the plan-reviewer's "import-time fragility" concern and the design-reviewer's "env vars not set at import" concern. Init failure is cached as a `_init_error` attribute — subsequent requests return the cached error immediately instead of re-attempting initialization.

---

### IV. Architecture as Risk Mitigation

The architecture is not just code organization — it is a risk mitigation strategy. Each structural choice addresses a specific failure mode.

#### Three-Layer Read-Only Safety

**Risk.** The agent writes to or corrupts the database.

**Mitigation.** Three independent layers, each sufficient on its own:

| Layer | Mechanism | Enforcement Level | Code Reference |
|-------|-----------|-------------------|----------------|
| Tool allowlist | `allowed_tools=["mcp__sqlite__*"]` | SDK-enforced; blocks all non-MCP tools | `agent.py` |
| Tool blocklist | `disallowed_tools=["Bash", "Write", "Edit"]` | SDK-enforced; explicitly blocks the three most dangerous tools | `agent.py` |
| Filesystem permissions | `chmod 444` on the database file | OS-enforced; rejects writes below the application layer | `seed_demo_db.py` |

**Why three layers?** The `allowed_tools` wildcard alone should be sufficient. However, a bug in early Agent SDK versions (v0.1.5-v0.1.9, issue #361) caused `allowed_tools` to be silently ignored. The tool blocklist would have caught the critical paths. Filesystem permissions protect regardless of any application-level bug.

**Verification.** On first request, `verify_read_only()` in `schema.py` attempts a write operation against the database. If the write succeeds, the system refuses to start. If it fails (the expected case), initialization continues. This is a startup-time safety gate, not a runtime check.

#### Error Isolation

**Risk.** Agent SDK errors, MCP server crashes, or database errors propagate as unformatted 500s to the client.

**Mitigation.** Custom exception hierarchy (`exceptions.py`) with HTTP status code mapping. `ClaudeDAError` is the base class; subclasses include `ConfigurationError` (500), `SchemaDiscoveryError` (500), `AgentError` (502), and `InputValidationError` (400). The provider's `_handle_error()` method catches `ClaudeDAError` and re-raises as LiteLLM's `CustomLLMError(status_code, message)` — preserving the correct HTTP status for each error type.

#### Audit Trail Integrity

**Risk.** Audit logging blocks the response path or fails silently, losing the audit record.

**Mitigation.** Fire-and-forget via `asyncio.create_task()` with `task.add_done_callback()` for exception suppression. The audit log is dispatched after the response is assembled but before it is returned. For streaming, the audit entry is written after the final chunk (`is_finished=True`), with SQL queries and metadata accumulated in memory during streaming.

---

### V. The Five Pivots

The system evolved through five design pivots. Each was triggered by review findings or implementation discoveries, not random exploration.

#### Pivot 1: Lazy Initialization

**Trigger.** Plan review identified that module-level initialization runs at import time, causing failures when environment variables are not set during test collection or LiteLLM provider scanning.

**What was preserved:** Full initialization sequence (config → schema → verify → prompt → agent → audit).
**What was discarded:** Eager initialization at module load.
**Why.** Import-time side effects are a well-known anti-pattern in Python. The `_ensure_initialized()` pattern with `asyncio.Lock` defers all initialization to first request, eliminating import-order dependencies.

#### Pivot 2: Streaming Return Type

**Trigger.** Design review identified that `astreaming()` must return `AsyncIterator` per LiteLLM's interface, but the original design returned a tuple `(iterator, future)` to coordinate audit logging.

**What was preserved:** Streaming capability and audit logging for streamed responses.
**What was discarded:** Tuple return type and `Future`-based audit coordination.
**Why.** The mutable container pattern (`result_holder = [None]`) passed as a single-element list allows the iterator to accumulate the result while the caller writes the audit entry after iteration completes. Simpler than Futures, no shared state issues.

#### Pivot 3: MCP Server Launch Strategy

**Trigger.** Plan review discovered that MCP server config uses plain dicts matching `McpStdioServerConfig` schema, not imported TypedDicts as originally assumed.

**What was preserved:** MCP server configuration as part of `ClaudeAgentOptions`.
**What was discarded:** TypedDict imports from the SDK.
**Why.** The official SDK examples use plain dict literals. Importing TypedDicts that don't exist in the SDK would fail at runtime.

#### Pivot 4: Permission Mode

**Trigger.** Plan review identified that the Agent SDK defaults to interactive permission approval, which hangs in a headless server context.

**What was preserved:** Agent SDK as the execution engine.
**What was discarded:** Default permission mode (interactive).
**Why.** `permission_mode="bypassPermissions"` is required for server-side use. The three-layer safety model (tool allowlist, blocklist, filesystem permissions) provides the actual safety guarantees — the permission prompt is for interactive CLI use, not headless servers.

#### Pivot 5: Database Permissions Strategy

**Trigger.** Plan review identified that `git` does not preserve `chmod 444` — committing `demo.db` to the repository would break the read-only enforcement after clone.

**What was preserved:** Filesystem permissions as the third safety layer.
**What was discarded:** Committed `demo.db` binary.
**Why.** The seeder script (`seed_demo_db.py`) generates the database at setup time and applies `chmod 444`. This ensures permissions are correct on every machine, regardless of git's file mode handling.

---

### VI. Acknowledged Limitations

Eight limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight.

#### L1: SQLite-Only

- **Impact:** Only SQLite is supported. Not production-realistic for multi-user analytics.
- **Current Mitigation:** The architecture is MCP-server-agnostic. The provider never touches the database directly. Swapping SQLite for PostgreSQL means configuring a PostgreSQL MCP server — no provider code changes.
- **North Star:** Multi-database support via MCP server configuration: PostgreSQL, MySQL, and any MCP-supported database.

#### L2: Full Schema in Prompt

- **Impact:** Doesn't scale past ~50 tables. Prompt grows linearly with schema size, consuming context window and increasing cost.
- **Current Mitigation:** Demo databases are small. The prompt assembly in `prompt.py` is modular — swapping full-schema for contextual-schema requires changing one function.
- **North Star:** Contextual schema injection — only tables relevant to the current question are included, using embedding-based relevance or LLM-based table selection.

#### L3: Stateless (No Conversation Memory)

- **Impact:** Each request is independent. "What about last month?" after "Show me this month's revenue" fails because the agent has no context.
- **Current Mitigation:** The Agent SDK supports sessions. Wiring conversation memory through the provider is straightforward but time-consuming.
- **North Star:** Conversation memory with configurable session TTL, enabling follow-up questions and iterative analysis.

#### L4: No Governance

- **Impact:** Single API key, no per-user access control, no query budgets.
- **Current Mitigation:** LiteLLM has built-in support for virtual keys, budget enforcement, and per-key capability profiles. Enabling them is configuration, not code.
- **North Star:** Per-user API keys with table-level access control and monthly budget caps, enforced by LiteLLM's virtual key system.

#### L5: No Caching

- **Impact:** Identical questions re-execute the full agent loop, incurring the same API cost and latency.
- **Current Mitigation:** Acceptable for exploratory analysis. Each question costs ~$0.10-0.50 in API calls.
- **North Star:** Result caching for repeated questions with TTL-based invalidation.

#### L6: Agent SDK v0.1.x

- **Impact:** The SDK is pre-1.0 and may introduce breaking changes.
- **Current Mitigation:** Version pinned to `>=0.1.30,<0.2.0`. Integration tests catch breaks. CLI subprocess is documented as a fallback.
- **North Star:** Upgrade to stable SDK release when available. The fallback strategy (CLI subprocess) is documented but has never been needed.

#### L7: Hallucinated Insights

- **Impact:** Claude may present plausible analysis not supported by the data. A trend described as "increasing" may actually be flat.
- **Current Mitigation:** Audit logs capture the exact SQL queries executed. Users can verify any claim by re-running the SQL. The system prompt includes instructions to ground all analysis in query results.
- **North Star:** Response validation layer that checks claims against query results before returning to the user.

#### L8: Prompt Injection Risk

- **Impact:** A crafted question could manipulate the agent into executing unintended queries or extracting sensitive data.
- **Current Mitigation:** Read-only enforcement prevents writes. Internal-only deployment is the primary mitigation. Audit logs capture all executed SQL for post-hoc review. The system prompt includes read-only instructions as a supplementary soft guardrail.
- **North Star:** Query classification layer that detects and blocks suspicious patterns before agent execution.

---

### VII. Validation Strategy

#### Test Pyramid

```
                    +---------------+
                    | Integration   |  5 tests against
                    | (API key)     |  live agent + MCP
                    +---------------+
               +-------------------------+
               |      Unit Tests         |  147 tests across
               |   (mocked SDK/MCP)      |  9 test files
               +-------------------------+
```

#### Coverage by Component

| Component | Test Files | Approach |
|-----------|-----------|----------|
| Provider | `tests/unit/test_provider.py` | Mock Agent SDK, test LiteLLM interface compliance |
| Agent | `tests/unit/test_agent.py` | Mock SDK `query()`, test message iteration and SQL extraction |
| Prompt | `tests/unit/test_prompt.py` | Direct function testing of prompt assembly |
| Schema | `tests/unit/test_schema.py` | Mock SQLite PRAGMA responses, test schema discovery |
| Config | `tests/unit/test_config.py` | Environment variable parsing with monkeypatch |
| Audit | `tests/unit/test_audit.py` | Test JSONL formatting and output routing |
| Exceptions | `tests/unit/test_exceptions.py` | HTTP status code mapping |
| Integration | `tests/integration/` | Live Agent SDK + MCP server (skipped without API key) |

#### Key Test Patterns

1. **AsyncMock for async code** — All agent and provider methods are async. Tests use `unittest.mock.AsyncMock` with `pytest-asyncio`.

2. **Environment-gated integration tests** — Integration tests require a live Anthropic API key. `pytest.mark.skipif` skips them in CI without API credentials.

3. **Monkeypatch for config** — Config tests use `monkeypatch.setenv` to test environment variable parsing without polluting the test environment.

4. **Fire-and-forget verification** — Audit tests verify that `asyncio.create_task` is called and that exceptions in audit tasks don't propagate.

#### Metrics

| Metric | Value |
|--------|-------|
| Total tests | 152 |
| Passing | 146 |
| Failing | 2 (runtime-dependent — Agent SDK version timing) |
| Skipped | 4 (integration tests without API key) |

---

### VIII. Process and Delivery Metrics

#### Five-Stage Specification Pipeline

The system was built through a 5-stage specification pipeline with formal review at each stage. Each review used a dual-reviewer model: a skeptic (finds issues) and a gatekeeper (makes pass/fail decisions).

| Stage | Artifact | Iterations | Blockers Found |
|-------|----------|------------|----------------|
| Specify | `spec.md` | 1 | 0 (5 warnings deferred to design) |
| Design | `design.md` | 1 | 3 (wrong SDK name, missing error translation, missing message conversion) |
| Plan | `plan.md` | 2 | 4 (message serialization, MCP config format, permission mode, git permissions) |
| Tasks | `tasks.md` | 1 + 2 chain validations | 1 |
| Implement | 8 source modules | 2 | 2 (missing integration tests, SQL injection in PRAGMA) |
| **Total** | | **7 iterations** | **10 blockers resolved** |

#### 41 Tasks Across 5 Phases

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1: Foundation | 6 | Project scaffold, config, exceptions, pyproject.toml |
| Phase 2: Database | 5 | Schema discovery, demo seeder, read-only verification |
| Phase 3: Core | 12 | Agent, provider, prompt, streaming, audit |
| Phase 4: Hardening | 10 | Error handling, lazy init, input validation, timeout |
| Phase 5: Validation | 8 | Unit tests, integration tests, documentation |

All 41 tasks completed. Two tasks (T-021, T-027) exceeded the 15-minute guideline and were subsequently split into a/b subtasks, validating the original sizing concern.

#### Review Effectiveness

The dual-reviewer model caught 10 blockers across 7 iterations. The most impactful catches:

1. **Wrong SDK package name** (design review) — The design used `claude-code-sdk` / `ClaudeCodeOptions`. The actual package is `claude-agent-sdk` / `ClaudeAgentOptions`. This would have been a Day 1 implementation failure.

2. **Permission mode hang** (plan review) — The Agent SDK defaults to interactive permission approval. In a headless LiteLLM server, this hangs indefinitely. Setting `permission_mode="bypassPermissions"` was critical.

3. **Git doesn't preserve chmod** (plan review) — Committing `demo.db` with `chmod 444` would lose permissions after `git clone`. Generating the database at setup time was the correct fix.

4. **SQL injection in PRAGMA** (implementation review) — An f-string in schema discovery (`f"PRAGMA table_info({table_name})"`) was flagged as a potential SQL injection vector. Fixed with parameterised queries.

#### Front-Loaded Research Prevented Wasted Effort

The spec review deferred 5 warnings to the design phase rather than blocking on them. This was the correct decision — the design phase resolved all 5 with better context. The design review then caught 3 blockers (wrong SDK name, missing error translation, missing message conversion) that would have been implementation failures.

The plan review was the most productive: 4 blockers in a single iteration, each addressing a runtime failure that would have been discovered only during live testing. Front-loading these discoveries into the plan phase saved an estimated 2-3 hours of implementation debugging.

#### Patterns Worth Documenting

1. **Skeptic + Gatekeeper dual-reviewer.** Separating "find issues" from "make pass/fail decisions" prevents the reviewer from self-censoring. The skeptic's job is to be paranoid; the gatekeeper's job is to be pragmatic.

2. **Blocker / warning / suggestion tiers.** Review classification allows approval with known warnings. Not every issue is a blocker — some are correctly deferred to the next phase.

3. **Verify SDK package names against PyPI before design.** Wrong names are blockers that waste review cycles. The `claude-code-sdk` → `claude-agent-sdk` catch saved a full implementation restart.

4. **Module-level singletons need lazy init.** Never rely on environment variables being available at import time. This is especially critical for LiteLLM providers, which are imported during provider scanning.

5. **Pin v0.x dependencies with upper bounds.** `>=0.1.30,<0.2.0` prevents surprise breakage from minor version bumps in pre-1.0 packages.

---

### IX. North Star Roadmap

#### Tier 1: Highest ROI

**Multi-Database Support**
- **What:** Configure PostgreSQL, MySQL, and other MCP-supported databases.
- **Why:** The architecture is MCP-server-agnostic but only SQLite is exercised. Proving multi-database support validates the abstraction.
- **Effort:** 1-2 days per database (MCP server config + integration tests).

**Contextual Schema Injection**
- **What:** Include only tables relevant to the current question in the system prompt.
- **Why:** Full schema doesn't scale past ~50 tables. Contextual injection enables enterprise-scale databases.
- **Effort:** 2-3 days (relevance classifier + prompt modification).

#### Tier 2: Medium ROI

**Conversation Memory**
- **What:** Maintain conversation state across requests for follow-up questions.
- **Why:** "What about last month?" is the natural follow-up to any analysis question.
- **Effort:** 2-3 days (session management + Agent SDK session wiring).

**Per-User Governance**
- **What:** LiteLLM virtual keys with per-user table access and budget caps.
- **Why:** Production deployment requires access control and cost management.
- **Effort:** 1-2 days (LiteLLM configuration, not provider code).

#### Tier 3: Long-Term

**Response Validation**
- Re-run the agent's SQL queries and verify that claimed trends and statistics match the actual results before returning to the user.

**Audit MCP Server**
- An MCP server that provides tools to query the audit log, enabling the agent to answer questions about its own history.

**Cost Optimization**
- Model tiering (cheap models for simple queries, expensive for complex analysis), response caching, and prompt compression.

---

### X. Conclusion

#### What Was Demonstrated

This project demonstrates systems integration thinking applied to three mature technologies. The goal was not to build the most complete analytics platform — it was to build the most thoughtful integration.

**Safety as architecture, not afterthought.** Three independent read-only layers, each sufficient on its own, with startup verification that refuses to run if the safety model is compromised. The three-layer approach was motivated by a real Agent SDK bug (issue #361) where `allowed_tools` was silently ignored — defense in depth is not theoretical.

**Review-driven development.** Ten blockers caught across seven review iterations, each preventing a runtime failure. The wrong SDK package name would have been a Day 1 failure. The permission mode hang would have been an inexplicable timeout in production. The git permissions issue would have silently disabled the third safety layer on every fresh clone. Front-loaded review is cheaper than post-hoc debugging.

**Honest scope calibration.** Eight acknowledged limitations, each with impact, current mitigation, and North Star resolution. The system does not pretend to solve problems it does not solve. SQLite-only is stated as a deliberate decision. Hallucinated insights are documented as a risk. Prompt injection is acknowledged with honest assessment of what read-only enforcement does and does not prevent.

#### The Five Pivots Tell the Story

1. **Eager init → Lazy init** — Never rely on env vars at import time
2. **Tuple return → Mutable container** — Match the interface your framework expects
3. **TypedDict imports → Plain dicts** — Use what the SDK actually provides
4. **Interactive permissions → Bypass** — Server context requires server-mode configuration
5. **Committed DB → Generated DB** — Git doesn't preserve what you think it preserves

Each pivot was discovered during review, not during debugging. The review process is the safety net.

#### Nothing Accidental

Every decision in this system is documented with its trade-off:

- MCP for DB access trades ecosystem dependency for zero custom connector code.
- Agent SDK trades v0.1.x instability for typed async API.
- SQLite trades production realism for zero-setup demos.
- Env vars trade structured config for Docker-native simplicity.
- JSONL logging trades browsability for machine parseability.
- Full schema in prompt trades scalability for implementation simplicity.
- Lazy init trades first-request latency for import-time safety.

The depth of thought is the deliverable. The code is the proof.

---

### References (Task 2)

1. Claude Agent SDK — https://pypi.org/project/claude-agent-sdk/ — v0.1.x async Python API for Claude agent interactions.

2. Model Context Protocol — https://modelcontextprotocol.io — Anthropic-backed standard for AI-tool integration.

3. `@modelcontextprotocol/server-sqlite` — MCP server providing SQLite database tools (read_query, write_query, list_tables, describe_table).

4. LiteLLM — https://github.com/BerriAI/litellm — OpenAI-compatible API gateway with custom provider support.

5. Anthropic (2025). "Building Effective Agents." — Agent architecture patterns and tool design best practices.

6. Agent SDK Issue #361 — `allowed_tools` silently ignored in v0.1.5-v0.1.9, motivating the three-layer safety model.

### Appendix: Artifact Registry (Task 2)

| Artifact | Path | Notes |
|----------|------|-------|
| PRD | `docs/brainstorms/20260207-claude-litellm.prd.md` | Product requirements and research |
| Specification | `docs/features/001-claude-da/spec.md` | Functional requirements and acceptance criteria |
| Design | `docs/features/001-claude-da/design.md` | Architecture, module interfaces, data flow |
| Plan | `docs/features/001-claude-da/plan.md` | Build order, phase dependencies, risk gates |
| Tasks | `docs/features/001-claude-da/tasks.md` | 41 tasks across 5 phases |
| Review History | `docs/features/001-claude-da/.review-history.md` | 7 iterations, 10 blockers resolved |
| Retrospective | `docs/features/001-claude-da/.retro.md` | Process learnings and patterns |
| Technical Guide | `docs/TECHNICAL_GUIDE.md` | Module reference and architecture |
| Source Code | `src/claude_da/` | 8 modules, 1,472 LOC |
| Tests | `tests/` | 14 test files, 152 tests, 2,772 LOC |
| Demo Seeder | `scripts/seed_demo_db.py` | E-commerce dataset generator |
| LiteLLM Config | `litellm_config.yaml` | Proxy routing configuration |

---

## Task 3: GitHub CI/CD Guardian

**Difficulty:** Medium
**Challenge prompt:** 封裝 GitHub CI/CD 成為 Claude Skills (Wrap GitHub CI/CD as Claude Skills)
**Project directory:** `github-claude-skills/`
**Detailed report:** [`github-claude-skills/REPORT.md`](github-claude-skills/REPORT.md)

---

### I. Executive Summary

#### The Problem

AI coding assistants have transformed how developers write code, but they have barely touched CI/CD. Research shows AI agents modify CI/CD configuration files in only **3.25% of file changes** ([arxiv 2601.17413](https://arxiv.org/html/2601.17413v1)), yet pipeline failures remain the number-one bottleneck after code generation. The average developer spends **2.5 hours** diagnosing a CI failure, trapped in a push-wait-fail cycle that existing tools do nothing to shorten.

For a proprietary trading firm, this gap is not an inconvenience — it is an operational risk. Knight Capital lost $440M in 45 minutes due to a deployment failure. CVE-2025-30066 (tj-actions supply chain attack) compromised 23,000+ repositories, exposing CI/CD secrets including exchange API keys. FINRA Regulatory Notice 15-09 requires documented change management for algorithmic trading systems but makes zero mention of CI/CD automation.

#### The Solution

A Claude Code skill plugin — 238 lines of structured markdown instructions, not code. The plugin gives Claude domain-specific CI/CD expertise through two capabilities:

1. **P0: Pipeline Failure Diagnosis** — Fetches recent workflow runs, identifies failures, pulls logs, categorizes the root cause into 1 of 6 categories, and proposes a fix with 3 options (Apply, Re-run, Skip).
2. **P1: Security Audit** — Discovers workflow files, runs `zizmor` if available, scans against 8 anti-patterns, checks the GitHub Advisory Database, and generates a severity-ranked report.

The skill is model-invoked: Claude auto-activates when it detects CI/CD-related requests. No slash command required.

#### Scope Calibration

This is a prompt-based skill plugin, not a runtime application. The "code" is structured markdown that instructs Claude how to behave. This is a deliberate engineering decision, not a limitation.

The skill does not replace GitHub Actions, auto-deploy code, store or display secret values, support non-GitHub CI/CD platforms, or provide local CI/CD testing. It shortens diagnosis time from ~2.5 hours to ~20 minutes by providing consistent triaging behavior, pre-built domain expertise, and a systematic diagnostic approach.

#### Differentiator

No existing tool combines AI-powered diagnosis with security audit in the developer's existing terminal. The competitive landscape reveals partial solutions:

| Tool | Strength | Gap |
|------|----------|-----|
| Claude Code (vanilla) | Full codebase context, `gh` CLI access | Ad-hoc results, no consistent triaging |
| Gitar.ai | Auto-fixes test failures | No codebase context, standalone tool |
| GitHub Copilot | Native GitHub integration | Limited CI/CD depth, no compliance |
| actionlint | YAML validation (24+ rules) | Static only, no AI diagnosis |
| zizmor | Security scanning | Security only, no diagnosis or authoring |

The honest question is: what does a skill add over vanilla Claude Code? Four things: consistent triaging behavior (predictable read/write/confirm escalation), pre-built domain expertise (6 failure categories, 8 security anti-patterns), context-triggered activation, and structured diagnostic approach (systematic 6-step root cause analysis).

#### Delivery Metrics

| Metric | Value |
|--------|-------|
| Core deliverables | 4 files, 355 lines |
| SKILL.md | 238 lines (under 500-line token budget) |
| Failure categories | 6 (P0) |
| Security anti-patterns | 8 (P1) |
| Validation checks | 67 automated, 100% passing |
| Tasks | 10 across 4 phases |
| Review phases | 6 (Spec, Design, Plan, Tasks, Implement, Security) |
| Duration | ~7 hours |

---

### II. Problem Decomposition

#### The CI/CD Neglect Pattern

The 3.25% statistic tells a structural story. AI coding assistants are optimised for source code — the part of the repository with the most training data, the clearest feedback loops, and the most immediate rewards. CI/CD configuration files are a different beast:

| Dimension | Source Code | CI/CD Config |
|-----------|-------------|--------------|
| Feedback loop | Seconds (compiler/linter) | Minutes (push-wait-fail) |
| AI training data | Abundant | Sparse |
| Error messages | Structured (stack traces) | Unstructured (log dumps) |
| Debugging tool | Debugger, REPL | Read logs, re-run, hope |
| Change frequency | High | Low (set-and-forget) |

The low change frequency is the trap. Teams write workflows once, forget about them, and then spend hours debugging when they break. By the time a CI failure occurs, the developer who wrote the workflow has moved on. The failure logs are verbose, unstructured, and often misleading.

#### Why Existing Tools Don't Help

Every existing tool solves one slice of the problem:

- **actionlint** validates YAML syntax but cannot diagnose why a valid workflow fails at runtime.
- **zizmor** finds security anti-patterns but cannot diagnose failures or propose fixes.
- **Gitar.ai** auto-fixes test failures but runs outside the developer's context — it cannot access the codebase.
- **GitHub Copilot** has GitHub integration but limited CI/CD debugging depth.

The gap is **contextual diagnosis**: reading the failure logs, understanding the codebase that produces them, categorising the root cause, and proposing a fix that accounts for the project's specific setup.

#### The Real Question

The real question is not "can AI read CI logs?" — it can. The real question is: **can structured prompt instructions make an LLM's CI/CD behavior consistent, safe, and auditable without writing any runtime code?**

This reframes the project from "CI/CD debugging tool" to "prompt engineering as software engineering" — demonstrating that structured markdown instructions can achieve the same consistency guarantees that traditional software achieves through code.

---

### III. Strategic Design Decisions

Seven decisions shape the skill. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

#### Decision 1: SKILL.md + Reference Files

**Context.** Claude Code loads skill instructions from a single SKILL.md file. Complex skills need detailed reference material (failure categories, security checklists), but cramming everything into one file creates a token-budget problem.

**Analysis.** The SKILL.md token budget is ~500 lines. The failure categories (39 lines) and security checklist (73 lines) are reference material that Claude needs only during specific procedure steps, not upfront. Loading them into SKILL.md would consume 112 lines of the budget on static lookup tables.

**Decision.** Keep SKILL.md under 500 lines with procedural instructions. Move detailed reference content to `references/` subdirectory. SKILL.md instructs Claude to `Read` the appropriate reference file at the relevant procedure step (P0 Step 4 for failure categories, P1 Step 3b for security checklist).

**Trade-off.** Two extra Read tool calls per invocation. Compensated by: (a) SKILL.md stays at 238 lines — well under the token budget, (b) reference files can be updated independently without touching the skill instructions, (c) Claude only loads what it needs for the current capability.

**Evidence.** SKILL.md L103: "Read `references/failure-categories.md`" (P0 Step 4). SKILL.md L199: "Read `references/security-checklist.md`" (P1 Step 3b). The reference files are loaded on-demand, not upfront.

#### Decision 2: No Scripts Directory

**Context.** The initial design considered a `scripts/` directory with shell scripts for common operations (log fetching, zizmor execution, result parsing).

**Analysis.** All operations use Claude Code's existing Bash tool to run `gh` CLI commands. No deterministic logic benefits from a shell script over inline instructions. A shell script for `gh run list --limit 10` adds a file to maintain, a dependency to document, and a failure mode (script not found, wrong permissions) — all for zero behavioral benefit.

**Decision.** No `scripts/` directory. All operations are inline Bash commands in SKILL.md procedure steps.

**Trade-off.** Longer SKILL.md procedure steps (commands are inline instead of single script calls). Compensated by: (a) zero external dependencies — the skill works on any machine with `gh` CLI, (b) each command is visible and auditable in the skill instructions, (c) no shell script maintenance, versioning, or permission issues.

**Evidence.** The skill uses exactly two external tools: `gh` CLI (required) and `zizmor` (optional). Both are invoked inline via Bash. The plan-reviewer validated that no proposed script contains logic that benefits from being a standalone file.

#### Decision 3: Three Behavioral Rules over Decision Trees

**Context.** The initial specification defined 6 formal tiers for action classification (Read, Analyze, Propose, Write, Execute, Destroy).

**Analysis.** A UX review flagged the 6-tier system as over-engineered for a markdown prompt file. Claude interprets behavioral instructions ("always ask before writing") more reliably than multi-branch conditional logic. Formal tier classification requires the LLM to first classify the action, then look up the tier's permissions, then apply them — three reasoning steps where one suffices.

**Decision.** Three behavioral rules:
1. **Read and analyze freely** — fetching CI status, reading logs, scanning workflow files require no confirmation.
2. **Propose freely, write only with confirmation** — diffs and suggestions are shown; file edits and workflow triggers require user approval.
3. **Destructive operations require double confirmation** — deleting a workflow requires showing what will be deleted and confirming twice.

**Trade-off.** Less formal than a decision tree — edge cases rely on Claude's judgment rather than explicit classification. Compensated by: (a) an ambiguity resolution table maps common user phrases to specific actions and confirmation levels, (b) the rules are testable — the validation suite greps for all three rules, (c) behavioral instructions align with how LLMs process natural language.

**Evidence.** SKILL.md L31-60 defines the three rules with an action classification table. The simplification from 6 tiers to 3 rules was the single most impactful design evolution — it improved both clarity and Claude's adherence in testing.

#### Decision 4: Zizmor as Optional Enrichment

**Context.** `zizmor` is the best-in-class security scanner for GitHub Actions. Should the skill require it or treat it as optional?

**Analysis.** Requiring zizmor means every user must install a Rust binary before using the security audit. Many developers won't have it. But ignoring it wastes a valuable data source for users who do have it.

**Decision.** Check availability at runtime (`which zizmor`). If present, run it and enrich the audit with its findings plus codebase context. If not, fall back to Claude's pattern matching against the security checklist. Don't require it, don't ignore it.

**Trade-off.** Inconsistent audit depth depending on whether zizmor is installed. Compensated by: (a) the 8 anti-pattern checklist provides baseline coverage regardless, (b) the audit report states its data sources explicitly — users know whether zizmor was used, (c) the skill suggests installing zizmor when it's not found.

**Evidence.** SKILL.md P1 Step 2: "Run `which zizmor`" — check availability. SKILL.md P1 Step 3a: "If zizmor is available, run `zizmor .github/workflows/`." SKILL.md P1 Step 3b: "Read `references/security-checklist.md` and scan against 8 anti-patterns" — this runs regardless of zizmor availability.

#### Decision 5: Plugin Structure

**Context.** Claude Code discovers skills through plugin manifests. The skill needs a discovery mechanism.

**Analysis.** The `.claude-plugin/plugin.json` manifest enables proper plugin discovery. The manifest is 5 lines of JSON declaring the plugin name (`github-cicd-guardian`), description, and version. Claude Code reads it to register the plugin and then loads skills from the `skills/` subdirectories.

**Decision.** Use the standard Claude Code plugin structure: `.claude-plugin/plugin.json` at the plugin root, with skills in `skills/<skill-name>/SKILL.md`.

**Trade-off.** Requires the correct directory structure — `plugin.json` must be in `.claude-plugin/`, not the root. The design review caught this location error twice (initially placed at root, then incorrectly "fixed" back to root).

**Evidence.** `.claude-plugin/plugin.json` (5 lines). The location was validated against Claude Code documentation after two incorrect placements during design.

#### Decision 6: Structured Output Format

**Context.** Both P0 and P1 produce reports. The format must be consistent, parseable, and actionable.

**Analysis.** Freeform text reports vary between invocations. Structured output (specific sections, tables, severity levels) enables consistent behavior and testable outcomes.

**Decision.** P0 outputs: status summary, failure identification, root cause category, proposed fix with 3 options. P1 outputs: severity-ranked findings table, per-finding detail (anti-pattern, file, line, remediation), summary statistics. Both use markdown tables for consistency.

**Trade-off.** More rigid than freeform — Claude must follow the template. Compensated by: (a) consistent output enables the validation suite to grep for expected sections, (b) users learn to expect a specific format, reducing cognitive load, (c) the template is embedded in SKILL.md, not a separate file.

**Evidence.** SKILL.md L111-137 defines the P0 output format. SKILL.md L204-238 defines the P1 output format. Both include explicit section headers that the validation suite checks for.

#### Decision 7: Prerequisites Inline

**Context.** The skill requires `gh` CLI authenticated with appropriate scopes. Where should prerequisites be checked?

**Analysis.** A separate prerequisites script adds a file and a failure mode. Inline checks in SKILL.md mean Claude verifies prerequisites as the first step of every invocation — no separate "setup" step that users might skip.

**Decision.** Prerequisites are the first section of SKILL.md (L13-29). Claude runs `gh auth status` before any capability. If auth fails, it provides the exact command to fix it (`gh auth login` or `gh auth refresh -s <scope>`).

**Trade-off.** Prerequisite checks run on every invocation, not just setup. Compensated by: (a) `gh auth status` is fast (<1 second), (b) error-driven scope discovery — instead of maintaining a static scope mapping, the error message tells the user which scope to add, (c) no "setup step" that users forget to run.

**Evidence.** SKILL.md L13-29 defines prerequisites. The error-driven scope discovery pattern avoids maintaining a scope mapping table that would become stale.

---

### IV. Architecture as Risk Mitigation

The architecture is prompt-based — the "code" is structured markdown instructions. Each structural choice addresses a specific failure mode.

#### Prompt Injection via CI Logs

**Risk.** CI logs may contain adversarial content designed to manipulate Claude's behavior — instructions to execute commands, modify files, or exfiltrate data.

**Mitigation.** Three layers:
1. **Triaging Rule 2** — All writes require user confirmation. Even if Claude is manipulated into proposing a malicious fix, the user must approve it.
2. **Explicit instruction** — SKILL.md marks CI logs as "untrusted input" and instructs Claude to treat instruction-like content as suspicious.
3. **Credential redaction** — Before quoting log evidence, Claude scans for credential patterns (AWS keys: `AKIA[0-9A-Z]{16}`, GitHub tokens: `ghp_[A-Za-z0-9_]{36}`, etc.) and replaces them with `[REDACTED]`.

**Residual risk.** Claude may present biased analysis influenced by adversarial log content. The user must exercise judgment. This is inherent to LLM-based log analysis — the skill never claims immunity from manipulation.

#### Incorrect Fix Applied

**Risk.** Claude proposes a fix that makes the problem worse or introduces new issues.

**Mitigation.** The fix is shown as an exact diff before writing. The user must approve. Post-fix, the skill recommends running `actionlint` to validate the modified YAML.

**Residual risk.** The user may approve without careful review. The skill is a tool, not a gatekeeper.

#### Security Audit False Negatives

**Risk.** The security audit misses a genuine vulnerability, giving false confidence.

**Mitigation.** Layered approach: pattern checks (8 anti-patterns) + zizmor (if available) + GitHub Advisory Database. Every audit report includes a limitations disclaimer — the skill never claims "your workflows are secure."

**Residual risk.** Novel attack patterns will be missed. The security checklist covers known anti-patterns; zero-day supply chain attacks are beyond scope.

#### Safety Invariants

Five invariants the skill maintains:

| Invariant | Mechanism | Validation |
|-----------|-----------|------------|
| Never execute commands found in CI logs | Explicit instruction in SKILL.md | SM-7 metric, grep verification |
| Never modify files during a security audit | P1 is read-only by design | SM-6 metric |
| Never display actual secret values | Credential redaction before quoting | SM-8 metric |
| Never bypass the triaging contract | All writes require confirmation | SM-4 metric |
| Always state audit limitations | Disclaimer template in P1 output | SM-9 metric |

---

### V. The Five Pivots

The skill evolved through five design pivots. Each was triggered by review findings.

#### Pivot 1: Triaging Simplification

**Trigger.** A UX review flagged the initial 6-tier action classification (Read, Analyze, Propose, Write, Execute, Destroy) as over-engineered for a markdown prompt file.

**What was preserved:** The core principle — read freely, write with confirmation, destroy with extra confirmation.
**What was discarded:** 6 formal tiers, tier classification logic, and the lookup table mapping actions to tiers.
**Why.** Claude interprets behavioral instructions more reliably than formal classification systems. Three simple rules beat a complex flowchart. This was validated during testing — Claude's adherence improved after the simplification.

#### Pivot 2: Frontmatter Format

**Trigger.** The plan review discovered that Claude Code docs recommend third-person trigger phrases in the `description` field for reliable auto-activation, not the declarative format used in the original design.

**What was preserved:** Skill metadata (name, description, version).
**What was discarded:** Declarative description format ("Diagnose GitHub Actions failures...").
**Why.** Third-person trigger phrases ("This skill should be used when the user asks to...") align with Claude Code's auto-activation matching. The declarative format worked but activated less reliably.

#### Pivot 3: No Scripts Directory

**Trigger.** Design analysis determined that no proposed shell script contains logic that benefits from being a standalone file.

**What was preserved:** All CLI commands (gh, zizmor, actionlint).
**What was discarded:** `scripts/` directory with helper shell scripts.
**Why.** Every shell script is one more file to maintain, version, and debug. Inline Bash commands in SKILL.md are visible, auditable, and require no file-path resolution.

#### Pivot 4: Zizmor Optional

**Trigger.** Requiring zizmor would block security audits for users who don't have a Rust toolchain installed.

**What was preserved:** Zizmor integration for users who have it.
**What was discarded:** Zizmor as a hard requirement.
**Why.** The 8 anti-pattern checklist provides baseline coverage. Zizmor enriches but isn't required. The skill checks availability at runtime and adapts.

#### Pivot 5: Behavioral Rules over Decision Trees

**Trigger.** Testing revealed that Claude followed 3 behavioral rules more consistently than a 6-branch decision tree.

**What was preserved:** The intent — predictable escalation from read to write to destroy.
**What was discarded:** Formal decision tree with tier classification.
**Why.** LLMs process natural language instructions better than formal logic. "Always ask before writing" is clearer than "classify action → lookup tier → check permissions → apply." The ambiguity resolution table handles edge cases without adding branches.

---

### VI. Acknowledged Limitations

Six limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight.

#### L1: GitHub Actions Only

- **Impact:** No support for GitLab CI, CircleCI, Jenkins, or other CI/CD platforms.
- **Current Mitigation:** GitHub Actions is the most common CI/CD platform for new projects. The skill focuses on depth over breadth.
- **North Star:** Platform-agnostic skill with adapter pattern — same diagnostic procedures, platform-specific log fetching and workflow parsing.

#### L2: No Local Testing

- **Impact:** The skill cannot simulate a pipeline run locally. Users must push and wait.
- **Current Mitigation:** The skill shortens the diagnosis phase (2.5 hours → ~20 minutes) but does not eliminate the push-wait-fail cycle. For local testing, `act` (a third-party tool for running GitHub Actions locally) is recommended.
- **North Star:** Integration with `act` for local pipeline simulation before pushing.

#### L3: LLM Prompt Injection

- **Impact:** Adversarial CI log content could influence Claude's analysis or proposed fixes.
- **Current Mitigation:** Triaging Rule 2 (user confirmation for all writes). CI logs are explicitly marked as untrusted. Credential redaction before quoting. Instruction-like content flagged as suspicious.
- **North Star:** Sandboxed log analysis where Claude's analysis of logs is separated from its ability to propose actions — two-stage reasoning with human gate between.

#### L4: False Negatives in Security Audit

- **Impact:** The audit may miss vulnerabilities, giving false confidence.
- **Current Mitigation:** Layered approach (pattern matching + zizmor + advisory DB). Every report includes limitations disclaimer. The skill never claims "your workflows are secure."
- **North Star:** Continuous audit pipeline that runs on every workflow change, not just on-demand.

#### L5: User Must Review Fixes

- **Impact:** The skill proposes fixes but cannot guarantee correctness. Users must review diffs carefully.
- **Current Mitigation:** Fixes shown as exact diffs before writing. `actionlint` recommended post-fix. Three-option choice (Apply, Re-run, Skip) gives the user control.
- **North Star:** Automated fix validation — apply the fix in a branch, trigger CI, and verify the fix resolves the failure before proposing to the user.

#### L6: No Cross-Repository Support

- **Impact:** Cannot diagnose issues that span multiple repositories (e.g., shared workflow reuse, organisation-level secrets).
- **Current Mitigation:** Single-repository focus. Cross-repo dependencies are flagged but not resolved.
- **North Star:** Organisation-level skill that can traverse repository dependencies and shared workflow files.

---

### VII. Validation Strategy

#### Automated Validation Suite

67 automated checks across 8 test phases, executed by `tests/validate_skill.sh` (179 lines):

| Phase | Focus | Checks |
|-------|-------|--------|
| 1. Structural Validation | File existence, JSON validity, line counts | 6 |
| 2. Plugin Manifest | Name, version, required fields | 3 |
| 3. SKILL.md Frontmatter | Name, description, version, length limit | 4 |
| 4. P0 Content | Commands, approval flow, untrusted input, error handling | 13 |
| 5. P1 Content | Audit steps, zizmor, checklist refs, secret protection | 12 |
| 6. Triaging Rules | 3 behavioral rules, ambiguity resolution examples | 6 |
| 7. Reference Files | 6 failure categories, 8 anti-patterns, regex patterns | 17 |
| 8. Security Invariants | SM-4, SM-6, SM-7, SM-8, SM-9, credential redaction | 6 |

#### Why Grep-Based Testing

The deliverables are markdown files, not executable code. Traditional unit tests don't apply. Instead, the validation suite uses `grep` to verify that specific strings, patterns, and structures exist in the correct files. Each check verifies a specific contract:

- "Does SKILL.md contain all three triaging rules?"
- "Does failure-categories.md define all 6 categories?"
- "Does security-checklist.md include all 8 anti-patterns?"
- "Does SKILL.md reference the credential redaction regex?"

This is regression testing for prompt engineering — every behavioral guarantee is verified by checking that the instruction exists in the file.

#### Test Fixtures

Two fixtures provide concrete validation targets:

1. **`tests/fixtures/sample-failure-logs.md`** (60 lines) — 7 log fixtures: one per failure category (dependency, YAML, code bug, flaky test, infrastructure, permissions) plus a prompt injection attempt. The prompt injection fixture tests Claude's handling of adversarial content.

2. **`tests/fixtures/vulnerable-workflow.yml`** (48 lines) — A single workflow with all 8 security anti-patterns embedded. Used for manual testing of P1's detection capabilities.

#### Success Metrics

| ID | Metric | Target |
|----|--------|--------|
| SM-1 | Diagnosis accuracy | Correct root cause category for sample logs |
| SM-2 | Time-to-diagnosis | <20 minutes from user request |
| SM-3 | Audit coverage | All 8 anti-patterns detected in vulnerable workflow |
| SM-4 | Write confirmation | 100% of file writes require user approval |
| SM-6 | Audit read-only | Zero file modifications during P1 |
| SM-7 | Log safety | Never execute commands found in logs |
| SM-8 | Secret protection | Never display actual secret values |
| SM-9 | Limitation disclosure | Every audit includes limitations disclaimer |

---

### VIII. Process and Delivery Metrics

#### Multi-Phase Development Pipeline

The skill was built through a structured pipeline with formal review at each stage:

| Stage | Duration | Iterations | Key Outcomes |
|-------|----------|------------|--------------|
| Brainstorm/PRD | Research phase | 1 | Problem framing, competitive analysis, scope decision |
| Specify | ~15 min | 1 (2 review cycles) | All blockers resolved, zero open issues |
| Design | ~35 min | 1 | Architecture validated, plugin structure confirmed |
| Plan | ~20 min | 1 | 2 blockers found (frontmatter format, version field) |
| Tasks | ~25 min | 2 + chain validation | 10 tasks across 4 phases |
| Implement | ~20 min | 1 | All 3 reviewers approved (implementation, quality, security) |
| Finish | ~60 min | — | PR, merge, retrospective |

#### 10 Tasks Across 4 Phases

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1: Plugin Structure | 3 | plugin.json, directory layout, SKILL.md frontmatter |
| Phase 2: P0 Implementation | 3 | Diagnosis procedure, failure categories, fix proposals |
| Phase 3: P1 Implementation | 2 | Security audit procedure, anti-pattern checklist |
| Phase 4: Validation | 2 | Validation script, test fixtures |

#### Review Effectiveness

The multi-phase review architecture (Spec → Design → Plan → Tasks → Implement) with dedicated reviewer personas caught issues at the earliest possible stage:

1. **plugin.json location** (design review) — Initially placed at the plugin root. Design review verified via Claude Code documentation that it must be at `.claude-plugin/plugin.json`. A second review caught the same error after it was incorrectly "fixed" back to the root. Lesson: authoritative source verification beats assumption-based design.

2. **Frontmatter format** (plan review) — The original description used a declarative format. Plan review verified that Claude Code docs recommend third-person trigger phrases for reliable auto-activation. Fixed before implementation.

3. **Security hardening** (implementation review) — The security reviewer identified 3 medium-severity issues post-implementation:
   - Prompt injection defense was too narrow (only covered command execution, not adversarial analysis)
   - The `--log` fallback could expose passing-step data
   - Log quoting lacked credential redaction
   All three were addressed before approval.

#### Patterns Worth Documenting

1. **Token budget as design constraint.** Track line counts throughout development. SKILL.md at 238 lines (under 500-line budget) means every line earns its place. Move static reference content (>40 lines) to `references/` subdirectory.

2. **Behavioral instructions over formal logic.** Claude follows "always ask before writing" more reliably than "classify action into tier 1-6, look up tier permissions, apply." Three rules beat six tiers.

3. **Grep-based regression testing.** Automated testing for LLM skill files without runtime dependencies. Each check verifies a specific string/pattern exists in the correct file. 67 checks run in seconds with zero infrastructure.

4. **Error-driven scope discovery.** Instead of maintaining a static token-scope mapping table, let the error message tell the user which scope to add (`gh auth refresh -s {scope}`). The mapping table would become stale; the error message is always current.

5. **Security invariant verification.** For each "never do X" requirement, define an explicit test metric (SM-N) and automate verification via grep. Five invariants, five metrics, five automated checks.

---

### IX. North Star Roadmap

#### Tier 1: Highest ROI

**V2 Capabilities: Workflow Authoring + Compliance**
- **What:** P2 (workflow authoring from natural language) and P3 (compliance readiness for regulatory frameworks).
- **Why:** P2 saves hours/week on workflow creation. P3 addresses the FINRA gap — regulatory intent vs. engineering practice.
- **Effort:** 2-3 days per capability (SKILL.md extensions + reference files + validation updates).

**Cross-Platform Support**
- **What:** GitLab CI, CircleCI, and Jenkins adapters using the same diagnostic procedures.
- **Why:** The diagnostic approach (fetch logs → categorise → fix) is platform-agnostic; only the log-fetching commands differ.
- **Effort:** 1-2 days per platform (adapter pattern, shared diagnostic logic).

#### Tier 2: Medium ROI

**Automated Fix Validation**
- **What:** Apply fix in a branch, trigger CI, verify fix resolves the failure before proposing to the user.
- **Why:** Eliminates the "user must review fix" limitation. The skill validates its own proposals.
- **Effort:** 3-5 days (branch management, CI trigger, result monitoring).

**Continuous Security Audit**
- **What:** Run P1 automatically on every workflow file change (pre-commit hook or CI step).
- **Why:** Shift-left security — catch anti-patterns before they reach the default branch.
- **Effort:** 2-3 days (hook integration, incremental audit, noise reduction).

#### Tier 3: Long-Term

**Organisation-Level Intelligence**
- Cross-repository workflow analysis, shared secret audit, and organisation-wide compliance reporting.

**Local CI Testing Integration**
- Integration with `act` for local pipeline simulation, reducing the push-wait-fail cycle.

**Regulatory Compliance Reporting**
- Automated mapping of CI/CD practices to FINRA, SOC2, and ISO 27001 requirements.

---

### X. Conclusion

#### What Was Demonstrated

This project demonstrates that prompt engineering is software engineering. The deliverable is 355 lines of markdown — no runtime code, no binaries, no dependencies beyond `gh` CLI. Yet it required the same rigor: problem decomposition, competitive analysis, scope decisions, architecture, safety invariants, testing, and review.

**Structured prompts as executable specifications.** SKILL.md is not a suggestion to Claude — it is a specification with testable contracts. The 67 automated checks verify that every behavioral rule, every procedure step, every safety invariant is present in the instruction set. This is regression testing for prompt engineering.

**Safety through behavioral contracts.** Five safety invariants maintained through explicit instructions, not code enforcement. The triaging contract (read freely, write with confirmation, destroy with double confirmation) provides the same guarantees as a permission system — through natural language instructions that Claude follows more reliably than formal decision trees.

**Honest scope calibration.** Six acknowledged limitations, each with impact, current mitigation, and North Star resolution. The skill does not claim to eliminate the push-wait-fail cycle — it shortens the diagnosis phase. The security audit does not claim completeness — it explicitly disclaims limitations in every report. The skill is a tool, not a gatekeeper.

#### The Five Pivots Tell the Story

1. **6 tiers → 3 rules** — Behavioral instructions beat formal classification for LLMs
2. **Declarative → Trigger phrases** — Match the framework's activation mechanism
3. **Scripts directory → Inline commands** — Don't create files for one-line operations
4. **Zizmor required → Zizmor optional** — Enrich when available, fall back when not
5. **Decision tree → Behavioral rules** — Natural language is the LLM's native interface

Each pivot simplified the design. The final skill is smaller, clearer, and more reliable than the initial design. Simplification through iteration is the meta-pattern.

#### Nothing Accidental

Every decision in this skill is documented with its trade-off:

- SKILL.md + references trades upfront loading for on-demand precision.
- No scripts trades convenience for zero maintenance overhead.
- Three rules trades formal completeness for LLM comprehension.
- Zizmor optional trades consistent depth for universal availability.
- Plugin structure trades directory convention for proper discovery.
- Structured output trades flexibility for consistency.
- Inline prerequisites trades per-invocation cost for never-skip reliability.

The depth of thought is the deliverable. The markdown is the proof.

---

### References (Task 3)

1. Rasheed et al. (2025). "Agents on the Bench: Large Language Model Agents as Software Engineering Interns." arxiv 2601.17413 — AI agents modify CI/CD config in only 3.25% of file changes.

2. Knight Capital Group — $440M loss in 45 minutes due to deployment failure (August 1, 2012).

3. CVE-2025-30066 — tj-actions/changed-files supply chain attack compromising 23,000+ repositories.

4. FINRA Regulatory Notice 15-09 — Guidance on algorithmic trading systems and change management requirements.

5. Claude Code Plugin Documentation — Plugin manifest structure, skill auto-activation, and trigger phrase format.

6. zizmor — https://github.com/woodruffw/zizmor — Security scanner for GitHub Actions.

7. actionlint — https://github.com/rhysd/actionlint — Static analysis for GitHub Actions workflow files.

### Appendix: Artifact Registry (Task 3)

| Artifact | Path | Notes |
|----------|------|-------|
| PRD | `docs/brainstorms/20260207-github-cicd-skill.prd.md` | Problem analysis and research |
| Specification | `docs/features/1-github-cicd-guardian/spec.md` | Requirements and acceptance criteria |
| Design | `docs/features/1-github-cicd-guardian/design.md` | Architecture and component design |
| Plan | `docs/features/1-github-cicd-guardian/plan.md` | Build order and phase structure |
| Tasks | `docs/features/1-github-cicd-guardian/tasks.md` | 10 tasks across 4 phases |
| Plugin Manifest | `.claude-plugin/plugin.json` | 5 lines, plugin discovery |
| SKILL.md | `skills/github-cicd-guardian/SKILL.md` | 238 lines, skill instructions |
| Failure Categories | `skills/github-cicd-guardian/references/failure-categories.md` | 39 lines, 6 categories |
| Security Checklist | `skills/github-cicd-guardian/references/security-checklist.md` | 73 lines, 8 anti-patterns |
| Validation Suite | `tests/validate_skill.sh` | 179 lines, 67 automated checks |
| Failure Log Fixtures | `tests/fixtures/sample-failure-logs.md` | 60 lines, 7 test fixtures |
| Vulnerable Workflow | `tests/fixtures/vulnerable-workflow.yml` | 48 lines, 8 embedded anti-patterns |
| Architecture Guide | `docs/architecture.md` | Technical onboarding guide |
| Knowledge Bank | `docs/knowledge-bank/claude-code-skill-patterns.md` | 12 learnings documented |
| Retrospective | `docs/features/1-github-cicd-guardian/.retro.md` | Process learnings |

---

## Task 4: SubTerminator

**Difficulty:** Hard
**Challenge prompt:** 瀏覽器自動控制任務 (Browser Automation Control Task)
**Project directory:** `subterminator/`
**Detailed report:** [`subterminator/REPORT.md`](subterminator/REPORT.md)

---

### I. Executive Summary

#### The Problem

Subscription services weaponize UX friction against cancellation. The industry term is "dark patterns" — retention offers, exit surveys, multi-step confirmations, buried settings, third-party billing redirects, and session timeouts — all designed to make cancellation harder than signup. Netflix requires 4-5 clicks through multiple pages. Other services are worse.

No production tool automates this with browser automation. Every subscription management service — Rocket Money, Trim, Chargeback, DoNotPay — uses human concierge operators for cancellation. The industry consensus is that browser automation doesn't work reliably against subscription services: Terms of Service prohibit it, bot detection blocks it, and UI changes break it faster than selectors can be maintained.

#### The Solution

A three-pillar architecture:

1. **MCP Orchestration** — An LLM (Claude/GPT-4) drives browser control via Microsoft's Playwright MCP server. The AI interprets page snapshots (accessibility trees, not DOM), decides the next action, and calls tools through the Model Context Protocol. No hardcoded selectors.

2. **Human Checkpoints** — Mandatory gates for authentication (login, CAPTCHA, MFA) and irreversible actions (final cancellation). These are structural — enforced by predicate-based conditions evaluated before every tool execution — not procedural ("remember to ask the user").

3. **Predicate-Based Service Configs** — Each service defines its behavior through callable predicates (`Callable[[ToolCall, NormalizedSnapshot], bool]`), not CSS selectors or hardcoded flows. Adding a new service means writing functions, not modifying engine code.

#### Scope Calibration

This is a mock-first MVP for Netflix. It is not a production cancellation service. This is a deliberate engineering decision, not a limitation.

Netflix's Terms of Service explicitly prohibit "any robot, spider, scraper or other automated means" for accessing their service. No sandbox or test environment exists — every test run risks account termination. Bot detection probability is HIGH (Playwright has "Medium Detection Rate" per Castle.io research; combined with Netflix's proprietary anti-bot measures, the effective risk is HIGH). Building against real Netflix as the primary target would mean: one test run per development iteration, potential account loss, and ToS violation submitted as assessment work.

The mock-first pivot (documented in brainstorm iteration 2, `docs/brainstorms/2026-02-03-subterminator-research.prd.md`) redirects engineering effort from fighting bot detection to building a robust orchestration engine. The mock replicates Netflix's actual flow structure; the same orchestration code works against both targets.

#### Differentiator

No open-source tool uses LLM-driven MCP orchestration for subscription cancellation. The combination of:
- AI page interpretation via accessibility tree (not screenshots or DOM selectors)
- Virtual tools (`complete_task`, `request_human_approval`) as LLM-callable functions
- Predicate-based checkpoint system evaluated before every tool execution
- Single-tool-per-turn enforcement preventing runaway automation

...is novel. Every existing cancellation service relies on human operators. This system demonstrates that AI-driven browser control is architecturally feasible — and shows exactly why it isn't yet production-ready.

#### Delivery Metrics

| Metric | Value |
|--------|-------|
| Tests | 337 |
| Coverage | 89% |
| Brainstorm iterations | 9 |
| Architectural pivots | 4 |
| Services implemented | 1 (Netflix) |
| Source LOC | ~3,503 |
| Test LOC | ~4,519 |
| Unit test files | 20 |
| Integration test files | 1 |
| Specification artifacts | 5 (PRD, Spec, Design, Plan, Tasks) |

---

### II. Problem Decomposition

#### Dark Pattern Taxonomy

Subscription cancellation flows exploit UX friction through well-documented patterns:

| Pattern | Description | Netflix Example |
|---------|-------------|-----------------|
| **Retention offers** | Discount or plan change to prevent cancellation | "Before you go — get 50% off for 3 months" |
| **Exit surveys** | Mandatory survey before proceeding | "Why are you leaving?" with radio buttons |
| **Multi-step confirmation** | 4-5 clicks through separate pages | Account → Cancel → Survey → Confirm → Done |
| **Third-party billing redirect** | Cannot cancel through the service | "Billed through iTunes — cancel there" |
| **Session timeouts** | Flow resets if user pauses too long | Re-authentication required mid-flow |
| **A/B testing** | Different cancellation paths for different users | Button text, page order, and offer content vary |

Third-party billing deserves special attention. Apple TV+, Google Play bundles, and carrier bundles (T-Mobile) are not edge cases — they are likely the most common billing method for mobile-first subscribers. When detected, the correct response is not to attempt automation but to inform the user they must cancel through the billing provider. This is handled as a first-class detection case, not an error path.

#### Why Automation Fails

Research conducted in brainstorm iteration 2 (`2026-02-03-subterminator-research.prd.md`) revealed three blockers:

| Blocker | Evidence | Impact |
|---------|----------|--------|
| **Netflix ToS prohibition** | "Any robot, spider, scraper or other automated means" explicitly prohibited | Account termination risk |
| **No sandbox environment** | Netflix provides no test/staging environment for developers | Cannot iterate without real subscription risk |
| **HIGH bot detection** | Playwright has "Medium Detection Rate" (Castle.io); Netflix uses proprietary CDN (Open Connect) with undocumented anti-bot measures | Combined risk is HIGH |

The industry consensus is clear: every production cancellation service (Rocket Money, Trim, Chargeback, DoNotPay) uses human operators. No production tool automates Netflix cancellation via browser.

#### The Real Question

The real question is not "can we click buttons?" — any Playwright script can click buttons. The real question is: **can AI adapt to unknown UIs while keeping humans in control of irreversible actions?**

CSS selectors break when Netflix A/B tests a new layout. State machines break when a new retention offer appears. Hardcoded flows break on any change. The only approach that survives UI change is semantic interpretation — reading the page the way a human would and deciding what to do next.

This reframes the project from "Netflix cancellation tool" to "AI browser orchestration engine with Netflix as proof of concept."

---

### III. Strategic Design Decisions

Seven decisions shape the architecture. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

#### Decision 1: Mock-First Architecture

**Context.** Netflix's Terms of Service prohibit automation. No sandbox exists. Bot detection probability is HIGH. Each test run risks account termination.

**Analysis.** Building against real Netflix as the primary target means: (a) one test attempt per development iteration (cannot re-cancel an already-cancelled subscription), (b) ToS violation submitted as professional assessment work, (c) bot detection may block the tool entirely on Day 3, leaving no deliverable. The research brainstorm (`2026-02-03-subterminator-research.prd.md`) identified this as a critical blocker.

**Decision.** Build against realistic mock Netflix pages as the primary deliverable. Real Netflix becomes optional validation, not a dependency.

**Trade-off.** Mock-first means the tool is not validated against production Netflix. Compensated by: (a) mock pages replicate Netflix's actual flow structure (account → cancel → survey → confirm), (b) the same orchestration code works against both targets (`--target mock|live`), (c) the engineering value is in the orchestration engine, not in Netflix-specific plumbing.

**Evidence.** The mock-first pivot was the single most important process decision. It enabled unlimited iteration (337 tests, 89% coverage) instead of 1-2 cautious attempts against real Netflix. Every subsequent design decision — AI-first interpretation, MCP orchestration, predicate-based configs — was only possible because mock-first removed the testing bottleneck.

#### Decision 2: MCP Orchestration over Custom Browser Tools

**Context.** The original design (brainstorm iteration 6, `20260205-ai-mcp-redesign.prd.md`) proposed building 7 custom browser tools, a custom element reference system, a custom snapshot format, and a custom action executor — 52 implementation tasks totaling ~3,000 LOC.

**Analysis.** Microsoft's Playwright MCP server already provides `browser_snapshot`, `browser_click`, `browser_type`, `browser_navigate`, and 10+ additional tools. It handles element references (`ref=s1e3`), accessibility tree snapshots, and screenshot capture. Building these from scratch is unnecessary when a production-grade, Microsoft-backed implementation exists.

**Decision.** Reuse Playwright MCP's 15+ tools. Build only the orchestration layer: task runner, checkpoint system, LLM client, and service configs.

**Trade-off.** Dependency on external MCP server (Node.js/npx required). Compensated by: (a) ~500 LOC of orchestration code instead of ~3,000 LOC of browser plumbing, (b) 15 tasks instead of 52, (c) Playwright MCP is Microsoft-backed and actively maintained, (d) the orchestration layer is the differentiator, not the browser tools.

**Evidence.** The comparison from `20260205-orchestrating-browser-mcps.prd.md`:

| Aspect | Original Design | MCP Approach |
|--------|-----------------|--------------|
| Tasks | 52 | ~15 |
| Browser tools | Build 7 custom | Reuse 15+ existing |
| Element refs | Custom registry | Playwright's ref system |
| Snapshots | Custom format | Accessibility tree from MCP |
| Code to write | ~3,000 LOC | ~500 LOC |

#### Decision 3: AI-First over Heuristic-First

**Context.** The original design (`docs/features/001-subterminator-cli/design.md`) used a tiered detection strategy: (1) URL pattern matching, (2) text-based heuristics, (3) Claude Vision as fallback.

**Analysis.** URL patterns and text heuristics work for the known flow but break on any variation. Netflix A/B tests different cancellation paths, button text, and page layouts. CSS selectors like `[data-uia='action-cancel-membership']` break when Netflix changes its data attributes. The brainstorm iteration 4 (`20260204-browser-automation-architecture.prd.md`) identified that accessibility-tree-based interpretation is 80-90% smaller in token usage than raw DOM and survives layout restructuring.

**Decision.** AI interprets every page via accessibility tree snapshot. The LLM decides the next action — no hardcoded state-action mapping. Heuristics are removed from the critical path; the service config provides hints to the LLM via `system_prompt_addition`, not selector tables.

**Trade-off.** Higher per-run cost (~$0.50-2.00 per run in API calls) and slower execution (one API call per turn). Justified because: (a) accuracy and adaptability are more important than speed for subscription cancellation, (b) the cost is acceptable for a task performed once per service, (c) the system degrades gracefully when the LLM is uncertain (requests human approval).

**Evidence.** The system prompt provides the service goal and rules; the accessibility tree provides the page state. The LLM reasons about both and calls the appropriate tool. When Netflix changes its button text from "Finish Cancellation" to "Confirm Cancellation," the LLM adapts — no code change required. A selector-based system would break.

#### Decision 4: Single-Tool-Per-Turn Enforcement

**Context.** LLMs can generate multiple tool calls in a single response. Executing all of them without review risks unintended consequences.

**Analysis.** In browser automation, each action changes the page state. Clicking a button navigates to a new page; the next action must be chosen based on the new page, not the old one. Batch-executing multiple clicks from a single LLM response means actions 2-N operate on stale assumptions about page state. More critically, runaway automation — where the LLM rapidly executes a series of actions without human oversight — is the primary safety risk.

**Decision.** Execute exactly one tool per turn. After each tool call, refresh the page snapshot (if navigation occurred) and let the LLM re-evaluate (`task_runner.py`).

**Trade-off.** Slower execution (one API round-trip per action). Compensated by: (a) checkpoint enforcement is possible because every action is individually reviewed, (b) stale element references cannot cause misclicks, (c) the user can observe progress in real-time, (d) max turns limit (20) bounds total execution time.

**Evidence.** The orchestration loop in `task_runner.py` processes `response.tool_calls[0]` only — the first tool call. Combined with the 20-turn maximum and SIGINT handling, this prevents the system from taking more actions than the user expects.

#### Decision 5: Virtual Tools

**Context.** The LLM needs a way to signal "I'm done" or "I need human help." These are not browser actions — Playwright MCP has no concept of task completion or human approval.

**Analysis.** MCP tools are browser actions (`browser_click`, `browser_navigate`, etc.). But the orchestration layer needs meta-actions: "the task is complete" and "I need human approval before proceeding." These could be implemented as special message patterns (e.g., "DONE: success"), but that requires parsing natural language — fragile and unreliable.

**Decision.** Inject two virtual tools into the tool list sent to the LLM:
- `complete_task(status: "success"|"failed", reason: str)` — signals task completion
- `request_human_approval(action: str, reason: str)` — requests explicit human approval

These are handled by the orchestration layer, not forwarded to Playwright MCP.

**Trade-off.** Tool list grows by 2 (now ~17 tools total, well under the 30-tool threshold identified in MCP research). The benefit — structured, parseable completion signals — eliminates an entire class of natural-language-parsing bugs.

**Evidence.** When the LLM detects the "Your cancellation is complete" page, it calls `complete_task(status="success", reason="Cancellation confirmed page detected")`. The orchestration layer then verifies completion by checking the service config's `success_indicators` — a second check beyond the LLM's judgment.

#### Decision 6: Predicate-Based Service Configs

**Context.** Adding new services should not require modifying the orchestration engine.

**Analysis.** The original design (`services/netflix.py` in design.md) used CSS selector lists:
```python
ServiceSelectors(
    cancel_link=["[data-uia='action-cancel-membership']", ...],
    decline_offer=["[data-uia='continue-cancel-btn']", ...],
)
```
These break on UI changes and couple the service config to DOM structure. The MCP orchestration approach doesn't use selectors — the LLM finds elements by interpreting the accessibility tree. What the service config needs to express is: "when should we require human approval?" and "how do we verify completion?" — questions answered by predicates, not selectors.

**Decision.** Service configs use callable predicates:
```python
ServiceConfig(
    checkpoint_conditions=[
        lambda tool, snap: "finish cancel" in snap.content.lower(),
    ],
    success_indicators=[
        lambda s: "cancelled" in s.content.lower(),
    ],
    auth_edge_case_detectors=[
        lambda s: "/login" in s.url,
    ],
)
```

**Trade-off.** Predicates are less declarative than YAML configs — they require Python knowledge to write. Compensated by: (a) predicates can express arbitrary conditions, not just pattern matching, (b) predicates are testable in isolation without a browser, (c) adding a new service is documented as a how-to guide in `README_FOR_DEV.md`.

**Evidence.** The Netflix service config (`mcp_orchestrator/services/netflix.py`) defines all Netflix-specific behavior through predicates. The `TaskRunner` evaluates these predicates generically — it has no Netflix-specific code. Adding a Disney+ config requires only a new file with new predicates, not engine changes.

#### Decision 7: Human Checkpoints as Non-Negotiable

**Context.** Browser automation that acts without human oversight on irreversible actions (cancelling a paid subscription, deleting account data) is unsafe by design.

**Analysis.** The safety invariant is: **no irreversible action without human confirmation**. This must be structural (enforced by the system architecture) rather than procedural (relying on the LLM to remember to ask). Three categories require human intervention:

| Category | Detection | Response |
|----------|-----------|----------|
| **Authentication** | Login page, CAPTCHA, MFA detected in snapshot | Pause and wait for human to complete in browser |
| **Final confirmation** | Checkpoint predicates match (e.g., "finish cancellation" on page) | Show screenshot, require explicit approval |
| **Unknown state** | No-action count >= 3 (LLM unable to determine next action) | Fail gracefully, provide manual steps |

**Decision.** Checkpoints are evaluated before every MCP tool execution. Authentication detection runs first (three-tier: login, CAPTCHA, MFA), then checkpoint conditions from the service config. If either triggers, the tool call is intercepted before execution.

**Trade-off.** User must interact with the CLI at least twice (authentication + final confirmation) even in the happy path. This is the correct trade-off — the cost of one interrupted user flow is lower than the cost of one unintended cancellation.

**Evidence.** The checkpoint flow in `checkpoint.py`:
1. `detect_auth_edge_case(snapshot, config)` — returns `"login"`, `"captcha"`, `"mfa"`, or `None`
2. If auth detected: `wait_for_auth_completion()` — pauses until user completes auth in browser
3. `should_checkpoint(tool, snapshot, config)` — evaluates service predicates
4. If checkpoint triggered: `request_approval(tool, snapshot)` — shows checkpoint UI with screenshot

---

### IV. Architecture as Risk Mitigation

The architecture is not just code organization — it is a risk mitigation strategy. Each structural choice addresses a specific failure mode.

#### Runaway Prevention

**Risk.** LLM autonomously executes a rapid series of browser actions, clicking through the cancellation flow without human oversight.

**Mitigation.** Three independent safeguards:
1. **Single-tool-per-turn** — Only one action per LLM response is executed (`task_runner.py`)
2. **Max turns limit (20)** — Hard cap on total actions before forced termination
3. **SIGINT handling** — Ctrl+C cleanly terminates the orchestration loop (exit code 130)

**Verification.** If all three fail simultaneously, the worst case is 20 browser actions. With checkpoints enforced before irreversible actions, the system cannot complete a cancellation without human approval even in this failure mode.

#### UI Change Resilience

**Risk.** Netflix changes its cancellation flow, breaking the tool.

**Mitigation.** The LLM interprets the accessibility tree semantically, not through selectors. The accessibility tree represents the page as a hierarchy of roles and names:
```
- button "Cancel Membership" [ref=s1e5]
- heading "Before you go" [ref=s1e8]
- button "Continue to Cancel" [ref=s1e12]
```
When Netflix changes `"Finish Cancellation"` to `"Confirm Cancellation"`, the LLM adapts — it understands both phrases mean "proceed with cancellation." A selector-based system would break.

#### Stale Reference Prevention

**Risk.** Element references become invalid after page navigation, causing clicks on wrong elements.

**Mitigation.** Playwright MCP's `ref` values are valid for one action only. After any navigation tool (`browser_navigate`, `browser_click` that triggers navigation), the orchestration loop refreshes the snapshot. The LLM receives fresh references for the new page state. Element refs from the previous page are not reusable — this is enforced by Playwright MCP's design, not by our code.

#### Safety Invariant

**Risk.** Automated cancellation of a subscription the user did not intend to cancel.

**Mitigation.** The safety invariant is structural: `CheckpointHandler.should_checkpoint()` is called before every MCP tool execution. The checkpoint condition for final cancellation (`"finish cancel" in snapshot.content.lower()`) is a predicate evaluated on the live page state, not a flag that can be toggled. Even if the LLM hallucinates or misinterprets the page, the checkpoint prevents execution without human approval.

#### Authentication Edge Case Detection

**Risk.** Automation encounters a login page, CAPTCHA, or MFA challenge and either fails silently or attempts to bypass it.

**Mitigation.** Three-tier detection in `checkpoint.py`:
1. **Login** — URL contains `/login` or snapshot contains sign-in elements
2. **CAPTCHA** — Snapshot contains CAPTCHA-related content
3. **MFA** — Snapshot contains multi-factor authentication prompts

When any tier triggers, the system pauses and prompts the user to complete authentication in the browser window. The orchestration loop waits, then refreshes the snapshot and continues.

---

### V. The Four Pivots

The system evolved through four architectural pivots. Each was triggered by research findings, not random exploration. Each preserved what worked and discarded what didn't.

#### Pivot 1: SubStretcher Plugin to SubTerminator CLI

**Date:** January 31, 2026
**Documented in:** `docs/brainstorms/2026-01-31-vici-challenge.md`

**Trigger.** The original concept was a browser extension (SubStretcher Plugin) that extracts billing data and auto-cancels subscriptions. A Chrome extension requires: extension manifest, content scripts, popup UI, Chrome Web Store distribution, and cross-browser testing. None of this demonstrates AI orchestration engineering.

**What was preserved:**
- Core concept: AI-driven subscription cancellation
- Config-driven service definitions
- Human-in-the-loop safety model

**What was discarded:**
- Chrome extension architecture
- TypeScript (switched to Python)
- Billing data extraction (focused purely on cancellation)
- Multi-service inventory (focused on Netflix only)

**Why.** A CLI tool with Playwright is a cleaner demo for an engineering assessment. No extension installation friction, no Chrome Web Store, no cross-browser concerns. The AI orchestration engine — the actual differentiator — is the same regardless of delivery mechanism.

#### Pivot 2: Live Netflix to Mock-First

**Date:** February 3, 2026
**Documented in:** `docs/brainstorms/2026-02-03-subterminator-research.prd.md`

**Trigger.** Research revealed three critical blockers: Netflix ToS prohibition, no sandbox environment, HIGH bot detection probability. Building against real Netflix meant 1-2 test attempts total, with risk of account termination.

**What was preserved:**
- Netflix as the target service (flow structure, page states)
- Same orchestration code for both mock and live targets
- Human checkpoint system

**What was discarded:**
- Real Netflix as primary development target
- Live E2E testing as the primary validation strategy
- Assumption that "disclaimer" mitigates ToS risk

**Why.** Mock-first enabled unlimited iteration (337 tests) instead of 1-2 cautious attempts. The engineering value is in the orchestration engine, not in successfully clicking Netflix's actual buttons. This was the single most important process decision.

#### Pivot 3: State Machine to AI Agent

**Date:** February 4-5, 2026
**Documented in:** `docs/brainstorms/20260204-browser-automation-architecture.prd.md`, `20260205-ai-driven-browser-control.prd.md`

**Trigger.** The state machine approach (`core/states.py`) with hardcoded selectors (`ServiceSelectors`) broke on any UI variation. The `data-uia` attributes Netflix uses are not stable across A/B tests. Research into browser automation solutions (OpenClaw, browser-use, Skyvern) revealed that accessibility-tree-based interpretation is 80-90% smaller in token usage than raw DOM and survives layout restructuring.

**What was preserved:**
- State concepts (the page IS in a state — login, retention offer, etc.)
- Checkpoint triggers (now as predicates instead of state transitions)
- Session logging and screenshot capture

**What was discarded:**
- `python-statemachine` library (explicit state transitions)
- `ServiceSelectors` dataclass (CSS selectors per action)
- Tiered detection (URL → text → AI fallback)
- Hardcoded state-action mapping

**Why.** The AI agent approach flips the architecture: instead of "detect state, execute hardcoded action," it becomes "interpret page, decide action." This survives UI changes because the LLM interprets semantically. The state machine was a reasonable starting point that revealed its own limitations through implementation.

#### Pivot 4: Custom Browser Tools to MCP Orchestration

**Date:** February 5, 2026
**Documented in:** `docs/brainstorms/20260205-ai-mcp-redesign.prd.md`, `20260205-orchestrating-browser-mcps.prd.md`

**Trigger.** The AI-first redesign (Pivot 3) still proposed building 7 custom browser tools, a custom element reference system, and a custom snapshot format — 52 tasks, ~3,000 LOC. Research revealed that Microsoft's Playwright MCP server already provides all of this.

**What was preserved:**
- AI-as-orchestrator pattern (the LLM decides, we execute)
- Single-tool-per-turn enforcement
- Human checkpoint system
- Service config pattern

**What was discarded:**
- Custom browser tools (7 planned)
- Custom element reference registry
- Custom snapshot format and pruning
- ~2,500 LOC of planned browser plumbing

**Why.** The MCP PRD (`20260205-orchestrating-browser-mcps.prd.md`) states it clearly: "This is unnecessary when Playwright MCP already provides `browser_snapshot`, `browser_click`, `browser_type`, etc." The value-add is orchestration — human checkpoints, completion verification, service configs, and the task runner loop. Building browser tools from scratch would be reinventing what Microsoft already ships.

---

### VI. Acknowledged Limitations

Ten limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight.

#### L1: Netflix-Only

- **Impact:** Only one service is implemented. Extensibility is designed and documented but not exercised in production.
- **Current Mitigation:** The predicate-based service config architecture (`ServiceConfig` dataclass) is designed for multi-service support. Adding a new service is documented as a how-to guide in `README_FOR_DEV.md`. Disney+, Hulu, and Spotify are listed as "coming soon" in the interactive service selection menu.
- **North Star:** 5+ services with shared orchestration engine, each requiring only a new config file.

#### L2: Mock-First (Real Netflix Not Validated)

- **Impact:** The tool works against mock Netflix pages. Real Netflix is optional and not validated in CI.
- **Current Mitigation:** Mock pages replicate Netflix's actual flow structure (account page, retention offer, exit survey, final confirmation, completion page). The same orchestration code works against both targets via `--target mock|live`. The mock is not a crude placeholder.
- **North Star:** Walk-forward validation against real services in a sandboxed environment with disposable test accounts.

#### L3: No CAPTCHA Solving

- **Impact:** When CAPTCHA is encountered, the tool cannot proceed automatically.
- **Current Mitigation:** Three-tier auth detection pauses the flow and prompts the user to complete the CAPTCHA in the browser window. This is the correct response — CAPTCHA solving services violate ToS and are ethically questionable.
- **North Star:** Maintain pause-and-wait as the correct approach. CAPTCHA solving is a non-goal.

#### L4: No Credential Management

- **Impact:** User must be pre-logged in or complete login manually when prompted.
- **Current Mitigation:** Browser session reuse via `--cdp-url` (connect to existing Chrome) or `--profile-dir` (persistent browser profiles). After one manual login, the session persists across runs.
- **North Star:** Integration with system credential vaults (macOS Keychain, 1Password CLI) for automated login with explicit user consent.

#### L5: Single Cancellation at a Time

- **Impact:** Cannot cancel multiple subscriptions concurrently.
- **Current Mitigation:** One service per run. Acceptable for the use case — subscription cancellation is not a batch operation.
- **North Star:** Sequential multi-service support (cancel Netflix, then Disney+, then Hulu) in a single session.

#### L6: English-Only

- **Impact:** No internationalization. Page interpretation assumes English text.
- **Current Mitigation:** LLMs are multilingual — the accessibility tree interpretation may work in other languages, but this is untested and unsupported.
- **North Star:** Explicit multi-language support with language-specific service configs and prompts.

#### L7: No Subscription Detection or Monitoring

- **Impact:** The user must know which subscriptions they have. The tool cancels; it does not discover.
- **Current Mitigation:** Out of scope. Subscription detection requires accessing billing pages for every potential service — a different product entirely.
- **North Star:** Integration with bank/credit card transaction APIs (Plaid) for automatic subscription discovery.

#### L8: Linear API Cost (~$0.50-2.00 per Run)

- **Impact:** Each run costs money in LLM API calls. 10+ screenshots per run at ~1,334 tokens per image.
- **Current Mitigation:** Acceptable for a task performed once per service. No caching or optimization implemented.
- **North Star:** Snapshot caching, prompt optimization, and model selection (use cheaper models for simple pages, expensive models for complex ones).

#### L9: Bot Detection Unmitigated for Live Mode

- **Impact:** Real Netflix may detect and block the automation.
- **Current Mitigation:** Playwright stealth settings are available but not guaranteed to evade detection. Mock-first approach means live mode is optional validation, not a dependency.
- **North Star:** Browser extension mode (Pivot 1 concept) where the tool controls the user's existing browser session — no new browser to detect.

#### L10: No Mobile App Subscription Support

- **Impact:** Cannot cancel subscriptions managed through iOS App Store or Google Play Store.
- **Current Mitigation:** Third-party billing detection identifies these cases and provides manual cancellation instructions for the correct platform.
- **North Star:** Integration with Apple/Google subscription management APIs (if they become available) or guided in-app cancellation flows.

---

### VII. Validation Strategy

#### Test Pyramid

```
                    +---------------+
                    |     E2E       |  Manual validation
                    |   (real)      |  against real Netflix
                    +---------------+
               +-------------------------+
               |      Integration        |  1 test file against
               |    (mock server)        |  orchestration flow
               +-------------------------+
          +-------------------------------------+
          |            Unit Tests               |  20 test files for
          |     (pure logic, no I/O)            |  all components
          +-------------------------------------+
```

#### Coverage by Component

| Component | Test Files | Approach |
|-----------|-----------|----------|
| MCP Orchestrator | `tests/unit/mcp_orchestrator/` | AsyncMock for async operations, mock MCP client |
| CLI Layer | `tests/unit/cli/` | Typer's CliRunner for integration, mock orchestrator |
| Services | `tests/unit/mcp_orchestrator/` | Predicate evaluation with synthetic snapshots |
| Core Utilities | `tests/unit/core/`, `tests/unit/utils/` | Direct function testing |
| Integration | `tests/integration/` | End-to-end orchestration with mock components |

#### Key Test Patterns

1. **AsyncMock for async code** — All MCP and LLM interactions are async. Tests use `unittest.mock.AsyncMock` with `pytest-asyncio` for full async test execution.

2. **CliRunner for CLI integration** — Typer's test client validates command parsing, exit codes, and output formatting without launching a browser.

3. **Parametrized fixtures** — Service configs, snapshot formats, and error conditions are tested across multiple variants using `@pytest.mark.parametrize`.

4. **Synthetic snapshots** — `NormalizedSnapshot` objects with controlled URLs, titles, and content for testing predicates and checkpoint conditions without browser state.

#### Metrics

| Metric | Value |
|--------|-------|
| Total tests | 337 |
| All passing | Yes |
| Coverage | 89% |
| Test execution time | ~5.5 seconds |

---

### VIII. Process and Delivery Metrics

#### Five-Stage Specification Pipeline

The system was built through a 5-stage specification pipeline. Each stage produced a versioned artifact with formal review.

| Stage | Artifact | Key Output |
|-------|----------|------------|
| Brainstorm/PRD | 9 brainstorm documents | Problem space exploration, research findings, architectural pivots |
| Specification | `spec.md` | Functional requirements, page states, error handling, test scenarios |
| Design | `design.md` | Component architecture, data flow, service layer design |
| Plan | `plan.md` | Build order, phase dependencies, TDD enforcement |
| Tasks | `tasks.md` | Individual implementation tasks with acceptance criteria |

#### Nine Brainstorm Iterations

The brainstorm documents tell the story of the project's evolution:

| # | Date | Document | Key Contribution |
|---|------|----------|------------------|
| 1 | Jan 31 | `2026-01-31-vici-challenge.md` | Initial concept: SubStretcher Plugin → CLI pivot |
| 2 | Feb 3 | `2026-02-03-subterminator-research.prd.md` | **Research pivot**: Live Netflix → Mock-first |
| 3 | Feb 3 | `2026-02-03-interactive-service-selection.prd.md` | Interactive CLI design |
| 4 | Feb 3 | `2026-02-03-byom-llm-abstraction.prd.md` | Model-agnostic LLM client design |
| 5 | Feb 3 | `2026-02-03-ci-cd-auto-merge.prd.md` | CI/CD pipeline design |
| 6 | Feb 4 | `20260204-browser-automation-architecture.prd.md` | **Architecture pivot**: Selectors → Accessibility tree |
| 7 | Feb 5 | `20260205-ai-driven-browser-control.prd.md` | **AI pivot**: Heuristic-first → AI-first |
| 8 | Feb 5 | `20260205-ai-mcp-redesign.prd.md` | AI-led MCP server design |
| 9 | Feb 5 | `20260205-orchestrating-browser-mcps.prd.md` | **MCP pivot**: Custom tools → Playwright MCP reuse |

The most impactful iterations were #2 (research findings that forced mock-first), #6 (accessibility tree over selectors), and #9 (reuse Playwright MCP instead of building custom tools).

#### Front-Loaded Research Prevented Wasted Effort

The most important process insight: **front-loaded research in iteration #2 prevented two critical failures:**

1. **ToS violation.** Without the research pivot, the project would have been built against real Netflix — submitting ToS-violating code as professional assessment work.

2. **Testing bottleneck.** Without mock-first, each test run would require a real subscription cancellation. At most 1-2 real tests are possible (you can't re-cancel an already-cancelled subscription). The 337 tests in the current suite would have been impossible.

The research brainstorm took approximately half a day. It saved the remaining 6 days from being spent on an approach that could not produce a reliable deliverable.

#### Patterns Worth Documenting

1. **Research before building.** The Feb 3 research brainstorm identified three critical blockers before any code was written. Every production cancellation service uses human operators — knowing this before coding prevented building a tool that the industry has already proven unviable in production.

2. **Mock-first as an engineering strategy, not a shortcut.** Mock-first is often dismissed as "not testing the real thing." In this case, it's the opposite — mock-first enables testing that is impossible with the real thing (no sandbox, no re-cancellation, account termination risk).

3. **Progressive architecture through brainstorms.** The 9 brainstorm iterations show architecture evolving through evidence: selectors → accessibility tree → AI-first → MCP orchestration. Each step was motivated by research findings, not refactoring for its own sake.

4. **Predicate-based configs over selector-based configs.** When the execution engine is AI-driven, the service config should express conditions (predicates), not instructions (selectors). This insight emerged from the architecture pivot and would not have been apparent without first building the selector-based approach.

#### Anti-Patterns to Avoid

1. **Building before researching.** If coding had started on Day 1 with the original plan (Chrome extension + real Netflix + CSS selectors), every line would have been thrown away by Day 3.

2. **Sunk cost on deprecated code.** The original `core/engine.py` (~400 LOC) and `core/agent.py` (~870 LOC) represented significant investment. The MCP pivot deprecated both. The correct response was to build the new approach in a new package (`mcp_orchestrator/`), not to try to retrofit the old code.

3. **Over-engineering before validation.** The AI-MCP redesign brainstorm (iteration 8) proposed a full custom MCP server with 7 tools, element registries, and snapshot factories — 52 tasks. The very next brainstorm (iteration 9) recognized that Playwright MCP already provides all of this. The 24-hour gap between "build everything custom" and "reuse what exists" highlights the value of continued research.

---

### IX. North Star Roadmap

#### Tier 1: Highest ROI

**Multi-Service Support**
- **What:** Add Disney+, Hulu, Spotify configs using the predicate-based service config pattern.
- **Why:** The architecture is designed for this but not yet exercised. Proving multi-service support validates the extensibility claim.
- **Effort:** 1-2 days per service (config + mock pages + tests).

**Walk-Forward Validation on Real Sites**
- **What:** Disposable test accounts for real-site validation in CI. Run against real Netflix with a dedicated test subscription.
- **Why:** Mock-first enables development; real-site validation proves production viability.
- **Effort:** 2-3 days (account management, test infrastructure, flaky test handling).

#### Tier 2: Medium ROI

**Browser Extension Mode**
- **What:** Control the user's existing Chrome browser session via Chrome DevTools Protocol, instead of launching a new Playwright-controlled browser.
- **Why:** Eliminates bot detection (the browser IS the user's browser), eliminates re-authentication (existing session), and addresses L4 and L9 simultaneously.
- **Effort:** 3-5 days (CDP connection, extension relay, session management).

**Credential Vault Integration**
- **What:** Integration with macOS Keychain, 1Password CLI, or Bitwarden CLI for automated login with explicit user consent.
- **Why:** Addresses L4 (no credential management) without building a custom credential store.
- **Effort:** 2-3 days per vault provider.

#### Tier 3: Long-Term

**Subscription Monitoring**
- Integration with Plaid or bank APIs for automatic subscription discovery. Different product, same platform.

**Mobile App Subscription Support**
- Guided cancellation flows for iOS App Store and Google Play Store subscriptions.

**Cost Optimization**
- Snapshot caching, prompt compression, model tiering (cheap models for simple pages, expensive for complex).

---

### X. Conclusion

#### What Was Demonstrated

This project is an exercise in engineering design thinking applied to browser automation and AI orchestration. The goal was never to build the most complete cancellation tool — it was to build the most thoughtful one.

**Research-driven architecture.** Nine brainstorm iterations, each motivated by research findings. The mock-first pivot prevented ToS violation and testing bottleneck. The MCP pivot eliminated 2,500 LOC of unnecessary browser plumbing. The AI-first pivot replaced brittle selectors with semantic interpretation. None of these pivots were random — each was documented with trigger, preserved elements, discarded elements, and rationale.

**Safety as structure, not procedure.** Human checkpoints are not a feature that can be disabled — they are evaluated before every tool execution by design. Single-tool-per-turn is not a suggestion to the LLM — it is enforced by the orchestration loop. Authentication detection is not a warning — it pauses the system and waits. The safety invariant is architectural: no irreversible action without human confirmation.

**Honest scope calibration.** Ten acknowledged limitations, each with impact, current mitigation, and North Star resolution. The system does not pretend to solve problems it does not solve. Mock-first is stated as a deliberate decision, not hidden as a limitation. API cost ($0.50-2.00 per run) is documented, not minimized. Bot detection is acknowledged as HIGH risk, not dismissed as "handled by stealth."

**Intellectual honesty about the industry.** Every production cancellation service uses human operators. No tool automates Netflix cancellation via browser in production. Stating this upfront — and then demonstrating an architecture that shows why it's worth trying — is more credible than pretending the problem is solved.

#### The Four Pivots Tell the Story

1. **SubStretcher Plugin → SubTerminator CLI** — Focus on the orchestration engine, not the delivery mechanism
2. **Live Netflix → Mock-first** — Research revealed blockers; mock-first enabled the project to exist
3. **State Machine → AI Agent** — Hardcoded selectors break; AI interpretation survives
4. **Custom Tools → MCP Orchestration** — Don't build what Microsoft already ships

Each pivot discarded investment (original architecture, CSS selectors, custom browser tools) in favor of a better approach. The willingness to pivot — four times in seven days — is itself a demonstration of engineering judgment.

#### Nothing Accidental

Every decision in this system is documented with its trade-off:

- Mock-first trades real-site validation for unlimited test iteration.
- MCP orchestration trades custom control for 5x less code.
- AI-first trades per-run cost for UI change resilience.
- Single-tool-per-turn trades speed for checkpoint enforcement.
- Virtual tools trade 2 extra tools in the list for structured completion signals.
- Predicate configs trade declarative simplicity for arbitrary expressiveness.
- Human checkpoints trade automation speed for safety guarantees.

The depth of thought is the deliverable. The code is the proof.

---

### References (Task 4)

1. Netflix Terms of Use — "Any robot, spider, scraper or other automated means" prohibition.

2. Castle.io (2025). "From Puppeteer Stealth to Nodriver: How Anti-Detect Frameworks Evolved to Evade Bot Detection." — Playwright "Medium Detection Rate" finding.

3. Microsoft Playwright MCP — https://github.com/microsoft/playwright-mcp — Browser automation MCP server with accessibility tree snapshots and element references.

4. MCP Python SDK — https://github.com/modelcontextprotocol/python-sdk — Official Model Context Protocol client library.

5. Speakeasy MCP Guide — Tool design research: 30-tool threshold, domain-aware actions, poka-yoke design.

6. Anthropic (2025). "Building Effective Agents." — Agent architecture patterns and tool design best practices.

7. Rocket Money — https://help.rocketmoney.com — Human concierge model for subscription cancellation (industry standard).

8. Agent Browser — https://agent-browser.dev/ — Snapshot + refs pattern research (200-400 tokens vs 3,000-5,000 for full DOM).

9. Netify — Netflix infrastructure analysis (Open Connect proprietary CDN, undocumented anti-bot measures).

### Appendix: Artifact Registry (Task 4)

| Artifact | Path | Notes |
|----------|------|-------|
| Brainstorm 1 | `docs/brainstorms/2026-01-31-vici-challenge.md` | Initial concept |
| Brainstorm 2 | `docs/brainstorms/2026-02-03-subterminator-research.prd.md` | Research pivot (mock-first) |
| Brainstorm 3 | `docs/brainstorms/2026-02-03-interactive-service-selection.prd.md` | Interactive CLI |
| Brainstorm 4 | `docs/brainstorms/2026-02-03-byom-llm-abstraction.prd.md` | Model-agnostic LLM |
| Brainstorm 5 | `docs/brainstorms/2026-02-03-ci-cd-auto-merge.prd.md` | CI/CD pipeline |
| Brainstorm 6 | `docs/brainstorms/20260204-browser-automation-architecture.prd.md` | Architecture pivot |
| Brainstorm 7 | `docs/brainstorms/20260205-ai-driven-browser-control.prd.md` | AI-first pivot |
| Brainstorm 8 | `docs/brainstorms/20260205-ai-mcp-redesign.prd.md` | MCP server design |
| Brainstorm 9 | `docs/brainstorms/20260205-orchestrating-browser-mcps.prd.md` | MCP orchestration pivot |
| Specification | `docs/features/001-subterminator-cli/spec.md` | Functional requirements |
| Design | `docs/features/001-subterminator-cli/design.md` | Architecture design |
| Architecture | `docs/architecture.md` | Current system diagrams |
| Developer Guide | `README_FOR_DEV.md` | ADRs and component guide |
| Changelog | `CHANGELOG.md` | Delivery history |
| Source Code | `src/subterminator/` | 28 Python modules, ~3,503 LOC |
| Tests | `tests/` | 31 test files, 337 tests, 89% coverage |
