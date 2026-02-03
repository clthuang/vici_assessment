# Retrospective: Interactive Service Selection CLI

**Feature:** 004-interactive-service-selection
**Completed:** 2026-02-04
**Duration:** ~2 hours from implementation start to verification

---

## What Went Well

- **Multi-stage review process** - 5 task review iterations caught 15+ issues before implementation, reducing rework
- **TDD approach** - RED-GREEN-REFACTOR cycle ensured comprehensive test coverage (414 tests, 89% coverage)
- **Parallel phase execution** - Phases 2 (Registry) and 3 (Accessibility) ran concurrently, optimizing implementation time
- **Clear separation of concerns** - registry.py, prompts.py, accessibility.py each have single responsibilities
- **questionary library choice** - Leveraged existing prompt_toolkit dependency from typer with no new transitive deps
- **Accessibility built-in** - NO_COLOR, TERM=dumb, --plain flag support from the start
- **Complete documentation trail** - PRD → Spec → Design → Plan → Tasks → .review-history.md
- **All 5 verification reviewers approved** - Behavior, quality, security, simplifier, and final reviewers found 0 blockers

## What Could Improve

- **5 task review iterations is excessive** - Could streamline with better upfront task templates
- **Line number references were brittle** - Iteration 4 required switching to code pattern matching
- **Design had 12 issues in iteration 1** - Spec could be more complete upfront
- **requires_api_key field added then removed** - YAGNI should be applied earlier
- **pytest-mock dependency was missing** - Caught in task review iteration 3

## Learnings Captured

### Patterns

| Pattern | Description |
|---------|-------------|
| **Landmark Verification** | Before editing files, verify exact code patterns exist as expected |
| **Code Pattern References** | Reference code by function/class names, not line numbers |
| **Import-Inside-Function for Tests** | Import modules inside test functions for fresh state after monkeypatching |
| **Registry over Constants** | Replace hardcoded lists with registry pattern for extensibility |
| **Git Checkpoint Before Breaking Changes** | Create commit before refactoring to enable rollback |

### Anti-Patterns

| Anti-Pattern | Mitigation |
|--------------|------------|
| Speculative Fields | Apply YAGNI - add fields only when needed |
| Brittle Line Number References | Use code pattern matching |
| Missing Test Dependencies | Review test patterns early, add dependencies upfront |
| Ambiguous Insertion Points | Show complete expected state or use pattern-based insertion |

### Heuristics

- **difflib cutoff 0.6** - 60% similarity for typo suggestions balances helpfulness vs noise
- **Menu performance <100ms** - Interactive menus must feel responsive
- **Exit code semantics** - 0=success, 1=failed, 2=cancelled, 3=invalid args, 4=config error
- **is_interactive() precedence** - flag → env vars → TTY detection

## Metrics

| Metric | Value |
|--------|-------|
| Total Tasks | 23 |
| Total Phases | 7 |
| Task Review Iterations | 5 |
| Tests Passed | 414 |
| Coverage | 89% |
| Verification Reviewers | 5 |
| Blockers at Verification | 0 |

## Key Decisions

1. **questionary over InquirerPy** - Simpler, shares prompt_toolkit with typer
2. **Static registry module over config file** - Type safety, no file I/O at startup
3. **Breaking change with major version bump** - No deprecation period for old syntax
4. **Help option loops menu** - Better UX for service discovery
5. **requires_api_key deferred** - YAGNI principle applied

## Recommendations for Future Features

1. Create task template using code patterns instead of line numbers
2. Add "dependencies check" phase before task breakdown
3. Limit task review iterations to 3 with escalation path
4. Add "spec completeness checklist" to reduce design review blockers
