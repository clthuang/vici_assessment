# SubTerminator CLI - Implementation Tasks

**Feature:** 001-subterminator-cli
**Generated:** February 3, 2026
**Target:** <15 minutes per task

---

## Task Legend

- `[ ]` Pending
- `[~]` In Progress
- `[x]` Complete
- `[!]` Blocked

## Dependency & Parallelization Guide

### Notation
- **Depends:** Tasks that must complete before this task can start
- **Parallel:** Tasks that can be worked on simultaneously by different developers
- **Blocks:** Tasks that cannot start until this task completes

### Team Parallelization Overview

| Stream | Owner | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 | Day 6 |
|--------|-------|-------|-------|-------|-------|-------|-------|
| **A: Core** | Dev A | P1, P2 | P7 | P11, P13 | P15 | P16 | P19.2 |
| **B: Data** | Dev B | P3, P4 | P8 | P12 | P14 | P17 | P19.1 |
| **C: Mock** | Dev C | P5, P6 | P9, P10 | — (merge) | — | P18 | P19.3 |

### Critical Path (Must Be Sequential)
```
P1 → P2 → P5 → P7 → P13 → P15 → P16/P17 → P18 → P19 → P20
```

### Parallel Tracks After P1
```
Track A: P2 → P7 → P11 → P13.1-13.2
Track B: P3 → P4 (independent)
Track C: P5 → P6 (independent, needs P2 types)
Track D: P8 → P12 (independent after P2)
Track E: P9 → P10 (independent after P1)
```

---

## Day 1: Foundation (P1-P6)

### P1: Project Setup

> **Parallel:** T1.1-T1.6 can be done in parallel by different developers
> **Blocks:** All subsequent phases depend on P1 completion

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T1.1 | Create `pyproject.toml` with all dependencies | 10m | — | T1.2, T1.5, T1.6 | File exists with playwright, typer, anthropic, python-statemachine, pytest, ruff, mypy, **requests** |
| T1.2 | Create directory structure | 5m | — | T1.1, T1.5, T1.6 | `src/subterminator/{cli,core,services,utils}/` and `tests/{unit,integration,e2e}/` exist |
| T1.3 | Create `__init__.py` with version | 5m | T1.2 | T1.4 | `from subterminator import __version__` works |
| T1.4 | Create `__main__.py` entry point | 5m | T1.2 | T1.3 | `python -m subterminator` runs without error |
| T1.5 | Create `.env.example` | 5m | — | T1.1, T1.2, T1.6 | Contains `ANTHROPIC_API_KEY=` and other config vars |
| T1.6 | Create `.gitignore` | 5m | — | T1.1, T1.2, T1.5 | Covers Python, venv, .env, output/, __pycache__ |
| T1.7 | Install dependencies | 10m | T1.1 | — | `pip install -e ".[dev]"` succeeds |
| T1.8 | Install Playwright browsers | 5m | T1.7 | — | `playwright install chromium` succeeds |

**Checkpoint:** `python -m subterminator --help` shows stub help

**Critical Note:** T1.1 must include `requests` library (used in P10 mock server). This was identified during plan verification.

---

### P2: Protocols & Data Types

> **Depends:** P1 complete
> **Parallel:** All T2.x tasks can be done in parallel (no internal dependencies)
> **Blocks:** P5 (State Machine), P7 (Browser), P8 (Heuristic), P11 (AI), P12 (Service), P13 (Engine)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T2.1 | Define `State` enum | 10m | P1 | T2.2-T2.6 | All 11 states defined: START, LOGIN_REQUIRED, ACCOUNT_ACTIVE, ACCOUNT_CANCELLED, THIRD_PARTY_BILLING, RETENTION_OFFER, EXIT_SURVEY, FINAL_CONFIRMATION, COMPLETE, ABORTED, FAILED |
| T2.2 | Define `AIInterpretation` dataclass | 5m | P1 | T2.1, T2.3-T2.6 | Fields: state, confidence, reasoning, actions |
| T2.3 | Define `CancellationResult` dataclass | 5m | P1 | T2.1-T2.2, T2.4-T2.6 | Fields: success, state, message, session_dir, effective_date |
| T2.4 | Define `BrowserProtocol` | 10m | P1 | T2.1-T2.3, T2.5-T2.6 | All methods from design: launch, navigate, click, fill, select_option, screenshot, html, url, text_content, close |
| T2.5 | Define `AIInterpreterProtocol` | 5m | T2.2 | T2.1, T2.3-T2.4, T2.6 | Method: interpret(screenshot: bytes) -> AIInterpretation |
| T2.6 | Define `ServiceProtocol` | 5m | P1 | T2.1-T2.5 | Properties: config, entry_url, selectors |

**Checkpoint:** `mypy src/subterminator/core/protocols.py` passes

**Team Note:** One developer can do all P2 tasks sequentially (~40m), OR split T2.1-T2.3 (types) and T2.4-T2.6 (protocols) between two developers.

---

### P3: Exceptions

