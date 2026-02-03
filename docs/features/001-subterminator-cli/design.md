# SubTerminator CLI - Architecture Design

**Feature:** 001-subterminator-cli
**Version:** 1.0
**Date:** February 3, 2026
**Status:** Draft

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLI Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Typer     │  │   Config    │  │   Output    │                 │
│  │   Commands  │  │   Loader    │  │   Formatter │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
└─────────┼────────────────┼────────────────┼─────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Orchestrator                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   CancellationEngine                         │   │
│  │  - Coordinates state machine, browser, AI                    │   │
│  │  - Handles human-in-the-loop checkpoints                     │   │
│  │  - Manages session lifecycle                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────┬───────────────────┬───────────────────┬───────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  State Machine  │  │    Browser      │  │  AI Interpreter │
│  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │
│  │ States    │  │  │  │ Playwright│  │  │  │ Claude    │  │
│  │ Transitions│ │  │  │ + Stealth │  │  │  │ Vision    │  │
│  │ Guards    │  │  │  └───────────┘  │  │  └───────────┘  │
│  └───────────┘  │  │  ┌───────────┐  │  │  ┌───────────┐  │
│                 │  │  │ Actions   │  │  │  │ Heuristics│  │
│                 │  │  │ (click,   │  │  │  │ (fallback)│  │
│                 │  │  │  fill)    │  │  │  └───────────┘  │
│                 │  │  └───────────┘  │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Service Layer                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Netflix   │  │    Mock     │  │  (Future    │                 │
│  │   Service   │  │   Service   │  │   Services) │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  Screenshot │  │   Session   │  │   Config    │                 │
│  │   Manager   │  │   Logger    │  │   Store     │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

| Principle | Application |
|-----------|-------------|
| **Separation of Concerns** | Each layer has single responsibility |
| **Dependency Injection** | Services injected into orchestrator |
| **Strategy Pattern** | Service implementations are interchangeable |
| **State Machine Pattern** | Explicit states prevent invalid flows |
| **Human-in-the-Loop** | Irreversible actions require confirmation |

---

## 2. Component Design

### 2.1 CLI Layer

#### 2.1.1 Module: `cli/main.py`

```python
# Public Interface
app = typer.Typer()

@app.command()
def cancel(
    service: str,
    dry_run: bool = False,
    target: str = "live",
    verbose: bool = False,
    output_dir: Path = None
) -> None:
    """Cancel a subscription service."""
    ...

@app.command()
def version() -> None:
    """Show version information."""
    ...
```

**Responsibilities:**
- Parse command line arguments
- Validate service name
- Create orchestrator with dependencies
- Handle exit codes
- Display output to user

**Dependencies:**
- `CancellationEngine` (orchestrator)
- `OutputFormatter` (display)
- `ConfigLoader` (settings)

#### 2.1.2 Module: `cli/output.py`

```python
class OutputFormatter:
    """Formats and displays CLI output."""

    def show_progress(self, state: str, message: str) -> None: ...
    def show_human_prompt(self, prompt_type: PromptType) -> str: ...
    def show_success(self, result: CancellationResult) -> None: ...
    def show_failure(self, error: CancellationError) -> None: ...
    def show_warning(self, message: str) -> None: ...
```

### 2.2 Orchestrator Layer

#### 2.2.1 Module: `core/engine.py`

```python
class CancellationEngine:
    """Coordinates the cancellation flow."""

    def __init__(
        self,
        service: ServiceProtocol,
        browser: BrowserProtocol,
        ai: AIInterpreterProtocol,
        state_machine: StateMachine,
        session: SessionLogger,
        output: OutputFormatter
    ): ...

    async def run(self, dry_run: bool = False) -> CancellationResult:
        """Execute the cancellation flow."""
        ...

    async def _handle_state(self, state: State) -> State:
        """Process current state and determine next state."""
        ...

    async def _human_checkpoint(self, checkpoint_type: CheckpointType) -> bool:
        """Pause for human input. Returns True to continue, False to abort."""
        ...
```

