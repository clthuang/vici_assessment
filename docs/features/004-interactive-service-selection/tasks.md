# Tasks: Interactive Service Selection CLI

**Feature:** 004-interactive-service-selection
**Plan Reference:** plan.md
**Created:** 2026-02-04

---

## Task Overview

| Phase | Tasks | Parallel Groups |
|-------|-------|-----------------|
| 1. Dependencies | 3 | 0 |
| 2. Registry | 4 | 0 |
| 3. Accessibility | 3 | 0 |
| 4. Prompts | 4 | 0 |
| 5. Cancel Command | 5 | 0 |
| 6. Fix Tests | 2 | 0 |
| 7. Documentation | 2 | 0 |
| **Total** | **23** | - |

**Note:** Phases 2 and 3 can run in parallel (separate parallel groups).

---

## Phase 1: Add questionary Dependency

### Task 1.0: Add pytest-mock to dev dependencies

**Files:** `pyproject.toml`

**Actions:**
1. Open pyproject.toml
2. Find the `dev` group under `[dependency-groups]` section (line 25)
3. Add `"pytest-mock>=3.0",` after `"pytest-cov>=5.0",` (line 29)
4. Save file

**Done when:**
- [ ] `pytest-mock>=3.0` appears in dev dependencies

---

### Task 1.1: Add questionary to pyproject.toml

**Files:** `pyproject.toml`

**Actions:**
1. Open pyproject.toml
2. Find the `dependencies` array under the `[project]` section (starts at line 15)
3. Add `"questionary>=2.0.0",` to the dependencies array, inserting it after `"typer[all]>=0.21",` and before `"anthropic>=0.40",`
4. Save file

The final dependencies array should look like:
```toml
dependencies = [
    "playwright>=1.58",
    "playwright-stealth>=1.0",
    "python-statemachine>=2.5",
    "typer[all]>=0.21",
    "questionary>=2.0.0",  # NEW LINE
    "anthropic>=0.40",
    "pydantic>=2.0",
    "requests",
]
```

**Done when:**
- [ ] `questionary>=2.0.0` appears in dependencies array

**Blocked by:** Task 1.0

---

### Task 1.2: Verify questionary Installation

**Commands:**
```bash
# Ensure you're in the project virtual environment first
source .venv/bin/activate  # or appropriate activation for your shell

pip install -e .
python -c "import questionary; print(questionary.__version__)"
python -c "from questionary import select, Choice, Separator, Style"
```

**Done when:**
- [ ] All three commands succeed without errors

**Blocked by:** Task 1.1

---

## Phase 2: Create Service Registry (can run parallel with Phase 3)

### Task 2.1: Create registry test file with failing tests

**Files:** `tests/unit/services/test_registry.py`, `tests/unit/services/__init__.py`

**Actions:**
1. Create `tests/unit/services/` directory if needed
2. Create `tests/unit/services/__init__.py` (empty file for pytest discovery)
3. Create test_registry.py with 9 test functions using these exact assertions:

