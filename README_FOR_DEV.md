# SubTerminator Developer Guide

A comprehensive guide for developers working on the SubTerminator codebase.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Layer-by-Layer Guide](#layer-by-layer-guide)
  - [CLI Layer](#cli-layer)
  - [Orchestrator (Engine)](#orchestrator-engine)
  - [State Machine](#state-machine)
  - [Browser Automation](#browser-automation)
  - [AI Detection](#ai-detection)
  - [Services](#services)
- [Development Workflow](#development-workflow)
- [How-To Guides](#how-to-guides)
  - [Adding a New Service](#adding-a-new-service)
  - [Adding a New State](#adding-a-new-state)
  - [Debugging Detection Issues](#debugging-detection-issues)
- [Architecture Decision Records](#architecture-decision-records)

---

## Architecture Overview

SubTerminator follows a layered architecture with clear separation of concerns:

```
CLI Layer (user interaction)
    |
    v
Orchestrator / Engine (coordination)
    |
    +---> State Machine (flow control)
    |
    +---> Browser (automation)
    |
    +---> AI Detection (page interpretation)
    |
    v
Services (site-specific logic)
```

### Core Intuition

1. **State machine drives the flow** - The cancellation process is modeled as explicit states with valid transitions. This prevents invalid navigation and provides clear debugging.

2. **Heuristic detection first, AI fallback** - Fast URL/text pattern matching handles most cases. Claude Vision is only invoked when heuristics fail, saving API costs and latency.

3. **Human checkpoints for irreversible actions** - Authentication and final confirmation always require human interaction. The tool assists, it never acts autonomously on critical decisions.

4. **Session logging for debugging** - Every state transition, screenshot, and AI call is logged. When something fails, the session directory contains everything needed to diagnose and fix.

### Data Flow

```
User runs: subterminator cancel netflix
                |
                v
    +------------------------+
    |      CLI (main.py)     |  <-- Parses args, creates components
    +------------------------+
                |
                v
    +------------------------+
    | CancellationEngine     |  <-- Main loop: handle state -> detect -> transition
    +------------------------+
          |         |
          v         v
    +---------+  +---------+
    | Browser |  |   AI    |  <-- Navigate, click, screenshot / Interpret state
    +---------+  +---------+
          |
          v
    +------------------------+
    | NetflixService         |  <-- Selectors, URLs, text indicators
    +------------------------+
```

---

## Layer-by-Layer Guide

### CLI Layer

**Location:** `src/subterminator/cli/`

The CLI layer handles user interaction using the [Typer](https://typer.tiangolo.com/) framework.

#### Entry Point: `main.py`

```python
# Key command definition
@app.command()
def cancel(
    service: str | None = typer.Option(None, "--service", "-s"),  # Interactive if None
    no_input: bool = typer.Option(False, "--no-input"),           # Disable prompts
    plain: bool = typer.Option(False, "--plain"),                 # No colors/animations
    dry_run: bool,          # --dry-run stops before final click
    target: str,            # "live" or "mock"
    headless: bool,         # --headless for CI
    verbose: bool,          # --verbose for detailed output
    output_dir: Path,       # --output-dir for artifacts
) -> None:
```

The `cancel` command:
1. Validates the service name
2. Shows ToS disclaimer
3. Creates all components (service, browser, AI, session logger)
4. Runs the cancellation engine
5. Reports result and sets exit code

**Exit codes:**
- `0`: Success
- `1`: Failure
- `2`: User aborted
- `3`: Invalid arguments
- `4`: Configuration error

#### Output Formatting: `output.py`

`OutputFormatter` handles all user-facing messages:

```python
formatter = OutputFormatter(verbose=True)
formatter.show_progress("STATE_NAME", "Message")  # Step indicator
formatter.show_warning("Warning text")            # Yellow warning
formatter.show_success(result)                    # Green success box
formatter.show_failure(result)                    # Red failure with diagnostics
```

Human prompts use `PromptType` enum:
- `AUTH`: Login required
- `CONFIRM`: Final cancellation confirmation
- `UNKNOWN`: Page state unclear

---

### Orchestrator (Engine)

**Location:** `src/subterminator/core/engine.py`

The `CancellationEngine` is the heart of SubTerminator. It coordinates all components through a main loop.

#### Key Methods

**`run(dry_run: bool) -> CancellationResult`**

The main entry point. Launches browser, runs state loop, handles exceptions:

```python
async def run(self, dry_run: bool = False) -> CancellationResult:
    try:
        await self.browser.launch()

        while not self._is_terminal_state():
            if self._step >= self.config.max_transitions:
                return self._complete(False, State.FAILED, "Max transitions exceeded")

            next_state = await self._handle_state(self._current_state)
            self._transition_to(next_state)
            self._step += 1

        # Determine result from final state
        success = self._current_state in (State.COMPLETE, State.ACCOUNT_CANCELLED)
        return self._complete(success, self._current_state, self._get_result_message())

    except UserAborted:
        return self._complete(False, State.ABORTED, "User aborted")
    finally:
        await self.browser.close()
```

**`_handle_state(state: State) -> State`**

The state handler - takes action based on current state:

```python
async def _handle_state(self, state: State) -> State:
    if state == State.START:
        await self.browser.navigate(self.service.entry_url)
        return await self._detect_state()

    elif state == State.LOGIN_REQUIRED:
        await self._human_checkpoint("AUTH", timeout)
        return await self._detect_state()

    elif state == State.ACCOUNT_ACTIVE:
        await self.browser.click(self.service.selectors.cancel_link)
        return await self._detect_state()

    elif state == State.FINAL_CONFIRMATION:
        if self.dry_run:
            return State.COMPLETE  # Skip actual click
        await self._human_checkpoint("CONFIRM", timeout)
        await self.browser.click(self.service.selectors.confirm_cancel)
        return await self._detect_state()

    # ... other states
```

**`_detect_state() -> State`**

Detection cascade - heuristic first, then AI:

```python
async def _detect_state(self) -> State:
    url = await self.browser.url()
    text = await self.browser.text_content()

    # Try heuristic first (fast, free)
    result = self.heuristic.interpret(url, text)
    if result.confidence >= 0.7:
        return result.state

    # Fall back to AI (slower, costs money)
    if self.ai:
        screenshot = await self.browser.screenshot()
        ai_result = await self.ai.interpret(screenshot)
        if ai_result.confidence >= 0.5:
            return ai_result.state

    return State.UNKNOWN
```

**`_human_checkpoint(checkpoint_type: str, timeout: int)`**

Pauses for human input:

```python
async def _human_checkpoint(self, checkpoint_type: str, timeout: int) -> None:
    # Show appropriate message
    self.output_callback(checkpoint_type, messages[checkpoint_type])

    # Wait for input
    if self.input_callback:
        response = self.input_callback(checkpoint_type, timeout)
        if checkpoint_type == "CONFIRM" and response != "confirm":
            raise UserAborted("User did not confirm")
```

---

### State Machine

**Location:** `src/subterminator/core/states.py`

The `CancellationStateMachine` uses [python-statemachine](https://python-statemachine.readthedocs.io/) to define valid states and transitions.

#### States (12 total)

| State | Type | Description |
|-------|------|-------------|
| `start` | Entry | Initial state before navigation |
| `login_required` | Auth | Authentication needed |
| `account_active` | Account | Logged in, subscription active |
| `account_cancelled` | Account | Subscription already cancelled |
| `third_party_billing` | Account | Billed through Apple/Google |
| `retention_offer` | Flow | Discount/retention offer shown |
| `exit_survey` | Flow | "Why are you leaving?" survey |
| `final_confirmation` | Flow | Final "Finish Cancellation" button |
| `complete` | Terminal | Cancellation successful |
| `aborted` | Terminal | User aborted |
| `failed` | Terminal | Process failed |
| `unknown` | Recovery | Unrecognized page state |

#### Transitions (10 named transitions)

```python
# From start -> various states after page load
navigate = (
    start.to(login_required)
    | start.to(account_active)
    | start.to(account_cancelled)
    | start.to(failed)
    | start.to(unknown)
)

# From login_required -> various states after auth
authenticate = (
    login_required.to(account_active)
    | login_required.to(account_cancelled)
    | login_required.to(failed)
)

# From account_active -> cancel flow states
click_cancel = (
    account_active.to(retention_offer)
    | account_active.to(exit_survey)
    | account_active.to(final_confirmation)
)

# From retention_offer -> next step (can loop)
decline_offer = (
    retention_offer.to(retention_offer)  # Multiple offers
    | retention_offer.to(exit_survey)
    | retention_offer.to(final_confirmation)
)

# From final_confirmation -> terminal
confirm = (
    final_confirmation.to(complete)
    | final_confirmation.to(failed)
)
```

#### State Diagram

```
              +-------+
              | START |
              +---+---+
                  |
        +---------+---------+
        |                   |
        v                   v
+---------------+    +--------------+
| LOGIN_REQUIRED|    | ACCOUNT_ACTIVE|
+-------+-------+    +-------+------+
        |                    |
        v                    v
+---------------+    +----------------+
| ACCOUNT_ACTIVE|    | RETENTION_OFFER|<--+
+---------------+    +--------+-------+   |
                             |            |
                    +--------+--------+   |
                    |                 |   |
                    v                 +---+
              +-----------+
              | EXIT_SURVEY|
              +-----+-----+
                    |
                    v
          +------------------+
          | FINAL_CONFIRMATION|
          +--------+---------+
                   |
         +---------+---------+
         |                   |
         v                   v
    +----------+        +--------+
    | COMPLETE |        | FAILED |
    +----------+        +--------+
```

---

### Browser Automation

**Location:** `src/subterminator/core/browser.py`

`PlaywrightBrowser` wraps [Playwright](https://playwright.dev/python/) with stealth capabilities.

#### Key Features

**Stealth mode** - Uses [playwright-stealth](https://pypi.org/project/playwright-stealth/) to avoid bot detection:

```python
async def launch(self) -> None:
    self._playwright = await async_playwright().start()
    self._browser = await self._playwright.chromium.launch(headless=self.headless)
    self._page = await self._browser.new_page()

    # Apply stealth patches
    stealth = Stealth()
    await stealth.apply_stealth_async(self._page)
```

**Selector fallback** - Tries multiple selectors until one works:

```python
async def click(self, selector: str | list[str]) -> None:
    selectors = [selector] if isinstance(selector, str) else selector
    for sel in selectors:
        try:
            element = await self._page.wait_for_selector(sel, timeout=5000)
            if element:
                await element.scroll_into_view_if_needed()
                await element.click()
                return
        except Exception:
            continue
    raise ElementNotFound(f"None of selectors found: {selectors}")
```

**Network idle waiting** - Waits for network to settle before proceeding:

```python
await self._page.goto(url, timeout=timeout, wait_until="networkidle")
```

#### BrowserProtocol

The browser is abstracted via a protocol for testing:

```python
class BrowserProtocol(Protocol):
    async def launch(self) -> None: ...
    async def navigate(self, url: str, timeout: int = 30000) -> None: ...
    async def click(self, selector: str | list[str]) -> None: ...
    async def screenshot(self, path: str | None = None) -> bytes: ...
    async def url(self) -> str: ...
    async def text_content(self) -> str: ...
    async def close(self) -> None: ...
```

---

### AI Detection

**Location:** `src/subterminator/core/ai.py`

Two interpreters implement the detection cascade.

#### HeuristicInterpreter

Fast, rule-based detection using URL patterns and text content:

```python
class HeuristicInterpreter:
    def interpret(self, url: str, text: str) -> AIInterpretation:
        text_lower = text.lower()

        # URL-based detection (high confidence)
        if "/login" in url or "/signin" in url:
            return AIInterpretation(State.LOGIN_REQUIRED, 0.95, "URL contains /login")

        # Text-based detection
        if "cancel membership" in text_lower and "/account" in url:
            return AIInterpretation(State.ACCOUNT_ACTIVE, 0.85, "Cancel link found")

        # Retention offer detection
        if any(phrase in text_lower for phrase in ["before you go", "special offer"]):
            return AIInterpretation(State.RETENTION_OFFER, 0.75, "Retention offer")

        # ... more patterns

        return AIInterpretation(State.UNKNOWN, 0.0, "No patterns matched")
```

**Detection priority:**
1. URL patterns (highest confidence)
2. Login form indicators
3. Third-party billing indicators
4. Retention offer phrases
5. Survey phrases
6. Confirmation button text
7. Completion indicators
8. Error indicators
9. UNKNOWN fallback

#### ClaudeInterpreter

AI-powered detection using Claude Vision:

```python
class ClaudeInterpreter:
    PROMPT_TEMPLATE = """Analyze this screenshot of a subscription cancellation flow.

    Determine which state this page represents:
    - LOGIN_REQUIRED: Login form is shown
    - ACCOUNT_ACTIVE: Account page with active subscription
    - RETENTION_OFFER: Discount or "stay with us" offer
    - FINAL_CONFIRMATION: Final "Finish Cancellation" button
    - COMPLETE: Cancellation confirmed
    ...

    Respond in JSON format:
    {"state": "<STATE>", "confidence": <0.0-1.0>, "reasoning": "...", "actions": [...]}
    """

    async def interpret(self, screenshot: bytes) -> AIInterpretation:
        image_data = base64.b64encode(screenshot).decode("utf-8")

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", ...}},
                    {"type": "text", "text": self.PROMPT_TEMPLATE},
                ],
            }],
        )

        return self._parse_response(response.content[0].text)
```

---

### Services

**Location:** `src/subterminator/services/`

Services contain site-specific configuration.

#### NetflixService

```python
class NetflixService:
    def __init__(self, target: str = "live"):
        self._config = ServiceConfig(
            name="Netflix",
            entry_url="https://www.netflix.com/account",
            mock_entry_url="http://localhost:8000/account",
            selectors=ServiceSelectors(
                cancel_link=[
                    "[data-uia='action-cancel-membership']",
                    "a:has-text('Cancel Membership')",
                    "button:has-text('Cancel Membership')",
                ],
                decline_offer=[
                    "[data-uia='continue-cancel-btn']",
                    "button:has-text('Continue to Cancel')",
                ],
                confirm_cancel=[
                    "[data-uia='confirm-cancel-btn']",
                    "button:has-text('Finish Cancellation')",
                ],
                # ...
            ),
            text_indicators={
                "login": ["Sign In", "Email", "Password"],
                "active": ["Cancel Membership", "Cancel Plan"],
                "cancelled": ["Restart Membership"],
                # ...
            }
        )
```

#### MockServer

For local testing without hitting real Netflix:

```python
class MockServer:
    def __init__(self, pages_dir: Path, port: int = 8000):
        self.pages_dir = pages_dir
        self.port = port

    def start(self) -> None:
        # Serves static HTML files mimicking Netflix pages
        # Supports ?variant= parameter for different flows
        pass
```

---

## Development Workflow

### Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd subterminator

# Dependencies managed by uv (creates .venv automatically)
uv sync

# Install browser binaries
uv run playwright install chromium
```

### Running Tests

```bash
# Unit tests (fast, no browser)
uv run pytest tests/unit/ -v

# Integration tests (uses mock server)
uv run pytest tests/integration/ -v

# All tests with coverage
uv run pytest --cov=subterminator --cov-report=html

# Specific test file
uv run pytest tests/unit/test_engine.py -v
```

### Linting and Type Checking

```bash
# Linting with Ruff
uv run ruff check src/
uv run ruff check --fix src/  # Auto-fix issues

# Type checking with mypy
uv run mypy src/
```

### Testing Against Mock Server

```bash
# Run with mock target (uses local test server)
uv run subterminator cancel netflix --target mock --dry-run

# Verbose output
uv run subterminator cancel netflix --target mock --dry-run --verbose
```

### Git Workflow

The repository uses an automated CI/CD pipeline that creates PRs and enables auto-merge.

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, run tests locally
uv run pytest tests/unit/

# Lint before commit
uv run ruff check src/

# Commit and push
git commit -m "feat: add new feature"
git push -u origin feature/my-feature
```

**What happens automatically:**

1. **CI runs** - Lint, test (85% coverage required), and build jobs execute
2. **PR created** - If all checks pass, a PR is auto-created targeting `main`
3. **Auto-merge enabled** - PR will merge automatically after approval

**Notes:**
- Works for `feature/*` and `fix/*` branches
- Requires branch protection on `main` for auto-merge (GitHub Pro/Team for private repos)
- Uses squash merge with automatic branch deletion

---

## How-To Guides

### Adding a New Service

To add support for a new subscription service (e.g., Spotify):

**1. Create service file**

```python
# src/subterminator/services/spotify.py

from dataclasses import dataclass
from subterminator.services.netflix import ServiceSelectors, ServiceConfig

class SpotifyService:
    def __init__(self, target: str = "live"):
        self.target = target
        self._config = ServiceConfig(
            name="Spotify",
            entry_url="https://www.spotify.com/account",
            mock_entry_url="http://localhost:8000/spotify/account",
            selectors=ServiceSelectors(
                cancel_link=[
                    "[data-testid='cancel-button']",
                    "button:has-text('Cancel Premium')",
                ],
                decline_offer=[...],
                survey_option=[...],
                survey_submit=[...],
                confirm_cancel=[...],
            ),
            text_indicators={
                "login": ["Log in", "Email address", "Password"],
                "active": ["Cancel Premium", "Change plan"],
                "cancelled": ["Get Premium again"],
                # ...
            }
        )

    @property
    def entry_url(self) -> str:
        return self._config.mock_entry_url if self.target == "mock" else self._config.entry_url

    # ... other properties
```

**2. Update CLI**

```python
# src/subterminator/cli/main.py

from subterminator.services.registry import get_service_by_id, get_available_services

# Get available services
services = get_available_services()  # Returns list of ServiceInfo

# Look up specific service
service = get_service_by_id("netflix")  # Returns ServiceInfo or None
```

**3. Add heuristic patterns**

Update `HeuristicInterpreter` if service has unique patterns.

**4. Create mock pages**

Add HTML files to `tests/mock_pages/spotify/` for testing.

**5. Write tests**

```python
# tests/unit/test_spotify_service.py

def test_spotify_selectors():
    service = SpotifyService()
    assert "cancel" in service.selectors.cancel_link[0].lower()
```

---

### Adding a New State

To add a new state to the cancellation flow:

**1. Add to State enum**

```python
# src/subterminator/core/protocols.py

class State(Enum):
    # ... existing states
    PAYMENT_UPDATE = auto()  # New state
```

**2. Add to state machine**

```python
# src/subterminator/core/states.py

class CancellationStateMachine(StateMachine):
    # ... existing states
    payment_update = SMState()

    # Add transitions
    navigate = (
        start.to(payment_update, cond="dest_is_payment_update")
        | ...
    )

    # Add condition method
    def dest_is_payment_update(self, dest: str) -> bool:
        return dest == "payment_update"
```

**3. Add handler in engine**

```python
# src/subterminator/core/engine.py

async def _handle_state(self, state: State) -> State:
    # ... existing handlers
    elif state == State.PAYMENT_UPDATE:
        # Handle the new state
        await self.browser.click(self.service.selectors.update_payment)
        return await self._detect_state()
```

**4. Add detection patterns**

```python
# src/subterminator/core/ai.py

class HeuristicInterpreter:
    def interpret(self, url: str, text: str) -> AIInterpretation:
        # ... existing patterns
        if "update payment" in text_lower or "payment method" in text_lower:
            return AIInterpretation(State.PAYMENT_UPDATE, 0.80, "Payment update detected")
```

**5. Update OutputFormatter colors**

```python
# src/subterminator/cli/output.py

state_colors = {
    # ... existing colors
    "PAYMENT_UPDATE": "\033[33m",  # Yellow
}
```

---

### Debugging Detection Issues

When state detection fails:

**1. Check session artifacts**

```bash
# Find latest session
ls -la output/netflix_*/

# View session log
cat output/netflix_20260203_123456/session.json | jq .

# View screenshots
open output/netflix_20260203_123456/*.png
```

**2. Run with verbose mode**

```bash
subterminator cancel netflix --verbose --target mock
```

**3. Test heuristic directly**

```python
from subterminator.core.ai import HeuristicInterpreter

interpreter = HeuristicInterpreter()
result = interpreter.interpret(
    url="https://www.netflix.com/account",
    text="Cancel Membership ..."  # Page text
)
print(f"State: {result.state}, Confidence: {result.confidence}")
```

**4. Check pattern priority**

The heuristic checks patterns in order. If a more specific pattern should match but a generic one matches first, reorder the checks in `HeuristicInterpreter.interpret()`.

**5. Add new patterns**

If pages consistently fail detection, add new patterns:

```python
# Add to appropriate list in HeuristicInterpreter
new_phrases = ["new pattern 1", "new pattern 2"]
if any(phrase in text_lower for phrase in new_phrases):
    return AIInterpretation(State.TARGET_STATE, 0.75, "New pattern detected")
```

---

## Architecture Decision Records

### ADR-1: Mock-First Development

**Context:** Testing against live Netflix requires a paid subscription and risks account issues.

**Decision:** Primary development and testing uses a local mock server with static HTML pages that simulate Netflix's cancellation flow.

**Consequences:**
- Fast, deterministic tests that run without network
- Can test all flow variants (retention offer, survey, etc.)
- Must keep mock pages updated when real UI changes
- Need occasional manual verification against real site

---

### ADR-2: python-statemachine for Flow Control

**Context:** Subscription cancellation has complex, branching flows with many edge cases.

**Decision:** Use python-statemachine library for explicit state management.

**Consequences:**
- Invalid state transitions are impossible at runtime
- Easy to visualize and reason about the flow
- Slight overhead vs simple if/else logic
- Clear debugging - always know current state

---

### ADR-3: Typer for CLI Framework

**Context:** Need a modern CLI framework with good developer experience.

**Decision:** Use Typer for CLI implementation.

**Consequences:**
- Automatic --help generation from type hints
- Clean async support
- Rich text output via Rich integration
- Dependency on Typer ecosystem

---

### ADR-4: Heuristic Before AI Detection

**Context:** Claude API calls cost money and add latency.

**Decision:** Always try fast URL/text heuristics first. Only invoke Claude when heuristics return low confidence.

**Consequences:**
- Most page detections are instant and free
- AI provides fallback for unknown/changed pages
- Must maintain heuristic patterns
- Confidence thresholds may need tuning

---

### ADR-5: Human Checkpoints for Safety

**Context:** Cancellation is irreversible and affects user's subscription.

**Decision:** Mandatory human confirmation for authentication and final cancellation. No fully autonomous operation.

**Consequences:**
- Users maintain control over critical actions
- Cannot be used for fully automated batch operations
- Better trust and safety guarantees
- Aligns with responsible automation practices

---

### ADR-6: Session Logging for Observability

**Context:** When automation fails, need to understand what happened.

**Decision:** Log every state transition, screenshot, and AI call to session directory.

**Consequences:**
- Full audit trail for debugging
- Disk space usage for screenshots
- Privacy consideration for logged data
- Easy to share failure reports

---

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| CLI entry | `src/subterminator/cli/main.py` |
| Interactive prompts | `src/subterminator/cli/prompts.py` |
| Accessibility settings | `src/subterminator/cli/accessibility.py` |
| Engine | `src/subterminator/core/engine.py` |
| State machine | `src/subterminator/core/states.py` |
| Browser | `src/subterminator/core/browser.py` |
| AI detection | `src/subterminator/core/ai.py` |
| Protocols | `src/subterminator/core/protocols.py` |
| Netflix service | `src/subterminator/services/netflix.py` |
| Service registry | `src/subterminator/services/registry.py` |
| Mock server | `src/subterminator/services/mock.py` |
| Output formatting | `src/subterminator/cli/output.py` |
| Config | `src/subterminator/utils/config.py` |
| Exceptions | `src/subterminator/utils/exceptions.py` |
| Session logging | `src/subterminator/utils/session.py` |

### Key Commands

```bash
# Run CLI
uv run subterminator cancel                                      # Interactive mode
uv run subterminator cancel --service netflix                    # Specify service directly
uv run subterminator cancel --service netflix --dry-run
uv run subterminator cancel --service netflix --target mock --verbose

# Tests
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# Lint
uv run ruff check src/
uv run mypy src/
```

### State Flow Summary

```
START -> LOGIN_REQUIRED -> ACCOUNT_ACTIVE -> RETENTION_OFFER* -> EXIT_SURVEY -> FINAL_CONFIRMATION -> COMPLETE
         (human auth)      (click cancel)    (decline offers)    (submit)       (human confirm)

* RETENTION_OFFER can repeat multiple times
```
