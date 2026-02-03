# Implementation Plan: Interactive Service Selection CLI

**Feature:** 004-interactive-service-selection
**Status:** Draft
**Created:** 2026-02-04
**Design Reference:** design.md

---

## 1. Implementation Overview

This plan breaks down the implementation into ordered steps with dependencies.
Each step is designed to be independently testable and reviewable.

**Total Steps:** 7
**Approach:** TDD (RED-GREEN-REFACTOR)
- Write failing test(s) first (RED)
- Write minimal implementation to pass (GREEN)
- Clean up code (REFACTOR)

---

## 2. Dependency Graph

```
Step 1: Add questionary dependency
    │
    ├──────────────────────────────────────────────┐
    ▼                                              ▼
Step 2: Create registry.py              Step 3: Create accessibility.py
    │          (PARALLEL - no interdependency)     │
    └──────────────────┬───────────────────────────┘
                       │
                       ▼
             Step 4: Create prompts.py
                       │  (depends on registry + accessibility)
                       ▼
             Step 5: Modify main.py
                       │  (depends on all above)
                       ▼
             Step 6: Update existing tests
                       │
                       ▼
             Step 7: Update documentation
```

**Note:** Steps 2 and 3 can be implemented in parallel as they have no interdependency.

---

## 3. Implementation Steps

### Step 1: Add questionary Dependency

**Goal:** Add questionary to project dependencies

**Files:**
- `pyproject.toml` (modify)

**Changes:**
```toml
dependencies = [
    "typer[all]>=0.9.0",
    "questionary>=2.0.0",  # ADD THIS LINE
    # ... existing deps
]
```

**questionary Features Used:**
- `questionary.select()` - for service menu with choices
- `questionary.Choice` - for menu items with disabled state
- `questionary.Separator` - for visual separator before Help
- `questionary.Style` - for custom styling (accessibility)

**Tests:** None (dependency only)

**Verification:**
- `pip install -e .` succeeds
- `python -c "import questionary; print(questionary.__version__)"` succeeds
- Verify prompt_toolkit compatibility: `python -c "from questionary import select"`

**Fallback if Dependency Conflict:**
If questionary conflicts with existing prompt_toolkit from typer:
1. Pin questionary to match typer's prompt_toolkit: `questionary>=2.0.0,<3.0`
2. If still conflicting, escalate to manual resolution

---

### Step 2: Create Service Registry Module

**Goal:** Implement ServiceInfo dataclass and registry functions

**Files:**
- `tests/unit/services/test_registry.py` (create FIRST - TDD)
- `src/subterminator/services/registry.py` (create after tests)

**TDD Sequence:**

**Phase 1: RED (Write Failing Tests)**
Create test_registry.py with all test cases below. Tests will fail (import error).

**Phase 2: GREEN (Minimal Implementation)**
1. Define `ServiceInfo` frozen dataclass
2. Define `SERVICE_REGISTRY` with initial services
3. Implement `get_all_services()` - returns sorted list
4. Implement `get_available_services()` - filters available=True
5. Implement `get_service_by_id(id)` - case-insensitive lookup
6. Implement `suggest_service(typo)` - uses `difflib.get_close_matches(typo, ids, n=1, cutoff=0.6)`

**Phase 3: REFACTOR**
Clean up any code duplication, add docstrings.

**Test Cases:**
```python
# test_registry.py
def test_get_all_services_returns_all():
    """All services returned including unavailable"""

def test_get_all_services_ordering():
    """Available first, then unavailable, alphabetical within each"""

def test_get_available_services_filters():
    """Only available=True services returned"""

def test_get_service_by_id_found():
    """Returns ServiceInfo for valid ID"""

def test_get_service_by_id_not_found():
    """Returns None for unknown ID"""

def test_get_service_by_id_case_insensitive():
    """'Netflix' and 'netflix' both work"""

def test_suggest_service_close_match():
    """'netflixx' suggests 'netflix' (uses difflib cutoff=0.6)"""

def test_suggest_service_no_match():
    """'xyz' returns None"""

def test_suggest_service_unavailable_not_suggested():
    """Unavailable services not suggested"""
```