> **Depends:** P1 complete (directory structure)
> **Parallel with:** P2 (can be developed simultaneously by different developer)
> **Blocks:** P4 (ConfigurationError), P7 (ElementNotFound), P13 (all exceptions)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T3.1 | Define `SubTerminatorError` base class | 3m | P1 | P2 | Base exception with docstring |
| T3.2 | Define `TransientError` | 3m | T3.1 | P2 | Inherits from base, for retry-able errors |
| T3.3 | Define `PermanentError` | 3m | T3.1 | P2 | Inherits from base, for non-retry-able errors |
| T3.4 | Define specialized exceptions | 10m | T3.1-T3.3 | P2 | ConfigurationError, ServiceError, HumanInterventionRequired, UserAborted, ElementNotFound |

**Checkpoint:** All exceptions importable from `subterminator.utils.exceptions`

**Team Note:** P3 is independent of P2 - assign to different developer for parallel progress.

---

### P4: Configuration

> **Depends:** P1 complete, P3 complete (for ConfigurationError)
> **Parallel with:** P2, P5 (after P3 done)
> **Blocks:** P13 (Engine needs config), P15 (CLI needs config)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T4.1 | Define `AppConfig` dataclass | 10m | P1 | P2, P5 | All fields: anthropic_api_key, output_dir, page_timeout, element_timeout, auth_timeout, confirm_timeout, max_retries, max_transitions |
| T4.2 | Implement `ConfigLoader.load()` | 10m | T4.1, P3 | P2, P5 | Reads from environment variables, returns AppConfig; raises ConfigurationError on missing required vars |

**Checkpoint:** `ConfigLoader.load()` returns valid AppConfig

**Team Note:** P4 is a small independent unit - good for a third developer or as a gap-filler task.

---

### P5: State Machine

> **Depends:** P2 complete (for State enum)
> **Parallel with:** P3, P4, P6 (after P2 done)
> **Blocks:** P13 (Engine uses state machine)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T5.1 | Create `CancellationStateMachine` class | 10m | T2.1 | P3, P4 | Inherits from StateMachine, has `start` as initial state |
| T5.2 | Define all states | 10m | T5.1 | P3, P4 | 11 states defined with correct `initial=True` and `final=True` flags |
| T5.3 | Define `navigate` transition | 5m | T5.2 | T5.4-T5.10 | start → multiple possible states |
| T5.4 | Define `authenticate` transition | 5m | T5.2 | T5.3, T5.5-T5.10 | login_required → account states |
| T5.5 | Define `click_cancel` transition | 5m | T5.2 | T5.3-T5.4, T5.6-T5.10 | account_active → cancel flow states |
| T5.6 | Define `decline_offer` transition | 5m | T5.2 | T5.3-T5.5, T5.7-T5.10 | retention_offer → next states |
| T5.7 | Define `submit_survey` transition | 5m | T5.2 | T5.3-T5.6, T5.8-T5.10 | exit_survey → next states |
| T5.8 | Define `confirm` transition | 5m | T5.2 | T5.3-T5.7, T5.9-T5.10 | final_confirmation → complete/failed |
| T5.9 | Define `abort` transition | 5m | T5.2 | T5.3-T5.8, T5.10 | Human checkpoint states → aborted |
| T5.10 | Define `resolve_unknown` transition | 5m | T5.2 | T5.3-T5.9 | unknown → any identified state |
| T5.11 | Add `on_enter_state` observer | 10m | T5.3-T5.10 | — | Logs transition, captures screenshot |

**Checkpoint:** Can create state machine, verify initial state is 'start'

**Team Note:** T5.3-T5.10 (transitions) can be split among developers - each transition is independent. One developer could do T5.3-T5.6, another T5.7-T5.10.

---

### P6: Session Logger

> **Depends:** P2 complete (for State enum, CancellationResult)
> **Parallel with:** P3, P4, P5 (after P2 done)
> **Blocks:** P13 (Engine uses session logger)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T6.1 | Define `StateTransition` dataclass | 5m | T2.1 | P3, P4, P5 | All fields per design |
| T6.2 | Define `AICall` dataclass | 5m | T2.2 | T6.1 | All fields per design |
| T6.3 | Create `SessionLogger.__init__` | 10m | T6.1, T6.2 | P3, P4, P5 | Creates session dir, initializes data dict |
| T6.4 | Implement `log_transition()` | 10m | T6.3 | T6.5 | Appends to transitions list, calls _save() |
| T6.5 | Implement `log_ai_call()` | 5m | T6.3 | T6.4 | Appends to ai_calls list, calls _save() |
| T6.6 | Implement `complete()` | 5m | T6.4, T6.5 | T6.7 | Sets completed_at, result, final_state |
| T6.7 | Implement `_save()` | 5m | T6.3 | T6.4-T6.6 | Writes JSON to session.json |

**Checkpoint:** Can log transitions and verify JSON file created

**Team Note:** P6 is independent of P5 (State Machine) - can be developed in parallel by different developer.

---

## Day 2: Core Components (P7-P10)

### P7: Browser Wrapper

