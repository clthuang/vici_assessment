# Tasks: Browser Session Reuse & Service-Agnostic Architecture

**Feature:** 005-browser-session-service-agnostic
**Created:** 2026-02-04

## Overview

17 plan steps broken into 90 atomic tasks across 6 phases and 14 parallel groups.

---

## Phase 1: Foundation

### Parallel Group 1A (Steps 1.1, 1.2, 1.3 - No dependencies)

#### Step 1.1: Create SelectorConfig Type

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 1.1.1 | Create `tests/unit/test_selectors.py` with test for `SelectorConfig(css=["selector"])` | Test exists, fails (no impl) | 5m |
| 1.1.2 | Add test for `SelectorConfig(css=["selector"], aria=("button", "Name"))` | Test exists, fails | 5m |
| 1.1.3 | Add test for `SelectorConfig(css=[])` raises `ValueError` | Test exists, fails | 5m |
| 1.1.4 | Create `src/subterminator/services/selectors.py` with `SelectorConfig` dataclass | All 3 tests pass | 10m |

#### Step 1.2: Create Error Types

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 1.2.1 | Create/extend `tests/unit/test_exceptions.py` with test for `CDPConnectionError(url)` message format | Test exists, fails | 5m |
| 1.2.2 | Add test for `ProfileLoadError(path)` message format | Test exists, fails | 5m |
| 1.2.3 | Add tests verifying both inherit from `PermanentError` | Tests exist, fail | 5m |
| 1.2.4 | Add `CDPConnectionError` and `ProfileLoadError` to `src/subterminator/utils/exceptions.py`, inheriting from existing `PermanentError` class | All tests pass | 10m |

#### Step 1.3: Update BrowserProtocol

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 1.3.1 | Add test verifying `click()` accepts `fallback_role` parameter | Test exists | 5m |
| 1.3.2 | Add test verifying `click()` accepts `timeout` parameter | Test exists | 5m |
| 1.3.3 | Add test for `is_cdp_connection` property in protocol | Test exists | 5m |
| 1.3.4 | Update `BrowserProtocol` in `protocols.py` with new signature. Note: Protocol tests verify that PlaywrightBrowser still satisfies the protocol after changes (use typing.runtime_checkable if needed) | Tests pass, protocol updated | 10m |

### Sequential Group 1B (Step 1.4 - depends on 1.1)

#### Step 1.4: Update ServiceProtocol

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 1.4.1 | Add test for `ServiceConfigProtocol` class in `protocols.py` with `name: str` property. This is a PROTOCOL class, separate from the existing `ServiceConfig` dataclass in `netflix.py` | Test exists | 5m |
| 1.4.2 | Add test verifying NetflixService satisfies updated ServiceProtocol (config returns object with `name` property) | Test exists | 5m |
| 1.4.3 | Add test for `service_id: str` property on ServiceProtocol | Test exists | 5m |
| 1.4.4 | Create `ServiceConfigProtocol` Protocol class in `protocols.py` with `name: str` property. Update `ServiceProtocol.config` type hint from `dict[str, Any]` to `ServiceConfigProtocol`. Add `service_id: str` property to ServiceProtocol | All tests pass | 10m |

**Blocked by:** 1.1.4 (SelectorConfig must exist for ServiceSelectors type reference)

---

## Phase 2: Service Layer

### Sequential Group 2A (Step 2.1 - depends on 1.1, 1.4)

#### Step 2.1: Update NetflixService Selectors

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 2.1.1 | Add test for `ServiceSelectors` dataclass with `SelectorConfig` fields | Test exists, fails | 5m |
| 2.1.2 | Add test for `service_id` property returning `"netflix"` | Test exists, fails | 5m |
| 2.1.3 | Add test for `selectors` returning `ServiceSelectors` (not dict) | Test exists, fails | 5m |
| 2.1.4 | Add test for each selector having `.css` and `.aria` attributes | Test exists, fails | 5m |
| 2.1.5 | Modify existing `ServiceSelectors` dataclass in `netflix.py` (line 7): change field types from `list[str]` to `SelectorConfig`. Import `SelectorConfig` from `selectors.py` | Dataclass fields use SelectorConfig type | 5m |
| 2.1.6 | Update selector values in `NetflixService._config` (lines 40-67) to use `SelectorConfig` format with ARIA fallbacks. Use these exact ARIA values: `cancel_link=("link", "Cancel Membership")`, `decline_offer=("button", "Continue to Cancel")`, `survey_option=None` (radio buttons vary, skip ARIA), `survey_submit=("button", "Continue")`, `confirm_cancel=("button", "Finish Cancellation")` | All tests pass | 15m |
| 2.1.7 | Add `service_id` property to `NetflixService` | `service_id` test passes | 5m |

**Blocked by:** 1.1.4, 1.4.4

