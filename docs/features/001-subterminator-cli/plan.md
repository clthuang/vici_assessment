# SubTerminator CLI - Implementation Plan

**Feature:** 001-subterminator-cli
**Version:** 1.0
**Date:** February 3, 2026
**Timeline:** 7 calendar days

---

## 1. Plan Overview

### 1.1 Dependency Graph

```
                    ┌─────────────────────────┐
                    │  P1: Project Setup      │
                    │  (pyproject.toml, dirs) │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  P2: Protocols    │ │  P3: Exceptions   │ │  P4: Config       │
│  & Data Types     │ │                   │ │                   │
└─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
          ┌───────────────────┐   ┌───────────────────┐
          │  P5: State Machine│   │  P6: Session      │
          │                   │   │  Logger           │
          └─────────┬─────────┘   └─────────┬─────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  P7: Browser      │ │  P8: Heuristic    │ │  P9: Mock Pages   │
│  Wrapper          │ │  Interpreter      │ │  (HTML)           │
└─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P10: Mock Server     │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P11: Claude AI       │
                    │  Interpreter          │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P12: Netflix Service │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P13: Cancellation    │
                    │  Engine               │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P14: CLI Output      │
                    │  Formatter            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P15: CLI Commands    │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  P16: Unit Tests  │ │  P17: Integration │ │  P18: GitHub      │
│                   │ │  Tests            │ │  Actions CI       │
└───────────────────┘ └───────────────────┘ └───────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P19: Documentation   │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  P20: Real Netflix    │
                    │  Validation (Stretch) │
                    └───────────────────────┘
```

### 1.2 Timeline Overview

| Day | Focus | Deliverables |
|-----|-------|--------------|
| **Day 1** | Foundation | P1-P6: Project setup, protocols, state machine |
| **Day 2** | Core Components | P7-P10: Browser, heuristics, mock pages/server |
| **Day 3** | Integration | P11-P13: AI interpreter, Netflix service, engine |
| **Day 4** | CLI & Output | P14-P15: Output formatting, CLI commands |
| **Day 5** | Testing & CI | P16-P18: Unit tests, integration tests, GitHub Actions |
| **Day 6** | Documentation | P19: README.md (user), README_FOR_DEV.md (developer) |
| **Day 7** | Validation | P20: Real Netflix test (stretch), demo recording |

---

## 2. Detailed Implementation Steps

### Phase 1: Project Setup (P1)

**Estimated effort:** 1-2 hours
**Dependencies:** None
**Output:** Working Python project structure

#### Tasks:
1. Create `pyproject.toml` with dependencies
2. Create directory structure per design.md Section 3
3. Create `src/subterminator/__init__.py` with version
4. Create `src/subterminator/__main__.py` entry point
5. Create `.env.example` with required env vars
6. Create `.gitignore` for Python project
7. Install dependencies: `pip install -e ".[dev]"`
8. Install Playwright browsers: `playwright install chromium`

#### Verification:
```bash
python -m subterminator --help  # Should show help (stub)
pytest --version  # Dev deps installed
```

---

### Phase 2: Protocols & Data Types (P2)

**Estimated effort:** 1 hour
**Dependencies:** P1
**Output:** `src/subterminator/core/protocols.py`

#### Tasks:
1. Define `State` enum with all states
2. Define `AIInterpretation` dataclass
3. Define `CancellationResult` dataclass
4. Define `BrowserProtocol`
5. Define `AIInterpreterProtocol`
6. Define `ServiceProtocol`

#### Verification:
```bash
python -c "from subterminator.core.protocols import State, BrowserProtocol"
mypy src/subterminator/core/protocols.py
```

---

### Phase 3: Exceptions (P3)

**Estimated effort:** 30 minutes
**Dependencies:** P1
**Output:** `src/subterminator/utils/exceptions.py`

#### Tasks:
1. Define exception hierarchy per design.md Section 5.2
2. Add docstrings to each exception