> **Depends:** P1 (Playwright installed), P2 (BrowserProtocol), P3 (ElementNotFound exception)
> **Parallel with:** P8, P9, P10 (all Day 2 phases can run in parallel)
> **Blocks:** P13 (Engine uses browser)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T7.1 | Create `PlaywrightBrowser.__init__` | 5m | T2.4 | P8, P9, P10 | Stores headless flag, initializes None for browser/page |
| T7.2 | Implement `launch()` | 15m | T7.1 | P8, P9, P10 | Starts playwright, launches chromium, creates page, applies stealth |
| T7.3 | Implement `navigate()` | 10m | T7.2 | T7.4-T7.11 | Goes to URL, waits for networkidle, handles timeout |
| T7.4 | Implement `click()` with fallback | 15m | T7.2, T3.4 | T7.3, T7.5-T7.11 | Tries multiple selectors, scrolls into view, clicks; raises ElementNotFound |
| T7.5 | Implement `fill()` | 5m | T7.2 | T7.3-T7.4, T7.6-T7.11 | Fills text input |
| T7.6 | Implement `select_option()` | 10m | T7.2 | T7.3-T7.5, T7.7-T7.11 | Handles dropdown and radio buttons |
| T7.7 | Implement `screenshot()` | 5m | T7.2 | T7.3-T7.6, T7.8-T7.11 | Returns bytes, optionally saves to path |
| T7.8 | Implement `html()` | 3m | T7.2 | T7.3-T7.7, T7.9-T7.11 | Returns page.content() |
| T7.9 | Implement `url()` | 3m | T7.2 | T7.3-T7.8, T7.10-T7.11 | Returns page.url |
| T7.10 | Implement `text_content()` | 5m | T7.2 | T7.3-T7.9, T7.11 | Returns inner_text of body |
| T7.11 | Implement `close()` | 5m | T7.2 | T7.3-T7.10 | Closes browser with cleanup |

**Checkpoint:** Can launch browser, navigate to example.com, screenshot, close

**Team Note:** T7.3-T7.11 methods are independent after T7.2 - can split: Dev A (T7.3-T7.6 navigation/interaction), Dev B (T7.7-T7.11 getters/cleanup).

---

### P8: Heuristic Interpreter

> **Depends:** P2 (State enum, AIInterpretation, AIInterpreterProtocol)
> **Parallel with:** P7, P9, P10 (all Day 2 phases can run in parallel)
> **Blocks:** P13 (Engine uses heuristic interpreter)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T8.1 | Create `HeuristicInterpreter` class | 5m | T2.1, T2.2, T2.5 | P7, P9, P10 | Class with interpret method signature |
| T8.2 | Implement URL-based detection | 10m | T8.1 | T8.3-T8.8 | /login → LOGIN_REQUIRED, /account patterns |
| T8.3 | Implement text detection: login states | 5m | T8.1 | T8.2, T8.4-T8.8 | "Sign In", "Email", "Password" |
| T8.4 | Implement text detection: account states | 10m | T8.1 | T8.2-T8.3, T8.5-T8.8 | "Cancel Membership", "Restart Membership" |
| T8.5 | Implement text detection: third-party billing | 5m | T8.1 | T8.2-T8.4, T8.6-T8.8 | "Billed through", "iTunes", "Google Play" |
| T8.6 | Implement text detection: cancel flow states | 10m | T8.1 | T8.2-T8.5, T8.7-T8.8 | retention, survey, confirmation, complete |
| T8.7 | Implement text detection: error state | 5m | T8.1 | T8.2-T8.6, T8.8 | "Something went wrong", "Error" |
| T8.8 | Return UNKNOWN with 0.0 confidence as fallback | 5m | T8.2-T8.7 | — | When no patterns match (catch-all) |

**Checkpoint:** Can detect ACCOUNT_ACTIVE from "/account" + "Cancel Membership"

**Team Note:** T8.2-T8.7 detection patterns are independent - can split: Dev A (T8.2-T8.4), Dev B (T8.5-T8.7), then merge for T8.8.

---

### P9: Mock Pages

> **Depends:** P1 (directory structure only - no code dependencies)
> **Parallel with:** P7, P8, P10 (completely independent work stream)
> **Blocks:** P10 (Mock Server needs pages), P11 (screenshot_test.png for AI testing), P17 (Integration tests need mock pages)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T9.1 | Create `mock_pages/netflix/` directory | 2m | P1 | P7, P8 | Directory exists |
| T9.2 | Create `account.html` | 15m | T9.1 | T9.3-T9.9 | Active subscription page with `[data-uia='action-cancel-membership']` link |
| T9.3 | Create `account_cancelled.html` | 10m | T9.1 | T9.2, T9.4-T9.9 | Shows "Restart Membership", no cancel link |
| T9.4 | Create `login.html` | 10m | T9.1 | T9.2-T9.3, T9.5-T9.9 | Login form with email/password fields |
| T9.5 | Create `cancelplan_survey.html` | 15m | T9.1 | T9.2-T9.4, T9.6-T9.9 | Exit survey with radio buttons, continue button |
| T9.6 | Create `cancelplan_retention.html` | 15m | T9.1 | T9.2-T9.5, T9.7-T9.9 | Retention offer with decline button |
| T9.7 | Create `cancelplan_confirm.html` | 10m | T9.1 | T9.2-T9.6, T9.8-T9.9 | Final confirmation with "Finish Cancellation" button |
| T9.8 | Create `cancelplan_complete.html` | 10m | T9.1 | T9.2-T9.7, T9.9 | Cancellation confirmed message |
| T9.9 | Create `error.html` | 5m | T9.1 | T9.2-T9.8 | Generic error page |
| T9.10 | Create `assets/netflix.css` | 10m | T9.1 | T9.2-T9.9 | Minimal styling for structure |
| T9.11 | Create `screenshot_test.png` | 5m | T9.2, T9.10 | — | Screenshot of account.html for AI testing |