**State Handling Logic:**
```python
async def _handle_state(self, state: State) -> State:
    match state:
        case State.START:
            await self.browser.navigate(self.service.entry_url)
            return await self._detect_state()

        case State.LOGIN_REQUIRED:
            continue_flow = await self._human_checkpoint(CheckpointType.AUTH)
            if not continue_flow:
                return State.ABORTED
            return await self._detect_state()

        case State.ACCOUNT_ACTIVE:
            await self.browser.click(self.service.selectors.cancel_link)
            return await self._detect_state()

        case State.ACCOUNT_CANCELLED:
            return State.COMPLETE  # Already done, exit successfully

        case State.THIRD_PARTY_BILLING:
            provider = await self._detect_billing_provider()
            self.output.show_third_party_instructions(provider)
            return State.FAILED

        case State.RETENTION_OFFER:
            await self.browser.click(self.service.selectors.decline_offer)
            return await self._detect_state()

        case State.EXIT_SURVEY:
            await self._complete_survey()
            return await self._detect_state()

        case State.FINAL_CONFIRMATION:
            if self.dry_run:
                self.output.show_dry_run_stop()
                return State.COMPLETE
            continue_flow = await self._human_checkpoint(CheckpointType.CONFIRM)
            if not continue_flow:
                return State.ABORTED
            await self.browser.click(self.service.selectors.confirm_cancel)
            return await self._detect_state()

        case State.UNKNOWN:
            # Try AI interpretation
            ai_result = await self.ai.interpret(await self.browser.screenshot())
            if ai_result.confidence >= 0.7:
                return ai_result.state
            # Low confidence - ask human
            return await self._human_checkpoint(CheckpointType.UNKNOWN_PAGE)
```

### 2.3 State Machine Layer

#### 2.3.1 Module: `core/states.py`

```python
from statemachine import StateMachine, State

class CancellationStateMachine(StateMachine):
    """Defines valid states and transitions for cancellation flow."""

    # States
    start = State(initial=True)
    login_required = State()
    account_active = State()
    account_cancelled = State()
    third_party_billing = State()
    retention_offer = State()
    exit_survey = State()
    final_confirmation = State()
    complete = State(final=True)
    aborted = State(final=True)
    failed = State(final=True)
    unknown = State()

    # Transitions
    navigate = (
        start.to(login_required, account_active, account_cancelled,
                 third_party_billing, failed, unknown)
    )
    authenticate = login_required.to(account_active, account_cancelled,
                                      third_party_billing, failed, unknown)
    click_cancel = account_active.to(retention_offer, exit_survey,
                                      final_confirmation, failed, unknown)
    decline_offer = retention_offer.to(retention_offer, exit_survey,
                                        final_confirmation, failed, unknown)
    submit_survey = exit_survey.to(retention_offer, final_confirmation,
                                    failed, unknown)
    confirm = final_confirmation.to(complete, failed)
    abort = (
        login_required.to(aborted) |
        final_confirmation.to(aborted) |
        unknown.to(aborted)
    )
    resolve_unknown = unknown.to(
        login_required, account_active, account_cancelled,
        retention_offer, exit_survey, final_confirmation, failed
    )

    # Guards
    def before_confirm(self) -> None:
        """Ensure human confirmation was received."""
        if not self.human_confirmed:
            raise TransitionNotAllowed("Human confirmation required")

    # Observers
    def on_enter_state(self, state: State) -> None:
        """Log state transitions and capture screenshots."""
        self.session.log_transition(self.current_state, state)
        self.browser.screenshot(f"{self.step}_{state.id}.png")
        self.step += 1
```

### 2.4 Browser Layer

#### 2.4.1 Module: `core/browser.py`