#### Verification:
```bash
python -c "from subterminator.utils.exceptions import SubTerminatorError, TransientError"
```

---

### Phase 4: Configuration (P4)

**Estimated effort:** 30 minutes
**Dependencies:** P1
**Output:** `src/subterminator/utils/config.py`

#### Tasks:
1. Define `AppConfig` dataclass
2. Implement `ConfigLoader.load()` from environment

#### Verification:
```bash
ANTHROPIC_API_KEY=test python -c "from subterminator.utils.config import ConfigLoader; print(ConfigLoader.load())"
```

---

### Phase 5: State Machine (P5)

**Estimated effort:** 2 hours
**Dependencies:** P2, P3
**Output:** `src/subterminator/core/states.py`

#### Tasks:
1. Define `CancellationStateMachine` using python-statemachine
2. Define all states: start, login_required, account_active, etc.
3. Define all transitions: navigate, authenticate, click_cancel, etc.
4. Add guards: `before_confirm` requiring human confirmation
5. Add observers: `on_enter_state` for logging

#### Verification:
```bash
python -c "
from subterminator.core.states import CancellationStateMachine
sm = CancellationStateMachine()
print(sm.current_state)  # Should be 'start'
"
```

---

### Phase 6: Session Logger (P6)

**Estimated effort:** 1 hour
**Dependencies:** P2, P4
**Output:** `src/subterminator/utils/session.py`

#### Tasks:
1. Define `StateTransition` dataclass
2. Define `AICall` dataclass
3. Implement `SessionLogger` class
4. Implement `log_transition()`, `log_ai_call()`, `complete()`
5. Implement `_save()` writing JSON

#### Verification:
```bash
python -c "
from subterminator.utils.session import SessionLogger
from pathlib import Path
s = SessionLogger(Path('./test_output'), 'netflix', 'mock')
s.log_transition('start', 'account_active', 'navigate', 'http://test', 'test.png', 'url', 0.9)
print(s.data)
"
```

---

### Phase 7: Browser Wrapper (P7)

**Estimated effort:** 2 hours
**Dependencies:** P2, P3
**Output:** `src/subterminator/core/browser.py`

#### Tasks:
1. Implement `PlaywrightBrowser` class
2. Implement `launch()` with stealth
3. Implement `navigate()` with timeout
4. Implement `click()` with selector fallback list
5. Implement `fill()`, `select_option()`
6. Implement `screenshot()`, `html()`, `url()`, `text_content()`
7. Implement `close()` with cleanup

#### Verification:
```bash
python -c "
import asyncio
from subterminator.core.browser import PlaywrightBrowser

async def test():
    b = PlaywrightBrowser(headless=True)
    await b.launch()
    await b.navigate('https://example.com')
    print(await b.url())
    await b.close()

asyncio.run(test())
"
```

---

### Phase 8: Heuristic Interpreter (P8)

**Estimated effort:** 1 hour
**Dependencies:** P2
**Output:** `src/subterminator/core/ai.py` (partial)

#### Tasks:
1. Implement `HeuristicInterpreter` class
2. Implement URL-based detection
3. Implement text-based detection for all states
4. Return `AIInterpretation` with confidence scores

#### Verification:
```bash
python -c "
from subterminator.core.ai import HeuristicInterpreter
h = HeuristicInterpreter()
result = h.interpret('/account', 'Cancel Membership available')
print(result.state, result.confidence)
"
```

---

### Phase 9: Mock Pages (P9)

**Estimated effort:** 2-3 hours
**Dependencies:** P1
**Output:** `mock_pages/netflix/*.html`

#### Tasks:
1. Create `account.html` - active subscription with cancel link
2. Create `account_cancelled.html` - restart membership shown
3. Create `login.html` - login form
4. Create `cancelplan_survey.html` - exit survey with radio buttons
5. Create `cancelplan_retention.html` - retention offer
6. Create `cancelplan_confirm.html` - final confirmation
7. Create `cancelplan_complete.html` - cancellation confirmed
8. Create `error.html` - error page
9. Create minimal `assets/netflix.css` for structure
10. Use same CSS selectors as real Netflix where possible

