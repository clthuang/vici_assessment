# SubTerminator CLI - Technical Specification

**Feature:** 001-subterminator-cli
**Version:** 1.0
**Date:** February 3, 2026
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

SubTerminator is a CLI tool that automates subscription cancellation flows, starting with Netflix. It uses browser automation (Playwright) and AI-powered page interpretation (Claude Vision) to navigate cancellation flows while keeping humans in control of irreversible actions.

### 1.2 Architecture Decision: Mock-First

Based on brainstorm findings:
- Netflix ToS prohibits automation (risk of account termination)
- No sandbox/test environment exists (cannot iterate on real flow)
- Bot detection probability is HIGH

**Solution:** Build against realistic mock Netflix pages as primary target. Real Netflix becomes optional validation after MVP is complete.

### 1.3 Scope

| In Scope (MVP) | Out of Scope |
|----------------|--------------|
| Netflix cancellation (mock + real) | Other services (Spotify, Hulu) |
| CLI interface (`subterminator cancel netflix`) | Browser extension |
| State machine navigation | Subscription detection/monitoring |
| Claude Vision page analysis | Credential storage |
| Human-in-the-loop confirmations | CAPTCHA bypass |
| Screenshot/logging diagnostics | Mobile app subscriptions |
| Dry-run mode | Concurrent cancellations |
| Mock server for testing | |
| Third-party billing detection | |
| Shared account warning | |

### 1.4 Risk Disclaimer

**Terms of Service Warning:** This tool automates interactions with Netflix's website, which may violate Netflix's Terms of Service. Users accept all risk of account suspension or termination. This tool is provided for educational and demonstration purposes.

This warning must be displayed:
- On first run (one-time acknowledgment)
- In README documentation
- In `--help` output

---

## 2. Functional Requirements

### 2.1 CLI Interface

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **CLI-1** | Command: `subterminator cancel <service>` | Must | Accepts "netflix" as service argument |
| **CLI-2** | Flag: `--dry-run` | Must | Stops before final confirmation click |
| **CLI-3** | Flag: `--target <mock\|live>` | Must | Defaults to "live"; "mock" uses local server |
| **CLI-4** | Flag: `--verbose` | Should | Increases logging detail |
| **CLI-5** | Flag: `--output-dir <path>` | Should | Custom location for screenshots/logs |
| **CLI-6** | Version command: `subterminator --version` | Must | Shows version number |
| **CLI-7** | Help command: `subterminator --help` | Must | Shows usage information |

### 2.2 State Machine

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **SM-1** | Implement state machine with defined states | Must | States: START, LOGIN_REQUIRED, ACCOUNT_ACTIVE, ACCOUNT_CANCELLED, CANCEL_FLOW, RETENTION_OFFER, EXIT_SURVEY, FINAL_CONFIRMATION, COMPLETE, FAILED, ABORTED |
| **SM-2** | Validate state transitions | Must | Invalid transitions raise error with current/attempted states |
| **SM-3** | Log all state transitions | Must | Each transition logged with timestamp and metadata |
| **SM-4** | Support retry on transient failures | Must | Max 3 retries for network/timeout errors |
| **SM-5** | Detect infinite loops | Must | Max 10 state transitions in cancel flow before failure |

### 2.3 Browser Automation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **BA-1** | Launch browser with stealth settings | Must | playwright-stealth applied; visible browser window |
| **BA-2** | Navigate to target URL | Must | Handles redirects; waits for page load |
| **BA-3** | Capture screenshot on state change | Must | PNG format; timestamped filename |
| **BA-4** | Capture HTML dump on failure | Must | Full page HTML saved for debugging |
| **BA-5** | Click elements by selector or text | Must | Scrolls element into view first |
| **BA-6** | Fill form fields | Must | Handles text inputs, radio buttons, dropdowns |
| **BA-7** | Wait for page transitions | Must | Configurable timeout (default 30s) |
| **BA-8** | Detect page state via URL and content | Must | Returns confidence score with state |

### 2.4 AI Page Interpretation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **AI-1** | Capture screenshot for Claude analysis | Must | 1024x768 resolution; PNG format |
| **AI-2** | Send screenshot + prompt to Claude Vision | Must | Uses anthropic SDK |
| **AI-3** | Parse Claude response to determine page state | Must | Returns state enum + confidence (0-1) |
| **AI-4** | Identify interactive elements | Should | Returns list of actionable buttons/links |
| **AI-5** | Fall back to heuristics on API failure | Must | Uses URL patterns and text matching |
| **AI-6** | Log AI interpretation results | Must | Includes prompt, response, confidence |

