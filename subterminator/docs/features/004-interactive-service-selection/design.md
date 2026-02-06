# Design: Interactive Service Selection CLI

**Feature:** 004-interactive-service-selection
**Status:** Draft
**Created:** 2026-02-04
**Spec Reference:** spec.md

---

## 1. Architecture Overview

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                          │
│                    (cli/main.py:cancel)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┐                                       │
│  │  Mode Detection      │                                       │
│  │  (cli/prompts.py)    │                                       │
│  └──────────┬───────────┘                                       │
│             │                                                   │
│             ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   is_interactive()?                      │   │
│  └────────────┬──────────────────────────────┬─────────────┘   │
│               │                              │                  │
│          TTY=True                       TTY=False               │
│          no --service                   or --service            │
│               │                              │                  │
│               ▼                              ▼                  │
│  ┌──────────────────────┐      ┌──────────────────────────┐    │
│  │  Interactive Menu    │      │  Direct Service Lookup   │    │
│  │  (questionary)       │      │  (registry.py)           │    │
│  └──────────┬───────────┘      └────────────┬─────────────┘    │
│             │                               │                   │
│             └──────────────┬────────────────┘                   │
│                            │                                    │
│                            ▼                                    │
│               ┌──────────────────────┐                          │
│               │  Service Registry    │                          │
│               │  Validation          │                          │
│               └──────────┬───────────┘                          │
│                          │                                      │
│                          ▼                                      │
│               ┌──────────────────────┐                          │
│               │  Existing Cancel     │                          │
│               │  Flow (unchanged)    │                          │
│               └──────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **ServiceRegistry** | `services/registry.py` | Service metadata storage and lookup |
| **InteractivePrompts** | `cli/prompts.py` | TTY detection, menu rendering |
| **AccessibilityUtils** | `cli/accessibility.py` | Color/animation settings |
| **CancelCommand** | `cli/main.py` | Entry point, mode routing |

### 1.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Menu library | questionary | Actively maintained, typer-compatible, accessibility support |
| Service registry | Static list | Simple, no external config needed, easy to extend |
| Mode detection | TTY + env vars | Standard practice for CLI tools |
| Fuzzy suggestions | difflib | Already in stdlib, no new deps |

---

## 2. Component Design

### 2.1 ServiceRegistry Component

**Location:** `src/subterminator/services/registry.py`

**Purpose:** Single source of truth for service metadata.

**Data Model:**
```python
@dataclass
class ServiceInfo:
    id: str           # "netflix"
    name: str         # "Netflix"
    description: str  # "Video streaming service"
    available: bool   # True if cancellation implemented
```

**Operations:**
- `get_all_services()` - All services including unavailable
- `get_available_services()` - Only cancellable services
- `get_service_by_id(id)` - Lookup by ID, returns None if not found
- `suggest_service(typo)` - Fuzzy match for error suggestions

**Registry Data:**
```python
SERVICE_REGISTRY = [
    ServiceInfo("netflix", "Netflix", "Video streaming service", available=True),
    ServiceInfo("spotify", "Spotify", "Music streaming service", available=False),
    ServiceInfo("hulu", "Hulu", "TV and movie streaming", available=False),
    ServiceInfo("disney", "Disney+", "Disney streaming service", available=False),
]
```

### 2.2 InteractivePrompts Component

**Location:** `src/subterminator/cli/prompts.py`

**Purpose:** Encapsulate all interactive mode logic.

**Functions:**
- `is_interactive()` - Determine if interactive mode is appropriate
- `select_service()` - Display menu, return selected service ID or None
- `show_services_help()` - Display help text for services

**Mode Detection Logic:**
```
is_interactive() = True when:
  - stdin.isatty() AND stdout.isatty()
  - AND NOT SUBTERMINATOR_NO_PROMPTS env var
  - AND NOT CI env var
  - AND NOT --no-input flag
```

### 2.3 AccessibilityUtils Component

**Location:** `src/subterminator/cli/accessibility.py`

**Purpose:** Centralize accessibility settings.

