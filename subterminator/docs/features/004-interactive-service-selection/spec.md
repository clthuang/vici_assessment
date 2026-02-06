# Specification: Interactive Service Selection CLI

**Feature:** 004-interactive-service-selection
**Status:** Draft
**Created:** 2026-02-04
**PRD Reference:** prd.md

---

## 1. Overview

This specification defines the implementation requirements for replacing the explicit service argument syntax (`subterminator cancel netflix`) with an interactive menu-based selection system.

---

## 2. Functional Requirements

### FR-1: Interactive Service Menu

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Running `subterminator cancel` without arguments SHALL display an interactive menu | Must |
| FR-1.2 | Menu SHALL list all registered services with name and description | Must |
| FR-1.3 | Available services SHALL be selectable via arrow keys | Must |
| FR-1.4 | Enter key SHALL confirm selection | Must |
| FR-1.5 | Unavailable services SHALL be displayed as disabled with "(coming soon)" suffix | Must |
| FR-1.6 | Ctrl+C SHALL cancel the menu and exit with code 2 | Must |
| FR-1.7 | Menu SHALL include a Help option that displays service details | Should |

### FR-2: Non-Interactive Mode

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | `--service` / `-s` flag SHALL bypass interactive menu | Must |
| FR-2.2 | `--no-input` flag SHALL disable all prompts | Must |
| FR-2.3 | `SUBTERMINATOR_NO_PROMPTS=1` environment variable SHALL disable prompts | Must |
| FR-2.4 | `CI=1` environment variable SHALL trigger non-interactive mode | Must |
| FR-2.5 | Non-interactive mode without `--service` SHALL error with exit code 3 | Must |

### FR-3: Service Validation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Unknown service names SHALL produce clear error message | Must |
| FR-3.2 | Error message SHALL list available services | Must |
| FR-3.3 | Fuzzy match suggestions SHALL be shown for typos (cutoff 0.6) | Should |
| FR-3.4 | Unavailable (coming soon) services SHALL error in non-interactive mode | Must |

### FR-4: Accessibility

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | `--plain` flag SHALL disable colors and animations | Must |
| FR-4.2 | `NO_COLOR` environment variable SHALL disable colors | Must |
| FR-4.3 | `TERM=dumb` SHALL disable colors | Should |
| FR-4.4 | Menu SHALL degrade gracefully in non-TTY environments | Must |

---

## 3. Non-Functional Requirements

### NFR-1: Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1.1 | Menu display time | < 100ms |
| NFR-1.2 | Service validation time | < 50ms |

### NFR-2: Compatibility

| ID | Requirement |
|----|-------------|
| NFR-2.1 | Python 3.10+ support |
| NFR-2.2 | Works on macOS, Linux, Windows terminals |
| NFR-2.3 | Compatible with common terminal emulators (iTerm2, Terminal.app, Windows Terminal, GNOME Terminal) |

---

## 4. Data Structures

### 4.1 ServiceInfo

```python
@dataclass
class ServiceInfo:
    id: str                    # Unique identifier, e.g., "netflix"
    name: str                  # Display name, e.g., "Netflix"
    description: str           # Brief description
    available: bool = True     # False for "coming soon"
```

Note: The `requires_api_key` field was originally planned but deferred per YAGNI principle.
It can be added when a concrete use case arises.

### 4.2 Service Registry

The service registry is a static list of `ServiceInfo` objects defined at module level. Initial services:

| ID | Name | Description | Available |
|----|------|-------------|-----------|
| netflix | Netflix | Video streaming service | Yes |
| spotify | Spotify | Music streaming service | No |
| hulu | Hulu | TV and movie streaming | No |
| disney | Disney+ | Disney streaming service | No |

---

## 5. Interface Contracts

### 5.1 CLI Interface

