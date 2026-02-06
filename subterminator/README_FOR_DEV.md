# SubTerminator Developer Guide

A comprehensive guide for developers working on the SubTerminator codebase.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Layer-by-Layer Guide](#layer-by-layer-guide)
  - [CLI Layer](#cli-layer)
  - [MCP Orchestrator](#mcp-orchestrator)
  - [Core Utilities](#core-utilities)
  - [Services](#services)
- [Development Workflow](#development-workflow)
- [How-To Guides](#how-to-guides)
  - [Adding a New Service](#adding-a-new-service)
  - [Debugging Issues](#debugging-issues)
- [Architecture Decision Records](#architecture-decision-records)

---

## Architecture Overview

SubTerminator uses LLM-driven orchestration with the Playwright MCP server:

```
CLI Layer (user interaction)
    |
    v
MCP Orchestrator (mcp_orchestrator/)
    - LLM-driven tool orchestration
    - Playwright MCP server
    - Dynamic page understanding
    |
    v
MCP Server (Playwright) --> Browser
```

### Core Intuition

1. **Human checkpoints for irreversible actions** - Authentication and final confirmation always require human interaction. The tool assists, never acts autonomously on critical decisions.

2. **LLM-driven adaptability** - The LLM interprets page snapshots and decides the next action, adapting to UI changes without code updates.

3. **Service-specific configuration** - Each service defines its URLs, predicates, and LLM hints.

### Data Flow

```
User runs: subterminator cancel --service netflix
                |
                v
    +------------------------+
    |      CLI (main.py)     |  <-- Parses args, creates components
    +------------------------+
                |
                v
    +------------------------+
    |     TaskRunner         |  <-- Main loop: snapshot -> LLM -> tool -> repeat
    +------------------------+
          |         |
          v         v
    +---------+  +-----------+
    | LLMClient| | MCPClient |  <-- Claude/GPT-4 / Playwright MCP
    +---------+  +-----------+
          |
          v
    +------------------------+
    | CheckpointHandler      |  <-- Human approval gates
    +------------------------+
```

---

## Layer-by-Layer Guide

### CLI Layer

**Location:** `src/subterminator/cli/`

The CLI layer handles user interaction using the [Typer](https://typer.tiangolo.com/) framework.

#### Entry Point: `main.py`

```python
@app.command()
def cancel(
    service: str | None = typer.Option(None, "--service", "-s"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    headless: bool = typer.Option(False, "--headless"),
    verbose: bool = typer.Option(False, "--verbose", "-V"),
    model: str | None = typer.Option(None, "--model"),
    max_turns: int = typer.Option(20, "--max-turns"),
    no_checkpoint: bool = typer.Option(False, "--no-checkpoint"),
    ...
) -> None:
```

**Exit codes:**
- `0`: Success (cancellation completed)
- `1`: Failure (cancellation failed)
- `2`: User cancelled (via Ctrl+C or menu)
- `3`: Invalid service
- `5`: MCP connection error
- `130`: SIGINT during orchestration

---

### MCP Orchestrator

**Location:** `src/subterminator/mcp_orchestrator/`

The MCP orchestrator uses LLM-driven tool selection with Playwright MCP server.

#### Module Structure

| File | Responsibility |
|------|----------------|
| `task_runner.py` | Main orchestration loop, virtual tools |
| `llm_client.py` | Claude/GPT-4 via LangChain |
| `mcp_client.py` | Playwright MCP server connection |
| `checkpoint.py` | Human approval gates, auth detection |
| `snapshot.py` | Parse browser_snapshot output |
| `types.py` | TaskResult, ToolCall, NormalizedSnapshot |
| `exceptions.py` | Custom exception types |
| `services/` | Service-specific configurations |

#### TaskRunner (`task_runner.py`)

The main loop executes one tool per turn:

```python
class TaskRunner:
    async def run(self, service: str, max_turns: int = 20) -> TaskResult:
        # 1. Connect to MCP, get tools
        # 2. Navigate to initial URL
        # 3. Loop: snapshot -> LLM -> execute tool -> repeat
        # 4. End on complete_task or max turns
```

**Virtual Tools:**
- `complete_task` - Signal task completion (success/failed)
- `request_human_approval` - Explicit approval request

**Flow per turn:**
1. LLM receives current page snapshot
2. LLM returns tool call (or text requiring prompting)
3. Check if checkpoint needed
4. Execute tool (MCP or virtual)
5. Add result to message history
6. Repeat

#### LLMClient (`llm_client.py`)

Abstracts Claude and GPT-4 via LangChain:

```python
class LLMClient:
    def __init__(self, model_name: str | None = None):
        # Resolves model from param -> env var -> default
        # Supports claude-* and gpt-* prefixes

    async def invoke(self, messages, tools) -> AIMessage:
        # Converts messages/tools to LangChain format
        # Handles retries with exponential backoff
```

**Model selection:**
1. Explicit `model_name` parameter
2. `SUBTERMINATOR_MODEL` env var
3. Default: `claude-opus-4-6`

#### MCPClient (`mcp_client.py`)

Manages Playwright MCP server subprocess:

```python
class MCPClient:
    async def connect(self):
        # Starts npx @playwright/mcp@latest subprocess
        # Initializes MCP session

    async def list_tools(self) -> list[dict]:
        # Returns available browser tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        # Executes tool and returns result text
```

**Browser profile:** Uses `.chrome-profile/` in project root for session persistence.

#### CheckpointHandler (`checkpoint.py`)

Manages human approval:

```python
class CheckpointHandler:
    def detect_auth_edge_case(snapshot, config) -> str | None:
        # Returns "login", "captcha", "mfa", or None

    def should_checkpoint(tool, snapshot, config) -> bool:
        # Checks service's checkpoint_conditions predicates

    async def request_approval(tool, snapshot) -> bool:
        # Shows checkpoint UI, returns True if approved
```

**Auth flow:** When login/CAPTCHA/MFA detected, waits for user to complete in browser, then continues.

#### Snapshot Parser (`snapshot.py`)

Parses Playwright MCP's markdown output:

```python
def normalize_snapshot(text: str) -> NormalizedSnapshot:
    # Extracts: url, title, content (accessibility tree)
```

**Input format:**
```
### Page
- Page URL: https://example.com
- Page Title: Example
- generic [ref=s1e0]:
  - banner [ref=s1e1]:
  ...
```

#### Service Configs (`services/`)

Each service defines:

```python
@dataclass
class ServiceConfig:
    name: str                    # "netflix"
    initial_url: str             # Starting URL
    goal_template: str           # LLM goal description
    checkpoint_conditions: list  # When to require approval
    success_indicators: list     # How to verify completion
    failure_indicators: list     # How to detect failure
    auth_edge_case_detectors: list  # Login/CAPTCHA/MFA detection
    system_prompt_addition: str  # Service-specific LLM instructions
```

**Predicates:**
- `SnapshotPredicate = Callable[[NormalizedSnapshot], bool]`
- `CheckpointPredicate = Callable[[ToolCall, NormalizedSnapshot], bool]`

---

### Core Utilities

**Location:** `src/subterminator/core/`

Utility modules that support the MCP orchestrator:

| File | Responsibility |
|------|----------------|
| `protocols.py` | Shared types (State enum, protocols) |
| `browser.py` | PlaywrightBrowser helper class |
| `states.py` | State transition logic (reference) |

---

### Services

**Location:** `src/subterminator/services/`

Site-specific configuration (registry and mock server for testing).

---

## Development Workflow

### Initial Setup

```bash
git clone <repo-url>
cd subterminator
uv sync
uv run playwright install chromium
```

### Running Tests

```bash
uv run pytest tests/unit/ -v           # Unit tests
uv run pytest tests/integration/ -v    # Integration tests
uv run pytest --cov=subterminator      # With coverage
```

### Linting

```bash
uv run ruff check src/
uv run ruff check --fix src/
uv run mypy src/
```

### Testing

```bash
# Requires ANTHROPIC_API_KEY
uv run subterminator cancel --service netflix --dry-run
```

---

## How-To Guides

### Adding a New Service

1. Create service config in `src/subterminator/mcp_orchestrator/services/`:

```python
# myservice.py
from .base import ServiceConfig

def is_login_page(snapshot: NormalizedSnapshot) -> bool:
    return "/login" in snapshot.url

def is_final_confirmation(tool: ToolCall, snapshot: NormalizedSnapshot) -> bool:
    return "confirm" in tool.name and "cancel" in snapshot.content.lower()

myservice_config = ServiceConfig(
    name="myservice",
    initial_url="https://myservice.com/account",
    goal_template="Cancel the MyService subscription",
    checkpoint_conditions=[is_final_confirmation],
    success_indicators=[lambda s: "cancelled" in s.content.lower()],
    auth_edge_case_detectors=[is_login_page],
)
```

2. Register in `services/registry.py`

3. Write tests in `tests/unit/mcp_orchestrator/`

### Debugging Issues

- Run with `--verbose` to see LLM reasoning
- Check message history in logs
- Verify snapshot parsing with unit tests

---

## Architecture Decision Records

### ADR-1: Mock-First Development

Testing uses local mock server with static HTML pages.

### ADR-2: Typer for CLI Framework

Modern CLI with automatic --help and async support.

### ADR-3: Human Checkpoints for Safety

Mandatory human confirmation for auth and final cancellation.

### ADR-4: Session Logging for Observability

Full audit trail for debugging.

### ADR-5: MCP Orchestration Pattern

**Context:** Subscription UIs change frequently, breaking hardcoded selectors.

**Decision:** Use LLM-driven orchestration with Playwright MCP server. The LLM interprets page snapshots and decides actions dynamically.

**Consequences:**
- More resilient to UI changes
- Higher per-run cost (API call per turn)
- Requires careful checkpoint design to prevent unintended actions
- Single-tool-per-turn prevents runaway automation
- Service configs use predicates instead of selectors

---

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| CLI entry | `src/subterminator/cli/main.py` |
| Task runner | `src/subterminator/mcp_orchestrator/task_runner.py` |
| LLM client | `src/subterminator/mcp_orchestrator/llm_client.py` |
| MCP server client | `src/subterminator/mcp_orchestrator/mcp_client.py` |
| Checkpoint handler | `src/subterminator/mcp_orchestrator/checkpoint.py` |
| Snapshot parser | `src/subterminator/mcp_orchestrator/snapshot.py` |
| Types | `src/subterminator/mcp_orchestrator/types.py` |
| Services | `src/subterminator/mcp_orchestrator/services/` |
| Core utilities | `src/subterminator/core/` |
| Config | `src/subterminator/utils/config.py` |

### Key Commands

```bash
# Run CLI
uv run subterminator cancel                      # Interactive
uv run subterminator cancel --service netflix    # Direct service
uv run subterminator cancel --service netflix --dry-run  # Stop at final confirmation

# Tests
uv run pytest tests/unit/ -v
uv run pytest tests/unit/mcp_orchestrator/ -v

# Lint
uv run ruff check src/
uv run mypy src/
```