#### Verification:
- Open each HTML file in browser
- Verify selectors match `NetflixService.selectors`

---

### Phase 10: Mock Server (P10)

**Estimated effort:** 1 hour
**Dependencies:** P9
**Output:** `src/subterminator/services/mock.py`

#### Tasks:
1. Implement `MockServer` class
2. Implement `start()` with background thread
3. Implement `stop()` with cleanup
4. Add variant support via query parameters

#### Verification:
```bash
python -c "
from subterminator.services.mock import MockServer
from pathlib import Path
s = MockServer(Path('mock_pages/netflix'), 8000)
s.start()
import requests
r = requests.get('http://localhost:8000/account.html')
print(r.status_code)
s.stop()
"
```

---

### Phase 11: Claude AI Interpreter (P11)

**Estimated effort:** 1.5 hours
**Dependencies:** P2, P4
**Output:** `src/subterminator/core/ai.py` (complete)

#### Tasks:
1. Implement `ClaudeInterpreter` class
2. Define `PROMPT_TEMPLATE` per design
3. Implement `interpret()` with Claude Vision API
4. Implement `_parse_response()` JSON parsing
5. Handle API errors gracefully

#### Verification:
```bash
# Requires ANTHROPIC_API_KEY
python -c "
import asyncio
from subterminator.core.ai import ClaudeInterpreter
from pathlib import Path

async def test():
    ai = ClaudeInterpreter()
    # Test with a simple image
    with open('mock_pages/netflix/screenshot_test.png', 'rb') as f:
        result = await ai.interpret(f.read())
    print(result)

asyncio.run(test())
"
```

---

### Phase 12: Netflix Service (P12)

**Estimated effort:** 1 hour
**Dependencies:** P2
**Output:** `src/subterminator/services/netflix.py`, `src/subterminator/services/base.py`

#### Tasks:
1. Define `ServiceSelectors` dataclass in base.py
2. Define `ServiceConfig` dataclass in base.py
3. Implement `NetflixService` class
4. Configure all selectors from design.md
5. Configure text indicators
6. Implement `entry_url` property with target switching

#### Verification:
```bash
python -c "
from subterminator.services.netflix import NetflixService
s = NetflixService(target='mock')
print(s.entry_url)  # Should be localhost
print(s.selectors.cancel_link)
"
```

---

### Phase 13: Cancellation Engine (P13)

**Estimated effort:** 3-4 hours
**Dependencies:** P5, P6, P7, P8, P11, P12
**Output:** `src/subterminator/core/engine.py`

#### Tasks:
1. Implement `CancellationEngine` class with DI
2. Implement `run()` main loop
3. Implement `_handle_state()` for each state
4. Implement `_detect_state()` cascading detection
5. Implement `_human_checkpoint()` for auth/confirm
6. Implement `_complete_survey()` helper
7. Add retry logic with `with_retry()`
8. Add max transition limit (10)

#### Verification:
```bash
# Manual test against mock server
python -c "
import asyncio
from subterminator.core.engine import CancellationEngine
# ... setup deps ...
# engine = CancellationEngine(...)
# result = await engine.run(dry_run=True)
"
```

---

### Phase 14: CLI Output Formatter (P14)

**Estimated effort:** 1.5 hours
**Dependencies:** P2, P3
**Output:** `src/subterminator/cli/output.py`

#### Tasks:
1. Implement `OutputFormatter` class
2. Implement `show_progress()` with step indicator
3. Implement `show_human_prompt()` for auth/confirm
4. Implement `show_success()` with result details
5. Implement `show_failure()` with diagnostics
6. Implement `show_warning()` for ToS disclaimer
7. Implement `show_third_party_instructions()`