```python
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import stealth_async

class PlaywrightBrowser:
    """Playwright-based browser automation with stealth."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def launch(self) -> None:
        """Launch browser with stealth settings."""
        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()
        await stealth_async(self._page)

    async def navigate(self, url: str, timeout: int = 30000) -> None:
        """Navigate to URL and wait for load."""
        await self._page.goto(url, timeout=timeout, wait_until="networkidle")

    async def click(self, selector: str | list[str]) -> None:
        """Click element by selector(s). Tries each until success."""
        selectors = [selector] if isinstance(selector, str) else selector
        for sel in selectors:
            try:
                element = await self._page.wait_for_selector(sel, timeout=5000)
                await element.scroll_into_view_if_needed()
                await element.click()
                return
            except Exception:
                continue
        raise ElementNotFound(f"None of selectors found: {selectors}")

    async def fill(self, selector: str, value: str) -> None:
        """Fill form field."""
        await self._page.fill(selector, value)

    async def select_option(self, selector: str, value: str | None = None) -> None:
        """Select dropdown or radio option."""
        if value:
            await self._page.select_option(selector, value)
        else:
            # Select first available option
            await self._page.click(f"{selector} option:first-child")

    async def screenshot(self, path: str | None = None) -> bytes:
        """Capture screenshot. Returns bytes, optionally saves to path."""
        return await self._page.screenshot(path=path, full_page=True)

    async def html(self) -> str:
        """Get full page HTML."""
        return await self._page.content()

    async def url(self) -> str:
        """Get current URL."""
        return self._page.url

    async def text_content(self) -> str:
        """Get visible text content."""
        return await self._page.inner_text("body")

    async def close(self) -> None:
        """Close browser."""
        if self._browser:
            await self._browser.close()
```

#### 2.4.2 Protocol: `core/protocols.py`

```python
from typing import Protocol

class BrowserProtocol(Protocol):
    """Interface for browser automation."""

    async def launch(self) -> None: ...
    async def navigate(self, url: str, timeout: int = 30000) -> None: ...
    async def click(self, selector: str | list[str]) -> None: ...
    async def fill(self, selector: str, value: str) -> None: ...
    async def select_option(self, selector: str, value: str | None = None) -> None: ...
    async def screenshot(self, path: str | None = None) -> bytes: ...
    async def html(self) -> str: ...
    async def url(self) -> str: ...
    async def text_content(self) -> str: ...
    async def close(self) -> None: ...


@dataclass
class AIInterpretation:
    """Result of AI page interpretation."""
    state: State
    confidence: float
    reasoning: str
    actions: list[dict] = field(default_factory=list)


class AIInterpreterProtocol(Protocol):
    """Interface for AI-based page interpretation."""

    async def interpret(self, screenshot: bytes) -> AIInterpretation: ...
```

### 2.5 AI Interpreter Layer

#### 2.5.1 Module: `core/ai.py`