**Functions:**
- `should_use_colors()` - Check NO_COLOR, TERM=dumb
- `should_use_animations()` - Check SUBTERMINATOR_PLAIN
- `get_questionary_style()` - Return styled or None

### 2.4 Modified CancelCommand

**Location:** `src/subterminator/cli/main.py` (modified)

**Changes:**
1. Remove positional `service` argument
2. Add `--service` / `-s` option
3. Add `--no-input` flag
4. Add `--plain` flag
5. Add service resolution logic before existing flow

---

## 3. Technical Decisions

### TD-1: Questionary vs InquirerPy

**Decision:** Use questionary

**Rationale:**
- questionary is simpler, fewer features but sufficient
- InquirerPy has fuzzy search built-in but adds complexity
- PRD deferred fuzzy search to future iteration
- questionary has better typer integration (same prompt_toolkit base)

**Trade-offs:**
- (-) No built-in fuzzy search
- (+) Smaller dependency
- (+) Better maintained

### TD-2: Registry as Module vs Config File

**Decision:** Static Python module

**Rationale:**
- Services require code implementation anyway
- No need for runtime configurability
- Type safety and IDE support
- Simpler than YAML/JSON config

**Trade-offs:**
- (-) Adding service requires code change
- (+) Compile-time validation
- (+) No file I/O at startup

### TD-3: Fuzzy Match Implementation

**Decision:** Use difflib.get_close_matches with cutoff=0.6

**Rationale:**
- Standard library, no new dependencies
- Adequate for typo correction
- cutoff=0.6 balances helpful suggestions vs noise

---

## 4. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| questionary breaks on Windows | Low | Medium | Test on Windows CI, fallback to plain mode |
| Non-TTY detection fails | Low | Low | Multiple env var checks, explicit --no-input |
| User confusion about old syntax | Medium | Low | Clear error message with migration hint |
| Color bleeding in accessibility mode | Medium | Low | Explicit style=None for monochrome |

---

## 5. Dependency Analysis

### 5.1 New Dependencies

| Package | Version | Size | Transitive Deps |
|---------|---------|------|-----------------|
| questionary | >=2.0 | ~50KB | prompt_toolkit (already via typer) |

### 5.2 Dependency Justification

questionary is chosen because:
1. Already compatible with typer's prompt_toolkit
2. No new transitive dependencies (prompt_toolkit shared)
3. Proven stability (used by many CLIs)
4. Explicit accessibility support (style=None)

---

## 6. Migration Strategy

### 6.1 Breaking Change Handling

The positional argument is removed immediately (no deprecation period per PRD decision).

**Error for old syntax:**
```
$ subterminator cancel netflix
Usage: subterminator cancel [OPTIONS]

Error: Got unexpected extra argument (netflix)

Hint: The positional syntax has changed in v2.0.
Use: subterminator cancel --service netflix
Or:  subterminator cancel  (for interactive menu)
```

### 6.2 Implementation Order

1. Add registry.py (no CLI changes yet)
2. Add prompts.py and accessibility.py (no CLI changes yet)
3. Modify main.py to use new components
4. Update tests
5. Update documentation

This allows incremental testing without breaking existing functionality until step 3.

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Component | Test Focus |
|-----------|------------|
| registry.py | Lookup, fuzzy match, filtering |
| accessibility.py | Env var detection |
| prompts.py (mock questionary) | Mode detection logic |

### 7.2 Integration Tests

| Scenario | Test Approach |
|----------|---------------|
| Interactive selection | Mock questionary.select |
| Non-interactive --service | Direct command invocation |
| Error cases | Verify exit codes and messages |
| Accessibility | Verify no colors when NO_COLOR set |

### 7.3 Manual Tests

| Scenario | Method |
|----------|--------|
| Real TTY interaction | Run in terminal manually |
| Windows compatibility | Test on Windows terminal |
| Screen reader | Test with VoiceOver/NVDA |

---

## 8. Interface Contracts

