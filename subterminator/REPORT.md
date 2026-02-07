# SubTerminator: Consulting Case Report

**Project:** AI-Orchestrated Subscription Cancellation Engine
**Author:** Terry
**Date:** February 2026
**Assessment:** VICI Holdings — 7-Day Challenge

---

## I. Executive Summary

### The Problem

Subscription services weaponize UX friction against cancellation. The industry term is "dark patterns" — retention offers, exit surveys, multi-step confirmations, buried settings, third-party billing redirects, and session timeouts — all designed to make cancellation harder than signup. Netflix requires 4-5 clicks through multiple pages. Other services are worse.

No production tool automates this with browser automation. Every subscription management service — Rocket Money, Trim, Chargeback, DoNotPay — uses human concierge operators for cancellation. The industry consensus is that browser automation doesn't work reliably against subscription services: Terms of Service prohibit it, bot detection blocks it, and UI changes break it faster than selectors can be maintained.

### The Solution

A three-pillar architecture:

1. **MCP Orchestration** — An LLM (Claude/GPT-4) drives browser control via Microsoft's Playwright MCP server. The AI interprets page snapshots (accessibility trees, not DOM), decides the next action, and calls tools through the Model Context Protocol. No hardcoded selectors.

2. **Human Checkpoints** — Mandatory gates for authentication (login, CAPTCHA, MFA) and irreversible actions (final cancellation). These are structural — enforced by predicate-based conditions evaluated before every tool execution — not procedural ("remember to ask the user").

3. **Predicate-Based Service Configs** — Each service defines its behavior through callable predicates (`Callable[[ToolCall, NormalizedSnapshot], bool]`), not CSS selectors or hardcoded flows. Adding a new service means writing functions, not modifying engine code.

### Scope Calibration

This is a mock-first MVP for Netflix. It is not a production cancellation service. This is a deliberate engineering decision, not a limitation.

Netflix's Terms of Service explicitly prohibit "any robot, spider, scraper or other automated means" for accessing their service. No sandbox or test environment exists — every test run risks account termination. Bot detection probability is HIGH (Playwright has "Medium Detection Rate" per Castle.io research; combined with Netflix's proprietary anti-bot measures, the effective risk is HIGH). Building against real Netflix as the primary target would mean: one test run per development iteration, potential account loss, and ToS violation submitted as assessment work.

The mock-first pivot (documented in brainstorm iteration 2, `docs/brainstorms/2026-02-03-subterminator-research.prd.md`) redirects engineering effort from fighting bot detection to building a robust orchestration engine. The mock replicates Netflix's actual flow structure; the same orchestration code works against both targets.

### Differentiator

No open-source tool uses LLM-driven MCP orchestration for subscription cancellation. The combination of:
- AI page interpretation via accessibility tree (not screenshots or DOM selectors)
- Virtual tools (`complete_task`, `request_human_approval`) as LLM-callable functions
- Predicate-based checkpoint system evaluated before every tool execution
- Single-tool-per-turn enforcement preventing runaway automation

...is novel. Every existing cancellation service relies on human operators. This system demonstrates that AI-driven browser control is architecturally feasible — and shows exactly why it isn't yet production-ready.

### Delivery Metrics

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

## II. Problem Decomposition

### Dark Pattern Taxonomy

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

### Why Automation Fails

Research conducted in brainstorm iteration 2 (`2026-02-03-subterminator-research.prd.md`) revealed three blockers:

| Blocker | Evidence | Impact |
|---------|----------|--------|
| **Netflix ToS prohibition** | "Any robot, spider, scraper or other automated means" explicitly prohibited | Account termination risk |
| **No sandbox environment** | Netflix provides no test/staging environment for developers | Cannot iterate without real subscription risk |
| **HIGH bot detection** | Playwright has "Medium Detection Rate" (Castle.io); Netflix uses proprietary CDN (Open Connect) with undocumented anti-bot measures | Combined risk is HIGH |

The industry consensus is clear: every production cancellation service (Rocket Money, Trim, Chargeback, DoNotPay) uses human operators. No production tool automates Netflix cancellation via browser.

### The Real Question

The real question is not "can we click buttons?" — any Playwright script can click buttons. The real question is: **can AI adapt to unknown UIs while keeping humans in control of irreversible actions?**

CSS selectors break when Netflix A/B tests a new layout. State machines break when a new retention offer appears. Hardcoded flows break on any change. The only approach that survives UI change is semantic interpretation — reading the page the way a human would and deciding what to do next.