```python
import anthropic
import base64

class ClaudeInterpreter:
    """Claude Vision-based page state interpreter."""

    PROMPT_TEMPLATE = """Analyze this screenshot of a subscription cancellation flow.

Determine which state this page represents:
- LOGIN_REQUIRED: Login form is shown
- ACCOUNT_ACTIVE: Account page with active subscription, cancel option visible
- ACCOUNT_CANCELLED: Account page showing cancelled/inactive subscription
- THIRD_PARTY_BILLING: Shows billing through Apple/Google/carrier
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
}"""

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key)

    async def interpret(self, screenshot: bytes) -> AIInterpretation:
        """Interpret page state from screenshot using Claude Vision."""
        image_data = base64.b64encode(screenshot).decode("utf-8")

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": self.PROMPT_TEMPLATE
                    }
                ]
            }]
        )

        return self._parse_response(response.content[0].text)

    def _parse_response(self, text: str) -> AIInterpretation:
        """Parse Claude's JSON response."""
        import json
        data = json.loads(text)
        return AIInterpretation(
            state=State[data["state"]],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            actions=data.get("actions", [])
        )


class HeuristicInterpreter:
    """Fallback heuristic-based page state detection."""

    def interpret(self, url: str, text: str) -> AIInterpretation:
        """Detect state from URL patterns and text content."""
        # URL-based detection (high confidence)
        if "/login" in url:
            return AIInterpretation(State.LOGIN_REQUIRED, 0.95, "URL contains /login")

        # Text-based detection (medium confidence)
        text_lower = text.lower()

        if "cancel membership" in text_lower and "/account" in url:
            return AIInterpretation(State.ACCOUNT_ACTIVE, 0.85, "Cancel link found")

        if "restart membership" in text_lower:
            return AIInterpretation(State.ACCOUNT_CANCELLED, 0.85, "Restart link found")

        if any(p in text_lower for p in ["billed through", "itunes", "google play", "t-mobile"]):
            return AIInterpretation(State.THIRD_PARTY_BILLING, 0.80, "Third-party billing detected")

        if "before you go" in text_lower or "special offer" in text_lower:
            return AIInterpretation(State.RETENTION_OFFER, 0.75, "Retention language detected")

        if "why are you leaving" in text_lower or "reason for cancelling" in text_lower:
            return AIInterpretation(State.EXIT_SURVEY, 0.75, "Survey language detected")

        if "finish cancellation" in text_lower:
            return AIInterpretation(State.FINAL_CONFIRMATION, 0.80, "Finish button detected")

        if "cancelled" in text_lower and "subscription" in text_lower:
            return AIInterpretation(State.COMPLETE, 0.80, "Cancellation confirmed")

        if "something went wrong" in text_lower or "error" in text_lower:
            return AIInterpretation(State.ERROR, 0.70, "Error detected")

        return AIInterpretation(State.UNKNOWN, 0.0, "No patterns matched")
```

### 2.6 Service Layer

#### 2.6.1 Module: `services/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ServiceSelectors:
    """CSS/XPath selectors for service-specific elements."""
    cancel_link: list[str]
    decline_offer: list[str]
    survey_option: list[str]
    survey_submit: list[str]
    confirm_cancel: list[str]

@dataclass
class ServiceConfig:
    """Configuration for a subscription service."""
    name: str
    entry_url: str
    mock_entry_url: str
    selectors: ServiceSelectors
    text_indicators: dict[str, list[str]]

class ServiceProtocol(Protocol):
    """Interface for subscription services."""

    @property
    def config(self) -> ServiceConfig: ...

    @property
    def entry_url(self) -> str: ...

    @property
    def selectors(self) -> ServiceSelectors: ...
```

#### 2.6.2 Module: `services/netflix.py`

```python
class NetflixService:
    """Netflix-specific service implementation."""

    def __init__(self, target: str = "live"):
        self.target = target
        self._config = ServiceConfig(
            name="Netflix",
            entry_url="https://www.netflix.com/account",
            mock_entry_url="http://localhost:8000/account",
            selectors=ServiceSelectors(
                cancel_link=[
                    "[data-uia='action-cancel-membership']",
                    "a:has-text('Cancel Membership')",
                    "button:has-text('Cancel Membership')"
                ],
                decline_offer=[
                    "[data-uia='continue-cancel-btn']",
                    "button:has-text('Continue to Cancel')",
                    "a:has-text('No Thanks')"
                ],
                survey_option=[
                    "input[type='radio']",
                    "[data-uia='cancel-reason-item']"
                ],
                survey_submit=[
                    "[data-uia='continue-btn']",
                    "button:has-text('Continue')"
                ],
                confirm_cancel=[
                    "[data-uia='confirm-cancel-btn']",
                    "button:has-text('Finish Cancellation')"
                ]
            ),
            text_indicators={
                "login": ["Sign In", "Email", "Password"],
                "active": ["Cancel Membership"],
                "cancelled": ["Restart Membership"],
                "third_party": ["Billed through", "iTunes", "Google Play", "T-Mobile"],
                "retention": ["Before you go", "Special offer", "discount"],
                "survey": ["Why are you leaving", "Reason for cancelling"],
                "confirmation": ["Finish Cancellation"],
                "complete": ["Cancelled", "Your cancellation is complete"]
            }
        )

    @property
    def config(self) -> ServiceConfig:
        return self._config

    @property
    def entry_url(self) -> str:
        if self.target == "mock":
            return self._config.mock_entry_url
        return self._config.entry_url

    @property
    def selectors(self) -> ServiceSelectors:
        return self._config.selectors
