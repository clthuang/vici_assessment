# SubTerminator Brainstorm: Research Findings & Refined PRD

**Date:** February 3, 2026
**Status:** Draft for Review (Post-Critical Review)
**Base PRD:** `docs/prds/subterminator_cli.md`

---

## Executive Summary

This brainstorm validates the SubTerminator PRD against real-world research findings. The research reveals **critical blockers** that require a **pivot in approach**.

### Key Findings Requiring Action

| Finding | Impact | Required Decision |
|---------|--------|-------------------|
| Netflix ToS explicitly prohibits automation | **BLOCKER** | Cannot ship ToS-violating code for assessment |
| No sandbox/test environment exists | **BLOCKER** | Cannot iterate on real Netflix flow |
| Zero production tools use browser automation for Netflix | **BLOCKER** | Industry consensus: automation doesn't work reliably |
| Bot detection probability is HIGH, not medium | **HIGH** | Real Netflix flow may fail entirely |

### Recommended Pivot

**Mock-first architecture:** Build against simulated Netflix pages as the PRIMARY deliverable. Real Netflix becomes optional validation, not a dependency.

This approach:
- Produces a complete, demonstrable project regardless of Netflix cooperation
- Enables proper test coverage and iteration
- Eliminates ToS risk for assessment
- Shows engineering rigor through comprehensive mock implementation

---

## Research Findings Summary

### 1. Netflix Anti-Automation & ToS Risk