```python
from subterminator.services.registry import (
    ServiceInfo, get_all_services, get_available_services,
    get_service_by_id, suggest_service
)

def test_get_all_services_returns_all():
    """All 4 services returned including unavailable"""
    services = get_all_services()
    assert len(services) == 4
    assert all(isinstance(s, ServiceInfo) for s in services)

def test_get_all_services_ordering():
    """Available first, then unavailable, alphabetical within each"""
    services = get_all_services()
    ids = [s.id for s in services]
    # netflix (available) first, then disney, hulu, spotify (unavailable, alphabetical)
    assert ids == ["netflix", "disney", "hulu", "spotify"]

def test_get_available_services_filters():
    """Only available=True services returned"""
    services = get_available_services()
    assert len(services) == 1
    assert services[0].id == "netflix"
    assert all(s.available for s in services)

def test_get_service_by_id_found():
    """Returns ServiceInfo for valid ID"""
    service = get_service_by_id("netflix")
    assert service is not None
    assert service.id == "netflix"
    assert service.available is True

def test_get_service_by_id_not_found():
    """Returns None for unknown ID"""
    assert get_service_by_id("unknown") is None

def test_get_service_by_id_case_insensitive():
    """'Netflix' and 'netflix' both work"""
    assert get_service_by_id("Netflix") is not None
    assert get_service_by_id("NETFLIX") is not None
    assert get_service_by_id("netflix") is not None

def test_suggest_service_close_match():
    """'netflixx' suggests 'netflix' (uses difflib cutoff=0.6)"""
    suggestion = suggest_service("netflixx")
    assert suggestion == "netflix"

def test_suggest_service_no_match():
    """'xyz' returns None"""
    assert suggest_service("xyz") is None

def test_suggest_service_unavailable_not_suggested():
    """Unavailable services not suggested (suggest from available only)"""
    # 'spotifi' is close to 'spotify' but spotify is unavailable
    assert suggest_service("spotifi") is None
```

**Done when:**
- [ ] Directory `tests/unit/services/` exists with `__init__.py`
- [ ] Test file exists with 9 test functions
- [ ] `pytest tests/unit/services/test_registry.py` fails with ImportError (module not found)

**Blocked by:** Task 1.2

---

### Task 2.2: Implement ServiceInfo dataclass

**Files:** `src/subterminator/services/registry.py`

**Actions:**
1. Create registry.py
2. Define `ServiceInfo` frozen dataclass with fields: id (str), name (str), description (str), available (bool, default=True)
3. Define `SERVICE_REGISTRY` list with these exact 4 services:
   - `ServiceInfo(id="netflix", name="Netflix", description="Video streaming service", available=True)`
   - `ServiceInfo(id="disney", name="Disney+", description="Disney streaming service", available=False)`
   - `ServiceInfo(id="hulu", name="Hulu", description="TV and movie streaming", available=False)`
   - `ServiceInfo(id="spotify", name="Spotify", description="Music streaming service", available=False)`

**Done when:**
- [ ] `from subterminator.services.registry import ServiceInfo` works
- [ ] ServiceInfo has all 4 fields
- [ ] SERVICE_REGISTRY has exactly 4 services with IDs: netflix, disney, hulu, spotify

**Blocked by:** Task 2.1

---

### Task 2.3: Implement registry functions

**Files:** `src/subterminator/services/registry.py`

**Actions:**
1. Implement `get_all_services()` - sorted, available first
2. Implement `get_available_services()` - filter available=True
3. Implement `get_service_by_id(service_id)` - case-insensitive lookup
4. Implement `suggest_service(typo)` - difflib.get_close_matches with cutoff=0.6

**Done when:**
- [ ] All 4 functions exist and are importable
- [ ] `pytest tests/unit/services/test_registry.py` passes (all 9 tests)

**Blocked by:** Task 2.2

---

### Task 2.4: Add registry to services __init__.py

**Files:** `src/subterminator/services/__init__.py`

**Actions:**
1. Add import at top of file (after existing imports):
   ```python
   from subterminator.services.registry import (
       ServiceInfo,
       get_all_services,
       get_available_services,
       get_service_by_id,
       suggest_service,
   )
   ```
2. Add to `__all__` list (do not remove existing exports):
   ```python
   __all__ = [
       # ... existing exports ...
       "ServiceInfo",
       "get_all_services",
       "get_available_services",
       "get_service_by_id",
       "suggest_service",
   ]
   ```

**Done when:**
- [ ] `from subterminator.services import ServiceInfo` works
- [ ] Existing exports still work: `from subterminator.services import NetflixService`

**Blocked by:** Task 2.3

---

## Phase 3: Create Accessibility Module (can run parallel with Phase 2)

### Task 3.1: Create accessibility test file with failing tests

**Files:** `tests/unit/cli/test_accessibility.py`, `tests/unit/cli/__init__.py`