### 2.5 Human-in-the-Loop

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **HIL-1** | Pause for authentication when login detected | Must | Clear CLI message; visible browser |
| **HIL-2** | Wait for user confirmation before final cancel | Must | Requires typing "confirm" to proceed |
| **HIL-3** | Allow user abort at any pause point | Must | Typing anything except "confirm" aborts |
| **HIL-4** | Timeout on human prompts | Must | 5 minutes for auth; 2 minutes for confirmation |
| **HIL-5** | Leave browser open on abort | Should | User can complete manually |
| **HIL-6** | Warn about shared account impact | Should | Confirmation prompt mentions all profiles will lose access |

### 2.6 Observability

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **OBS-1** | Create session directory per run | Must | Format: `./output/<service>_<timestamp>/` |
| **OBS-2** | Save screenshot at each state transition | Must | Named: `<step>_<state>.png` |
| **OBS-3** | Write JSON log of all events | Must | Includes timestamps, states, actions, errors |
| **OBS-4** | On failure, output manual completion steps | Must | CLI displays suggested next actions |
| **OBS-5** | Summary output on completion | Must | Shows success/failure, effective date, artifacts location |

### 2.7 Mock Server

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| **MOCK-1** | Serve static HTML pages mimicking Netflix | Must | 5 core pages minimum |
| **MOCK-2** | Use same CSS selectors as real Netflix | Must | Playwright code works unchanged |
| **MOCK-3** | Support configurable flow variants | Should | JSON config selects A/B variants |
| **MOCK-4** | Simulate error conditions | Should | Timeout, session expiry, error pages |
| **MOCK-5** | Start/stop programmatically | Must | For integration tests |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-PERF-1** | Page load timeout | 30 seconds |
| **NFR-PERF-2** | Element detection timeout | 10 seconds |
| **NFR-PERF-3** | Claude API response time | < 10 seconds |
| **NFR-PERF-4** | Total flow (happy path, mock) | < 60 seconds |

### 3.2 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-REL-1** | Success rate against mock (happy path) | 100% |
| **NFR-REL-2** | Graceful failure rate (no crashes) | 100% |
| **NFR-REL-3** | Retry success for transient errors | > 80% |

### 3.3 Testability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-TEST-1** | Unit test coverage (core logic) | > 80% |
| **NFR-TEST-2** | Integration tests against mock | All happy + error paths |
| **NFR-TEST-3** | Tests run without network/API | Mock mode only |

### 3.4 Maintainability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-MAINT-1** | Adding new service | < 1 day effort |
| **NFR-MAINT-2** | All public functions documented | Docstrings required |
| **NFR-MAINT-3** | Type hints throughout | mypy strict mode passes |

---

## 4. Page States (Netflix)

### 4.1 State Definitions

| State | URL Pattern | Visual Indicators | Actions |
|-------|-------------|-------------------|---------|
| **LOGIN_REQUIRED** | `/login` | "Sign In" heading, email/password fields | PAUSE for human auth |
| **ACCOUNT_ACTIVE** | `/account` | "Cancel Membership" link visible | Click cancel link |
| **ACCOUNT_CANCELLED** | `/account` | "Restart Membership" text, no cancel link | EXIT (already cancelled) |
| **RETENTION_OFFER** | `/cancelplan*` | "Before you go", discount offer, "Continue to Cancel" button | Click decline/continue |
| **EXIT_SURVEY** | `/cancelplan*` | "Why are you leaving?", radio buttons | Select option, submit |
| **FINAL_CONFIRMATION** | `/cancelplan*` | "Finish Cancellation" button, effective date | PAUSE for human confirmation |
| **COMPLETE** | `/cancelplan*` or `/account` | "Cancelled" heading, confirmation message | EXIT (success) |
| **ERROR** | Any | "Something went wrong", error message | EXIT (failure) |
| **UNKNOWN** | Any | None of the above detected | Attempt AI interpretation → PAUSE if low confidence |
| **THIRD_PARTY_BILLING** | `/account` | "Billed through iTunes/Google Play/T-Mobile" or similar | EXIT (cannot automate, provide instructions) |