### Sequential Group 2B (Step 2.2 - depends on 2.1)

#### Step 2.2: Create Service Factory

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 2.2.1 | Create `tests/unit/test_factory.py` with test for `create_service("netflix", "live")` | Test exists, fails | 5m |
| 2.2.2 | Add test for `create_service("netflix", "mock")` returns mock target | Test exists, fails | 5m |
| 2.2.3 | Add test for case insensitive `create_service("NETFLIX")` | Test exists, fails | 5m |
| 2.2.4 | Add test for `create_service("unknown")` raises `ValueError` | Test exists, fails | 5m |
| 2.2.5 | Add test for typo suggestion in error message | Test exists, fails | 5m |
| 2.2.6 | Implement `create_service()` and `get_mock_pages_dir()` in `services/__init__.py` | All tests pass | 15m |

**Blocked by:** 2.1.7

---

## Phase 3: Browser Core

### Sequential Group 3A (Step 3.1 - depends on 1.2, 1.3)

#### Step 3.1: Add CDP Connection Support

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 3.1.1 | Add test: `cdp_url` stored in `__init__` | Test exists, fails | 5m |
| 3.1.2 | Add test: `is_cdp_connection` returns `True` when cdp_url set | Test exists, fails | 5m |
| 3.1.3 | Add test: `ValueError` if both `cdp_url` and `user_data_dir` provided | Test exists, fails | 5m |
| 3.1.4 | Add test: `_created_page` defaults to `False` | Test exists, fails | 5m |
| 3.1.5 | Add test: `launch()` calls `connect_over_cdp` when cdp_url set. Mock using `@patch("subterminator.core.browser.async_playwright")` with `mock_playwright.start` returning AsyncMock that has `chromium.connect_over_cdp` as AsyncMock | Test exists, fails | 10m |
| 3.1.6 | Add test: stealth NOT applied for CDP | Test exists, fails | 5m |
| 3.1.7 | Add test: `CDPConnectionError` raised on failure | Test exists, fails | 5m |
| 3.1.8 | Add test: page reuse from existing context | Test exists, fails | 5m |
| 3.1.9 | Add test: new page created when none suitable, `_created_page=True` | Test exists, fails | 5m |
| 3.1.10 | Add `cdp_url`, `user_data_dir`, `cdp_timeout` params to `__init__`. Add mutual exclusivity validation. Initialize `_created_page=False` | Tests 3.1.1-3.1.4 pass | 10m |
| 3.1.11 | Implement `_launch_cdp()` method: call `connect_over_cdp(cdp_url, timeout=cdp_timeout)`. Skip stealth. Handle `CDPConnectionError` | Tests 3.1.5-3.1.7 pass | 10m |
| 3.1.12 | Add page reuse logic in `_launch_cdp()`: skip system pages (`chrome://`, `about:`, `chrome-extension://`), create new page if needed, set `_created_page=True` when creating | All 9 tests pass | 10m |

**Blocked by:** 1.2.4, 1.3.4

### Sequential Group 3B (Step 3.2 - depends on 3.1)

#### Step 3.2: Add Persistent Profile Support

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 3.2.1 | Add test: `user_data_dir` parameter stored in `__init__` and accessible. Note: This test should pass immediately since 3.1.10 already added the parameter | Test exists, passes (verifies 3.1.10) | 5m |
| 3.2.2 | Add test: `launch_persistent_context` called with path | Test exists, fails | 5m |
| 3.2.3 | Add test: directory auto-created if missing | Test exists, fails | 5m |
| 3.2.4 | Add test: `ProfileLoadError` raised on corruption | Test exists, fails | 5m |
| 3.2.5 | Implement persistent profile in `browser.py` | All tests pass | 15m |

**Blocked by:** 3.1.10

### Parallel Group 3C (Steps 3.3, 3.4 - can run in parallel after their deps)

#### Step 3.3: Add ARIA Fallback to click() (depends on 1.3)

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 3.3.1 | Add test: `click()` with CSS only succeeds | Test exists | 5m |
| 3.3.2 | Add test: CSS list tries each in order | Test exists, fails | 5m |
| 3.3.3 | Add test: `fallback_role` tries ARIA after CSS fails | Test exists, fails | 5m |
| 3.3.4 | Add test: ARIA fallback succeeds when CSS fails | Test exists, fails | 5m |
| 3.3.5 | Add test: `ElementNotFound` includes CSS selectors (no ARIA provided) | Test exists | 5m |
| 3.3.6 | Add test: `ElementNotFound` includes ARIA when both fail | Test exists, fails | 5m |
| 3.3.7 | Add test: explicit `fallback_role=None` shows CSS-only error | Test exists, fails | 5m |
| 3.3.8 | Add test: `timeout` passed to `wait_for_selector` | Test exists, fails | 5m |
| 3.3.9 | Implement ARIA fallback in `click()` | All 8 tests pass | 15m |