### 8.1 ServiceInfo Dataclass

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ServiceInfo:
    """Immutable metadata for a cancellable service."""
    id: str           # Unique identifier, lowercase, e.g., "netflix"
    name: str         # Display name, e.g., "Netflix"
    description: str  # Brief description, e.g., "Video streaming service"
    available: bool = True  # False for "coming soon" services
```

**Constraints:**
- `id` must be unique across all services
- `id` must be lowercase alphanumeric (pattern: `^[a-z][a-z0-9-]*$`)
- `name` max length: 50 characters
- `description` max length: 100 characters

### 8.2 Registry Module Interface

```python
# src/subterminator/services/registry.py

def get_all_services() -> list[ServiceInfo]:
    """
    Return all registered services including unavailable ones.

    Returns:
        List of ServiceInfo ordered by name alphabetically,
        available services first, then unavailable.
    """
    ...

def get_available_services() -> list[ServiceInfo]:
    """
    Return only services where available=True.

    Returns:
        List of available ServiceInfo ordered alphabetically by name.
    """
    ...

def get_service_by_id(service_id: str) -> ServiceInfo | None:
    """
    Look up a service by its unique ID.

    Args:
        service_id: The service identifier (case-insensitive).

    Returns:
        ServiceInfo if found, None otherwise.
    """
    ...

def suggest_service(typo: str) -> str | None:
    """
    Suggest a service ID for a potential typo.

    Uses difflib.get_close_matches with cutoff=0.6.
    Only suggests from available services.

    Args:
        typo: The mistyped service name.

    Returns:
        Suggested service ID if close match found, None otherwise.
    """
    ...
```

### 8.3 Prompts Module Interface

```python
# src/subterminator/cli/prompts.py

def is_interactive(no_input_flag: bool = False) -> bool:
    """
    Determine if interactive mode should be used.

    Args:
        no_input_flag: Value of --no-input CLI flag.

    Returns:
        True if all conditions met:
        - stdin.isatty() and stdout.isatty()
        - no_input_flag is False
        - SUBTERMINATOR_NO_PROMPTS env var not set
        - CI env var not set
    """
    ...

def select_service(plain: bool = False) -> str | None:
    """
    Display interactive service selection menu.

    Args:
        plain: If True, disable colors/styling.

    Returns:
        Selected service ID, or None if user cancelled (Ctrl+C).

    Raises:
        Never raises - handles all questionary exceptions internally.
    """
    ...

def show_services_help() -> None:
    """
    Print formatted help text showing all services and their status.

    Output format:
        --- Supported Services ---

          Netflix: Video streaming service [Available]
          Spotify: Music streaming service [Coming Soon]
          ...
    """
    ...
```

### 8.4 Accessibility Module Interface

```python
# src/subterminator/cli/accessibility.py

def should_use_colors() -> bool:
    """
    Check if terminal colors should be used.

    Returns:
        False if any of:
        - NO_COLOR env var is set (any value)
        - TERM env var is "dumb"
        True otherwise.
    """
    ...

def should_use_animations() -> bool:
    """
    Check if animations/spinners should be used.

    Returns:
        False if any of:
        - should_use_colors() returns False
        - SUBTERMINATOR_PLAIN env var is set
        True otherwise.
    """
    ...

def get_questionary_style() -> Style | None:
    """
    Get questionary Style object based on accessibility settings.

    Returns:
        None if should_use_colors() is False (uses default monochrome).
        Custom Style object otherwise with cyan/green accents.
    """
    ...
```

### 8.5 Modified Cancel Command Signature

```python
# src/subterminator/cli/main.py

@app.command()
def cancel(
    service: str | None = typer.Option(
        None,
        "--service", "-s",
        help="Service to cancel (bypasses interactive menu)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="Run without making actual changes",
    ),
    no_input: bool = typer.Option(
        False,
        "--no-input",
        help="Disable all interactive prompts (requires --service)",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Disable colors and animations (accessibility)",
    ),
    target: str = typer.Option(
        "live",
        "--target", "-t",
        help="Target environment: 'live' or 'mock'",
    ),
    headless: bool = typer.Option(
        False,
        "--headless",
        help="Run browser in headless mode",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-V",
        help="Show detailed progress information",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir", "-o",
        help="Directory for session artifacts",
    ),
) -> None:
    """Cancel a subscription service."""
    ...