```

#### 2.6.3 Module: `services/mock.py`

```python
import http.server
import threading
from pathlib import Path

class MockServer:
    """Local HTTP server serving mock Netflix pages."""

    def __init__(self, pages_dir: Path, port: int = 8000):
        self.pages_dir = pages_dir
        self.port = port
        self._server: http.server.HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start mock server in background thread."""
        handler = http.server.SimpleHTTPRequestHandler
        handler.directory = str(self.pages_dir)
        self._server = http.server.HTTPServer(("localhost", self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        """Stop mock server."""
        if self._server:
            self._server.shutdown()
            self._thread.join()
```

### 2.7 Infrastructure Layer

#### 2.7.1 Module: `utils/session.py`

```python
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class StateTransition:
    timestamp: str
    from_state: str
    to_state: str
    trigger: str
    url: str
    screenshot: str
    detection_method: str
    confidence: float

@dataclass
class AICall:
    timestamp: str
    screenshot: str
    prompt_tokens: int
    response_tokens: int
    state_detected: str
    confidence: float

class SessionLogger:
    """Logs session data to JSON file."""

    def __init__(self, output_dir: Path, service: str, target: str):
        self.session_id = f"{service}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = output_dir / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.data = {
            "session_id": self.session_id,
            "service": service,
            "target": target,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
            "final_state": None,
            "transitions": [],
            "ai_calls": [],
            "error": None
        }

    def log_transition(self, from_state: str, to_state: str,
                       trigger: str, url: str, screenshot: str,
                       detection_method: str, confidence: float) -> None:
        """Log a state transition."""
        self.data["transitions"].append(asdict(StateTransition(
            timestamp=datetime.now().isoformat(),
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            url=url,
            screenshot=screenshot,
            detection_method=detection_method,
            confidence=confidence
        )))
        self._save()

    def log_ai_call(self, screenshot: str, prompt_tokens: int,
                    response_tokens: int, state: str, confidence: float) -> None:
        """Log an AI interpretation call."""
        self.data["ai_calls"].append(asdict(AICall(
            timestamp=datetime.now().isoformat(),
            screenshot=screenshot,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            state_detected=state,
            confidence=confidence
        )))
        self._save()

    def complete(self, result: str, final_state: str, error: str | None = None) -> None:
        """Mark session complete."""
        self.data["completed_at"] = datetime.now().isoformat()
        self.data["result"] = result
        self.data["final_state"] = final_state
        self.data["error"] = error
        self._save()

    def _save(self) -> None:
        """Write session data to JSON file."""
        log_path = self.output_dir / "session.json"
        with open(log_path, "w") as f:
            json.dump(self.data, f, indent=2)

    @property
    def screenshots_dir(self) -> Path:
        """Directory for screenshots."""
        return self.output_dir
```

#### 2.7.2 Module: `utils/config.py`

```python
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class AppConfig:
    """Application configuration."""
    anthropic_api_key: str | None
    output_dir: Path
    page_timeout: int = 30000
    element_timeout: int = 10000
    auth_timeout: int = 300000  # 5 minutes
    confirm_timeout: int = 120000  # 2 minutes
    max_retries: int = 3
    max_transitions: int = 10

class ConfigLoader:
    """Loads configuration from environment and files."""

    @staticmethod
    def load() -> AppConfig:
        return AppConfig(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            output_dir=Path(os.environ.get("SUBTERMINATOR_OUTPUT", "./output")),
            page_timeout=int(os.environ.get("SUBTERMINATOR_PAGE_TIMEOUT", 30000)),
            element_timeout=int(os.environ.get("SUBTERMINATOR_ELEMENT_TIMEOUT", 10000)),
        )
```

---

## 3. Directory Structure

```
subterminator/
├── pyproject.toml
├── README.md
├── .env.example
│
├── src/
│   └── subterminator/
│       ├── __init__.py
│       ├── __main__.py           # Entry point
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py           # Typer commands
│       │   └── output.py         # Output formatting
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── engine.py         # CancellationEngine
│       │   ├── states.py         # State machine
│       │   ├── browser.py        # Playwright wrapper
│       │   ├── ai.py             # Claude interpreter
│       │   └── protocols.py      # Interfaces
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── base.py           # Service protocol
│       │   ├── netflix.py        # Netflix implementation
│       │   └── mock.py           # Mock server
│       │
│       └── utils/
│           ├── __init__.py
│           ├── session.py        # Session logging
│           ├── config.py         # Configuration
│           └── exceptions.py     # Custom exceptions
│
├── mock_pages/
│   └── netflix/
│       ├── account.html          # Active subscription
│       ├── account_cancelled.html
│       ├── login.html
│       ├── cancelplan_survey.html
│       ├── cancelplan_retention.html
│       ├── cancelplan_confirm.html
│       ├── cancelplan_complete.html
│       ├── error.html
│       └── assets/
│           ├── netflix.css
│           └── netflix.js
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   │
│   ├── unit/
│   │   ├── test_states.py
│   │   ├── test_browser.py
│   │   ├── test_ai.py
│   │   └── test_session.py
│   │
│   ├── integration/
│   │   ├── test_mock_flow.py
│   │   └── test_engine.py
│   │
│   └── e2e/
│       └── test_real_netflix.py  # Manual trigger only
│
└── output/                       # Generated at runtime
    └── netflix_20260203_101530/
        ├── session.json
        └── 01_account_active.png
```

---

## 4. Data Flow

### 4.1 Happy Path Flow

```
User: subterminator cancel netflix
         │
         ▼
┌─────────────────┐
│  CLI parses     │
│  arguments      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create engine  │
│  with deps      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  engine.run()   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  State: START                           │
│  → Navigate to netflix.com/account      │
│  → Screenshot + detect state            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  State: ACCOUNT_ACTIVE                  │
│  → Click "Cancel Membership"            │
│  → Wait for page load                   │
│  → Screenshot + detect state            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  State: EXIT_SURVEY                     │
│  → Select first survey option           │
│  → Click continue                       │
│  → Screenshot + detect state            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  State: FINAL_CONFIRMATION              │
│  → Display warning about shared access  │
│  → Prompt user: "Type 'confirm'"        │
│  ← User types: confirm                  │
│  → Click "Finish Cancellation"          │
│  → Screenshot + detect state            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  State: COMPLETE                        │
│  → Save final screenshot                │
│  → Write session log                    │
│  → Display success message              │
└─────────────────────────────────────────┘
         │
         ▼
Exit code: 0
```

### 4.2 State Detection Flow

```
┌─────────────────┐
│  Page loaded    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  1. URL-based detection                 │
│     - Check URL patterns                │
│     - High confidence if matched        │
└────────┬────────────────────────────────┘
         │
         │ confidence < 0.8?
         ▼
┌─────────────────────────────────────────┐
│  2. Text-based detection                │
│     - Search for key phrases            │
│     - Medium confidence                 │
└────────┬────────────────────────────────┘
         │
         │ confidence < 0.7?
         ▼
┌─────────────────────────────────────────┐
│  3. AI-based detection                  │
│     - Capture screenshot                │
│     - Send to Claude Vision             │
│     - Parse response                    │
└────────┬────────────────────────────────┘
         │
         │ confidence < 0.5?
         ▼
┌─────────────────────────────────────────┐
│  4. Human checkpoint                    │
│     - Show screenshot                   │
│     - Ask user to identify/continue     │
└─────────────────────────────────────────┘
```

---

## 5. Error Handling Strategy

### 5.1 Retry Logic

```python
async def with_retry(
    operation: Callable,
    max_retries: int = 3,
    retry_on: tuple[type[Exception], ...] = (TimeoutError, NetworkError)
) -> T:
    """Execute operation with retry for transient failures."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except retry_on as e:
            last_error = e
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    raise last_error
```

### 5.2 Exception Hierarchy

```python
class SubTerminatorError(Exception):
    """Base exception for all SubTerminator errors."""
    pass

