# Retrospective: Statistical Arbitrage Backtester (001)

## What Went Well

- **Multi-stage review caught critical math bugs early.** Spec review iteration 1 caught 3 blockers: Jensen's inequality in portfolio return aggregation, ddof mismatch for Kelly estimator, and commission formula dimensional error. All would have been silent runtime bugs.
- **Plan review caught yfinance breaking change before implementation.** `multi_level_index=True` default in yfinance >= 0.2.51 was identified as a blocker before any code was written.
- **TDD ordering enforced by review.** Plan-reviewer caught implementation-before-tests in Phases 6-10 and forced RED-GREEN-REGRESSION pattern.
- **Known-answer acceptance criteria (AC-1 through AC-7 + AC-1b)** mapped directly to integration tests with analytically known answers. AC-1b specifically catches Jensen's inequality bugs.
- **Implementation converged in 5 iterations** with decreasing severity: 1 blocker (iter 2), 0 blockers (iters 3-5). Clean convergence.
- **Final metrics:** 88 tests, 93% coverage, 0 lint errors, all 8 ACs green.

## What Could Improve

- **Half-Kelly scaling blocker** was a spec-implementation gap. The spec clearly stated the scaling, but the implementation missed it. A per-module spec-verification checklist would help.
- **AC-7 parameter drift** (100 paths/3*SE instead of spec's 200/2*SE) happened silently. Deviating from spec parameters without approval weakens acceptance criteria.
- **AlwaysLongStrategy as alias** instead of proper subclass persisted through 3 iterations. DRY instinct conflicted with spec's semantic clarity.
- **Stale documentation** (5-param vs 3-param run_backtest signature in spec/design) was accepted as "documentation-only debt" across 3 iterations. Stale docs erode trust.
- **Task review required 5 iterations** (10 total reviews). Missing expected values, ambiguous signatures, and off-by-one errors indicate the initial decomposition lacked self-review.
- **Reviewer false positives in iteration 4** (4 false positives from cached context) suggest context staleness after 3+ iterations.

## Patterns Worth Documenting

1. **Spec every formula with units, ddof, and edge cases** -- eliminated ddof blocker and commission dimensional error before implementation.
2. **Design ACs where the wrong answer is qualitatively different** -- AC-1b produces negative when correct is zero, maximizing bug detection signal.
3. **Single temporal alignment point (shift in engine only)** -- prevents distributed look-ahead bugs, verified by AC-2.
4. **Frozen dataclasses + copy-at-boundaries** -- pragmatic Python immutability without deep copies.
5. **Exception co-location** -- DataError in data.py, not in exceptions.py. Keeps raise sites adjacent.
6. **AC readiness map in plan** -- tracks when each criterion becomes testable, prevents writing AC tests before dependencies exist.
7. **Phase-level regression** -- every phase runs the full test suite after GREEN, catching cross-module breakage.

## Anti-Patterns to Avoid

1. **Implementing from memory instead of reading the spec verbatim** -- root cause of half-Kelly, AC-7, and survivorship warning issues.
2. **Applying DRY across semantic boundaries** -- AlwaysLong alias violated spec's class distinction.
3. **Relaxing test parameters for stability** without checking the spec.
4. **Accepting documentation drift** -- either fix the spec or fix the code, never neither.
5. **Reviewing from cached context** -- after 3 iterations, force full re-read of source.

## Key Heuristics

- For mathematical software, the spec should include exact formulas, units, ddof, and edge cases.
- One blocker per implementation iteration indicates healthy convergence; multiple suggest spec gaps.
- Tasks with pre-computed expected values converge faster in review.
- 51 tasks / 12 phases / 88 tests is appropriate granularity for a 9-module system.
- Front-loaded specification (brainstorm + specify + design + plan + tasks) enables fast implementation (~3 hours for the actual coding + review).