```

### 8.6 Exit Code Contract

| Code | Constant | Meaning |
|------|----------|---------|
| 0 | `EXIT_SUCCESS` | Operation completed successfully |
| 1 | `EXIT_FAILURE` | Operation failed (cancellation error) |
| 2 | `EXIT_CANCELLED` | User cancelled (Ctrl+C, menu cancel) |
| 3 | `EXIT_INVALID_ARGS` | Invalid arguments (unknown service, missing --service) |
| 4 | `EXIT_CONFIG_ERROR` | Configuration error |

### 8.7 Error Message Formats

**Unknown service:**
```
Error: Unknown service '{service}'
Available services: {comma-separated list}
Did you mean: {suggestion}?  (only if suggestion exists)
```

**Missing service in non-interactive mode:**
```
Error: --service required in non-interactive mode
Example: subterminator cancel --service netflix
```

**Unavailable service:**
```
Error: '{service}' is not yet available
Currently available: {comma-separated list}
```

---

## 9. Sequence Diagrams

### 9.1 Interactive Mode Flow

```
User                    CLI                     Prompts                Registry
  |                      |                         |                      |
  |  cancel              |                         |                      |
  |--------------------->|                         |                      |
  |                      |  is_interactive()?      |                      |
  |                      |------------------------>|                      |
  |                      |  True                   |                      |
  |                      |<------------------------|                      |
  |                      |                         |                      |
  |                      |  select_service()       |                      |
  |                      |------------------------>|                      |
  |                      |                         |  get_all_services()  |
  |                      |                         |--------------------->|
  |                      |                         |  [ServiceInfo...]    |
  |                      |                         |<---------------------|
  |  [Menu displayed]    |                         |                      |
  |<---------------------------------------------- |                      |
  |                      |                         |                      |
  |  [Arrow/Enter]       |                         |                      |
  |---------------------------------------------->|                      |
  |                      |  "netflix"              |                      |
  |                      |<------------------------|                      |
  |                      |                         |                      |
  |                      |  [Continue with existing flow]                 |
  |                      |                         |                      |
```

### 9.2 Non-Interactive Mode Flow

```
User                    CLI                     Registry
  |                      |                         |
  |  cancel -s netflix   |                         |
  |--------------------->|                         |
  |                      |  get_service_by_id()    |
  |                      |------------------------>|
  |                      |  ServiceInfo            |
  |                      |<------------------------|
  |                      |                         |
  |                      |  [Check available]      |
  |                      |                         |
  |                      |  [Continue with existing flow]
  |                      |                         |
```

### 9.3 Error Flow (Unknown Service)

```
User                    CLI                     Registry
  |                      |                         |
  |  cancel -s netflixx  |                         |
  |--------------------->|                         |
  |                      |  get_service_by_id()    |
  |                      |------------------------>|
  |                      |  None                   |
  |                      |<------------------------|
  |                      |                         |
  |                      |  suggest_service()      |
  |                      |------------------------>|
  |                      |  "netflix"              |
  |                      |<------------------------|
  |                      |                         |
  |  Error + suggestion  |                         |
  |<---------------------|                         |
  |                      |                         |
  |  [Exit code 3]       |                         |
```

---

## 10. Clarifications (Addressing Review Feedback)

### 10.1 Help Option Behavior (FR-1.7)

**Menu Structure:**
```
Which subscription would you like to cancel?

❯ Netflix - Video streaming service
  Spotify - Music streaming service (coming soon)  [disabled]
  Hulu - TV and movie streaming (coming soon)  [disabled]
  ─────────────────────────
  Help - Show more information
```

**Help Flow:**
1. User selects "Help" from menu → `select_service()` detects `__help__` value
2. `show_services_help()` is called, prints detailed service information
3. Menu re-displays (loop continues)
4. User can then select a service or Ctrl+C to exit

**Help Output Format:**
```
--- Supported Services ---

  Netflix: Video streaming service [Available]
  Spotify: Music streaming service [Coming Soon]
  Hulu: TV and movie streaming [Coming Soon]
  Disney+: Disney streaming service [Coming Soon]