**Actions:**
1. Create `tests/unit/cli/` directory if needed
2. Create `tests/unit/cli/__init__.py` (empty file for pytest discovery)
3. Create test_accessibility.py with 8 test functions using these exact assertions:

```python
import pytest
from questionary import Style
from subterminator.cli.accessibility import (
    should_use_colors, should_use_animations, get_questionary_style
)

def test_should_use_colors_default(monkeypatch):
    """True when no env vars set"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    assert should_use_colors() is True

def test_should_use_colors_no_color_set(monkeypatch):
    """False when NO_COLOR is set (any value)"""
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_use_colors() is False
    monkeypatch.setenv("NO_COLOR", "")  # Empty string also counts
    assert should_use_colors() is False

def test_should_use_colors_term_dumb(monkeypatch):
    """False when TERM=dumb"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert should_use_colors() is False

def test_should_use_animations_default(monkeypatch):
    """True when no env vars set"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("SUBTERMINATOR_PLAIN", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    assert should_use_animations() is True

def test_should_use_animations_no_color(monkeypatch):
    """False when NO_COLOR set (inherits from colors)"""
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_use_animations() is False

def test_should_use_animations_plain_set(monkeypatch):
    """False when SUBTERMINATOR_PLAIN set"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("SUBTERMINATOR_PLAIN", "1")
    assert should_use_animations() is False

def test_get_questionary_style_with_colors(monkeypatch):
    """Returns Style object when colors enabled"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    style = get_questionary_style()
    assert style is not None
    assert isinstance(style, Style)

def test_get_questionary_style_no_colors(monkeypatch):
    """Returns None when colors disabled"""
    monkeypatch.setenv("NO_COLOR", "1")
    assert get_questionary_style() is None
```

**Done when:**
- [ ] Directory `tests/unit/cli/` exists with `__init__.py`
- [ ] Test file exists with 8 test functions
- [ ] `pytest tests/unit/cli/test_accessibility.py` fails with ImportError (module not found)

**Blocked by:** Task 1.2

---

### Task 3.2: Implement accessibility functions

**Files:** `src/subterminator/cli/accessibility.py`

**Actions:**
1. Create accessibility.py
2. Implement `should_use_colors()`:
   - Return False if `NO_COLOR` env var exists (any value including empty)
   - Return False if `TERM` == "dumb"
   - Return True otherwise
3. Implement `should_use_animations()`:
   - Return False if `should_use_colors()` returns False
   - Return False if `SUBTERMINATOR_PLAIN` env var exists
   - Return True otherwise
4. Implement `get_questionary_style()`:
   - If `should_use_colors()` returns False, return None
   - Otherwise return `questionary.Style([("answer", "fg:cyan"), ("question", "fg:cyan bold"), ("pointer", "fg:green bold")])`

**Done when:**
- [ ] All 3 functions exist and are importable
- [ ] `pytest tests/unit/cli/test_accessibility.py` passes (all 8 tests)

**Blocked by:** Task 3.1

---

### Task 3.3: Verify accessibility module imports

**Files:** `src/subterminator/cli/accessibility.py`

**Actions:**
1. Verify direct module import works (no __init__.py changes needed for this module)

**Done when:**
- [ ] `from subterminator.cli.accessibility import should_use_colors` works
- [ ] `from subterminator.cli.accessibility import should_use_animations` works
- [ ] `from subterminator.cli.accessibility import get_questionary_style` works

**Note:** Direct module imports are intentional. No __init__.py changes required.

**Blocked by:** Task 3.2

---

## Phase 4: Create Prompts Module

### Task 4.1: Create prompts test file with failing tests

**Files:** `tests/unit/cli/test_prompts.py`

**Actions:**
1. Create test_prompts.py with 9 test functions using these patterns:

```python
import pytest
from unittest.mock import MagicMock

def test_is_interactive_tty(mocker):
    """True when both stdin/stdout are TTY"""
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("sys.stdout.isatty", return_value=True)
    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is True

def test_is_interactive_no_input_flag(mocker):
    """False when no_input_flag=True (highest precedence)"""
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("sys.stdout.isatty", return_value=True)
    from subterminator.cli.prompts import is_interactive
    assert is_interactive(no_input_flag=True) is False

def test_is_interactive_no_prompts_env(mocker, monkeypatch):
    """False when SUBTERMINATOR_NO_PROMPTS set"""
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("sys.stdout.isatty", return_value=True)
    monkeypatch.setenv("SUBTERMINATOR_NO_PROMPTS", "1")
    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is False

def test_is_interactive_ci_env(mocker, monkeypatch):
    """False when CI env var set"""
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("sys.stdout.isatty", return_value=True)
    monkeypatch.setenv("CI", "1")
    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is False

def test_is_interactive_not_tty(mocker):
    """False when stdin or stdout not TTY"""
    mocker.patch("sys.stdin.isatty", return_value=False)
    mocker.patch("sys.stdout.isatty", return_value=True)
    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is False

def test_show_services_help_output(capsys):
    """Prints formatted service list with [Available]/[Coming Soon]"""
    from subterminator.cli.prompts import show_services_help
    show_services_help()
    captured = capsys.readouterr()
    assert "Netflix" in captured.out
    assert "[Available]" in captured.out
    assert "[Coming Soon]" in captured.out

def test_select_service_returns_selection(mocker):
    """Returns service ID when user selects (mock questionary)"""
    mock_select = mocker.patch("subterminator.cli.prompts.questionary.select")
    mock_select.return_value.ask.return_value = "netflix"
    from subterminator.cli.prompts import select_service
    assert select_service() == "netflix"

def test_select_service_returns_none_on_cancel(mocker):
    """Returns None when questionary.ask() returns None (Ctrl+C)"""
    mock_select = mocker.patch("subterminator.cli.prompts.questionary.select")
    mock_select.return_value.ask.return_value = None
    from subterminator.cli.prompts import select_service
    assert select_service() is None

def test_select_service_help_loop(mocker, capsys):
    """Re-displays menu after __help__ selection"""
    mock_select = mocker.patch("subterminator.cli.prompts.questionary.select")
    # First call returns __help__, second call returns netflix
    mock_select.return_value.ask.side_effect = ["__help__", "netflix"]
    from subterminator.cli.prompts import select_service
    result = select_service()
    assert result == "netflix"
    # Verify help was shown
    captured = capsys.readouterr()
    assert "Netflix" in captured.out
```

**Notes:**
- These tests use pytest-mock's `mocker` fixture (added in Task 1.0)
- The import-inside-function pattern (`from subterminator.cli.prompts import ...`) is intentional to ensure fresh module state after patching env vars and sys attributes

**Done when:**
- [ ] Test file exists with 9 test functions
- [ ] `pytest tests/unit/cli/test_prompts.py` fails with ImportError

**Blocked by:** Task 1.0, Task 2.4, Task 3.3

---

### Task 4.2: Implement is_interactive function

**Files:** `src/subterminator/cli/prompts.py`

**Actions:**
1. Create prompts.py
2. Implement `is_interactive(no_input_flag=False)`:
   - Return False if no_input_flag
   - Return False if SUBTERMINATOR_NO_PROMPTS env var
   - Return False if CI env var
   - Return stdin.isatty() and stdout.isatty()

**Done when:**
- [ ] is_interactive function exists
- [ ] 5 is_interactive tests pass

**Blocked by:** Task 4.1

---

### Task 4.3: Implement show_services_help function

**Files:** `src/subterminator/cli/prompts.py`

**Actions:**
1. Implement `show_services_help()`:
   - Print "--- Supported Services ---"
   - For each service, print name, description, [Available]/[Coming Soon]

**Done when:**
- [ ] show_services_help function exists
- [ ] test_show_services_help_output passes