**Checkpoint:** All HTML files open in browser with correct structure

**Team Note:** P9 is **ideal for a frontend/design-focused developer** or junior team member. All T9.2-T9.10 pages are completely independent and can be split among multiple people. T9.11 must wait for T9.2 (needs account.html rendered to screenshot).

---

### P10: Mock Server

> **Depends:** P1 (requests library in dependencies), P9 (mock pages to serve)
> **Parallel with:** P7, P8 (after P9 has at least T9.2 done)
> **Blocks:** P17 (Integration tests use mock server)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T10.1 | Create `MockServer.__init__` | 5m | P1, T9.1 | P7, P8 | Stores pages_dir, port, initializes server/thread as None |
| T10.2 | Implement `start()` | 15m | T10.1 | P7, P8 | Creates HTTPServer, starts in daemon thread |
| T10.3 | Implement `stop()` | 10m | T10.2 | — | Calls shutdown, joins thread |
| T10.4 | Add custom handler for variant routing | 15m | T10.2 | — | Handles `?variant=` query parameter |

**Checkpoint:** Can start server, fetch account.html, stop server

**Critical Note:** T10.2 uses Python's `http.server` from stdlib, NOT `requests`. The `requests` library is used elsewhere for testing/fetching - ensure it's in pyproject.toml (see T1.1).

---

## Day 3: Integration (P11-P13)

### P11: Claude AI Interpreter

> **Depends:** P2 (AIInterpretation, AIInterpreterProtocol), P3 (exceptions), P9.11 (screenshot_test.png for testing)
> **Parallel with:** P12 (completely independent)
> **Blocks:** P13 (Engine uses AI interpreter)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T11.1 | Create `ClaudeInterpreter.__init__` | 5m | T2.2, T2.5 | P12 | Initializes Anthropic client with API key |
| T11.2 | Define `PROMPT_TEMPLATE` | 10m | T2.1 | P12 | Full prompt per design with all states |
| T11.3 | Implement `interpret()` | 15m | T11.1, T11.2 | P12 | Encodes image, calls Claude Vision API |
| T11.4 | Implement `_parse_response()` | 10m | T11.3, T2.2 | P12 | Parses JSON, returns AIInterpretation |
| T11.5 | Add error handling | 10m | T11.3, P3 | P12 | Handles API errors, JSON parse errors gracefully |

**Checkpoint:** Can interpret screenshot (requires API key)

**Critical Note:** Testing T11.3 requires T9.11 (screenshot_test.png). If P9 is behind schedule, create a simple test PNG manually to unblock.

---

### P12: Netflix Service

> **Depends:** P2 (ServiceProtocol)
> **Parallel with:** P11 (completely independent)
> **Blocks:** P13 (Engine uses service for selectors/URLs)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T12.1 | Create `ServiceSelectors` dataclass | 5m | P1 | P11 | Fields: cancel_link, decline_offer, survey_option, survey_submit, confirm_cancel |
| T12.2 | Create `ServiceConfig` dataclass | 5m | T12.1 | P11 | Fields: name, entry_url, mock_entry_url, selectors, text_indicators |
| T12.3 | Create `NetflixService.__init__` | 10m | T12.2, T2.6 | P11 | Takes target, creates full ServiceConfig |
| T12.4 | Configure all selectors | 10m | T12.3 | P11 | Multiple fallback selectors per action |
| T12.5 | Configure text indicators | 10m | T12.3 | T12.4 | All text patterns for each state |
| T12.6 | Implement `entry_url` property | 5m | T12.3 | T12.4, T12.5 | Returns mock or live URL based on target |

**Checkpoint:** Can get selectors and entry_url for mock target

**Team Note:** P11 (AI) and P12 (Service) are completely independent - assign to different developers for maximum parallelization on Day 3.

---

### P13: Cancellation Engine