### 4.2 State Transitions

```
START → LOGIN_REQUIRED | ACCOUNT_ACTIVE | ACCOUNT_CANCELLED | THIRD_PARTY_BILLING | ERROR | UNKNOWN

LOGIN_REQUIRED → ACCOUNT_ACTIVE | ACCOUNT_CANCELLED | THIRD_PARTY_BILLING | ERROR | UNKNOWN (after auth)

ACCOUNT_ACTIVE → RETENTION_OFFER | EXIT_SURVEY | FINAL_CONFIRMATION | ERROR | UNKNOWN

THIRD_PARTY_BILLING → (terminal, cannot automate)

RETENTION_OFFER → RETENTION_OFFER | EXIT_SURVEY | FINAL_CONFIRMATION | ERROR | UNKNOWN

EXIT_SURVEY → RETENTION_OFFER | FINAL_CONFIRMATION | ERROR | UNKNOWN

FINAL_CONFIRMATION → COMPLETE | ERROR | ABORTED (user abort)

COMPLETE → (terminal)
ABORTED → (terminal)
ERROR → (terminal, after retries exhausted)
```

### 4.3 Detection Strategy

1. **URL-based detection** (high confidence):
   - `/login` → LOGIN_REQUIRED
   - `/account` → check for cancel vs restart link

2. **Text-based detection** (medium confidence):
   - Search for key phrases: "Cancel Membership", "Restart Membership", "Finish Cancellation"

3. **AI-based detection** (fallback):
   - Send screenshot to Claude when heuristics fail or have low confidence
   - Claude returns state classification + confidence score

---

## 5. Error Handling

### 5.1 Error Categories

| Category | Examples | Retry? | User Action |
|----------|----------|--------|-------------|
| **Transient** | Network timeout, page load failure | Yes (3x) | Wait |
| **Recoverable** | Session expired, login required | No | Human auth |
| **Permanent** | Account locked, geographic restriction | No | Manual steps provided |
| **Third-Party** | iTunes/Google Play/T-Mobile billing | No | Redirect to billing provider |
| **Unexpected** | Unknown page state, crash | No | Manual steps + diagnostics |

### 5.1.1 Third-Party Billing Detection

High priority detection (likely common). When detected:
```
⚠ Cannot cancel through Netflix.

Your subscription is billed through {provider}.
To cancel, you must:
  1. Open {provider} app/website
  2. Navigate to subscriptions
  3. Cancel Netflix from there

Netflix cannot process this cancellation directly.
```

### 5.2 Failure Output

On any non-success exit:
```
✗ Cancellation failed.

Last successful state: {state}
Failed at: {description}

Diagnostics:
  URL: {current_url}
  Screenshot: {path}
  Log: {path}

Suggested manual steps:
  1. Navigate to netflix.com/account
  2. {context-specific steps}

Report issues: {link}
```

---

## 6. Data Structures

### 6.1 Session Log (JSON)

```json
{
  "session_id": "netflix_20260203_101530",
  "service": "netflix",
  "target": "mock|live",
  "started_at": "2026-02-03T10:15:30Z",
  "completed_at": "2026-02-03T10:17:45Z",
  "result": "success|failure|aborted",
  "final_state": "COMPLETE",
  "transitions": [
    {
      "timestamp": "2026-02-03T10:15:32Z",
      "from_state": "START",
      "to_state": "ACCOUNT_ACTIVE",
      "trigger": "page_loaded",
      "url": "https://www.netflix.com/account",
      "screenshot": "01_account_active.png",
      "detection_method": "url_pattern",
      "confidence": 0.95
    }
  ],
  "ai_calls": [
    {
      "timestamp": "2026-02-03T10:16:00Z",
      "screenshot": "03_unknown.png",
      "prompt_tokens": 1500,
      "response_tokens": 150,
      "state_detected": "RETENTION_OFFER",
      "confidence": 0.85
    }
  ],
  "error": null
}
```

### 6.2 Service Configuration (YAML)

```yaml
netflix:
  name: "Netflix"
  entry_url: "https://www.netflix.com/account"
  mock_entry_url: "http://localhost:8000/account"

  states:
    login_required:
      url_patterns: ["/login"]
      text_indicators: ["Sign In", "Email", "Password"]

    account_active:
      url_patterns: ["/account"]
      text_indicators: ["Cancel Membership"]

    # ... etc

  actions:
    click_cancel:
      selectors:
        - "[data-uia='action-cancel-membership']"
        - "a:has-text('Cancel Membership')"

    # ... etc
```

