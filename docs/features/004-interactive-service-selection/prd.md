# PRD: Interactive Service Selection CLI

**Status:** Brainstorm
**Created:** 2026-02-03
**Author:** Claude (Brainstorm Agent)

---

## Problem Statement

The current CLI requires users to explicitly type the service name:

```bash
subterminator cancel netflix
```

This has several issues:

1. **Discovery** - Users must know supported services upfront
2. **Typos** - "netflixx" fails with unhelpful error
3. **Scalability** - As services grow, memorizing names becomes harder
4. **Onboarding** - New users don't know what's available

## Proposed Solution

Replace the explicit service argument with an **interactive menu**:

```bash
subterminator cancel-services
# or just
subterminator cancel
```

This opens an interactive prompt where users select from available services.

**Per user clarification:** This replaces the old command entirely - no backwards compatibility with `subterminator cancel netflix` syntax.

---

## User Stories

### US-1: Interactive Service Selection
**As a** new user
**I want** to see a list of cancellable services
**So that** I can discover what's supported and select easily

**Acceptance Criteria:**
- Running `subterminator cancel` shows interactive menu
- Services displayed with name and brief description
- Arrow keys to navigate, Enter to select
- Shows "Coming soon" for planned services (greyed out)

### US-2: Search/Filter Services
**As a** user with many services
**I want** to type to filter the service list
**So that** I can quickly find my target service

**Acceptance Criteria:**
- Typing characters filters the list
- Fuzzy matching (e.g., "net" matches "Netflix")
- Clear indication of filter being active

### US-3: Non-Interactive Mode for Scripts
**As a** developer automating cancellations
**I want** to specify the service without prompts
**So that** my scripts work in CI/CD

**Acceptance Criteria:**
- `--service netflix` flag bypasses interactive mode
- `--no-input` flag prevents any prompts
- Clear error if service not specified in non-interactive mode
- Environment variable `SUBTERMINATOR_NO_PROMPTS=1` also works

### US-4: Accessible Menu
**As a** user with a screen reader
**I want** the menu to work without animations
**So that** I can use the tool effectively

**Acceptance Criteria:**
- `--plain` flag disables colors and animations
- Respects `NO_COLOR` environment variable
- Static text output works with screen readers
- Menu degrades gracefully in non-TTY environments

---

## Technical Design

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     CLI Entry Point                       │
│                   (main.py:cancel)                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   ┌─────────────────┐    ┌─────────────────────────┐    │
│   │ Interactive     │    │ Non-Interactive         │    │
│   │ Mode            │    │ Mode                    │    │
│   │ (TTY detected)  │    │ (--service flag)        │    │
│   └────────┬────────┘    └────────────┬────────────┘    │
│            │                          │                  │
│            ▼                          │                  │
│   ┌─────────────────┐                 │                  │
│   │ Service Menu    │                 │                  │
│   │ (questionary)   │                 │                  │
│   └────────┬────────┘                 │                  │
│            │                          │                  │
│            └──────────┬───────────────┘                  │
│                       │                                  │
│                       ▼                                  │
│            ┌─────────────────┐                          │
│            │ Service Factory │                          │
│            │ (load service)  │                          │
│            └────────┬────────┘                          │
│                     │                                   │
│                     ▼                                   │
│            ┌─────────────────┐                          │
│            │ CancellationFlow│                          │
│            └─────────────────┘                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Add Questionary Dependency

```toml
# pyproject.toml
dependencies = [
    "questionary>=2.0",
    # ... existing deps
]
```

#### 2. Service Registry

```python
# src/subterminator/services/registry.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class ServiceInfo:
    """Metadata for a cancellable service."""
    id: str                    # "netflix"
    name: str                  # "Netflix"
    description: str           # "Video streaming service"
    available: bool = True     # False for "coming soon"
    requires_api_key: bool = False

# Registry of all services
SERVICE_REGISTRY: list[ServiceInfo] = [
    ServiceInfo(
        id="netflix",
        name="Netflix",
        description="Video streaming service",
        available=True,
    ),
    ServiceInfo(
        id="spotify",
        name="Spotify",
        description="Music streaming service",
        available=False,  # Coming soon
    ),
    ServiceInfo(
        id="hulu",
        name="Hulu",
        description="TV and movie streaming",
        available=False,
    ),
    ServiceInfo(
        id="disney",
        name="Disney+",
        description="Disney streaming service",
        available=False,
    ),
]

def get_available_services() -> list[ServiceInfo]:
    """Get services that are currently available."""
    return [s for s in SERVICE_REGISTRY if s.available]

def get_all_services() -> list[ServiceInfo]:
    """Get all services including coming soon."""
    return SERVICE_REGISTRY

def get_service_by_id(service_id: str) -> Optional[ServiceInfo]:
    """Look up service by ID."""
    for s in SERVICE_REGISTRY:
        if s.id == service_id:
            return s
    return None
```

