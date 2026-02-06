# Specification: Browser Session Reuse & Service-Agnostic Architecture

**Feature:** 005-browser-session-service-agnostic
**Status:** Draft
**Created:** 2026-02-04

## 1. Overview

This feature adds two capabilities to SubTerminator:

1. **Browser Session Reuse** - Connect to existing Chrome sessions via CDP, eliminating re-login friction
2. **Service-Agnostic Architecture** - Refactor engine and CLI to support multiple services beyond Netflix

## 2. Functional Requirements

### 2.1 Browser Session Reuse (CDP Connection)

#### FR-1: CDP Connection Support
The `PlaywrightBrowser` class SHALL support connecting to an existing Chrome browser via Chrome DevTools Protocol (CDP).

**Acceptance Criteria:**
- [ ] `PlaywrightBrowser.__init__()` accepts optional `cdp_url` parameter
- [ ] When `cdp_url` provided, connects to existing browser instead of launching new
- [ ] Reuses existing page/tab if available, creates new if not
- [ ] Stealth settings not applied when connecting to existing browser (user's browser)

#### FR-2: Persistent Browser Profile
The `PlaywrightBrowser` class SHALL support persistent browser profiles for session persistence.

**Acceptance Criteria:**
- [ ] `PlaywrightBrowser.__init__()` accepts optional `user_data_dir` parameter
- [ ] When `user_data_dir` provided, uses `launch_persistent_context()`
- [ ] Login state persists between runs when using same `user_data_dir`

#### FR-3: CLI Flags for Browser Options
The CLI SHALL expose browser connection options.

**Acceptance Criteria:**
- [ ] `--cdp-url` flag connects to existing Chrome (e.g., `--cdp-url http://localhost:9222`)
- [ ] `--profile-dir` flag uses persistent profile (e.g., `--profile-dir ~/.subterminator/chrome-profile`)
- [ ] Help text explains how to start Chrome with remote debugging

#### FR-4: Error Handling for Browser Connection
The system SHALL provide clear error messages for connection failures.

**Acceptance Criteria:**
- [ ] "Cannot connect to Chrome at {url}. Is Chrome running with --remote-debugging-port?" when CDP connection fails
- [ ] Profile directory auto-created if missing (with info message)
- [ ] "Failed to load browser profile from {path}" when profile is corrupted
- [ ] Connection timeout configurable (default 10000ms / 10 seconds)

### 2.2 ARIA-Based Element Selection

#### FR-5: ARIA Fallback in Click Method
The `PlaywrightBrowser.click()` method SHALL support ARIA-based fallback when CSS selectors fail.

**Acceptance Criteria:**
- [ ] `click()` accepts optional `fallback_role: tuple[str, str]` parameter
- [ ] CSS selectors tried first (current behavior preserved)
- [ ] If all CSS selectors fail AND `fallback_role` provided, use `get_by_role(role, name=name)`
- [ ] Error message includes both CSS selectors and ARIA role attempted

#### FR-6: Service Selector Format Update
Service selectors SHALL use `SelectorConfig` with CSS and ARIA role definitions.

**Acceptance Criteria:**
- [ ] All selectors use `SelectorConfig` dataclass with `css` and `aria` fields
- [ ] Netflix service updated with ARIA fallbacks for all selectors
- [ ] No backward compatibility needed (pre-production codebase)

### 2.3 Service-Agnostic Architecture

#### FR-7: Engine Type Abstraction
The `CancellationEngine` SHALL accept any `ServiceProtocol` implementation.

**Acceptance Criteria:**
- [ ] `CancellationEngine.__init__()` type hint changed from `NetflixService` to `ServiceProtocol`
- [ ] No direct import of `NetflixService` in engine.py
- [ ] Engine works identically with Netflix and any future service

#### FR-8: Service Factory Pattern
A factory function SHALL create service instances by ID.

**Acceptance Criteria:**
- [ ] `create_service(service_id: str, target: str) -> ServiceProtocol` function exists
- [ ] Factory registered in `services/__init__.py` or `services/registry.py`
- [ ] Unknown service ID raises `ValueError` with suggestion
- [ ] Factory extensible for future services

#### FR-9: CLI Service Instantiation
The CLI SHALL use the service factory instead of hardcoded Netflix.

**Acceptance Criteria:**
- [ ] CLI imports `create_service` instead of `NetflixService`
- [ ] Selected service passed through factory
- [ ] Mock page path derived from service ID (not hardcoded "netflix")

#### FR-10: Generic Checkpoint Messages
Human checkpoint messages SHALL not reference specific services.

**Acceptance Criteria:**
- [ ] AUTH checkpoint: "Please log in to {service_name} in the browser..."
- [ ] CONFIRM checkpoint: "WARNING: This will cancel your {service_name} subscription..."
- [ ] Service name obtained from `service.config.name`

## 3. Non-Functional Requirements

### NFR-1: Backward Compatibility
All existing functionality MUST continue working without changes to user behavior.

**Acceptance Criteria:**
- [ ] Default behavior (no CDP, no profile) unchanged
- [ ] All existing tests pass
- [ ] Netflix cancellation flow works identically

### NFR-2: Performance
CDP connection SHOULD not add significant latency.

**Acceptance Criteria:**
- [ ] CDP connection established within 5 seconds
- [ ] No measurable difference in click/navigation speed

### NFR-3: Documentation
New features MUST be documented.

**Acceptance Criteria:**
- [ ] CLI help updated with new flags
- [ ] README section on browser session reuse
- [ ] Code docstrings for new parameters

## 4. Technical Constraints

### TC-1: Playwright Version
Current Playwright version must support `connect_over_cdp()` and `launch_persistent_context()`.

### TC-2: Chrome Remote Debugging
CDP connection requires Chrome started with `--remote-debugging-port=9222`.

### TC-3: Stealth Mode
`playwright-stealth` cannot be applied when connecting to existing browser (no page hook available).

## 5. Out of Scope

- OpenClaw integration (stability concerns)
- Browser-Use integration (future enhancement)
- Skyvern integration (infrastructure complexity)
- Proxy rotation / anti-bot features
- CAPTCHA solving
- Multi-service support beyond Netflix (future feature)

## 6. Test Requirements

### Unit Tests

| Test | Description |
|------|-------------|
| `test_browser_cdp_connection` | Mock CDP connection, verify correct Playwright calls |
| `test_browser_persistent_profile` | Mock persistent context, verify user_data_dir passed |
| `test_click_aria_fallback` | CSS fails → ARIA succeeds |
| `test_click_aria_fallback_both_fail` | CSS and ARIA fail → ElementNotFound |
| `test_service_factory_known` | Factory returns Netflix for "netflix" |
| `test_service_factory_unknown` | Factory raises ValueError for "unknown" |
| `test_engine_accepts_protocol` | Engine initializes with mock ServiceProtocol |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_cli_cdp_flag` | CLI with --cdp-url calls browser.launch(cdp_url=...) |
| `test_cli_profile_flag` | CLI with --profile-dir calls browser.launch(user_data_dir=...) |
| `test_mock_flow_aria_fallback` | Mock page with no data-uia attrs, ARIA fallback succeeds |

## 7. Acceptance Criteria Summary

| Requirement | Criteria Count | Priority |
|-------------|----------------|----------|
| FR-1: CDP Connection | 4 | High |
| FR-2: Persistent Profile | 3 | Medium |
| FR-3: CLI Flags | 3 | High |
| FR-4: Error Handling | 3 | Medium |
| FR-5: ARIA Fallback | 4 | High |
| FR-6: Selector Format | 3 | Medium |
| FR-7: Engine Abstraction | 3 | High |
| FR-8: Service Factory | 4 | High |
| FR-9: CLI Service | 3 | High |
| FR-10: Generic Messages | 3 | Low |

## 8. Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Playwright | Existing | `connect_over_cdp()`, `launch_persistent_context()` |
| ServiceProtocol | Existing | Already defined in protocols.py |

## 9. Risks

| Risk | Mitigation |
|------|------------|
| CDP connection unreliable | Clear error messages, fallback to new browser |
| ARIA selectors not matching | Keep CSS as primary, ARIA as fallback only |
| Breaking existing flows | Comprehensive test suite, all existing tests must pass |

## 10. Resolved Questions

1. ~~Should we expose model selection in CLI?~~ → Out of scope for this feature
2. **Should `--profile-dir` auto-create directory if missing?** → Yes, auto-create with warning message
3. **Should we add `--headless` flag override for CDP connections?** → No, CDP connections inherit the browser's existing mode