**Blocked by:** Task 4.2

---

### Task 4.4: Implement select_service function

**Files:** `src/subterminator/cli/prompts.py`

**Actions:**
1. Implement `select_service(plain=False)`:
   - Build choices list from registry (disabled for unavailable)
   - Add Separator and Help option
   - Loop: call questionary.select, handle __help__ by calling show_services_help
   - Return service ID or None (Ctrl+C)

**Done when:**
- [ ] select_service function exists
- [ ] All 9 prompts tests pass

**Blocked by:** Task 4.3

---

## Phase 5: Modify Cancel Command

### Task 5.1: Create git checkpoint

**Commands:**
```bash
# First verify working directory state
git status

# If clean or only expected changes, create checkpoint
git add -A && git commit -m "chore: checkpoint before cancel command refactor"
```

**Done when:**
- [ ] Working directory state verified (no unexpected files)
- [ ] Commit created with checkpoint message

**Blocked by:** Task 4.4

---

### Task 5.2: Create cancel command tests

**Files:** `tests/integration/test_cli_cancel.py`

**Note:** These are unit-level integration tests that mock external dependencies (questionary) but test the CLI entry point integration. Use CliRunner with questionary mocked.

**Actions:**
1. Create test_cli_cancel.py with 8 test functions:

```python
"""Integration tests for cancel command with interactive service selection."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from subterminator.cli.main import app

runner = CliRunner()


class TestCancelInteractiveMode:
    """Tests for interactive mode behavior."""

    @patch("subterminator.cli.main.is_interactive")
    @patch("subterminator.cli.main.select_service")
    def test_cancel_interactive_mode(
        self, mock_select: MagicMock, mock_interactive: MagicMock
    ) -> None:
        """Shows menu when no --service flag and TTY."""
        mock_interactive.return_value = True
        mock_select.return_value = "netflix"
        # Will fail at cancellation flow, but that's expected
        result = runner.invoke(app, ["cancel"])
        mock_select.assert_called_once()

    @patch("subterminator.cli.main.is_interactive")
    @patch("subterminator.cli.main.select_service")
    def test_cancel_user_cancels(
        self, mock_select: MagicMock, mock_interactive: MagicMock
    ) -> None:
        """Exit code 2 when user presses Ctrl+C."""
        mock_interactive.return_value = True
        mock_select.return_value = None  # Ctrl+C
        result = runner.invoke(app, ["cancel"])
        assert result.exit_code == 2
        assert "cancelled" in result.output.lower()


class TestCancelNonInteractiveMode:
    """Tests for non-interactive mode behavior."""

    @patch("subterminator.cli.main.is_interactive")
    def test_cancel_non_interactive_with_service(
        self, mock_interactive: MagicMock
    ) -> None:
        """Bypasses menu with --service flag."""
        mock_interactive.return_value = False
        # Will fail at cancellation flow but service should be accepted
        result = runner.invoke(app, ["cancel", "--service", "netflix"])
        # Should NOT fail with "service required" error
        assert "--service required" not in result.output

    @patch("subterminator.cli.main.is_interactive")
    def test_cancel_non_interactive_missing_service(
        self, mock_interactive: MagicMock
    ) -> None:
        """Errors with exit 3 when no --service in non-TTY."""
        mock_interactive.return_value = False
        result = runner.invoke(app, ["cancel"])
        assert result.exit_code == 3
        assert "--service required" in result.output.lower()


class TestCancelServiceValidation:
    """Tests for service name validation."""

    def test_cancel_unknown_service(self) -> None:
        """Shows error with suggestion for typo."""
        result = runner.invoke(app, ["cancel", "--service", "netflixx"])
        assert result.exit_code == 3
        assert "unknown service" in result.output.lower()
        assert "did you mean" in result.output.lower()
        assert "netflix" in result.output.lower()

    def test_cancel_unavailable_service(self) -> None:
        """Shows error for 'coming soon' services."""
        result = runner.invoke(app, ["cancel", "--service", "spotify"])
        assert result.exit_code == 3
        assert "not yet available" in result.output.lower()


class TestCancelFlags:
    """Tests for command flags."""

    @patch("subterminator.cli.main.is_interactive")
    @patch("subterminator.cli.main.select_service")
    def test_cancel_plain_flag(
        self, mock_select: MagicMock, mock_interactive: MagicMock
    ) -> None:
        """Passes --plain to select_service."""
        mock_interactive.return_value = True
        mock_select.return_value = "netflix"
        result = runner.invoke(app, ["cancel", "--plain"])
        mock_select.assert_called_once_with(plain=True)

    @patch("subterminator.cli.main.is_interactive")
    def test_cancel_no_input_flag(self, mock_interactive: MagicMock) -> None:
        """Forces non-interactive with --no-input."""
        # Even if is_interactive would return True, --no-input should override
        result = runner.invoke(app, ["cancel", "--no-input"])
        assert result.exit_code == 3
        assert "--service required" in result.output.lower()
```