This reframes the project from "Netflix cancellation tool" to "AI browser orchestration engine with Netflix as proof of concept."

---

## III. Strategic Design Decisions

Seven decisions shape the architecture. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

### Decision 1: Mock-First Architecture

**Context.** Netflix's Terms of Service prohibit automation. No sandbox exists. Bot detection probability is HIGH. Each test run risks account termination.

**Analysis.** Building against real Netflix as the primary target means: (a) one test attempt per development iteration (cannot re-cancel an already-cancelled subscription), (b) ToS violation submitted as professional assessment work, (c) bot detection may block the tool entirely on Day 3, leaving no deliverable. The research brainstorm (`2026-02-03-subterminator-research.prd.md`) identified this as a critical blocker.

**Decision.** Build against realistic mock Netflix pages as the primary deliverable. Real Netflix becomes optional validation, not a dependency.

**Trade-off.** Mock-first means the tool is not validated against production Netflix. Compensated by: (a) mock pages replicate Netflix's actual flow structure (account → cancel → survey → confirm), (b) the same orchestration code works against both targets (`--target mock|live`), (c) the engineering value is in the orchestration engine, not in Netflix-specific plumbing.

**Evidence.** The mock-first pivot was the single most important process decision. It enabled unlimited iteration (337 tests, 89% coverage) instead of 1-2 cautious attempts against real Netflix. Every subsequent design decision — AI-first interpretation, MCP orchestration, predicate-based configs — was only possible because mock-first removed the testing bottleneck.

### Decision 2: MCP Orchestration over Custom Browser Tools

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

### Decision 3: AI-First over Heuristic-First

**Context.** The original design (`docs/features/001-subterminator-cli/design.md`) used a tiered detection strategy: (1) URL pattern matching, (2) text-based heuristics, (3) Claude Vision as fallback.

**Analysis.** URL patterns and text heuristics work for the known flow but break on any variation. Netflix A/B tests different cancellation paths, button text, and page layouts. CSS selectors like `[data-uia='action-cancel-membership']` break when Netflix changes its data attributes. The brainstorm iteration 4 (`20260204-browser-automation-architecture.prd.md`) identified that accessibility-tree-based interpretation is 80-90% smaller in token usage than raw DOM and survives layout restructuring.

**Decision.** AI interprets every page via accessibility tree snapshot. The LLM decides the next action — no hardcoded state-action mapping. Heuristics are removed from the critical path; the service config provides hints to the LLM via `system_prompt_addition`, not selector tables.

**Trade-off.** Higher per-run cost (~$0.50-2.00 per run in API calls) and slower execution (one API call per turn). Justified because: (a) accuracy and adaptability are more important than speed for subscription cancellation, (b) the cost is acceptable for a task performed once per service, (c) the system degrades gracefully when the LLM is uncertain (requests human approval).

**Evidence.** The system prompt provides the service goal and rules; the accessibility tree provides the page state. The LLM reasons about both and calls the appropriate tool. When Netflix changes its button text from "Finish Cancellation" to "Confirm Cancellation," the LLM adapts — no code change required. A selector-based system would break.

### Decision 4: Single-Tool-Per-Turn Enforcement

**Context.** LLMs can generate multiple tool calls in a single response. Executing all of them without review risks unintended consequences.

**Analysis.** In browser automation, each action changes the page state. Clicking a button navigates to a new page; the next action must be chosen based on the new page, not the old one. Batch-executing multiple clicks from a single LLM response means actions 2-N operate on stale assumptions about page state. More critically, runaway automation — where the LLM rapidly executes a series of actions without human oversight — is the primary safety risk.

**Decision.** Execute exactly one tool per turn. After each tool call, refresh the page snapshot (if navigation occurred) and let the LLM re-evaluate (`task_runner.py`).

**Trade-off.** Slower execution (one API round-trip per action). Compensated by: (a) checkpoint enforcement is possible because every action is individually reviewed, (b) stale element references cannot cause misclicks, (c) the user can observe progress in real-time, (d) max turns limit (20) bounds total execution time.

**Evidence.** The orchestration loop in `task_runner.py` processes `response.tool_calls[0]` only — the first tool call. Combined with the 20-turn maximum and SIGINT handling, this prevents the system from taking more actions than the user expects.

### Decision 5: Virtual Tools

**Context.** The LLM needs a way to signal "I'm done" or "I need human help." These are not browser actions — Playwright MCP has no concept of task completion or human approval.