#### 3. Interactive Menu

```python
# src/subterminator/cli/prompts.py

import sys
import os
import questionary
from questionary import Choice, Separator

from ..services.registry import get_all_services, ServiceInfo

def is_interactive() -> bool:
    """Check if we're in an interactive TTY."""
    if os.environ.get("SUBTERMINATOR_NO_PROMPTS"):
        return False
    if os.environ.get("CI"):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()

def select_service() -> str:
    """Show interactive service selection menu."""
    services = get_all_services()

    choices = []
    for service in services:
        if service.available:
            choices.append(Choice(
                title=f"{service.name} - {service.description}",
                value=service.id,
            ))
        else:
            # Greyed out "coming soon" services
            choices.append(Choice(
                title=f"{service.name} - {service.description} (coming soon)",
                value=service.id,
                disabled="Not yet available",
            ))

    # Add separator and help option
    choices.append(Separator())
    choices.append(Choice(
        title="Help - Show more information",
        value="__help__",
    ))

    # Loop instead of recursion to avoid stack overflow on repeated help
    while True:
        result = questionary.select(
            "Which subscription would you like to cancel?",
            choices=choices,
            use_indicator=True,
            use_shortcuts=True,
            style=get_questionary_style(),  # Apply accessibility styles
        ).ask()

        # None means Ctrl+C was pressed
        if result is None:
            return None

        if result == "__help__":
            show_services_help()
            continue  # Re-prompt

        return result

def show_services_help():
    """Display help information about services."""
    print("\n--- Supported Services ---\n")
    for service in get_all_services():
        status = "Available" if service.available else "Coming Soon"
        print(f"  {service.name}: {service.description} [{status}]")
    print()
```

#### 4. Updated CLI Command

```python
# src/subterminator/cli/main.py

import typer
from typing import Optional
from .prompts import is_interactive, select_service
from ..services.registry import get_service_by_id, get_available_services

app = typer.Typer()

@app.command()
def cancel(
    service: Optional[str] = typer.Option(
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
        help="Disable all interactive prompts",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Disable colors and animations (accessibility)",
    ),
    # ... other options
) -> None:
    """Cancel a subscription service."""

    # Determine service
    if service:
        # Non-interactive: validate provided service
        service_info = get_service_by_id(service)
        if not service_info:
            available = [s.id for s in get_available_services()]
            typer.echo(f"Error: Unknown service '{service}'")
            typer.echo(f"Available services: {', '.join(available)}")

            # Fuzzy suggestion using difflib
            from difflib import get_close_matches
            suggestions = get_close_matches(service, available, n=1, cutoff=0.6)
            if suggestions:
                typer.echo(f"Did you mean: {suggestions[0]}?")

            raise typer.Exit(3)
        if not service_info.available:
            typer.echo(f"Error: '{service}' is not yet available")
            raise typer.Exit(3)
        selected_service = service
    elif no_input or not is_interactive():
        # Non-interactive without service specified
        typer.echo("Error: --service required in non-interactive mode")
        typer.echo("Example: subterminator cancel --service netflix")
        raise typer.Exit(3)
    else:
        # Interactive mode: show menu
        selected_service = select_service()
        if not selected_service:
            typer.echo("Cancelled.")
            raise typer.Exit(2)

    # Continue with cancellation flow...
    typer.echo(f"Selected: {selected_service}")
    # ... rest of cancel logic
```

#### 5. Accessibility Support

```python
# src/subterminator/cli/accessibility.py

import os

def should_use_colors() -> bool:
    """Check if colors should be used."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return True

def should_use_animations() -> bool:
    """Check if animations/spinners should be used."""
    if os.environ.get("SUBTERMINATOR_PLAIN"):
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return True

# Apply to questionary
def get_questionary_style():
    """Get questionary style based on accessibility settings."""
    if not should_use_colors():
        return None  # Default monochrome

    from questionary import Style
    return Style([
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:green"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
    ])
```