**Done when:**
- [ ] Test file exists with 8 test functions
- [ ] Tests fail (old CLI interface doesn't support --service flag)

**Blocked by:** Task 5.1

---

### Task 5.3: Remove positional argument, add options

**Files:** `src/subterminator/cli/main.py`

**Landmark verification (do this first):**
Before editing, verify these landmarks exist in main.py:
1. `SUPPORTED_SERVICES = ["netflix"]` on line 26
2. `service: str = typer.Argument(` starting on line 53
3. `if service.lower() not in SUPPORTED_SERVICES:` starting on line 89
4. Function signature ends with `) -> None:` on line 86

If line numbers differ from above, adjust the following steps accordingly.

**Actions:**
1. Delete line 26: `SUPPORTED_SERVICES = ["netflix"]` (and the blank line after it)

2. Delete lines 53-56 (the positional service argument):
   ```python
   service: str = typer.Argument(
       ...,
       help="Service to cancel (currently only 'netflix' supported)",
   ),
   ```

3. Delete lines 88-92 (old validation block inside cancel() function):
   ```python
   # T15.5: Service validation
   if service.lower() not in SUPPORTED_SERVICES:
       print(f"\033[31mError: Unsupported service '{service}'.\033[0m")
       print(f"Supported services: {', '.join(SUPPORTED_SERVICES)}")
       raise typer.Exit(code=3)  # Invalid args
   ```

4. Add new options inside the function signature (before the closing `)`). Insert after `output_dir` parameter and before `) -> None:`:
   ```python
       output_dir: Path | None = typer.Option(
           None,
           "--output-dir",
           "-o",
           help="Directory for session artifacts (screenshots, logs)",
       ),
       service: str | None = typer.Option(
           None,
           "--service",
           "-s",
           help="Service to cancel (bypasses interactive menu)",
       ),
       no_input: bool = typer.Option(
           False,
           "--no-input",
           help="Disable all interactive prompts",
       ),
       plain: bool = typer.Option(
           False,
           "--plain",
           help="Disable colors and animations",
       ),
   ) -> None:
   ```

**Done when:**
- [ ] `SUPPORTED_SERVICES` constant removed
- [ ] Old positional argument removed
- [ ] Old service validation block removed
- [ ] `subterminator cancel --help` shows new options (--service, --no-input, --plain)
- [ ] Old positional syntax `subterminator cancel netflix` errors with "Got unexpected extra argument"

**Blocked by:** Task 5.2

---

### Task 5.4: Implement service resolution logic

**Files:** `src/subterminator/cli/main.py`

**Context after Task 5.3:** After Task 5.3 removes the old validation block (lines 88-92), there will be a gap between the docstring (line 87) and the ToS disclaimer. The service resolution code fills this gap.

**Actions:**
1. Add imports at top of file (after the existing imports, around line 17-18):
   ```python
   from subterminator.services.registry import get_service_by_id, suggest_service, get_available_services
   from subterminator.cli.prompts import is_interactive, select_service
   ```

2. The old validation block (lines 88-92) was deleted in Task 5.3. In its place, add the service resolution logic. This goes immediately after the docstring `"""Cancel a subscription service."""` and before the ToS disclaimer:
   ```python
   """Cancel a subscription service."""
   # Service resolution (replaces old SUPPORTED_SERVICES validation)
   if service:
       service_info = get_service_by_id(service)
       if not service_info:
           suggestion = suggest_service(service)
           available = [s.id for s in get_available_services()]
           typer.echo(f"Error: Unknown service '{service}'.")
           if suggestion:
               typer.echo(f"Did you mean: {suggestion}?")
           typer.echo(f"Available services: {', '.join(available)}")
           raise typer.Exit(code=3)
       elif not service_info.available:
           typer.echo(f"Error: Service '{service}' is not yet available.")
           typer.echo("This service is coming soon.")
           raise typer.Exit(code=3)
       selected_service = service_info.id  # Use normalized ID from registry
   elif is_interactive(no_input):
       selected_service = select_service(plain=plain)
       if selected_service is None:
           typer.echo("Cancelled.")
           raise typer.Exit(code=2)
   else:
       typer.echo("Error: --service required in non-interactive mode.")
       typer.echo("Usage: subterminator cancel --service <name>")
       raise typer.Exit(code=3)

   # T15.7: ToS disclaimer (this line already exists)
   formatter = OutputFormatter(verbose=verbose)
   ```

3. Find the SessionLogger instantiation by searching for `session = SessionLogger(`. Change `service=service.lower(),` to `service=selected_service,`:
   ```python
   session = SessionLogger(
       output_dir=config.output_dir,
       service=selected_service,  # CHANGED from service.lower()
       target=target,
   )
   ```

4. Add epilog to cancel command decorator. Find `@app.command()` and change to:
   ```python
   @app.command(epilog="Migration note: The positional syntax 'subterminator cancel netflix' is deprecated. Use '--service netflix' instead.")
   ```

**Exit codes:**
- 0: Success (unchanged)
- 1: Cancellation failed (unchanged)
- 2: User cancelled (Ctrl+C in menu)
- 3: Missing --service OR unknown service OR unavailable service
- 4: Config error (unchanged)

**Done when:**
- [ ] All 8 cancel command tests pass
- [ ] Exit code 2 when user cancels menu
- [ ] Exit code 3 with "Unknown service 'X'" when service not found
- [ ] Exit code 3 with "not yet available" when service unavailable
- [ ] Exit code 3 with "--service required" in non-interactive mode

**Blocked by:** Task 5.3

---

### Task 5.5: Verify integration

**Commands:**
```bash
pytest tests/integration/test_cli_cancel.py -v
```

**Done when:**
- [ ] All 8 integration tests pass

**Blocked by:** Task 5.4

---

## Phase 6: Update Existing Tests

### Task 6.1: Identify broken tests

**Commands:**
```bash
# Run full suite and capture output (includes collection errors)
pytest tests/ -v --tb=short 2>&1 | tee test_failures.txt

# Review for FAILED, ERROR, and collection failures
grep -E "(FAILED|ERROR|ModuleNotFoundError|ImportError)" test_failures.txt
```

**Actions:**
1. Run full test suite with output capture
2. Review test_failures.txt for all failure types
3. Document list of broken tests

**Done when:**
- [ ] List of broken tests documented in test_failures.txt

**Blocked by:** Task 5.5

---

### Task 6.2: Fix broken tests

**Files:** `tests/unit/test_cli.py`

**Note:** Use code patterns (not line numbers) to locate changes since earlier tasks may have shifted line numbers.

**Specific changes to `tests/unit/test_cli.py`:**

1. **Delete class `TestSupportedServices`** - Find and delete the entire class containing these three test methods:
   - `test_netflix_is_supported`
   - `test_supported_services_is_list`
   - `test_supported_services_not_empty`

   Registry functionality is now tested in `tests/unit/services/test_registry.py`.

2. **Delete import of `SUPPORTED_SERVICES`** - Find the import line:
   ```python
   # FIND: from subterminator.cli.main import SUPPORTED_SERVICES, app
   # CHANGE TO:
   from subterminator.cli.main import app
   ```

3. **Fix CLI invocation syntax in `TestCancelCommandValidation`:**
   Search for all `runner.invoke(app, ["cancel",` patterns and add `"--service",` flag:
   - `["cancel", "invalid_service"]` → `["cancel", "--service", "invalid_service"]`
   - `["cancel", "spotify"]` → `["cancel", "--service", "spotify"]`
   - `["cancel", "badservice"]` → `["cancel", "--service", "badservice"]`
   - `["cancel", "BADSERVICE"]` → `["cancel", "--service", "BADSERVICE"]`

4. **Update assertions in `TestCancelCommandValidation`:**
   - Find `assert "unsupported service" in result.output.lower()` and change to `assert "unknown service" in result.output.lower()`
   - Find `assert "netflix" in result.output.lower()` in `test_invalid_service_shows_supported_services` and change to `assert "available services" in result.output.lower()`

5. **Fix `TestCancelCommandOptions.test_dry_run_option_accepted`:**
   Find `["cancel", "netflix", "--dry-run"]` and change to `["cancel", "--service", "netflix", "--dry-run"]`

6. **Update `test_help_shows_all_options`:**
   Find this test function and add these assertions after the existing assertions:
   ```python
   assert "--service" in output
   assert "--no-input" in output
   assert "--plain" in output
   ```

**Done when:**
- [ ] `pytest tests/unit/test_cli.py` passes with 0 failures
- [ ] No imports or references to `SUPPORTED_SERVICES` remain in test_cli.py
- [ ] `pytest tests/` passes (full suite)
- [ ] Coverage doesn't decrease

**Blocked by:** Task 6.1

---

## Phase 7: Update Documentation

### Task 7.1: Update README

**Files:** `README.md`

**Actions:**
1. Update cancel command examples
2. Add Interactive Mode section
3. Add Non-Interactive Mode section
4. Document --service, --no-input, --plain flags
5. Document environment variables

**Done when:**
- [ ] README shows correct v2.0 syntax

**Blocked by:** Task 6.2

---

### Task 7.2: Add migration guide

**Files:** `README.md`

**Actions:**
1. Add "Migration from v1.x" section
2. Show old vs new syntax
3. Explain breaking change

**Done when:**
- [ ] Migration section exists with clear examples

**Blocked by:** Task 7.1

---

## Dependency Summary

```
1.0 → 1.1 → 1.2 → [2.1, 3.1] (parallel)
                    ↓
                 2.1 → 2.2 → 2.3 → 2.4 ─┐
                 3.1 → 3.2 → 3.3 ───────┤
                                        ↓
                                     4.1 → 4.2 → 4.3 → 4.4
                                                    ↓
                                     5.1 → 5.2 → 5.3 → 5.4 → 5.5
                                                             ↓
                                                    6.1 → 6.2
                                                          ↓
                                                    7.1 → 7.2
```

---

## Acceptance Criteria (from spec.md)

- [ ] AC-1: Interactive mode when `cancel` runs without --service
- [ ] AC-2: Menu navigation with arrow keys
- [ ] AC-3: Service selection with Enter
- [ ] AC-4: Disabled services shown but not selectable
- [ ] AC-5: Ctrl+C exits with code 2
- [ ] AC-6: --service bypasses menu
- [ ] AC-7: Non-interactive without --service errors (exit 3)
- [ ] AC-8: Unknown service shows fuzzy suggestion
- [ ] AC-9: NO_COLOR disables colors
- [ ] AC-10: Help option shows details and re-displays menu