**Analysis.** MCP tools are browser actions (`browser_click`, `browser_navigate`, etc.). But the orchestration layer needs meta-actions: "the task is complete" and "I need human approval before proceeding." These could be implemented as special message patterns (e.g., "DONE: success"), but that requires parsing natural language — fragile and unreliable.

**Decision.** Inject two virtual tools into the tool list sent to the LLM:
- `complete_task(status: "success"|"failed", reason: str)` — signals task completion
- `request_human_approval(action: str, reason: str)` — requests explicit human approval

These are handled by the orchestration layer, not forwarded to Playwright MCP.

**Trade-off.** Tool list grows by 2 (now ~17 tools total, well under the 30-tool threshold identified in MCP research). The benefit — structured, parseable completion signals — eliminates an entire class of natural-language-parsing bugs.

**Evidence.** When the LLM detects the "Your cancellation is complete" page, it calls `complete_task(status="success", reason="Cancellation confirmed page detected")`. The orchestration layer then verifies completion by checking the service config's `success_indicators` — a second check beyond the LLM's judgment.

### Decision 6: Predicate-Based Service Configs

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

### Decision 7: Human Checkpoints as Non-Negotiable

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

## IV. Architecture as Risk Mitigation

The architecture is not just code organization — it is a risk mitigation strategy. Each structural choice addresses a specific failure mode.

### Runaway Prevention

**Risk.** LLM autonomously executes a rapid series of browser actions, clicking through the cancellation flow without human oversight.

**Mitigation.** Three independent safeguards:
1. **Single-tool-per-turn** — Only one action per LLM response is executed (`task_runner.py`)
2. **Max turns limit (20)** — Hard cap on total actions before forced termination
3. **SIGINT handling** — Ctrl+C cleanly terminates the orchestration loop (exit code 130)

**Verification.** If all three fail simultaneously, the worst case is 20 browser actions. With checkpoints enforced before irreversible actions, the system cannot complete a cancellation without human approval even in this failure mode.

### UI Change Resilience

**Risk.** Netflix changes its cancellation flow, breaking the tool.

**Mitigation.** The LLM interprets the accessibility tree semantically, not through selectors. The accessibility tree represents the page as a hierarchy of roles and names:
```
- button "Cancel Membership" [ref=s1e5]
- heading "Before you go" [ref=s1e8]
- button "Continue to Cancel" [ref=s1e12]
```
When Netflix changes `"Finish Cancellation"` to `"Confirm Cancellation"`, the LLM adapts — it understands both phrases mean "proceed with cancellation." A selector-based system would break.

### Stale Reference Prevention

**Risk.** Element references become invalid after page navigation, causing clicks on wrong elements.

**Mitigation.** Playwright MCP's `ref` values are valid for one action only. After any navigation tool (`browser_navigate`, `browser_click` that triggers navigation), the orchestration loop refreshes the snapshot. The LLM receives fresh references for the new page state. Element refs from the previous page are not reusable — this is enforced by Playwright MCP's design, not by our code.

### Safety Invariant

**Risk.** Automated cancellation of a subscription the user did not intend to cancel.

**Mitigation.** The safety invariant is structural: `CheckpointHandler.should_checkpoint()` is called before every MCP tool execution. The checkpoint condition for final cancellation (`"finish cancel" in snapshot.content.lower()`) is a predicate evaluated on the live page state, not a flag that can be toggled. Even if the LLM hallucinates or misinterprets the page, the checkpoint prevents execution without human approval.

### Authentication Edge Case Detection

**Risk.** Automation encounters a login page, CAPTCHA, or MFA challenge and either fails silently or attempts to bypass it.

**Mitigation.** Three-tier detection in `checkpoint.py`:
1. **Login** — URL contains `/login` or snapshot contains sign-in elements
2. **CAPTCHA** — Snapshot contains CAPTCHA-related content
3. **MFA** — Snapshot contains multi-factor authentication prompts

When any tier triggers, the system pauses and prompts the user to complete authentication in the browser window. The orchestration loop waits, then refreshes the snapshot and continues.

---

## V. The Four Pivots

The system evolved through four architectural pivots. Each was triggered by research findings, not random exploration. Each preserved what worked and discarded what didn't.

### Pivot 1: SubStretcher Plugin to SubTerminator CLI

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

### Pivot 2: Live Netflix to Mock-First

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

### Pivot 3: State Machine to AI Agent

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

### Pivot 4: Custom Browser Tools to MCP Orchestration

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

## VI. Acknowledged Limitations

Ten limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight.

### L1: Netflix-Only