class TransientError(SubTerminatorError):
    """Errors that may succeed on retry."""
    pass

class PermanentError(SubTerminatorError):
    """Errors that will not succeed on retry."""
    pass

class ConfigurationError(PermanentError):
    """Invalid configuration."""
    pass

class ServiceError(PermanentError):
    """Service-specific error (e.g., third-party billing)."""
    pass

class HumanInterventionRequired(SubTerminatorError):
    """Flow requires human input to continue."""
    pass

class UserAborted(SubTerminatorError):
    """User chose to abort the operation."""
    pass
```

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
                    ┌───────────┐
                    │   E2E     │  1-2 manual tests
                    │  (real)   │  against real Netflix
                    └───────────┘
               ┌─────────────────────┐
               │    Integration      │  ~10 tests against
               │    (mock server)    │  mock server
               └─────────────────────┘
          ┌───────────────────────────────┐
          │           Unit Tests          │  ~30 tests for
          │    (pure logic, no I/O)       │  state machine,
          │                               │  parsing, etc.
          └───────────────────────────────┘
```

### 6.2 Test Fixtures

```python
# conftest.py

@pytest.fixture
def mock_server():
    """Start mock server for integration tests."""
    server = MockServer(Path("mock_pages/netflix"), port=8001)
    server.start()
    yield server
    server.stop()

@pytest.fixture
def mock_browser():
    """Mock browser for unit tests."""
    return MagicMock(spec=BrowserProtocol)

@pytest.fixture
def mock_ai():
    """Mock AI interpreter for unit tests."""
    ai = MagicMock(spec=AIInterpreterProtocol)
    ai.interpret.return_value = AIInterpretation(
        state=State.ACCOUNT_ACTIVE,
        confidence=0.9,
        reasoning="Test mock"
    )
    return ai
```