```
subterminator cancel [OPTIONS]

Options:
  -s, --service TEXT    Service to cancel (bypasses interactive menu)
  -n, --dry-run         Run without making actual changes
  --no-input            Disable all interactive prompts
  --plain               Disable colors and animations
  --help                Show this message and exit
```

### 5.2 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operation failed (cancellation error) - preserved from existing code |
| 2 | User cancelled (Ctrl+C or menu cancellation) |
| 3 | Invalid arguments (unknown service, missing --service in non-interactive) |
| 4 | Configuration error - preserved from existing code |

### 5.3 Environment Variables

| Variable | Effect |
|----------|--------|
| `SUBTERMINATOR_NO_PROMPTS=1` | Disable interactive prompts |
| `NO_COLOR=1` | Disable colors |
| `CI=1` | Trigger non-interactive mode |
| `TERM=dumb` | Disable colors |
| `SUBTERMINATOR_PLAIN=1` | Disable colors and animations |

---

## 6. Acceptance Criteria

### AC-1: Interactive Mode Default

**Given** a TTY terminal without `--service` flag
**When** user runs `subterminator cancel`
**Then** an interactive menu is displayed with available services

### AC-2: Menu Navigation

**Given** the interactive menu is displayed
**When** user presses arrow keys
**Then** selection indicator moves between selectable services

### AC-3: Service Selection

**Given** the interactive menu with a service highlighted
**When** user presses Enter
**Then** the selected service is used for the cancellation flow

### AC-4: Disabled Services

**Given** the interactive menu is displayed
**When** viewing an unavailable service
**Then** it appears disabled and cannot be selected

### AC-5: Menu Cancellation

**Given** the interactive menu is displayed
**When** user presses Ctrl+C
**Then** program exits with code 2 and message "Cancelled."

### AC-6: Non-Interactive with Service

**Given** the `--service netflix` flag
**When** user runs `subterminator cancel --service netflix`
**Then** no interactive menu is shown and netflix is used directly

### AC-7: Non-Interactive Missing Service

**Given** a non-TTY environment or `--no-input` flag
**When** user runs `subterminator cancel` without `--service`
**Then** error is shown with exit code 3

### AC-8: Unknown Service Error

**Given** the `--service netflixx` flag (typo)
**When** user runs the command
**Then** error shows "Unknown service 'netflixx'" with suggestion "Did you mean: netflix?"

### AC-9: Accessibility Mode

**Given** `NO_COLOR=1` environment variable
**When** user runs `subterminator cancel`
**Then** menu displays without colors or styling

### AC-10: Help Option

**Given** the interactive menu is displayed
**When** user selects "Help"
**Then** service details are printed and menu is re-displayed

---

## 7. Dependencies

### 7.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| questionary | >=2.0.0 | Interactive terminal prompts |

### 7.2 Existing Dependencies

| Package | Purpose |
|---------|---------|
| typer | CLI framework (already installed) |
| rich | Terminal styling (via typer[all]) |

---

## 8. File Structure

```
src/subterminator/
├── cli/
│   ├── main.py              # Modified: cancel command
│   ├── prompts.py           # New: interactive menu logic
│   └── accessibility.py     # New: accessibility utilities
└── services/
    └── registry.py          # New: service registry
```

---

## 9. Scope Boundaries

### In Scope

- Interactive service selection menu
- Non-interactive `--service` flag
- Service registry with metadata
- Accessibility modes (plain, no-color)
- Error messages with fuzzy suggestions
- Exit code standardization

### Out of Scope

- Fuzzy search within menu (deferred)
- Service icons/emojis
- Remember last selected service
- `cancel-services` command alias
- Service count display in menu

---

## 10. Breaking Changes

The old positional argument syntax is removed:

```bash
# No longer works
subterminator cancel netflix

# Must use
subterminator cancel --service netflix
# Or interactive
subterminator cancel
```

This requires a major version bump (v2.0).

---

## 11. Open Questions

1. Should the menu show service count ("3 of 10 services available")? - Deferred to future enhancement