> **Depends:** P4 (Config), P5 (State Machine), P6 (Session Logger), P7 (Browser), P8 (Heuristic), P11 (AI), P12 (Service)
> **This is the integration point - requires most prior phases complete**
> **Parallel with:** None (integration phase)
> **Blocks:** P15 (CLI uses engine), P16 (Unit tests), P17 (Integration tests)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T13.1 | Create `CancellationEngine.__init__` | 10m | P4, P5, P6, P7, P8, P11, P12 | — | DI for all dependencies |
| T13.2 | Implement `run()` main loop | 15m | T13.1 | T13.15 | Loops until terminal state, respects max_transitions |
| T13.3 | Implement `_detect_state()` | 15m | T13.1, P8, P11 | T13.4-T13.12 | Cascades: heuristic → AI → human checkpoint |
| T13.4 | Implement `_handle_state()` for START | 10m | T13.1 | T13.5-T13.12, T13.14 | Navigates to entry URL |
| T13.5 | Implement `_handle_state()` for LOGIN_REQUIRED | 10m | T13.1, T13.13 | T13.4, T13.6-T13.12, T13.14 | Human checkpoint for auth |
| T13.6 | Implement `_handle_state()` for ACCOUNT_ACTIVE | 10m | T13.1 | T13.4-T13.5, T13.7-T13.12, T13.14 | Clicks cancel link |
| T13.7 | Implement `_handle_state()` for ACCOUNT_CANCELLED | 5m | T13.1 | T13.4-T13.6, T13.8-T13.12, T13.14 | Returns COMPLETE (already done) |
| T13.8 | Implement `_handle_state()` for THIRD_PARTY_BILLING | 10m | T13.1 | T13.4-T13.7, T13.9-T13.12, T13.14 | Shows instructions, returns FAILED |
| T13.9 | Implement `_handle_state()` for RETENTION_OFFER | 10m | T13.1 | T13.4-T13.8, T13.10-T13.12, T13.14 | Clicks decline button |
| T13.10 | Implement `_handle_state()` for EXIT_SURVEY | 10m | T13.1, T13.14 | T13.4-T13.9, T13.11-T13.12 | Selects option, submits |
| T13.11 | Implement `_handle_state()` for FINAL_CONFIRMATION | 15m | T13.1, T13.13 | T13.4-T13.10, T13.12 | Dry-run check, human checkpoint, click confirm |
| T13.12 | Implement `_handle_state()` for UNKNOWN | 10m | T13.1, T13.3, T13.13 | T13.4-T13.11 | AI interpretation, human checkpoint if low confidence |
| T13.13 | Implement `_human_checkpoint()` | 15m | T13.1, P3 | T13.4-T13.12, T13.14 | Prompts user, handles timeout, returns continue/abort |
| T13.14 | Implement `_complete_survey()` helper | 10m | T13.1 | T13.4-T13.13 | Selects first option, clicks continue |
| T13.15 | Implement `with_retry()` utility | 10m | P3 | T13.2-T13.14 | Retry logic with exponential backoff |

**Checkpoint:** Engine can run against mock in dry-run mode

**Critical Integration Point:** P13 is the main integration phase. Before starting:
- Ensure P5 (State Machine) is fully tested
- Ensure P7 (Browser) can navigate and screenshot
- Ensure P8 (Heuristic) returns valid AIInterpretation

**Team Note:** T13.4-T13.12 (state handlers) can be split among 2-3 developers IF T13.1 and T13.13 are done first. Suggested split:
- Dev A: T13.4-T13.7 (initial + account states)
- Dev B: T13.8-T13.11 (cancel flow states)
- Dev C: T13.12, T13.14, T13.15 (utilities)

---

## Day 4: CLI & Output (P14-P15)

### P14: CLI Output Formatter

> **Depends:** P2 (State enum for display), P3 (exception types for error display)
> **Parallel with:** P15 can start after T14.1-T14.2 are done
> **Blocks:** P15 (CLI commands use formatter)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T14.1 | Create `OutputFormatter` class | 5m | P1 | — | Initialize with optional rich console |
| T14.2 | Implement `show_progress()` | 10m | T14.1, T2.1 | T14.3-T14.8 | Shows step indicator with state and message |
| T14.3 | Implement `show_human_prompt()` for AUTH | 10m | T14.1 | T14.2, T14.4-T14.8 | Clear message, waits for Enter |
| T14.4 | Implement `show_human_prompt()` for CONFIRM | 10m | T14.1 | T14.2-T14.3, T14.5-T14.8 | Shows warning, requires "confirm" input |
| T14.5 | Implement `show_success()` | 10m | T14.1 | T14.2-T14.4, T14.6-T14.8 | Shows checkmark, effective date, screenshot path |
| T14.6 | Implement `show_failure()` | 15m | T14.1, P3 | T14.2-T14.5, T14.7-T14.8 | Shows diagnostics, manual steps, artifacts |
| T14.7 | Implement `show_warning()` | 5m | T14.1 | T14.2-T14.6, T14.8 | Yellow warning for ToS disclaimer |
| T14.8 | Implement `show_third_party_instructions()` | 10m | T14.1 | T14.2-T14.7 | Provider-specific cancellation steps |

**Checkpoint:** All output methods produce readable CLI output

**Team Note:** T14.2-T14.8 are independent display methods - can be split among developers. Good opportunity for parallel work.

---

### P15: CLI Commands

> **Depends:** P4 (Config), P13 (Engine), P14 (Output Formatter)
> **Parallel with:** None (depends on P13 completion)
> **Blocks:** P16 (needs CLI to test), P17 (needs CLI for e2e), P18 (CI needs working CLI)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T15.1 | Create Typer app | 5m | P1 | T15.4 | `app = typer.Typer()` with help text |
| T15.2 | Implement `cancel` command signature | 10m | T15.1 | T15.4 | Arguments: service, --dry-run, --target, --verbose, --output-dir |
| T15.3 | Implement `cancel` command body | 15m | T15.2, P4, P13, P14 | — | Creates dependencies, runs engine |
| T15.4 | Implement `version` command | 5m | T15.1 | T15.2 | Shows `subterminator {version}` |
| T15.5 | Add service validation | 5m | T15.2 | T15.6-T15.7 | Only "netflix" supported, clear error for others |
| T15.6 | Implement exit code handling | 10m | T15.3, P3 | T15.5, T15.7 | 0=success, 1=failure, 2=aborted, 3=invalid args, 4=config error |
| T15.7 | Add ToS disclaimer on first run | 15m | T15.1, P14 | T15.5-T15.6 | Stores acknowledgment, shows warning |
| T15.8 | Update `__main__.py` | 5m | T15.3 | — | Calls `app()` from cli.main |