**Blocked by:** 1.3.4

#### Step 3.4: Update close() for CDP (depends on 3.1)

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 3.4.1 | Add test: CDP `close()` does not close browser | Test exists, fails | 5m |
| 3.4.2 | Add test: CDP `close()` only closes page if `_created_page=True` | Test exists, fails | 5m |
| 3.4.3 | Add test: Non-CDP `close()` closes browser normally (validates unchanged behavior) | Test exists, passes | 5m |
| 3.4.4 | Add test: `playwright.stop()` called for both modes | Test exists, fails | 5m |
| 3.4.5 | Implement conditional close behavior | All tests pass | 10m |

**Blocked by:** 3.1.10

---

## Phase 4: Engine Updates

### Sequential Group 4A (Step 4.1 - depends on 1.4, 2.1)

#### Step 4.1: Update Engine Type Annotation

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 4.1.1 | Add test: engine accepts mock `ServiceProtocol` | Test exists | 5m |
| 4.1.2 | Add test: engine works with `NetflixService` | Test exists | 5m |
| 4.1.3 | Update type annotation from `NetflixService` to `ServiceProtocol` | Tests pass, no direct import | 10m |

**Blocked by:** 1.4.4, 2.1.7

### Sequential Group 4B (Step 4.2 - CRITICAL, depends on 1.1, 2.1, 3.3, 4.1)

#### Step 4.2: Update Engine to Use SelectorConfig

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 4.2.1 | Add test: engine extracts `.css` from `SelectorConfig` | Test exists, fails | 5m |
| 4.2.2 | Add test: engine passes `.aria` as `fallback_role` | Test exists, fails | 5m |
| 4.2.3 | Add test: engine handles `aria=None` correctly | Test exists, fails | 5m |
| 4.2.4 | Add test: `_click_selector` helper works correctly | Test exists, fails | 5m |
| 4.2.5 | Implement `_click_selector(self, selector_config: SelectorConfig) -> None` helper that calls `await self.browser.click(selector_config.css, fallback_role=selector_config.aria)` | Helper works | 10m |
| 4.2.6 | Update all `browser.click()` calls in `_handle_state` method branches to use `_click_selector` helper: ACCOUNT_ACTIVE (line 176), RETENTION_OFFER (line 190), FINAL_CONFIRMATION (line 205). Also update `_complete_survey` method (lines 324-326) | Click calls updated | 10m |
| 4.2.7 | Verify all engine tests pass with updated click pattern | All tests pass | 5m |

**Blocked by:** 1.1.4, 2.1.6, 3.3.9, 4.1.3

*Note: 4.2.6 now references specific state handlers. Check engine.py for actual handler names.*

### Sequential Group 4C (Step 4.3 - depends on 4.1)

#### Step 4.3: Generic Checkpoint Messages

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 4.3.1 | Add test: auth prompt includes `service.config.name` | Test exists, fails | 5m |
| 4.3.2 | Add test: confirm prompt includes `service.config.name` | Test exists, fails | 5m |
| 4.3.3 | Add test: no hardcoded "Netflix" in prompts | Test exists, fails | 5m |
| 4.3.4 | Update AUTH message in `_human_checkpoint` method (line 289): replace `"Please log in to Netflix in the browser"` with `f"Please log in to {self.service.config.name} in the browser"`. Note: CONFIRM and UNKNOWN messages don't mention service name | All tests pass | 10m |

**Blocked by:** 4.1.3

---

## Phase 5: CLI Integration

### Sequential Group 5A (Step 5.1 - depends on 3.1, 3.2)

#### Step 5.1: Add CLI Flags

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 5.1.1 | Add test: `--cdp-url` parsed correctly | Test exists, fails | 5m |
| 5.1.2 | Add test: `--profile-dir` parsed correctly | Test exists, fails | 5m |
| 5.1.3 | Add test: flags passed to `PlaywrightBrowser` | Test exists, fails | 5m |
| 5.1.4 | Add test: `--help` shows new flags | Test exists, fails | 5m |
| 5.1.5 | Add test: when both `--cdp-url` and `--profile-dir` provided, CLI shows error before browser init. Implement using typer callback validation with clear message "'--cdp-url and --profile-dir cannot be used together'". Browser's ValueError is defense-in-depth | Test exists, fails | 5m |
| 5.1.6 | Implement CLI flags in `main.py` | All tests pass | 15m |

**Blocked by:** 3.1.10, 3.2.5

### Sequential Group 5B (Step 5.2 - depends on 2.1, 2.2)