- **Impact:** Only one service is implemented. Extensibility is designed and documented but not exercised in production.
- **Current Mitigation:** The predicate-based service config architecture (`ServiceConfig` dataclass) is designed for multi-service support. Adding a new service is documented as a how-to guide in `README_FOR_DEV.md`. Disney+, Hulu, and Spotify are listed as "coming soon" in the interactive service selection menu.
- **North Star:** 5+ services with shared orchestration engine, each requiring only a new config file.

### L2: Mock-First (Real Netflix Not Validated)

- **Impact:** The tool works against mock Netflix pages. Real Netflix is optional and not validated in CI.
- **Current Mitigation:** Mock pages replicate Netflix's actual flow structure (account page, retention offer, exit survey, final confirmation, completion page). The same orchestration code works against both targets via `--target mock|live`. The mock is not a crude placeholder.
- **North Star:** Walk-forward validation against real services in a sandboxed environment with disposable test accounts.

### L3: No CAPTCHA Solving

- **Impact:** When CAPTCHA is encountered, the tool cannot proceed automatically.
- **Current Mitigation:** Three-tier auth detection pauses the flow and prompts the user to complete the CAPTCHA in the browser window. This is the correct response — CAPTCHA solving services violate ToS and are ethically questionable.
- **North Star:** Maintain pause-and-wait as the correct approach. CAPTCHA solving is a non-goal.

### L4: No Credential Management

- **Impact:** User must be pre-logged in or complete login manually when prompted.
- **Current Mitigation:** Browser session reuse via `--cdp-url` (connect to existing Chrome) or `--profile-dir` (persistent browser profiles). After one manual login, the session persists across runs.
- **North Star:** Integration with system credential vaults (macOS Keychain, 1Password CLI) for automated login with explicit user consent.

### L5: Single Cancellation at a Time

- **Impact:** Cannot cancel multiple subscriptions concurrently.
- **Current Mitigation:** One service per run. Acceptable for the use case — subscription cancellation is not a batch operation.
- **North Star:** Sequential multi-service support (cancel Netflix, then Disney+, then Hulu) in a single session.

### L6: English-Only

- **Impact:** No internationalization. Page interpretation assumes English text.
- **Current Mitigation:** LLMs are multilingual — the accessibility tree interpretation may work in other languages, but this is untested and unsupported.
- **North Star:** Explicit multi-language support with language-specific service configs and prompts.

### L7: No Subscription Detection or Monitoring

- **Impact:** The user must know which subscriptions they have. The tool cancels; it does not discover.
- **Current Mitigation:** Out of scope. Subscription detection requires accessing billing pages for every potential service — a different product entirely.
- **North Star:** Integration with bank/credit card transaction APIs (Plaid) for automatic subscription discovery.

### L8: Linear API Cost (~$0.50-2.00 per Run)

- **Impact:** Each run costs money in LLM API calls. 10+ screenshots per run at ~1,334 tokens per image.
- **Current Mitigation:** Acceptable for a task performed once per service. No caching or optimization implemented.
- **North Star:** Snapshot caching, prompt optimization, and model selection (use cheaper models for simple pages, expensive models for complex ones).

### L9: Bot Detection Unmitigated for Live Mode

- **Impact:** Real Netflix may detect and block the automation.
- **Current Mitigation:** Playwright stealth settings are available but not guaranteed to evade detection. Mock-first approach means live mode is optional validation, not a dependency.
- **North Star:** Browser extension mode (Pivot 1 concept) where the tool controls the user's existing browser session — no new browser to detect.

### L10: No Mobile App Subscription Support

- **Impact:** Cannot cancel subscriptions managed through iOS App Store or Google Play Store.
- **Current Mitigation:** Third-party billing detection identifies these cases and provides manual cancellation instructions for the correct platform.
- **North Star:** Integration with Apple/Google subscription management APIs (if they become available) or guided in-app cancellation flows.

---

## VII. Validation Strategy

### Test Pyramid

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

### Coverage by Component

| Component | Test Files | Approach |
|-----------|-----------|----------|
| MCP Orchestrator | `tests/unit/mcp_orchestrator/` | AsyncMock for async operations, mock MCP client |
| CLI Layer | `tests/unit/cli/` | Typer's CliRunner for integration, mock orchestrator |
| Services | `tests/unit/mcp_orchestrator/` | Predicate evaluation with synthetic snapshots |
| Core Utilities | `tests/unit/core/`, `tests/unit/utils/` | Direct function testing |
| Integration | `tests/integration/` | End-to-end orchestration with mock components |

