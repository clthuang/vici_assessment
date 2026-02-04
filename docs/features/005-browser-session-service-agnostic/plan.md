# Implementation Plan: Browser Session Reuse & Service-Agnostic Architecture

**Feature:** 005-browser-session-service-agnostic
**Status:** Draft
**Created:** 2026-02-04

## Overview

This plan sequences the implementation of browser session reuse (CDP/persistent profiles), ARIA selector fallback, and service-agnostic refactoring. The plan follows TDD principles and orders tasks to minimize integration risk.

## Implementation Order Rationale

The implementation follows a foundation-first, dependency-aware order:

1. **Protocol Updates First** - All components depend on these interfaces
2. **Selector Infrastructure** - Required before browser changes
3. **Error Types** - Required before browser can raise new errors
4. **Browser Core** - Central component, enables CLI changes
5. **Service Factory** - Enables CLI to use dynamic service creation
6. **CLI Integration** - Brings new features to users
7. **Engine Updates** - Last, as it consumes all other changes

## Phases

### Phase 1: Foundation (Protocols, Types, Errors)

These are dependency-free and enable all other work.

#### Step 1.1: Create SelectorConfig Type
**File:** `src/subterminator/services/selectors.py` (new file)
**Test File:** `tests/unit/test_selectors.py` (new file)

**TDD Sequence:**
1. Write test for SelectorConfig with css list
2. Write test for SelectorConfig with css + aria
3. Write test for empty css list validation
4. Implement SelectorConfig dataclass

**Acceptance:**
- [ ] SelectorConfig(css=["selector"]) works
- [ ] SelectorConfig(css=["selector"], aria=("button", "Name")) works
- [ ] SelectorConfig(css=[]) raises ValueError

**Dependencies:** None

---

#### Step 1.2: Create Error Types
**File:** `src/subterminator/utils/exceptions.py` (extend existing)
**Test File:** `tests/unit/test_exceptions.py` (extend or create)

**Note:** Add to existing `utils/exceptions.py` which already has `PermanentError`, `TransientError`, etc.

**TDD Sequence:**
1. Write test for CDPConnectionError with url and message format
2. Write test for ProfileLoadError with path and message format
3. Write tests verifying both inherit from PermanentError
4. Implement error classes

**Acceptance:**
- [ ] CDPConnectionError stores url attribute
- [ ] ProfileLoadError stores path attribute
- [ ] Both inherit from PermanentError
- [ ] Error messages include actionable guidance

**Dependencies:** None

---

#### Step 1.3: Update BrowserProtocol
**File:** `src/subterminator/core/protocols.py`
**Test File:** `tests/unit/test_protocols.py` (extend existing)

**Changes:**
- Add `fallback_role: tuple[str, str] | None = None` to click()
- Add `timeout: int = 5000` to click()
- Add `is_cdp_connection: bool` property

**TDD Sequence:**
1. Write test verifying click() signature compatibility
2. Write test for is_cdp_connection property
3. Update protocol definition

**Acceptance:**
- [ ] click() accepts fallback_role parameter
- [ ] click() accepts timeout parameter
- [ ] is_cdp_connection property defined
- [ ] Existing implementations still satisfy protocol

**Note on mock_browser fixture:** The `mock_browser` fixture in `conftest.py` uses `MagicMock(spec=BrowserProtocol)`. Adding `is_cdp_connection` to the protocol will automatically be available on the mock due to MagicMock behavior (returns another MagicMock for unknown attributes). Explicit fixture updates can be done in Phase 6 if needed for stricter testing.

**Dependencies:** None

---

#### Step 1.4: Update ServiceProtocol
**File:** `src/subterminator/core/protocols.py`
**Test File:** `tests/unit/test_protocols.py` (extend existing)

**Changes:**
- Add ServiceConfig protocol (minimal, just `name` property)
- Update config return type to ServiceConfig
- Update selectors return type hint (forward reference to ServiceSelectors)
- Add service_id property

**TDD Sequence:**
1. Write test for ServiceConfig protocol
2. Write test verifying existing NetflixService still satisfies protocol
3. Update protocol definitions