**Checkpoint:** `python -m subterminator cancel netflix --target mock --dry-run` runs

**Critical Path Note:** P15 is on the critical path. T15.3 requires P13 (Engine) to be complete. Plan for this dependency.

---

## Day 5: Testing & CI (P16-P18)

### P16: Unit Tests

> **Depends:** P2-P8 complete (all components to test)
> **Parallel with:** P17 (different test scopes), P18 (CI setup)
> **Blocks:** P18 (CI runs unit tests)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T16.1 | Create `conftest.py` with fixtures | 15m | P2, P5, P6, P7, P8 | P17.1, P18.1-P18.2 | mock_browser, mock_ai, mock_session fixtures |
| T16.2 | Write `test_states.py`: valid transitions | 15m | T16.1, P5 | T16.3-T16.7, P17, P18 | Test all valid state transitions |
| T16.3 | Write `test_states.py`: invalid transitions | 10m | T16.2 | T16.4-T16.7, P17, P18 | Test transition errors raised |
| T16.4 | Write `test_browser.py`: click fallback | 10m | T16.1, P7 | T16.2-T16.3, T16.5-T16.7, P17, P18 | Test selector fallback logic |
| T16.5 | Write `test_ai.py`: URL detection | 15m | T16.1, P8 | T16.2-T16.4, T16.6-T16.7, P17, P18 | Test all URL patterns |
| T16.6 | Write `test_ai.py`: text detection | 15m | T16.1, P8 | T16.2-T16.5, T16.7, P17, P18 | Test all text patterns |
| T16.7 | Write `test_session.py`: log format | 10m | T16.1, P6 | T16.2-T16.6, P17, P18 | Verify JSON structure |
| T16.8 | Verify >80% coverage on core | 10m | T16.2-T16.7 | P17, P18 | Run pytest-cov, add tests if needed |

**Checkpoint:** `pytest tests/unit/ -v --cov` shows >80% on core modules

**Team Note:** Unit tests (P16), integration tests (P17), and CI setup (P18) can all proceed in parallel with different developers.

---

### P17: Integration Tests

> **Depends:** P9 (Mock pages), P10 (Mock server), P13 (Engine), P15 (CLI)
> **Parallel with:** P16 (different test scope), P18 (CI setup)
> **Blocks:** P18 (CI runs integration tests)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T17.1 | Create mock server fixture | 10m | P10 | P16, P18.1-P18.2 | Starts/stops mock server for tests |
| T17.2 | Write `test_mock_flow.py`: happy path | 15m | T17.1, P9, P13 | P16, P18 | Full flow from account to complete |
| T17.3 | Write `test_mock_flow.py`: already cancelled | 10m | T17.1, P9, P13 | T17.2, T17.4-T17.6, P16, P18 | Detects cancelled, exits cleanly |
| T17.4 | Write `test_mock_flow.py`: retention decline | 10m | T17.1, P9, P13 | T17.2-T17.3, T17.5-T17.6, P16, P18 | Navigates past retention offer |
| T17.5 | Write `test_mock_flow.py`: dry-run | 10m | T17.1, P9, P13 | T17.2-T17.4, T17.6, P16, P18 | Stops at final confirmation |
| T17.6 | Write `test_engine.py`: state detection | 15m | T17.1, P8, P13 | T17.2-T17.5, P16, P18 | Test detection cascade |

**Checkpoint:** `pytest tests/integration/ -v` passes

**Team Note:** T17.2-T17.6 are independent test scenarios - can be split among developers.

---

### P18: GitHub Actions CI

> **Depends:** P1 (project structure), P16/P17 (tests to run)
> **Parallel with:** P16, P17 (CI setup can happen while tests are being written)
> **Blocks:** P20 (validation requires CI passing)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T18.1 | Create `.github/workflows/ci.yml` | 10m | P1 | P16, P17 | Workflow file with trigger on push/PR |
| T18.2 | Add Python setup step | 5m | T18.1 | P16, P17 | Python 3.11, pip install, playwright install |
| T18.3 | Add lint step | 5m | T18.2 | T18.4-T18.7, P16, P17 | `ruff check src/` |
| T18.4 | Add type check step | 5m | T18.2 | T18.3, T18.5-T18.7, P16, P17 | `mypy src/` |
| T18.5 | Add unit test step | 5m | T18.2, P16 | T18.3-T18.4, T18.6-T18.7 | `pytest tests/unit/` |
| T18.6 | Add integration test step | 5m | T18.2, P17 | T18.3-T18.5, T18.7 | `pytest tests/integration/` |
| T18.7 | Add coverage reporting | 5m | T18.5, T18.6 | T18.3-T18.4 | Upload coverage report |

**Checkpoint:** Push to branch, CI passes

**Team Note:** T18.1-T18.4 can be done early (Day 4 even) before tests are complete. Only T18.5-T18.7 require tests to exist.

---

## Day 6: Documentation (P19)

### P19.1: README.md (User)