```

### 10.2 select_service() Error Handling

**Return Value Semantics:**
- `str` - Valid service ID selected by user
- `None` - User cancelled (Ctrl+C pressed)

**Internal Handling:**
```python
def select_service(plain: bool = False) -> str | None:
    """
    Display interactive service selection menu.

    Returns:
        str: Selected service ID
        None: User cancelled with Ctrl+C

    Note: questionary.select().ask() returns None on Ctrl+C.
    All other questionary exceptions are caught and re-raised as
    RuntimeError (should never happen with valid configuration).
    """
    while True:
        result = questionary.select(...).ask()

        if result is None:
            return None  # User cancelled

        if result == "__help__":
            show_services_help()
            continue  # Re-display menu

        return result  # Valid service ID
```

**Caller Responsibility (in main.py):**
```python
selected = select_service(plain=plain)
if selected is None:
    typer.echo("Cancelled.")
    raise typer.Exit(code=2)  # EXIT_CANCELLED
```

### 10.3 Fuzzy Match Specification

**Implementation Details:**
```python
from difflib import get_close_matches

def suggest_service(typo: str) -> str | None:
    """
    Returns single best suggestion or None.

    Uses difflib.get_close_matches with:
    - n=1 (return at most 1 match)
    - cutoff=0.6 (60% similarity threshold)

    Only matches against available service IDs.
    """
    available_ids = [s.id for s in get_available_services()]
    matches = get_close_matches(typo.lower(), available_ids, n=1, cutoff=0.6)
    return matches[0] if matches else None
```

**Examples:**
| Input | Output | Reason |
|-------|--------|--------|
| `"netflixx"` | `"netflix"` | Close match (1 char diff) |
| `"netlix"` | `"netflix"` | Close match (1 char diff) |
| `"xyz"` | `None` | No match above 0.6 threshold |
| `"spot"` | `None` | Spotify not available, so not suggested |

### 10.4 Backward Compatibility & Migration

**Breaking Change (per PRD):**
The positional argument `service` is **removed entirely**. This is a breaking change.

**Current CLI:**
```bash
subterminator cancel netflix  # WORKS in current version
```

**New CLI:**
```bash
subterminator cancel netflix  # ERRORS with hint
subterminator cancel --service netflix  # WORKS
subterminator cancel  # WORKS (interactive)
```

**Typer Behavior:**
When typer receives an unexpected positional argument, it displays:
```
Usage: subterminator cancel [OPTIONS]
Try 'subterminator cancel --help' for help.

Error: Got unexpected extra argument (netflix)
```

**Migration Hint** (added via custom error callback or epilog):
We add a hint in the command help and README:
```
Note: As of v2.0, use --service flag or interactive mode.
  Old: subterminator cancel netflix
  New: subterminator cancel --service netflix
       subterminator cancel  (interactive)
```

**SUPPORTED_SERVICES Removal:**
The `SUPPORTED_SERVICES = ["netflix"]` list in main.py is **removed** and replaced with registry lookups:
```python
# OLD
if service.lower() not in SUPPORTED_SERVICES:
    ...

# NEW
from subterminator.services.registry import get_service_by_id
service_info = get_service_by_id(service)
if service_info is None:
    ...
```

### 10.5 Exit Code Reconciliation

**Spec vs Design:**
The spec defines exit codes 0, 2, 3. The design extends this to match existing code behavior:

| Code | Spec | Design | Current Code | Resolution |
|------|------|--------|--------------|------------|
| 0 | Success | SUCCESS | Yes (line 171) | Keep |
| 1 | - | FAILURE | Yes (line 177) | Keep (existing) |
| 2 | User cancelled | CANCELLED | Yes (line 174) | Keep |
| 3 | Invalid args | INVALID_ARGS | Yes (line 92) | Keep |
| 4 | - | CONFIG_ERROR | Yes (line 185) | Keep (existing) |

**Resolution:** Design is authoritative. Exit codes 1 and 4 exist in current code and are preserved. Spec should be updated to include all exit codes.

### 10.6 Non-TTY Fallback Behavior

**Decision Flow:**
```
cancel() called
  │
  ├─ --service provided? ─── YES ──→ Use that service (skip interactive)
  │
  NO
  │
  ├─ is_interactive()? ─── YES ──→ Show menu
  │
  NO (non-TTY or env vars set)
  │
  └─→ Error: "--service required in non-interactive mode"
      Exit code 3