### Key Test Patterns

1. **AsyncMock for async code** — All MCP and LLM interactions are async. Tests use `unittest.mock.AsyncMock` with `pytest-asyncio` for full async test execution.

2. **CliRunner for CLI integration** — Typer's test client validates command parsing, exit codes, and output formatting without launching a browser.

3. **Parametrized fixtures** — Service configs, snapshot formats, and error conditions are tested across multiple variants using `@pytest.mark.parametrize`.

4. **Synthetic snapshots** — `NormalizedSnapshot` objects with controlled URLs, titles, and content for testing predicates and checkpoint conditions without browser state.

### Metrics

| Metric | Value |
|--------|-------|
| Total tests | 337 |
| All passing | Yes |
| Coverage | 89% |
| Test execution time | ~5.5 seconds |

---

## VIII. Process and Delivery Metrics

### Five-Stage Specification Pipeline

The system was built through a 5-stage specification pipeline. Each stage produced a versioned artifact with formal review.

| Stage | Artifact | Key Output |
|-------|----------|------------|
| Brainstorm/PRD | 9 brainstorm documents | Problem space exploration, research findings, architectural pivots |
| Specification | `spec.md` | Functional requirements, page states, error handling, test scenarios |
| Design | `design.md` | Component architecture, data flow, service layer design |
| Plan | `plan.md` | Build order, phase dependencies, TDD enforcement |
| Tasks | `tasks.md` | Individual implementation tasks with acceptance criteria |

### Nine Brainstorm Iterations

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

### Front-Loaded Research Prevented Wasted Effort

The most important process insight: **front-loaded research in iteration #2 prevented two critical failures:**

1. **ToS violation.** Without the research pivot, the project would have been built against real Netflix — submitting ToS-violating code as professional assessment work.