---

## 7. API Contracts

### 7.1 CLI Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (cancellation complete or already cancelled) |
| 1 | Failure (automation could not complete) |
| 2 | Aborted (user cancelled at confirmation) |
| 3 | Invalid arguments |
| 4 | Configuration error |

### 7.2 Claude Vision Prompt Format

```
Analyze this screenshot of a subscription cancellation flow.

Determine which state this page represents:
- LOGIN_REQUIRED: Login form is shown
- ACCOUNT_ACTIVE: Account page with active subscription, cancel option visible
- ACCOUNT_CANCELLED: Account page showing cancelled/inactive subscription
- RETENTION_OFFER: Discount or "stay with us" offer
- EXIT_SURVEY: "Why are you leaving?" survey
- FINAL_CONFIRMATION: Final "Finish Cancellation" button
- COMPLETE: Cancellation confirmed
- ERROR: Error message displayed
- UNKNOWN: Cannot determine

Also identify any actionable buttons/links with their approximate text.

Respond in JSON format:
{
  "state": "<STATE>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>",
  "actions": [{"text": "<button text>", "action": "<click|skip>"}]
}
```

---

## 8. Test Scenarios

### 8.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_state_machine_valid_transitions` | All valid transitions succeed |
| `test_state_machine_invalid_transitions` | Invalid transitions raise error |
| `test_state_detection_url_patterns` | URL-based detection returns correct states |
| `test_state_detection_text_patterns` | Text-based detection with mock HTML |
| `test_retry_logic` | Transient failures retry up to 3x |
| `test_session_log_format` | Log output matches schema |

### 8.2 Integration Tests (Mock Server)

| Test | Description |
|------|-------------|
| `test_happy_path_cancellation` | Full flow: account → cancel → survey → confirm → complete |
| `test_already_cancelled` | Detects cancelled state, exits cleanly |
| `test_retention_offer_decline` | Navigates past retention offer |
| `test_dry_run_stops_at_confirmation` | Doesn't click final button |
| `test_user_abort` | Handles non-"confirm" input correctly |
| `test_session_timeout` | Handles mock timeout, prompts re-auth |
| `test_error_page_handling` | Captures diagnostics on error page |

### 8.3 E2E Tests (Manual, Real Netflix)

| Test | Description |
|------|-------------|
| `e2e_real_netflix_dry_run` | Runs against real Netflix in dry-run mode |
| `e2e_real_netflix_cancellation` | Full cancellation (requires active subscription) |

---

## 9. Acceptance Criteria Summary

### 9.1 MVP Complete When

- [ ] `subterminator cancel netflix --target mock` completes happy path
- [ ] `subterminator cancel netflix --target mock --dry-run` stops at final confirmation
- [ ] All unit tests pass (>80% coverage on core logic)
- [ ] All integration tests pass against mock server
- [ ] Screenshots and logs generated correctly
- [ ] Human-in-the-loop pauses work correctly
- [ ] CLI help and version commands work
- [ ] GitHub Actions runs lint + unit tests on push

### 9.2 Stretch Goals

- [ ] `subterminator cancel netflix --target live` works against real Netflix
- [ ] Multiple mock flow variants (A/B tests)
- [ ] Full edge case coverage in state machine
- [ ] Demo video recorded

---

## 10. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| Playwright | 1.58+ | Browser automation |
| playwright-stealth | 2.0+ | Anti-detection |
| python-statemachine | 2.5+ | State management |
| Typer | 0.21+ | CLI framework |
| anthropic | latest | Claude Vision API |
| pytest | 8.0+ | Testing |
| pytest-asyncio | latest | Async test support |
| pytest-playwright | latest | Playwright fixtures |

---

## 11. Open Questions

| Question | Status | Answer |
|----------|--------|--------|
| Budget for Claude API calls? | Resolved | ~$25-40 development |
| Test with real Netflix? | Resolved | Yes, as final validation |
| Mock fidelity level? | Resolved | Pixel-perfect, same selectors |
| Netflix A/B variants to mock? | Open | TBD during implementation |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial specification from brainstorm |
