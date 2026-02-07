# Retrospective: Claude-DA

**Feature**: 001-claude-da
**Duration**: ~9.5 hours (2026-02-07, 09:58 - 19:30)
**Phases**: brainstorm (5 iterations) -> specify -> design -> plan -> tasks -> implement
**Result**: 41/41 tasks complete, 145 unit tests passing, 6 integration test stubs

---

## What Went Well

- **Multi-phase review process caught 7 blockers before implementation.** Design review found wrong SDK package name, missing error translation, and API mismatch (query() takes str, not messages). Plan review found interactive permission mode hanging headless, git not preserving chmod 444, and unverified imports. All resolved before writing code.

- **Three-layer safety architecture with evidence-based rationale.** Tool allowlist, tool blocklist, and filesystem permissions each independently prevent writes. Redundancy justified by real SDK bug (issue #361, allowed_tools ignored in v0.1.5-0.1.9).

- **Acyclic module dependency chain.** provider -> agent -> prompt -> schema -> config -> exceptions. Each phase built and tested independently with no circular risk.

- **Lazy initialization solved import-time fragility.** LiteLLM requires module-level singleton, but double-check locking defers heavy work to first request. Init failure is cached to prevent cascading retries.

- **Pre-implementation gate with documented fallback.** Phase 3 gate: "If Agent SDK smoke test fails, fall back to CLI subprocess." Never needed, but having the escape hatch planned reduced risk.

- **Four-tier documentation with audience separation.** PRD (product context), REPORT.md (evaluators), README.md (users), TECHNICAL_GUIDE.md (engineers). Each cross-references without duplicating.

- **Mutable container pattern for streaming audit.** astreaming() must return AsyncIterator, but audit needs the accumulated result. Single-element list passed as result_holder solves this without Futures or shared state.

## What Could Improve

- **Spec drift without formal update.** The spec still lists `query_timeout` (HTTP 504) as a distinct error code, but the design chose not to surface it. Flagged 3 times across reviews, never corrected. Specs should be updated when design deviates.

- **Security review only at implementation, not design.** SQL injection in PRAGMA f-strings was caught during implementation review, not when the PRAGMA interface was designed. Adding security checkpoints to design reviews would catch injection-prone patterns earlier.

- **Large tasks accepted despite guideline violations.** T-021 and T-027 both exceeded the 15-minute guideline. Both were subsequently split into a/b subtasks, proving the original concern was valid. The guideline should be enforced as a hard constraint.

- **Integration test stubs created retroactively.** Implementation review found 5 missing integration tests. They were created as stubs that skip without API key, but their absence during the first review indicates the implementation didn't strictly follow task order.

- **Design-plan inconsistency on streaming return type.** Design Section 2.6 still shows tuple return; plan correctly switched to container pattern. Deferred across phases, never resolved.

## Patterns Worth Documenting

| Pattern | When to Use |
|---|---|
| Skeptic + Gatekeeper dual-reviewer | Every phase review -- separates finding issues from making pass/fail decisions |
| Blocker / warning / suggestion tiers | Review classification -- allows approval with known warnings |
| Phase gates with explicit fail actions | Risk management -- turn unknowns into bounded decisions |
| Prior art research as design input | Design phase -- validate approach against existing implementations |
| Fire-and-forget with exception suppression | Non-critical async work (audit, telemetry) |
| Environment-gated integration tests | Tests requiring external services -- pytest.mark.skipif |
| Verified feasibility claims with source links | PRD/design -- prevent designing against nonexistent capabilities |

## Key Heuristics

1. **Verify SDK package names against PyPI before design.** Wrong names are blockers that waste review cycles.
2. **When bridging two APIs, document type mismatches in design.** query() takes str but OpenAI sends list[dict].
3. **Module-level singletons need lazy init.** Never rely on env vars being available at import time.
4. **git doesn't preserve file permissions.** Generate security-critical permissions at setup time, not via git.
5. **Check SDKs for interactive defaults in server contexts.** Permission prompts hang headless.
6. **Pin v0.x dependencies with upper bounds.** `>=0.1.30,<0.2.0` prevents surprise breakage.
7. **If reviews exceed 2 iterations, requirements are likely ambiguous.** Clarify at the prior phase.
8. **Deferred spec updates accumulate as documentation debt.** Update specs in the same phase where changes are decided.
9. **Enforce task size limits as hard constraints.** Tasks split post-hoc prove the guideline was right.
10. **Design reviews should include security checkpoints.** Especially for dynamic query construction.

## Review Effectiveness

| Phase | Skeptic Iterations | Blockers Found | Resolved Before Next Phase |
|---|---|---|---|
| Specify | 1 | 0 (5 warnings deferred to design) | Yes |
| Design | 1 | 3 | Yes |
| Plan | 2 | 4 | Yes |
| Tasks | 1 + 2 chain validations | 1 | Yes |
| Implement | 2 | 2 (missing tests, SQL injection) | Yes |
| **Total** | | **10 blockers** | **All resolved** |