> **Depends:** P15 (CLI complete to document), P17 (integration tests pass)
> **Parallel with:** P19.2, P19.3 (all documentation can be written in parallel)
> **Blocks:** P20 (validation needs documentation)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T19.1 | Write Quick Start section | 10m | P15 | P19.2, P19.3 | 3 commands to get running |
| T19.2 | Write Installation section | 10m | P1 | T19.1, T19.3-T19.7, P19.2, P19.3 | Prerequisites, pip, playwright |
| T19.3 | Write Usage section | 15m | P15 | T19.1-T19.2, T19.4-T19.7, P19.2, P19.3 | All commands with examples |
| T19.4 | Write Configuration section | 10m | P4 | T19.1-T19.3, T19.5-T19.7, P19.2, P19.3 | Env vars table, .env example |
| T19.5 | Write What to Expect section | 10m | P13 | T19.1-T19.4, T19.6-T19.7, P19.2, P19.3 | Flow description, screenshots |
| T19.6 | Write Troubleshooting section | 10m | P16, P17 | T19.1-T19.5, T19.7, P19.2, P19.3 | Common errors |
| T19.7 | Write ToS Warning section | 5m | — | T19.1-T19.6, P19.2, P19.3 | Prominent disclaimer |

**Checkpoint:** New user can follow README and run first command

**Team Note:** All P19.1 sections are independent - can be split among writers.

---

### P19.2: README_FOR_DEV.md (Developer)

> **Depends:** All implementation phases complete (P1-P15)
> **Parallel with:** P19.1, P19.3 (all documentation can be written in parallel)
> **Blocks:** P20 (validation needs documentation)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T19.8 | Write Architecture Overview | 15m | P13 | P19.1, P19.3 | Big picture, core intuition, layer summary |
| T19.9 | Write Layer-by-Layer Guide: CLI | 10m | P15 | T19.8, T19.10-T19.17, P19.1, P19.3 | Entry point, Typer commands |
| T19.10 | Write Layer-by-Layer Guide: Engine | 15m | P13 | T19.8-T19.9, T19.11-T19.17, P19.1, P19.3 | State handling, checkpoints |
| T19.11 | Write Layer-by-Layer Guide: State Machine | 10m | P5 | T19.8-T19.10, T19.12-T19.17, P19.1, P19.3 | States, transitions, adding new |
| T19.12 | Write Layer-by-Layer Guide: Browser | 10m | P7 | T19.8-T19.11, T19.13-T19.17, P19.1, P19.3 | Playwright, stealth, selectors |
| T19.13 | Write Layer-by-Layer Guide: AI | 10m | P8, P11 | T19.8-T19.12, T19.14-T19.17, P19.1, P19.3 | Heuristic vs Claude, cascade |
| T19.14 | Write Layer-by-Layer Guide: Services | 10m | P12 | T19.8-T19.13, T19.15-T19.17, P19.1, P19.3 | Adding new service |
| T19.15 | Write Development Workflow | 15m | P1, P16, P17 | T19.8-T19.14, T19.16-T19.17, P19.1, P19.3 | Setup, running locally, testing |
| T19.16 | Write How-To Guides | 15m | P5, P12 | T19.8-T19.15, T19.17, P19.1, P19.3 | Adding service, state, debugging |
| T19.17 | Write ADRs | 10m | — | T19.8-T19.16, P19.1, P19.3 | Mock-first, python-statemachine, Typer |

**Checkpoint:** New developer can understand architecture in 15 min

**Team Note:** T19.9-T19.14 (layer guides) can be split - assign each layer to the developer who implemented it for fastest/most accurate documentation.

---

### P19.3: Code Documentation

> **Depends:** All implementation phases complete (P1-P15)
> **Parallel with:** P19.1, P19.2 (all documentation can be written in parallel)
> **Blocks:** P20 (code should be documented before validation)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T19.18 | Add docstrings to core/ modules | 15m | P5, P6, P7, P8, P11, P13 | T19.19-T19.21, P19.1, P19.2 | All public classes/functions documented |
| T19.19 | Add docstrings to services/ modules | 10m | P12 | T19.18, T19.20-T19.21, P19.1, P19.2 | All public classes/functions documented |
| T19.20 | Add docstrings to cli/ modules | 10m | P14, P15 | T19.18-T19.19, T19.21, P19.1, P19.2 | All public classes/functions documented |
| T19.21 | Add docstrings to utils/ modules | 10m | P3, P4 | T19.18-T19.20, P19.1, P19.2 | All public classes/functions documented |

**Checkpoint:** `pydocstyle src/` passes

**Team Note:** Each module's docstrings should be written by the developer who implemented that module - fastest and most accurate.

---

## Day 7: Validation (P20) - Stretch

### P20: Real Netflix Validation

> **Depends:** P15 (CLI working), P16-P18 (all tests pass), P19 (documentation complete)
> **Parallel with:** None (final validation phase)
> **Blocks:** None (final phase)