#### Step 5.2: Use Service Factory in CLI

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 5.2.1 | Add test: CLI uses `create_service` instead of direct `NetflixService(target=target)` instantiation (see main.py line 158) | Test exists, fails | 5m |
| 5.2.2 | Add test: mock target uses `get_mock_pages_dir(service_id)` for path derivation | Test exists, fails | 5m |
| 5.2.3 | Add test: unknown service error from `create_service` is helpful (uses existing `suggest_service` from registry) | Test exists, fails | 5m |
| 5.2.4 | Update CLI main.py: replace `NetflixService(target=target)` with `create_service(selected_service, target)` | All tests pass | 10m |

**Blocked by:** 2.1.7, 2.2.6

---

## Phase 6: Integration Testing

### Sequential Group 6A (Step 6.1 - depends on Phase 3 + 5)

#### Step 6.1: CDP Integration Test

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 6.1.1 | Review `tests/integration/` patterns, then create `tests/integration/test_browser_cdp.py` with CDP connection test using mocked playwright | Test file exists with connection test | 10m |
| 6.1.2 | Add test for `close()` not closing browser | Test exists | 5m |
| 6.1.3 | Add test for full flow with CDP | Test passes | 10m |

**Blocked by:** 3.4.5, 5.1.6

### Sequential Group 6B (Step 6.2 - depends on Phase 3 + 4.2 + 5)

#### Step 6.2: ARIA Fallback Integration Test

| ID | Task | Acceptance | Est |
|----|------|------------|-----|
| 6.2.1 | Review `mock_pages/netflix/` structure, then create `mock_pages/netflix/aria_test_account.html` without `data-uia` attributes. Use elements matching ARIA roles: `<a>Cancel Membership</a>` for cancel_link, `<button>Continue to Cancel</button>` for decline_offer, `<button>Continue</button>` for survey_submit, `<button>Finish Cancellation</button>` for confirm_cancel. Note: survey_option has aria=None, relies on CSS only | Mock page exists | 10m |
| 6.2.2 | Create `tests/integration/test_aria_fallback.py` with ARIA success test | Test passes | 10m |
| 6.2.3 | Add test for error message when both CSS and ARIA fail | Test passes | 10m |

**Blocked by:** 3.3.9, 4.2.6, 5.1.6

---

## Summary

| Phase | Tasks | Parallel Groups |
|-------|-------|-----------------|
| Phase 1 | 16 | 2 (1A, 1B) |
| Phase 2 | 13 | 2 (2A, 2B) |
| Phase 3 | 31 | 3 (3A, 3B, 3C) |
| Phase 4 | 14 | 3 (4A, 4B, 4C) |
| Phase 5 | 10 | 2 (5A, 5B) |
| Phase 6 | 6 | 2 (6A, 6B) |
| **Total** | **90** | **14** |

*Note: Task counts updated after splitting 3.1.10 (→ 3.1.10-12) and 4.2.6 (→ 4.2.6-7). Phase 3 increased from 21 to 31 due to 3.1 having 12 tasks (9 tests + 3 implementation).*

## Execution Order

```
Parallel Group 1A: 1.1.1-1.1.4, 1.2.1-1.2.4, 1.3.1-1.3.4 (can run simultaneously)
                      ↓
Sequential Group 1B: 1.4.1-1.4.4 (after 1.1.4)
                      ↓
Sequential Group 2A: 2.1.1-2.1.7 (after 1.4.4)
                      ↓
Sequential Group 2B: 2.2.1-2.2.6 (after 2.1.7)

Sequential Group 3A: 3.1.1-3.1.12 (after 1.2.4, 1.3.4)
                      ↓
Sequential Group 3B: 3.2.1-3.2.5 (after 3.1.10)

Parallel Group 3C: 3.3.1-3.3.9 (after 1.3.4), 3.4.1-3.4.5 (after 3.1.10)

Sequential Group 4A: 4.1.1-4.1.3 (after 1.4.4, 2.1.7)
                      ↓
Sequential Group 4B: 4.2.1-4.2.7 (after 3.3.9, 4.1.3) ⚠️ CRITICAL PATH

Sequential Group 4C: 4.3.1-4.3.4 (after 4.1.3)

Sequential Group 5A: 5.1.1-5.1.6 (after 3.1.10, 3.2.5)
Sequential Group 5B: 5.2.1-5.2.4 (after 2.1.7, 2.2.6)

Sequential Group 6A: 6.1.1-6.1.3 (after 3.4.5, 5.1.6)
Sequential Group 6B: 6.2.1-6.2.3 (after 3.3.9, 4.2.6, 5.1.6)
```

## Verification Checklist

After each task:
- [ ] Test written (RED) or implementation done (GREEN)
- [ ] mypy passes
- [ ] ruff passes

After each step:
- [ ] All step tests pass
- [ ] No regressions

After each phase:
- [ ] Full test suite passes
- [ ] Phase functionality verified