```

**is_interactive() Precedence:**
```python
def is_interactive(no_input_flag: bool = False) -> bool:
    # Flag takes highest precedence
    if no_input_flag:
        return False

    # Env vars override TTY detection
    if os.environ.get("SUBTERMINATOR_NO_PROMPTS"):
        return False
    if os.environ.get("CI"):
        return False

    # TTY detection as fallback
    return sys.stdin.isatty() and sys.stdout.isatty()
```

### 10.7 questionary Dependency Addition

**pyproject.toml Change:**
```toml
[project]
dependencies = [
    "typer[all]>=0.9.0",
    "questionary>=2.0.0",  # NEW
    # ... other deps
]
```

**Compatibility Notes:**
- questionary 2.0+ requires prompt_toolkit 3.0+
- typer[all] already includes prompt_toolkit 3.0+
- No version conflicts expected

### 10.8 ServiceInfo ID Validation

**Approach:** Convention-based, not runtime-enforced.

**Rationale:**
- Services are developer-defined in code, not user input
- Static list is validated by code review
- Runtime validation adds complexity for no user benefit

**Documentation Constraint:**
```python
SERVICE_REGISTRY = [
    # ID pattern: ^[a-z][a-z0-9-]*$ (lowercase, alphanumeric with hyphens)
    ServiceInfo("netflix", ...),  # Valid
    # ServiceInfo("Netflix", ...),  # Invalid - uppercase
    # ServiceInfo("123", ...),  # Invalid - starts with number
]
```

### 10.9 Disabled Menu Items (questionary)

**questionary Native Support:**
```python
from questionary import Choice

choices = [
    Choice(title="Netflix - Video streaming", value="netflix"),
    Choice(
        title="Spotify - Music streaming (coming soon)",
        value="spotify",
        disabled="Not yet available"  # Shows greyed out, not selectable
    ),
]
```

**Visual Rendering:**
```
❯ Netflix - Video streaming
  Spotify - Music streaming (coming soon)  (disabled: Not yet available)
```

### 10.10 Accessibility Module Justification

**Decision:** Keep as separate file.

**Rationale:**
1. **Testability:** Easy to mock env vars in isolation
2. **Single Responsibility:** Color/animation logic separate from prompts
3. **Reuse:** Can be used by output.py for consistent styling
4. **Size:** 3 functions now, may grow (e.g., screen reader detection)

The module is small but purposeful. It does not warrant merging.

### 10.11 Iteration 2 Clarifications

**requires_api_key Field:**
The spec's `requires_api_key` field is intentionally omitted from the design. It was marked "Reserved for future use" and no current functionality depends on it. Adding unused fields is over-engineering. It can be added when a concrete use case arises.

**select_service() Exception Handling:**
Clarification: The function truly never raises to the caller. The "re-raised as RuntimeError" was a draft note. Final behavior:
- Returns `str` on selection
- Returns `None` on Ctrl+C
- Logs and returns `None` on any unexpected questionary error (defensive)

**Migration Hint Implementation:**
The migration hint is provided via:
1. Command epilog (shown in `--help` output)
2. README update with migration guide
3. CHANGELOG entry

We do NOT attempt to intercept Typer's internal error messages. The user sees Typer's standard "Got unexpected extra argument" error, and discovers the new syntax via `--help` or docs.

**Help Output Display:**
Help text is printed inline (terminal not cleared). User sees help output above the re-displayed menu. This is standard behavior for terminal prompts.