| Finding | Source | Impact |
|---------|--------|--------|
| Netflix ToS explicitly prohibits "any robot, spider, scraper or other automated means" | [Netflix ToS](https://tsandzzz.com/netflix-terms-of-use) | **HIGH RISK** - Account termination possible |
| Netflix uses proprietary CDN (Open Connect), anti-bot measures undocumented | [Netify](https://www.netify.ai/resources/applications/netflix) | Medium - Detection level unknown |
| Playwright/Puppeteer have "Medium Detection" rates by anti-bot systems | [Castle.io](https://blog.castle.io/from-puppeteer-stealth-to-nodriver-how-anti-detect-frameworks-evolved-to-evade-bot-detection/) | Medium - Stealth techniques available |

**Recommendation:** Add prominent disclaimer about ToS risks. Consider alternative demo targets (see below).

### 2. Netflix Cancellation Flow (Current)

| Step | URL/Action | Notes |
|------|-----------|-------|
| 1 | `netflix.com/account` | Account settings page |
| 2 | Click "Cancel Membership" | Link location may vary by A/B test |
| 3 | `netflix.com/cancelplan` | Cancellation initiation |
| 4 | Select cancellation reason | Survey with radio buttons |
| 5 | Click "Finish Cancellation" | Final confirmation |

**Important Edge Cases:**
- Third-party billing (Apple, Google Play, T-Mobile) requires cancellation through those platforms
- Viewing history retained 24 months after cancellation
- Can continue streaming until billing period ends

### 3. Existing Tools Landscape

| Tool | Approach | Netflix Support |
|------|----------|-----------------|
| Rocket Money | Human concierge (not automation) | Yes, via humans |
| Trim | AI assistant via SMS | Limited |
| Chargeback | Full-service human operators | Yes |
| DoNotPay | Automated + human hybrid | Unknown |

**Key Insight:** No production tool uses browser automation for Netflix. They all use human operators for complex cancellations.

### 4. Testing Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| No Netflix sandbox/test accounts | Must use real subscription | Use trial accounts, document flow via pageflows.com |
| No public cancellation API | Must use browser automation | As designed |
| Third-party billing exceptions | Cannot automate Apple/Google billing | Detect and report (already in PRD) |

### 5. Technical Stack Recommendations

Based on research, here are the recommended libraries:

| Component | Library | Version | Why |
|-----------|---------|---------|-----|
| Browser Automation | Playwright | 1.58.0 | Async API, robust, good debugging |
| State Machine | python-statemachine | 2.5.0 | Native async, declarative, validators |
| Anti-Detection | playwright-stealth | 2.0.1 | Basic evasions (not bulletproof) |
| CLI Framework | Typer | 0.21.1 | Type-hint based, minimal boilerplate |
| AI Integration | anthropic | latest | Claude Vision for page analysis |

### 6. Claude Vision for Page Analysis

| Consideration | Recommendation |
|---------------|----------------|
| Screenshot resolution | 1024x768 (XGA) optimal for token efficiency |
| Format | PNG or JPEG, base64 encoded |
| Token cost | ~1334 tokens per 1000x1000px image |
| Prompt structure | Image BEFORE text in prompt |
| Limitations | May struggle with low-quality/rotated images |

---

## Risk Analysis

### Critical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Netflix ToS violation** | High | Account ban | Disclaimer; use own test account; consider alternative target |
| **R2: Bot detection blocks automation** | Medium | Flow fails | playwright-stealth; human-like timing; retry with user browser |
| **R3: Netflix UI changes break flow** | Medium | Flow fails | AI-based page interpretation (as designed) |

### Moderate Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R4: CAPTCHA during flow** | Low-Medium | Requires human | Pause and let user solve (as designed) |
| **R5: No way to test without real account** | High | Limited testing | Use trial account; mock tests for core logic |
| **R6: Third-party billing unhandled** | Medium | User confusion | Detect and report clearly |

---

## Proposed PRD Modifications

### 1. Add Risk Disclaimer (NEW Section)

```markdown
## Risk Disclosure

**Terms of Service Warning:** This tool automates interactions with Netflix's
website, which may violate Netflix's Terms of Service. Users accept all risk
of account suspension or termination. This tool is provided for educational
and demonstration purposes.

**Recommendation:** Use this tool only on accounts you are willing to lose
access to.
```

### 2. Revise Technical Constraints (Section 2.4)

Add specific versions:
```markdown
### 2.4 Technical Constraints
- Python 3.11+
- Playwright 1.58+ (async API)
- python-statemachine 2.5+ for state management
- Typer 0.21+ for CLI
- anthropic SDK for Claude Vision
- playwright-stealth for basic anti-detection
```

### 3. Add Alternative Demo Targets (NEW Section)

For safer demonstration/evaluation:

| Target | ToS Risk | Complexity | Notes |
|--------|----------|------------|-------|
| Netflix | High | Medium | Original target |
| **Demo mode** | None | Low | Simulated flow with mock pages |
| Local test server | None | Low | Puppeteer test pages |

**Recommendation:** Implement `--demo` mode that runs against local mock pages for safe evaluation.

### 4. Revise Open Questions (Section 13)

Update based on research:

| ID | Question | Research Answer |
|----|----------|-----------------|
| Q-1 | Can we test E2E without active subscription? | **No sandbox exists.** Use trial account or mock mode. |
| Q-2 | How does Netflix handle automation detection? | **Undocumented.** Expect medium detection rate; use stealth. |
| Q-3 | Should surveys be answered honestly? | **Generically.** Select "Other" or first option. |

### 5. Revise Architecture for Extensibility

Add explicit service abstraction:

```
subterminator/
├── cli/                    # Typer CLI
│   └── main.py
├── core/
│   ├── state_machine.py    # python-statemachine based
│   ├── browser.py          # Playwright wrapper with stealth
│   └── ai_interpreter.py   # Claude Vision integration
├── services/
│   ├── base.py             # Abstract service interface
│   ├── netflix.py          # Netflix-specific implementation
│   └── mock.py             # Demo mode mock service
├── utils/
│   ├── screenshots.py
│   └── logging.py
└── tests/
    ├── unit/               # Core logic tests (no browser)
    ├── integration/        # Mock service tests
    └── e2e/                # Real browser tests (manual trigger)
```

---

## Implementation Recommendations

### Phase 1: Foundation (Day 1-2)
1. Project scaffolding (pyproject.toml, structure)
2. CLI skeleton with Typer
3. State machine with python-statemachine
4. Basic Playwright wrapper with stealth

### Phase 2: Core Logic (Day 3-4)
1. Page state detection with Claude Vision
2. Netflix service implementation
3. Human-in-the-loop checkpoints
4. Screenshot/logging infrastructure

### Phase 3: Reliability (Day 5-6)
1. Error handling and retry logic
2. Demo/mock mode for testing
3. GitHub Actions CI/CD
4. Unit and integration tests

### Phase 4: Polish (Day 7)
1. Documentation (README, usage examples)
2. E2E testing with real account
3. Edge case handling refinement
4. Final demo recording

---

## Alternative Approaches Considered

### A. Use Claude Computer Use Instead of Custom Automation

| Pros | Cons |
|------|------|
| Official Anthropic tool | Slower (multiple screenshot cycles) |
| Less custom code | Less control over flow |
| Better AI integration | Still violates Netflix ToS |

**Decision:** Custom Playwright approach gives more control and demonstrates engineering skill better.

### B. Target Different Service (Not Netflix)

| Service | ToS Risk | Flow Complexity | Demo Value |
|---------|----------|-----------------|------------|
| Netflix | High | Medium | High (well-known) |
| Hulu | High | Medium | Medium |
| Mock service | None | Configurable | Lower |

**Decision:** Keep Netflix as primary target but add mock mode for safe demonstration.

### C. Browser Extension Instead of CLI

| Pros | Cons |
|------|------|
| No bot detection | Out of MVP scope per PRD |
| User's existing session | More complex to develop |
| | Distribution challenges |

**Decision:** CLI as designed; browser extension is future enhancement.

---

## Codebase Status

| Item | Status |
|------|--------|
| Source code | Not started |
| Python setup | Not started |
| CI/CD | Not started |
| Tests | Not started |
| Documentation | PRD complete |

**Everything needs to be built from scratch.**

---

## Critical Review Findings (Self-Critique)

### Blockers Identified

| Issue | Why It's a Blocker | Resolution |
|-------|-------------------|------------|
| **ToS violation** | Cannot submit ToS-violating code for professional assessment. "Disclaimer" is not a real solution. | **PIVOT: Mock-first architecture** |
| **No testing strategy** | Cannot iterate when each test requires real subscription cancellation. Only 1-2 real tests possible. | **Mock pages enable unlimited iteration** |
| **7-day timeline unrealistic** | Days 5-6 scope includes 4+ days of work (error handling, retry logic, demo mode, CI/CD, tests) | **Reduce scope to mock-first MVP** |

### False Certainties Corrected

| Original Claim | Correction |
|----------------|------------|
| A/B variants A-D are "known" | **Speculation.** No evidence these specific variants exist. Label as hypotheses. |
| Bot detection is "Medium" probability | **HIGH probability.** Research shows Playwright has "Medium Detection Rate" + Netflix uses proprietary anti-bot = HIGH combined risk. |
| Third-party billing is edge case | **Likely common.** Apple TV+, Google Play, T-Mobile bundles are prevalent. Should be Day 1 detection. |
| ~1334 tokens per image (cost known) | **Total run cost unestimated.** 10+ screenshots per run × tokens = $0.50-2.00 per attempt. Testing budget needed. |

### Missing Considerations Added

| Gap | Addition |
|-----|----------|
| Shared/family plan risk | If account holder cancels, all profiles lose access. Must warn user. |
| API cost budget | Estimate: $20-50 for development testing, $5-10 for final demos |
| Fallback plan | If bot detection blocks on Day 3, project delivers mock-only |
| Demo mode definition | Now explicitly defined below |

---

## Revised Strategy: Mock-First Architecture

### Mock Mode Definition (Explicit)

Mock mode consists of:

1. **Local HTML pages** - Static pages mimicking Netflix UI at each flow state
2. **Simple HTTP server** - Python `http.server` or similar serving mock pages
3. **Configurable responses** - JSON config to simulate different A/B variants, errors
4. **Same state machine** - Identical core logic, different browser target

**Implementation effort:** ~1 day for basic mocks, ~2 days for full variant coverage

### Revised Project Scope

| Component | MVP (Days 1-5) | Stretch (Days 6-7) |
|-----------|---------------|-------------------|
| CLI with Typer | Yes | - |
| State machine (python-statemachine) | Yes (happy path + 3 error states) | Full edge case coverage |
| Mock Netflix pages | Yes (5 core pages) | All variants |
| Playwright automation | Yes (against mocks) | Against real Netflix |
| Claude Vision integration | Yes (against mocks) | Against real Netflix |
| Screenshot/logging | Yes | - |
| Unit tests | Yes (>80% core logic) | - |
| Integration tests | Yes (against mocks) | - |
| E2E with real Netflix | No | Optional (1 test) |
| GitHub Actions CI | Basic (lint + unit tests) | Full pipeline |

### Revised Timeline

| Day | Deliverable | Risk Mitigation |
|-----|-------------|-----------------|
| 1 | Project scaffold, CLI, mock pages skeleton | If slow, cut mock variants |
| 2 | State machine, basic page detection | Core logic testable by EOD |
| 3 | Playwright + mock integration, screenshots | Working demo against mocks |
| 4 | Claude Vision integration, human-in-loop | Can show AI-powered detection |
| 5 | Error handling, unit tests, CI basics | **MVP COMPLETE** |
| 6 | *Stretch:* More mock variants, edge cases | Cut if behind |
| 7 | *Stretch:* Real Netflix test (1 attempt), polish | Optional validation only |

### Budget Estimate

| Item | Estimated Cost |
|------|----------------|
| Claude API (development) | $20-30 |
| Claude API (demos) | $5-10 |
| Netflix subscription (optional) | $15-23/month |
| **Total required** | **$25-40** |
| **Total with Netflix test** | **$40-70** |

---

## User Decisions (Resolved)

| Question | Decision |
|----------|----------|
| Strategy | **Mock-first with real Netflix validation** |
| Mock fidelity | Realistic mocks (pixel-perfect, same selectors) |
| Timeline | 7 calendar days |
| Real Netflix | Yes, as final validation (not primary development target) |

### Final Approach

1. **Days 1-5:** Build complete system against realistic mock Netflix pages
2. **Days 6-7:** Validate against real Netflix, polish, document

The mock is not a crude placeholder - it replicates Netflix's actual HTML/CSS structure, selectors, and flow. The same Playwright code works against both mock and real Netflix.

---

## Sources

### Netflix Research
- [Netflix Terms of Use](https://tsandzzz.com/netflix-terms-of-use)
- [How to Cancel Netflix - Official](https://help.netflix.com/en/node/407)
- [Netflix Infrastructure](https://www.netify.ai/resources/applications/netflix)

### Anti-Detection
- [Anti-Detect Framework Evolution](https://blog.castle.io/from-puppeteer-stealth-to-nodriver-how-anti-detect-frameworks-evolved-to-evade-bot-detection/)
- [Undetected ChromeDriver vs Selenium Stealth](https://www.zenrows.com/blog/undetected-chromedriver-vs-selenium-stealth)
- [Bot Detection Methods 2025](https://blog.castle.io/bot-detection-101-how-to-detect-bots-in-2025-2/)
- [Avoid Bot Detection with Playwright Stealth](https://brightdata.com/blog/how-tos/avoid-bot-detection-with-playwright-stealth)

### Libraries
- [Playwright Python Docs](https://playwright.dev/python/docs/library)
- [python-statemachine](https://pypi.org/project/python-statemachine/)
- [playwright-stealth](https://pypi.org/project/playwright-stealth/)
- [Typer](https://pypi.org/project/typer/)

### Claude Vision
- [Claude Vision API](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Claude Computer Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)

### Similar Tools
- [Rocket Money](https://help.rocketmoney.com/en/articles/934402-how-do-i-cancel-a-subscription)
- [Subscription Cancellation Apps Comparison](https://www.19pine.ai/blog/best-management-and-subscription-cancellation-apps)