| ID | Task | Est | Depends | Parallel With | Acceptance Criteria |
|----|------|-----|---------|---------------|---------------------|
| T20.1 | Verify Netflix account available | 5m | — | T20.6 | Active subscription confirmed |
| T20.2 | Run dry-run against real Netflix | 15m | T20.1, P15, P18 | — | `subterminator cancel netflix --dry-run` |
| T20.3 | Document any selector issues | 10m | T20.2 | — | Note differences from mock |
| T20.4 | Update selectors if needed | 15m | T20.3 | — | Fix any broken selectors |
| T20.5 | Re-run dry-run to confirm | 10m | T20.4 | — | Flow reaches FINAL_CONFIRMATION |
| T20.6 | Record demo video (optional) | 20m | T20.5 | T20.1 | Screen recording of successful run |

**Checkpoint:** Screenshots show real Netflix pages, flow completes

**Risk Note:** T20.2-T20.5 are sequential and may require multiple iterations. Real Netflix UI may differ from mock - budget extra time for debugging.

---

## Summary

| Day | Tasks | Total Est. | Solo Dev | 2-Dev Team | 3-Dev Team |
|-----|-------|------------|----------|------------|------------|
| Day 1 | T1.1-T6.7 (38 tasks) | ~5.5 hrs | 5.5 hrs | 3 hrs | 2 hrs |
| Day 2 | T7.1-T10.4 (26 tasks) | ~4 hrs | 4 hrs | 2 hrs | 1.5 hrs |
| Day 3 | T11.1-T13.15 (23 tasks) | ~4 hrs | 4 hrs | 3 hrs | 2.5 hrs |
| Day 4 | T14.1-T15.8 (16 tasks) | ~2.5 hrs | 2.5 hrs | 1.5 hrs | 1 hr |
| Day 5 | T16.1-T18.7 (21 tasks) | ~3 hrs | 3 hrs | 1.5 hrs | 1 hr |
| Day 6 | T19.1-T19.21 (21 tasks) | ~3.5 hrs | 3.5 hrs | 2 hrs | 1.5 hrs |
| Day 7 | T20.1-T20.6 (6 tasks) | ~1.5 hrs | 1.5 hrs | 1.5 hrs | 1.5 hrs |

**Total:** 151 tasks, ~24 hours estimated (solo), ~14.5 hrs (2-dev), ~11 hrs (3-dev)

---

## Critical Path Analysis

```
P1 ──┬── P2 ──┬── P5 ───────────────┐
     │        ├── P6 ───────────────┤
     │        ├── P7 ───────────────┤
     ├── P3 ──┼── P8 ───────────────┼── P13 ── P15 ── P16 ──┬── P18 ── P19 ── P20
     │        └── P4 ───────────────┤          │     P17 ──┘
     └── P9 ── P10 ─────────────────┤          │
               P11 ─────────────────┤          │
               P12 ─────────────────┘          └── P14
```

**Critical Path (longest sequential dependency):**
`P1 → P2 → P5 → P13 → P15 → P17 → P18 → P19 → P20`

**Bottleneck Phases:**
1. **P1 (Project Setup)** - All work depends on this
2. **P2 (Protocols)** - Most components depend on types/interfaces
3. **P13 (Engine)** - Integration point requiring P4-P12 complete
4. **P15 (CLI)** - Requires P13 (Engine) complete

---

## Parallelization Recommendations

### For 2-Developer Team

| Day | Developer A (Core Path) | Developer B (Support Path) |
|-----|------------------------|---------------------------|
| 1 | P1 → P2 → P5 | P3 → P4 → P6 |
| 2 | P7 | P8 → P9 → P10 |
| 3 | P11 → P13.1-P13.8 | P12 → P13.9-P13.15 |
| 4 | P15 | P14 |
| 5 | P16 | P17 → P18 |
| 6 | P19.2 | P19.1 → P19.3 |
| 7 | P20.1-P20.3 | P20.4-P20.6 |

### For 3-Developer Team

| Day | Dev A (Engine) | Dev B (Infrastructure) | Dev C (Mock/Test) |
|-----|---------------|----------------------|------------------|
| 1 | P1 → P2 | P3 → P4 | (wait for P1) → P5 → P6 |
| 2 | P7 | P8 | P9 → P10 |
| 3 | P13 | P11 → P12 | (support P13) |
| 4 | P15 | P14 | (support P15) |
| 5 | P16 (engine tests) | P17 | P18 |
| 6 | P19.2 | P19.1 | P19.3 |
| 7 | P20 | (support P20) | (support P20) |

---

## Risk Mitigation

### High-Risk Dependencies

| Risk | Mitigation |
|------|------------|
| P13 blocked waiting for P4-P12 | Start P13.15 (retry utility) early - it has no dependencies |
| T9.11 (screenshot) blocking T11 tests | Create placeholder PNG if P9 delayed |
| Real Netflix UI differs from mock (P20) | Budget 2-3x time for T20.2-T20.5 iterations |
| CI fails on integration tests | Run tests locally before pushing (T17 checkpoint) |

### Merge Points

These tasks require coordination when multiple developers merge work:

1. **End of Day 1:** All protocols (P2) must be agreed upon before P5-P8 start
2. **End of Day 2:** Browser (P7) and Heuristic (P8) interfaces must match P2 contracts
3. **Start of Day 3:** P13 integration requires all components ready
4. **End of Day 5:** All tests must pass before documentation (P19)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial task breakdown from plan |
| 1.1 | 2026-02-03 | Claude | Added dependency annotations, parallel work guidance, critical path analysis, team parallelization recommendations, risk mitigation |