**Acceptance:**
- [ ] ServiceConfig protocol with name property defined
- [ ] ServiceProtocol.config returns ServiceConfig
- [ ] ServiceProtocol.service_id property defined
- [ ] Existing NetflixService satisfies updated protocol

**Dependencies:** Step 1.1 (SelectorConfig exists so ServiceSelectors can use it as field type)

**Note:** ServiceProtocol.selectors returns `ServiceSelectors` dataclass (defined in netflix.py), which contains `SelectorConfig` fields. The dependency on Step 1.1 is because ServiceSelectors needs SelectorConfig to exist.

---

### Phase 2: Service Layer Updates

#### Step 2.1: Update NetflixService Selectors
**File:** `src/subterminator/services/netflix.py`
**Test File:** `tests/unit/test_netflix_service.py` (extend existing)

**Changes:**
- Create ServiceSelectors dataclass
- Convert all selectors to SelectorConfig format
- Add ARIA fallbacks to all selectors
- Add service_id property

**TDD Sequence:**
1. Write test for ServiceSelectors dataclass with SelectorConfig fields
2. Write test for service_id property returning "netflix"
3. Write test for selectors returning ServiceSelectors (not dict)
4. Write test for each selector having css and aria attributes
5. Migrate selectors to new format

**Acceptance:**
- [ ] ServiceSelectors dataclass with all 5 selectors
- [ ] Each selector is SelectorConfig with css list
- [ ] cancel_link, decline_offer, confirm_cancel have ARIA fallbacks
- [ ] service.selectors.cancel_link.css returns list
- [ ] service.selectors.cancel_link.aria returns tuple or None
- [ ] service_id returns "netflix"
- [ ] ARIA names match actual Netflix button text (e.g., "Cancel Membership", "Finish Cancellation")

**Note on ARIA Names:** ARIA role/name pairs must match the actual button text on Netflix. Refer to design.md Section 6.7 for the exact ARIA names to use.

**Breaking Change Strategy:** This step changes ServiceSelectors field types from `list[str]` to `SelectorConfig`. All code that accesses `service.selectors.X` will break. However, since Step 4.2 (Engine SelectorConfig Usage) updates the engine to use `.css` and `.aria` extraction, we must:
1. Update ServiceSelectors and Netflix selectors in this step
2. Update any unit tests that mock selectors to use SelectorConfig
3. Step 4.2 will then update the engine to consume the new format

The TDD approach handles this: tests are written first to expect SelectorConfig, then implementation changes to match.

**Dependencies:** Step 1.1 (SelectorConfig), Step 1.4 (ServiceProtocol update)

---

#### Step 2.2: Create Service Factory
**File:** `src/subterminator/services/__init__.py`
**Test File:** `tests/unit/test_factory.py` (new file)

**TDD Sequence:**
1. Write test for create_service("netflix", "live") returns NetflixService
2. Write test for create_service("netflix", "mock") returns NetflixService with mock target
3. Write test for create_service("NETFLIX") (case insensitive)
4. Write test for create_service("unknown") raises ValueError
5. Write test for ValueError includes suggestion when typo
6. Verify get_mock_pages_dir("netflix") returns "mock_pages/netflix" (simple inline assertion, path is just `f"mock_pages/{service_id}"`)
7. Implement factory function

**Note on get_mock_pages_dir:** This is a simple one-liner (`return f"mock_pages/{service_id.lower()}"`). A dedicated test case may be overkill - consider inline assertion in factory tests. The path is relative; CLI code joins with project root.

**Acceptance:**
- [ ] create_service("netflix", "live") returns configured NetflixService
- [ ] Case insensitive service ID matching
- [ ] ValueError for unknown service with helpful message
- [ ] Typo suggestion when similar service exists
- [ ] get_mock_pages_dir() derives path from service_id

**Dependencies:** Step 2.1 (updated NetflixService)

---

### Phase 3: Browser Core Changes

#### Step 3.1: Add CDP Connection Support
**File:** `src/subterminator/core/browser.py`
**Test File:** `tests/unit/test_browser.py` (extend existing)