**Dependencies:** Step 1 (questionary installed - though registry doesn't use it directly)

---

### Step 3: Create Accessibility Module

**Goal:** Implement accessibility utility functions

**Files:**
- `tests/unit/cli/test_accessibility.py` (create FIRST - TDD)
- `src/subterminator/cli/accessibility.py` (create after tests)

**TDD Sequence:**

**Phase 1: RED (Write Failing Tests)**
Create test_accessibility.py with all test cases. Tests will fail (import error).

**Phase 2: GREEN (Minimal Implementation)**
1. Implement `should_use_colors()` - checks NO_COLOR, TERM=dumb
2. Implement `should_use_animations()` - checks SUBTERMINATOR_PLAIN + inherits from colors
3. Implement `get_questionary_style()` - returns `questionary.Style` or None

**Phase 3: REFACTOR**
Add docstrings, ensure consistent env var checking pattern.

**Test Cases:**
```python
# test_accessibility.py
def test_should_use_colors_default():
    """True when no env vars set"""

def test_should_use_colors_no_color_set():
    """False when NO_COLOR is set (any value)"""

def test_should_use_colors_term_dumb():
    """False when TERM=dumb"""

def test_should_use_animations_default():
    """True when no env vars set"""

def test_should_use_animations_no_color():
    """False when NO_COLOR set (inherits from colors)"""

def test_should_use_animations_plain_set():
    """False when SUBTERMINATOR_PLAIN set"""

def test_get_questionary_style_with_colors():
    """Returns Style object when colors enabled"""

def test_get_questionary_style_no_colors():
    """Returns None when colors disabled"""
```

**Dependencies:** Step 1 (questionary needed for Style import)

---

### Step 4: Create Interactive Prompts Module

**Goal:** Implement TTY detection and menu display

**Files:**
- `tests/unit/cli/test_prompts.py` (create FIRST - TDD)
- `src/subterminator/cli/prompts.py` (create after tests)

**TDD Sequence:**

**Phase 1: RED (Write Failing Tests)**
Create test_prompts.py with all test cases. Tests will fail (import error).

**Phase 2: GREEN (Minimal Implementation)**
1. Implement `is_interactive(no_input_flag)` - checks flag, env vars, then TTY
2. Implement `show_services_help()` - print formatted help using registry
3. Implement `select_service(plain)` - questionary.select() menu with help loop

**Phase 3: REFACTOR**
Extract common patterns, add docstrings.

**Non-TTY Handling:**
- `is_interactive()` performs TTY detection via `sys.stdin.isatty() and sys.stdout.isatty()`
- If not interactive, main.py (Step 5) will require `--service` flag
- questionary is only called when `is_interactive()` returns True
- questionary's `.ask()` returns None on Ctrl+C (no exception handling needed)

**Test Cases:**
```python
# test_prompts.py
def test_is_interactive_tty():
    """True when both stdin/stdout are TTY"""

def test_is_interactive_no_input_flag():
    """False when no_input_flag=True (highest precedence)"""

def test_is_interactive_no_prompts_env():
    """False when SUBTERMINATOR_NO_PROMPTS set"""

def test_is_interactive_ci_env():
    """False when CI env var set"""

def test_is_interactive_not_tty():
    """False when stdin or stdout not TTY"""

def test_show_services_help_output(capsys):
    """Prints formatted service list with [Available]/[Coming Soon]"""

def test_select_service_returns_selection(mocker):
    """Returns service ID when user selects (mock questionary)"""

def test_select_service_returns_none_on_cancel(mocker):
    """Returns None when questionary.ask() returns None (Ctrl+C)"""

def test_select_service_help_loop(mocker):
    """Re-displays menu after __help__ selection (mock returns help then netflix)"""
```

**Dependencies:** Step 2 (registry), Step 3 (accessibility)

---

### Step 5: Modify Cancel Command

**Goal:** Update CLI to use interactive menu and new options

**Files:**
- `tests/integration/test_cli_cancel.py` (create/modify FIRST - TDD)
- `src/subterminator/cli/main.py` (modify after tests)

**CLI Interface Change:**
```
# OLD (v1.x)
subterminator cancel <service>      # positional required argument

# NEW (v2.0)
subterminator cancel                # interactive menu (default)
subterminator cancel --service X    # non-interactive
subterminator cancel -s X           # short form
```

The positional `service: str = typer.Argument(...)` is **removed entirely** and replaced with `service: str | None = typer.Option(None, "--service", "-s", ...)`.

**TDD Sequence:**

**Phase 1: RED (Write Failing Tests)**
Create/modify test_cli_cancel.py with new test cases.

**Phase 2: GREEN (Minimal Implementation)**
1. Remove positional `service` argument (line ~52-56 in current main.py)
2. Add `--service` / `-s` option (optional, default None)
3. Add `--no-input` flag
4. Add `--plain` flag
5. Remove `SUPPORTED_SERVICES = ["netflix"]` list (line ~26)
6. Add service resolution logic (before existing flow):
   ```python
   if service:
       # Validate via registry
       service_info = get_service_by_id(service)
       if not service_info:
           # Show error with fuzzy suggestion
       elif not service_info.available:
           # Show "not yet available" error
   elif is_interactive(no_input):
       # Show menu
       selected = select_service(plain=plain)
       if selected is None:
           # User cancelled
   else:
       # Error: --service required
   ```
7. Update error messages to spec formats
8. Add migration hint to command epilog

**Phase 3: REFACTOR**
Extract service resolution into helper function.

**Test Cases:**
```python
# test_cli_cancel.py (integration tests)
def test_cancel_interactive_mode(mocker):
    """Shows menu when no --service flag and TTY"""

def test_cancel_non_interactive_with_service():
    """Bypasses menu with --service flag"""

def test_cancel_non_interactive_missing_service():
    """Errors with exit 3 when no --service in non-TTY"""

def test_cancel_unknown_service():
    """Shows error with suggestion for typo"""

def test_cancel_unavailable_service():
    """Shows error for 'coming soon' services"""

def test_cancel_plain_flag():
    """Disables colors with --plain"""

def test_cancel_no_input_flag():
    """Forces non-interactive with --no-input"""

def test_cancel_user_cancels():
    """Exit code 2 when user presses Ctrl+C"""
```

**Rollback Strategy:**
Before modifying main.py:
1. `git add -A && git commit -m "WIP: before cancel command refactor"`
2. If implementation fails, `git reset --hard HEAD~1`

**Dependencies:** Steps 2, 3, 4 (all new modules)

---

### Step 6: Update Existing Tests

**Goal:** Fix any tests broken by CLI changes

**Files:**
- `tests/` (various - identify and fix)

**Expected Breakages (based on current codebase):**

1. **tests/unit/cli/test_main.py** (if exists)
   - Tests using `cancel netflix` positional syntax → change to `cancel --service netflix`
   - Tests mocking `SUPPORTED_SERVICES` → remove, use registry mocks

2. **tests/integration/test_*.py**
   - Any CLI invocations with positional service → add `--service` flag
   - Tests expecting specific error messages → update to new formats

3. **Fixtures using old syntax:**
   - `CliRunner.invoke(app, ["cancel", "netflix"])` → `["cancel", "--service", "netflix"]`

**Tasks:**
1. Run `pytest tests/ -v` to identify all failures
2. For each failure:
   - If positional syntax: add `--service` flag
   - If SUPPORTED_SERVICES: mock registry instead
   - If error message changed: update assertion
3. Run `pytest tests/` to verify all pass

**Verification:**
- `pytest tests/` passes with no regressions
- Coverage doesn't decrease

**Dependencies:** Step 5 (main.py changes)

---

### Step 7: Update Documentation

**Goal:** Document new CLI syntax and migration

**Files:**
- `README.md` (modify)
- `docs/` (if exists, modify)

**Tasks:**
1. Update command examples in README
2. Add migration section for v1.x → v2.0 users
3. Document new flags (--service, --no-input, --plain)
4. Document environment variables

**Example README Section:**
```markdown
## Usage

### Interactive Mode (default)
```bash
subterminator cancel
# Shows menu to select a service
```

### Non-Interactive Mode
```bash
subterminator cancel --service netflix
subterminator cancel -s netflix  # short form
```

### Migration from v1.x
The positional argument syntax has changed:
```bash
# Old (v1.x) - no longer works
subterminator cancel netflix

# New (v2.0)
subterminator cancel --service netflix
```
```

**Dependencies:** Step 5 (CLI finalized)

---

## 4. Risk Mitigations

| Risk | Step | Mitigation |
|------|------|------------|
| questionary compatibility | 1 | Verify import works before proceeding |
| Broken existing tests | 6 | Run tests after each step, fix immediately |
| TTY detection edge cases | 4 | Comprehensive test coverage with mocks |
| User migration confusion | 7 | Clear migration guide in docs |

---

## 5. Rollback Points

Each step is independently deployable:

- **After Step 2:** Registry exists but unused - safe
- **After Step 3:** Accessibility exists but unused - safe
- **After Step 4:** Prompts exists but unused - safe
- **After Step 5:** Breaking change - requires version bump
- **After Step 6:** Tests pass - stable
- **After Step 7:** Docs updated - complete

**Critical Point:** Step 5 is the breaking change.

**Step 5 Rollback Procedure:**
1. **Before starting Step 5:** Create git checkpoint
   ```bash
   git add -A && git commit -m "chore: checkpoint before cancel command refactor"
   ```
2. **If Step 5 fails mid-implementation:**
   ```bash
   git reset --hard HEAD~1  # Revert to checkpoint
   ```
3. **If Step 5 completes but tests fail:**
   - Fix tests in Step 6 (preferred)
   - Or rollback: `git reset --hard HEAD~1`

Ensure all Step 4 tests pass before starting Step 5.

---

## 6. Estimated Complexity

| Step | Complexity | New Lines | Files Changed |
|------|------------|-----------|---------------|
| 1 | Low | ~1 | 1 |
| 2 | Medium | ~80 | 2 |
| 3 | Low | ~40 | 2 |
| 4 | Medium | ~100 | 2 |
| 5 | High | ~50 | 2 |
| 6 | Medium | Variable | Variable |
| 7 | Low | ~30 | 1-2 |

---

## 7. Success Criteria

- [ ] All acceptance criteria from spec.md pass
- [ ] All tests pass (unit + integration)
- [ ] No regressions in existing functionality
- [ ] Documentation is complete and accurate
- [ ] Exit codes match spec (0, 1, 2, 3, 4)