### Command Examples

```bash
# Interactive mode (default)
subterminator cancel
# → Shows menu: Netflix, Spotify (disabled), ...

# Non-interactive with flag
subterminator cancel --service netflix

# Short form
subterminator cancel -s netflix

# Explicit non-interactive
subterminator cancel --service netflix --no-input

# Accessibility mode
subterminator cancel --plain
NO_COLOR=1 subterminator cancel

# Via environment
SUBTERMINATOR_NO_PROMPTS=1 subterminator cancel --service netflix
```

### Error Messages

```
# No service in non-interactive mode
$ subterminator cancel --no-input
Error: --service required in non-interactive mode
Example: subterminator cancel --service netflix

# Unknown service (with fuzzy suggestion)
$ subterminator cancel --service netflixx
Error: Unknown service 'netflixx'
Available services: netflix
Did you mean: netflix?

# Unavailable service
$ subterminator cancel --service spotify
Error: 'spotify' is not yet available
This service is coming soon. Currently available: netflix
```

---

## Migration Guide

### Breaking Change

The old syntax is **removed**:
```bash
# OLD (no longer works)
subterminator cancel netflix

# NEW
subterminator cancel                  # Interactive
subterminator cancel --service netflix  # Non-interactive
```

### Versioning Strategy

This is a **breaking change** requiring a **major version bump** (v1.x → v2.0).

**Deprecation Timeline:**
1. **v1.x (current):** Old syntax works, no changes
2. **v1.next:** Add new `--service` flag as alternative. Old syntax shows deprecation warning:
   ```
   DEPRECATED: 'subterminator cancel netflix' will be removed in v2.0
   Use: subterminator cancel --service netflix
   ```
3. **v2.0:** Remove old syntax, interactive mode is default

**Changelog Entry (for v2.0):**
```markdown
## Breaking Changes
- `subterminator cancel <service>` syntax removed
- Use `subterminator cancel --service <service>` for non-interactive mode
- Use `subterminator cancel` for interactive service selection menu
```

### User Migration

1. **Interactive users:** Just run `subterminator cancel` and use the menu
2. **Script users:** Update scripts to use `--service netflix` flag
3. **CI/CD:** Add `--no-input` to ensure no prompts

### User Discovery

Users will discover the change via:
1. **Deprecation warning** in v1.next (if they use old syntax)
2. **Clear error message** in v2.0 with migration hint
3. **CHANGELOG.md** entry
4. **README update** with new syntax

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `questionary` | `>=2.0` | Interactive terminal prompts |

### Already Available

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework |
| `rich` | Already installed via typer[all] |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Service discoverability | Manual docs lookup | Instant via menu |
| Typo errors | Common | Eliminated (menu selection) |
| New user onboarding | Read docs first | Self-explanatory |
| Script compatibility | Breaking | Supported via --service |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change | High | Clear migration guide, versioned release |
| Menu UX issues | Medium | Extensive testing, accessibility modes |
| questionary dependency | Low | Well-maintained, 1k+ stars |
| Non-TTY environments | Medium | Graceful degradation to --service requirement |

---

## Decisions (Resolved from Open Questions)

1. **Fuzzy search:** Not in v1. questionary.select doesn't have built-in fuzzy; would need InquirerPy. Keep simple for now.
2. **Service icons/emojis:** No. Accessibility concern, adds complexity, no clear benefit.
3. **Remember last selected:** No. Privacy concern, adds state management complexity.
4. **`cancel-services` alias:** No. One command is simpler. `cancel` is clear enough.

## Exit Codes (Documented)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | User cancelled (Ctrl+C or cancelled at menu) |
| 3 | Invalid arguments (unknown service, missing --service in non-interactive) |

## Open Questions (Remaining)

1. Should the menu show service count ("3 of 10 services available")?

---

## References

- [Questionary Documentation](https://questionary.readthedocs.io/)
- [CLI Guidelines - Prompting](https://clig.dev/#prompting)
- [Building Accessible GitHub CLI](https://github.blog/engineering/user-experience/building-a-more-accessible-github-cli/)
- [NO_COLOR Standard](https://no-color.org/)