**Changes:**
- Add cdp_url parameter to __init__
- Add user_data_dir parameter to __init__ (validation only - implementation in 3.2)
- Add cdp_timeout parameter to __init__
- Add mutual exclusivity validation for cdp_url and user_data_dir
- Initialize _created_page = False for all instances (used by close())
- Add _launch_cdp() method
- Update launch() to call _launch_cdp when cdp_url set
- Skip stealth for CDP connections
- Add is_cdp_connection property

**TDD Sequence:**
1. Write test: cdp_url stored in __init__
2. Write test: is_cdp_connection returns True when cdp_url set
3. Write test: ValueError if both cdp_url and user_data_dir provided (validate early!)
4. Write test: _created_page defaults to False for all browser instances
5. Write test: launch() calls connect_over_cdp when cdp_url set (mock playwright)
6. Write test: stealth NOT applied for CDP connection
7. Write test: CDPConnectionError raised on connection failure
8. Write test: page reuse from existing context
9. Write test: new page created when no suitable pages exist, _created_page set True
10. Implement CDP support

**Acceptance:**
- [ ] cdp_url parameter accepted in __init__
- [ ] is_cdp_connection property returns correct value
- [ ] ValueError raised if both cdp_url and user_data_dir provided
- [ ] _created_page = False initialized in __init__ for all browser instances
- [ ] connect_over_cdp called with correct URL
- [ ] cdp_timeout defaults to 10000ms (intentionally lower than Playwright's 30000ms default for faster connection feedback to user)
- [ ] Stealth not applied for CDP
- [ ] CDPConnectionError raised with clear message on failure
- [ ] First navigable page reused
- [ ] System pages (chrome://, about:) skipped
- [ ] _created_page = True when new page created in CDP mode

**Dependencies:** Step 1.2 (CDPConnectionError), Step 1.3 (BrowserProtocol)

---

#### Step 3.2: Add Persistent Profile Support
**File:** `src/subterminator/core/browser.py`
**Test File:** `tests/unit/test_browser.py` (extend existing)

**Changes:**
- Add _launch_persistent() method
- Update launch() to call _launch_persistent when user_data_dir set
- Auto-create directory if missing

**Note:** user_data_dir parameter and mutual exclusivity validation already added in Step 3.1.

**TDD Sequence:**
1. Write test: user_data_dir stored in __init__ (verify Step 3.1 added it)
2. Write test: launch_persistent_context called with correct path (mock playwright)
3. Write test: directory auto-created if missing
4. Write test: ProfileLoadError raised on corruption
5. Implement persistent profile support

**Acceptance:**
- [ ] user_data_dir parameter accepted in __init__ (from Step 3.1)
- [ ] Mutually exclusive with cdp_url (validated in Step 3.1)
- [ ] launch_persistent_context called with correct user_data_dir
- [ ] Directory auto-created with info log
- [ ] ProfileLoadError on corruption with actionable message
- [ ] Stealth applied to persistent context pages

**Dependencies:** Step 1.2 (ProfileLoadError), Step 3.1 (launch() refactoring, __init__ parameters)

---

#### Step 3.3: Add ARIA Fallback to click()
**File:** `src/subterminator/core/browser.py`
**Test File:** `tests/unit/test_browser.py` (extend existing)

**Changes:**
- Add fallback_role parameter to click()
- Add timeout parameter to click()
- Try all CSS selectors first
- Try ARIA fallback if CSS fails
- Update ElementNotFound error message format

**TDD Sequence:** (8 tests + implementation)
1. Write test: click() with CSS only succeeds (existing behavior)
2. Write test: click() with CSS list tries each in order
3. Write test: click() with fallback_role tries ARIA after CSS fails
4. Write test: click() with ARIA fallback succeeds when CSS fails
5. Write test: ElementNotFound includes CSS selectors in message (fallback_role not provided at all)
6. Write test: ElementNotFound includes ARIA in message when provided but fails
7. Write test: CSS fails with fallback_role=None explicit raises ElementNotFound with CSS-only message (tests explicit None vs omitted)
8. Write test: timeout parameter passed to wait_for_selector
9. Implement ARIA fallback

**Note on tests #5 vs #7:** Test #5 tests omitting fallback_role entirely. Test #7 tests explicitly passing `fallback_role=None`. Both should produce CSS-only error messages, but the code path may differ.

**Acceptance:**
- [ ] CSS selectors tried first in order
- [ ] ARIA fallback only used when all CSS fail
- [ ] get_by_role called with correct role and name
- [ ] Timeout applied to each attempt
- [ ] ElementNotFound message includes all attempted selectors
- [ ] Existing tests still pass (backward compatible)

**Dependencies:** Step 1.3 (BrowserProtocol.click signature)

---

#### Step 3.4: Update close() for CDP
**File:** `src/subterminator/core/browser.py`
**Test File:** `tests/unit/test_browser.py` (extend existing)

**Changes:**
- Use _created_page flag (initialized in Step 3.1)
- Only close page if we created it
- Never call browser.close() for CDP
- Only call playwright.stop()

**Note:** The `_created_page` flag is already initialized to `False` in `__init__` (Step 3.1). This step only uses it in close(), does not initialize it.

**TDD Sequence:**
1. Write test: CDP close() does not close browser
2. Write test: CDP close() only closes page if _created_page is True (uses flag from 3.1)
3. Write test: Non-CDP close() closes browser normally
4. Write test: playwright.stop() called for both modes
5. Implement conditional close behavior

**Acceptance:**
- [ ] CDP mode: browser.close() NOT called
- [ ] CDP mode: page.close() only if we created it
- [ ] Normal mode: browser.close() called
- [ ] playwright.stop() always called

**Dependencies:** Step 3.1 (CDP connection tracking)

---

### Phase 4: Engine Updates

#### Step 4.1: Update Engine Type Annotation
**File:** `src/subterminator/core/engine.py`
**Test File:** `tests/unit/test_engine.py` (extend existing)

**Changes:**
- Change service parameter from NetflixService to ServiceProtocol
- Remove direct import of NetflixService

**TDD Sequence:**
1. Write test: engine accepts mock ServiceProtocol
2. Write test: engine works with NetflixService (unchanged behavior)
3. Update type annotation

**Acceptance:**
- [ ] Engine type hint is ServiceProtocol
- [ ] No direct import of NetflixService in engine.py
- [ ] All existing engine tests pass
- [ ] Engine works identically with Netflix

**Dependencies:** Step 1.4 (ServiceProtocol), Step 2.1 (NetflixService satisfies protocol)

---

#### Step 4.2: Update Engine to Use SelectorConfig
**File:** `src/subterminator/core/engine.py`
**Test File:** `tests/unit/test_engine.py` (extend existing)

**CRITICAL:** This step addresses the SelectorConfig → Engine → Browser data flow.

After Step 2.1, `self.service.selectors.cancel_link` returns `SelectorConfig`, not `list[str]`.
The engine must extract `.css` and `.aria` before calling `browser.click()`.

**Changes:**
- Update all browser.click() calls to extract css and aria from SelectorConfig
- Add optional helper method `_click_selector(selector_config)` for cleaner code
- Engine now passes `selector_config.css` and `fallback_role=selector_config.aria`

**TDD Sequence:**
1. Write test: engine extracts .css from SelectorConfig and passes to browser.click()
2. Write test: engine extracts .aria from SelectorConfig and passes as fallback_role
3. Write test: engine handles SelectorConfig with aria=None correctly
4. Write test: _click_selector helper calls browser.click with correct arguments
5. Update all engine click calls

**Engine Pattern (from design.md Section 3.4):**
```python
# Before: engine passed selectors directly
await self.browser.click(self.service.selectors.cancel_link)  # BROKEN after Step 2.1

# After: engine extracts css and aria
selector_config = self.service.selectors.cancel_link
await self.browser.click(
    selector_config.css,
    fallback_role=selector_config.aria,
)

# Or using helper
async def _click_selector(self, selector_config: SelectorConfig) -> None:
    await self.browser.click(
        selector_config.css,
        fallback_role=selector_config.aria,
    )
```

**Acceptance:**
- [ ] Engine extracts .css from SelectorConfig before click()
- [ ] Engine passes .aria as fallback_role parameter
- [ ] All click calls updated to new pattern
- [ ] Engine works with both ARIA-enabled and ARIA-disabled selectors
- [ ] All existing engine tests pass (with mocks updated)

**Dependencies:** Step 1.1 (SelectorConfig), Step 2.1 (selectors return SelectorConfig), Step 3.3 (browser.click accepts fallback_role), Step 4.1 (type annotation)

**Note on Parallel Development:** TDD tests for this step can be written and run with mocks before Step 3.3 is complete. The engine tests mock browser.click() behavior. However, full integration requires Step 3.3.

---

#### Step 4.3: Generic Checkpoint Messages
**File:** `src/subterminator/core/engine.py`
**Test File:** `tests/unit/test_engine.py` (extend existing)

**Changes:**
- Replace "Netflix" with service.config.name in messages
- Update AUTH_PROMPT, CONFIRM_PROMPT, UNKNOWN_PROMPT templates

**TDD Sequence:**
1. Write test: auth prompt includes service.config.name
2. Write test: confirm prompt includes service.config.name
3. Write test: no hardcoded "Netflix" in any prompt
4. Update message templates

**Acceptance:**
- [ ] AUTH_PROMPT uses {service.config.name}
- [ ] CONFIRM_PROMPT uses {service.config.name}
- [ ] UNKNOWN_PROMPT uses {service.config.name}
- [ ] No hardcoded "Netflix" strings remain

**Dependencies:** Step 4.1 (engine uses ServiceProtocol)

---

### Phase 5: CLI Integration

#### Step 5.1: Add CLI Flags
**File:** `src/subterminator/cli/main.py`
**Test File:** `tests/integration/test_cli.py` (extend existing)

**Changes:**
- Add --cdp-url flag
- Add --profile-dir flag
- Pass flags to PlaywrightBrowser
- Update help text

**TDD Sequence:**
1. Write test: --cdp-url parsed correctly
2. Write test: --profile-dir parsed correctly
3. Write test: flags passed to PlaywrightBrowser
4. Write test: --help shows new flags with examples
5. Write test: error when both --cdp-url and --profile-dir provided
6. Implement CLI flags

**Acceptance:**
- [ ] --cdp-url flag accepts URL string
- [ ] --profile-dir flag accepts path
- [ ] Flags correctly passed to browser initialization
- [ ] Help text includes examples
- [ ] Clear error for mutually exclusive flags

**Dependencies:** Step 3.1 (CDP support), Step 3.2 (profile support)

---

#### Step 5.2: Use Service Factory in CLI
**File:** `src/subterminator/cli/main.py`
**Test File:** `tests/integration/test_cli.py` (extend existing)

**Changes:**
- Import create_service instead of NetflixService
- Use factory for service instantiation
- Use get_mock_pages_dir for mock path derivation

**TDD Sequence:**
1. Write test: CLI uses create_service for service
2. Write test: mock target uses get_mock_pages_dir
3. Write test: error message for unknown service is helpful
4. Update CLI to use factory

**Acceptance:**
- [ ] CLI imports create_service, not NetflixService
- [ ] Service created via factory
- [ ] Mock page path derived from service_id
- [ ] Unknown service error is actionable

**Dependencies:** Step 2.1 (service_id property), Step 2.2 (service factory, get_mock_pages_dir)

---

### Phase 6: Integration Testing

**Note:** Use existing test fixtures from `tests/conftest.py` and patterns from `tests/integration/` for mock setup.

**Key fixtures to use/extend:**
- `mock_browser` - Mock PlaywrightBrowser (extend with `is_cdp_connection` property)
- `mock_page` - Mock Playwright page object
- `mock_playwright` - Mock Playwright instance for CDP connection tests
- `mock_service` - Mock ServiceProtocol implementation
- `tmp_path` - pytest built-in for profile directories

See `tests/integration/test_engine.py` and `tests/integration/test_cli.py` for existing patterns.

#### Step 6.1: CDP Integration Test
**File:** `tests/integration/test_browser_cdp.py` (new file)

**Tests:**
- Mock playwright CDP connection using existing fixture patterns
- Verify full flow works with CDP browser
- Verify close behavior for CDP

**TDD Sequence:**
1. Review existing integration test patterns in `tests/integration/`
2. Write test for CDP connection using mocked playwright
3. Write test for close() not closing browser
4. Write test for full flow with CDP-connected browser

**Acceptance:**
- [ ] CDP connection integrates with full flow
- [ ] Chrome not closed after flow completion
- [ ] Tests use existing pytest fixture patterns

---

#### Step 6.2: ARIA Fallback Integration Test
**File:** `tests/integration/test_aria_fallback.py` (new file)

**Tests:**
- Mock page with modified selectors (no data-uia attrs)
- Verify ARIA fallback finds elements
- Verify error messages helpful when both fail

**TDD Sequence:**
1. Review existing mock page patterns in `mock_pages/netflix/`
2. Create test mock page without data-uia attributes
3. Write test for ARIA fallback success
4. Write test for comprehensive error message when both fail

**Acceptance:**
- [ ] ARIA fallback works in mock flow
- [ ] Error messages include all attempted selectors
- [ ] Tests use existing pytest fixture patterns

---

## Dependency Graph

```
Phase 1 (Foundation):
  1.1 SelectorConfig ─────────────────────────────────┐
  1.2 Error Types ─────────────────────────────┐      │
  1.3 BrowserProtocol ──────────────────┐      │      │
  1.4 ServiceProtocol ───────┐          │      │      │
                             │          │      │      │
Phase 2 (Service):           ▼          │      │      │
  2.1 Netflix Selectors ◄────┼──────────┼──────┼──────┘
  2.2 Service Factory ◄──────┘          │      │
                                        │      │
Phase 3 (Browser):                      ▼      ▼
  3.1 CDP Connection ◄──────────────────┼──────┤
    (includes mutual exclusivity        │      │
     validation and _created_page init) │      │
  3.2 Persistent Profile ◄──────────────┴──────┘
    (depends on 3.1 for __init__)
  3.3 ARIA Fallback ◄── 1.3 (BrowserProtocol.click)
  3.4 CDP Close ◄── 3.1 (_created_page tracking)

Phase 4 (Engine):
  4.1 Type Annotation ◄── 1.4, 2.1
  4.2 SelectorConfig Usage ◄── 1.1, 2.1, 3.3, 4.1  ⚠️ CRITICAL
    (Engine must extract .css/.aria before calling browser.click)
  4.3 Generic Messages ◄── 4.1

Phase 5 (CLI):
  5.1 CLI Flags ◄── 3.1, 3.2
  5.2 Service Factory ◄── 2.1, 2.2

Phase 6 (Integration):
  6.1 CDP Integration ◄── All Phase 3 + 5
  6.2 ARIA Integration ◄── Phase 3 + 4.2 + 5
```

**Critical Path for ARIA End-to-End:**
```
1.1 SelectorConfig → 2.1 Netflix Selectors → 4.2 Engine SelectorConfig Usage
                                                      ↓
1.3 BrowserProtocol → 3.3 ARIA Fallback ─────────────┘
                                                      ↓
                                               6.2 ARIA Integration
```

## Verification Checklist

After each step:
- [ ] Run unit tests for modified file
- [ ] Run type checker (mypy)
- [ ] Run linter (ruff)

After each phase:
- [ ] Run full test suite
- [ ] Verify no regressions in existing tests

Final verification:
- [ ] All 420+ existing tests pass
- [ ] All new tests pass
- [ ] Manual testing with real Chrome CDP
- [ ] Manual testing with profile persistence

## Risk Mitigation

1. **Breaking changes**: Each step maintains backward compatibility. Default behavior unchanged.

2. **Test isolation**: Each step has isolated tests. No cross-step test dependencies.

3. **Rollback points**: Each step is atomic. Can revert single step if issues found.

4. **Integration risk**: Phase 6 catches integration issues before merge.

## Estimated Effort

| Phase | Steps | Complexity |
|-------|-------|------------|
| Phase 1 | 4 | Low |
| Phase 2 | 2 | Low |
| Phase 3 | 4 | Medium |
| Phase 4 | 3 | Medium |
| Phase 5 | 2 | Low |
| Phase 6 | 2 | Medium |

Total: 17 implementation steps

**Note:** Phase 4 now includes Step 4.2 (SelectorConfig usage) which is critical for ARIA to work end-to-end.