---

## 7. Dependencies

### 7.1 Production Dependencies

```toml
[project]
dependencies = [
    "playwright>=1.58",
    "playwright-stealth>=2.0",
    "python-statemachine>=2.5",
    "typer[all]>=0.21",
    "anthropic>=0.40",
    "pydantic>=2.0",
]
```

### 7.2 Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-playwright>=0.5",
    "pytest-cov>=5.0",
    "mypy>=1.8",
    "ruff>=0.5",
]
```

---

## 8. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Netflix changes selectors | Medium | Mock still works; real may break | AI fallback; selector lists with alternatives |
| Claude API unavailable | Low | Cannot use AI interpretation | Heuristic fallback; graceful degradation |
| Bot detection blocks automation | High (real) | Real flow fails | Mock-first approach; stealth settings |
| State machine infinite loop | Low | Flow hangs | Max transition limit (10); timeout |
| User closes browser mid-flow | Low | Orphaned process | Browser close detection; cleanup |

---

## 9. Open Design Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| Mock page visual fidelity | Decided | Replicate key selectors/structure, minimal CSS (functional, not pixel-perfect) |
| A/B variant configuration | Decided | Query parameter approach: `?variant=retention` selects different HTML file |
| CLI progress indicator | Decided | Step-by-step output (simpler, better for logs) with optional `--verbose` spinner |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial design from spec |