2. **Testing bottleneck.** Without mock-first, each test run would require a real subscription cancellation. At most 1-2 real tests are possible (you can't re-cancel an already-cancelled subscription). The 337 tests in the current suite would have been impossible.

The research brainstorm took approximately half a day. It saved the remaining 6 days from being spent on an approach that could not produce a reliable deliverable.

### Patterns Worth Documenting

1. **Research before building.** The Feb 3 research brainstorm identified three critical blockers before any code was written. Every production cancellation service uses human operators — knowing this before coding prevented building a tool that the industry has already proven unviable in production.

2. **Mock-first as an engineering strategy, not a shortcut.** Mock-first is often dismissed as "not testing the real thing." In this case, it's the opposite — mock-first enables testing that is impossible with the real thing (no sandbox, no re-cancellation, account termination risk).

3. **Progressive architecture through brainstorms.** The 9 brainstorm iterations show architecture evolving through evidence: selectors → accessibility tree → AI-first → MCP orchestration. Each step was motivated by research findings, not refactoring for its own sake.

4. **Predicate-based configs over selector-based configs.** When the execution engine is AI-driven, the service config should express conditions (predicates), not instructions (selectors). This insight emerged from the architecture pivot and would not have been apparent without first building the selector-based approach.

### Anti-Patterns to Avoid

1. **Building before researching.** If coding had started on Day 1 with the original plan (Chrome extension + real Netflix + CSS selectors), every line would have been thrown away by Day 3.

2. **Sunk cost on deprecated code.** The original `core/engine.py` (~400 LOC) and `core/agent.py` (~870 LOC) represented significant investment. The MCP pivot deprecated both. The correct response was to build the new approach in a new package (`mcp_orchestrator/`), not to try to retrofit the old code.

3. **Over-engineering before validation.** The AI-MCP redesign brainstorm (iteration 8) proposed a full custom MCP server with 7 tools, element registries, and snapshot factories — 52 tasks. The very next brainstorm (iteration 9) recognized that Playwright MCP already provides all of this. The 24-hour gap between "build everything custom" and "reuse what exists" highlights the value of continued research.

---

## IX. North Star Roadmap

### Tier 1: Highest ROI

**Multi-Service Support**
- **What:** Add Disney+, Hulu, Spotify configs using the predicate-based service config pattern.
- **Why:** The architecture is designed for this but not yet exercised. Proving multi-service support validates the extensibility claim.
- **Effort:** 1-2 days per service (config + mock pages + tests).

**Walk-Forward Validation on Real Sites**
- **What:** Disposable test accounts for real-site validation in CI. Run against real Netflix with a dedicated test subscription.
- **Why:** Mock-first enables development; real-site validation proves production viability.
- **Effort:** 2-3 days (account management, test infrastructure, flaky test handling).

### Tier 2: Medium ROI

**Browser Extension Mode**
- **What:** Control the user's existing Chrome browser session via Chrome DevTools Protocol, instead of launching a new Playwright-controlled browser.
- **Why:** Eliminates bot detection (the browser IS the user's browser), eliminates re-authentication (existing session), and addresses L4 and L9 simultaneously.
- **Effort:** 3-5 days (CDP connection, extension relay, session management).

**Credential Vault Integration**
- **What:** Integration with macOS Keychain, 1Password CLI, or Bitwarden CLI for automated login with explicit user consent.
- **Why:** Addresses L4 (no credential management) without building a custom credential store.
- **Effort:** 2-3 days per vault provider.

### Tier 3: Long-Term

**Subscription Monitoring**
- Integration with Plaid or bank APIs for automatic subscription discovery. Different product, same platform.

**Mobile App Subscription Support**
- Guided cancellation flows for iOS App Store and Google Play Store subscriptions.

**Cost Optimization**
- Snapshot caching, prompt compression, model tiering (cheap models for simple pages, expensive for complex).

---

## X. Conclusion

### What Was Demonstrated

This project is an exercise in engineering design thinking applied to browser automation and AI orchestration. The goal was never to build the most complete cancellation tool — it was to build the most thoughtful one.

**Research-driven architecture.** Nine brainstorm iterations, each motivated by research findings. The mock-first pivot prevented ToS violation and testing bottleneck. The MCP pivot eliminated 2,500 LOC of unnecessary browser plumbing. The AI-first pivot replaced brittle selectors with semantic interpretation. None of these pivots were random — each was documented with trigger, preserved elements, discarded elements, and rationale.

**Safety as structure, not procedure.** Human checkpoints are not a feature that can be disabled — they are evaluated before every tool execution by design. Single-tool-per-turn is not a suggestion to the LLM — it is enforced by the orchestration loop. Authentication detection is not a warning — it pauses the system and waits. The safety invariant is architectural: no irreversible action without human confirmation.

**Honest scope calibration.** Ten acknowledged limitations, each with impact, current mitigation, and North Star resolution. The system does not pretend to solve problems it does not solve. Mock-first is stated as a deliberate decision, not hidden as a limitation. API cost ($0.50-2.00 per run) is documented, not minimized. Bot detection is acknowledged as HIGH risk, not dismissed as "handled by stealth."

**Intellectual honesty about the industry.** Every production cancellation service uses human operators. No tool automates Netflix cancellation via browser in production. Stating this upfront — and then demonstrating an architecture that shows why it's worth trying — is more credible than pretending the problem is solved.

### The Four Pivots Tell the Story

1. **SubStretcher Plugin → SubTerminator CLI** — Focus on the orchestration engine, not the delivery mechanism
2. **Live Netflix → Mock-first** — Research revealed blockers; mock-first enabled the project to exist
3. **State Machine → AI Agent** — Hardcoded selectors break; AI interpretation survives
4. **Custom Tools → MCP Orchestration** — Don't build what Microsoft already ships

Each pivot discarded investment (original architecture, CSS selectors, custom browser tools) in favor of a better approach. The willingness to pivot — four times in seven days — is itself a demonstration of engineering judgment.

### Nothing Accidental

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

## References

1. Netflix Terms of Use — "Any robot, spider, scraper or other automated means" prohibition.

2. Castle.io (2025). "From Puppeteer Stealth to Nodriver: How Anti-Detect Frameworks Evolved to Evade Bot Detection." — Playwright "Medium Detection Rate" finding.

3. Microsoft Playwright MCP — https://github.com/microsoft/playwright-mcp — Browser automation MCP server with accessibility tree snapshots and element references.

4. MCP Python SDK — https://github.com/modelcontextprotocol/python-sdk — Official Model Context Protocol client library.

5. Speakeasy MCP Guide — Tool design research: 30-tool threshold, domain-aware actions, poka-yoke design.

6. Anthropic (2025). "Building Effective Agents." — Agent architecture patterns and tool design best practices.

7. Rocket Money — https://help.rocketmoney.com — Human concierge model for subscription cancellation (industry standard).

8. Agent Browser — https://agent-browser.dev/ — Snapshot + refs pattern research (200-400 tokens vs 3,000-5,000 for full DOM).

9. Netify — Netflix infrastructure analysis (Open Connect proprietary CDN, undocumented anti-bot measures).

---

## Appendix: Artifact Registry

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