#### Verification:
```bash
python -c "
from subterminator.cli.output import OutputFormatter
o = OutputFormatter()
o.show_progress('ACCOUNT_ACTIVE', 'Clicking cancel link...')
"
```

---

### Phase 15: CLI Commands (P15)

**Estimated effort:** 2 hours
**Dependencies:** P13, P14
**Output:** `src/subterminator/cli/main.py`

#### Tasks:
1. Create Typer app
2. Implement `cancel` command with arguments
3. Implement `version` command
4. Wire up dependencies to engine
5. Handle exit codes per spec
6. Add ToS disclaimer on first run
7. Update `__main__.py` to call CLI

#### Verification:
```bash
python -m subterminator --version
python -m subterminator cancel netflix --target mock --dry-run
```

---

### Phase 16: Unit Tests (P16)

**Estimated effort:** 3 hours
**Dependencies:** P5, P6, P7, P8
**Output:** `tests/unit/*.py`

#### Tasks:
1. Create `conftest.py` with fixtures
2. `test_states.py`: Valid/invalid transitions
3. `test_browser.py`: Mock-based browser tests
4. `test_ai.py`: Heuristic detection tests
5. `test_session.py`: Log format validation
6. Target >80% coverage on core logic

#### Verification:
```bash
pytest tests/unit/ -v --cov=subterminator --cov-report=term-missing
```

---

### Phase 17: Integration Tests (P17)

**Estimated effort:** 2 hours
**Dependencies:** P10, P13, P15
**Output:** `tests/integration/*.py`

#### Tasks:
1. `test_mock_flow.py`: Happy path against mock
2. `test_mock_flow.py`: Already cancelled detection
3. `test_mock_flow.py`: Retention offer decline
4. `test_mock_flow.py`: Dry run stops at confirm
5. `test_engine.py`: Engine integration with mocks

#### Verification:
```bash
pytest tests/integration/ -v
```

---

### Phase 18: GitHub Actions CI (P18)

**Estimated effort:** 1 hour
**Dependencies:** P16, P17
**Output:** `.github/workflows/ci.yml`

#### Tasks:
1. Create workflow for push/PR
2. Set up Python 3.11
3. Install dependencies
4. Run ruff lint
5. Run mypy type check
6. Run pytest unit tests
7. Run pytest integration tests (mock only)
8. Report coverage

#### Verification:
- Push to feature branch
- Check Actions tab for passing CI

---

### Phase 19: Documentation (P19)

**Estimated effort:** 3-4 hours
**Dependencies:** P15
**Output:** `README.md`, `README_FOR_DEV.md`, docstrings

#### Tasks:

##### 19.1 User Documentation: `README.md`
Goal: Get users installed and using the CLI in under 5 minutes.

Structure:
```markdown
# SubTerminator

One-liner description + badge

## Quick Start (30 seconds)
- pip install command
- Set API key
- Run command

## Installation
- Prerequisites (Python 3.11+)
- pip install steps
- Playwright browser install

## Usage
- Basic command: `subterminator cancel netflix`
- Dry run mode
- Mock mode for testing
- All CLI flags with examples

## Configuration
- Environment variables table
- .env file example

## What to Expect
- Screenshot of typical flow
- Human checkpoints explained

## Troubleshooting
- Common errors and fixes

## Terms of Service Warning
- Prominent disclaimer

## License
```

##### 19.2 Developer Documentation: `README_FOR_DEV.md`
Goal: Get engineers productive in the codebase quickly. Start from the big picture, drill down to details.

Structure with signposting:
```markdown
# SubTerminator - Developer Guide

## Table of Contents (with section links)

## 1. Architecture Overview
### 1.1 The Big Picture
- High-level diagram (from design.md)
- "Start here" pointer to key files

### 1.2 Core Intuition
- State machine drives everything
- Mock-first development approach
- Human-in-the-loop philosophy

### 1.3 Layer Summary
| Layer | Responsibility | Key Files |
|-------|---------------|-----------|
(Quick reference table)

---
► Next: Deep dive into each layer

## 2. Layer-by-Layer Guide

### 2.1 CLI Layer
- Entry point: `cli/main.py`
- How Typer commands work
- Output formatting

### 2.2 Orchestrator (Engine)
- `core/engine.py` walkthrough
- State handling flow
- Human checkpoint logic

### 2.3 State Machine
- States and transitions diagram
- Adding new states
- Guards and observers

### 2.4 Browser Automation
- Playwright wrapper design
- Stealth configuration
- Selector fallback strategy

### 2.5 AI Interpretation
- Heuristic vs Claude Vision
- Detection cascade
- Prompt engineering notes

### 2.6 Services
- Adding a new service (step-by-step)
- Service protocol contract

---
► Next: How to develop and test

## 3. Development Workflow

### 3.1 Setup
- Clone, install, verify

### 3.2 Running Locally
- Mock server usage
- Debug mode

### 3.3 Testing Strategy
- Unit vs Integration vs E2E
- Running specific tests
- Coverage targets

### 3.4 Code Style
- Ruff, mypy configuration
- Pre-commit hooks

---
► Next: Common tasks

## 4. How-To Guides

### 4.1 Adding a New Service
### 4.2 Adding a New Page State
### 4.3 Modifying Detection Logic
### 4.4 Debugging a Failed Flow

## 5. Troubleshooting for Developers

## 6. Architecture Decision Records (ADRs)
- Why mock-first?
- Why python-statemachine?
- Why Typer over Click?
```

##### 19.3 Code Documentation
1. Add docstrings to all public classes and functions
2. Include type hints (already required by mypy)
3. Add inline comments for non-obvious logic

#### Verification:
- New user: Follow README.md, successfully run first command
- New developer: Follow README_FOR_DEV.md, understand architecture in 15 min
- `python -m subterminator --help` matches README.md
- All public functions have docstrings: `pydocstyle src/`

---

### Phase 20: Real Netflix Validation (P20) - Stretch

**Estimated effort:** 1-2 hours
**Dependencies:** P15
**Output:** Successful dry-run against real Netflix

#### Tasks:
1. Set up real Netflix account (or use existing)
2. Run `subterminator cancel netflix --dry-run`
3. Verify flow reaches FINAL_CONFIRMATION
4. Document any selector/flow issues found
5. Record demo video (optional)

#### Verification:
- Screenshots show real Netflix pages
- Flow reaches final confirmation without errors

---

## 3. Risk Mitigation Checkpoints

| Checkpoint | Day | Criteria | Fallback |
|------------|-----|----------|----------|
| **MVP Demo** | 3 | Can run `--dry-run` against mock | Focus on core flow only |
| **Test Suite** | 5 | Unit + integration tests pass | Reduce test coverage target |
| **CI Green** | 5 | GitHub Actions passes | Manual testing only |
| **Real Netflix** | 7 | Dry-run works on real site | Demo mock-only |

---

## 4. Definition of Done

### MVP (Day 5)

- [ ] `subterminator cancel netflix --target mock` completes happy path
- [ ] `subterminator cancel netflix --target mock --dry-run` stops at final confirm
- [ ] Human-in-the-loop pauses work for auth and confirmation
- [ ] Screenshots and logs saved to output directory
- [ ] Unit tests pass with >80% coverage on core
- [ ] Integration tests pass against mock server
- [ ] GitHub Actions CI runs on push
- [ ] CLI help and version commands work

### Stretch (Day 6-7)

- [ ] README.md complete (user quick-start guide)
- [ ] README_FOR_DEV.md complete (developer onboarding)
- [ ] Real Netflix dry-run successful
- [ ] Multiple mock flow variants (retention, no-survey)
- [ ] Demo video recorded

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial plan from design |
