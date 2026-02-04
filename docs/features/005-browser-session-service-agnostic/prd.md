# PRD: Browser Automation Architecture Improvements

**Status:** Draft
**Created:** 2026-02-04
**Updated:** 2026-02-04
**Type:** Feature PRD

## 1. Problem Statement

Our current SubTerminator implementation has several limitations:

1. **Brittle CSS Selectors**: Netflix UI changes break automation (e.g., `data-uia` attributes)
2. **Headless Browser Friction**: Users must re-login every run - no session persistence
3. **Netflix Hardcoding**: Engine and CLI are tightly coupled to Netflix, blocking multi-service support
4. **Purpose-Specific Code**: Built only for subscription cancellation, limited reusability

**Core Questions:**
1. Should we adopt general-purpose AI browser agents, or improve our purpose-built solution?
2. How do we reduce user friction (login every time)?
3. How do we make element selection more robust?
4. How do we generalize beyond Netflix?

## 2. User Stories

### US-1: Connect to Existing Browser Session
**As a** regular user who is already logged into Netflix in my browser,
**I want** SubTerminator to connect to my existing browser session,
**So that** I don't have to log in again and can start cancellation immediately.

**Acceptance Criteria:**
- [ ] User can start Chrome with `--remote-debugging-port=9222`
- [ ] User can run `subterminator cancel --cdp-url http://localhost:9222`
- [ ] SubTerminator reuses the existing logged-in session
- [ ] Clear error message if Chrome is not running or port is wrong

### US-2: Persistent Login State
**As a** power user who runs SubTerminator frequently,
**I want** my login state to persist between runs,
**So that** I only need to log in once and subsequent runs are faster.

**Acceptance Criteria:**
- [ ] User can specify `--profile-dir ~/.subterminator/chrome-profile`
- [ ] First run: user logs in, state saved to profile directory
- [ ] Subsequent runs: already logged in, skips authentication checkpoint
- [ ] Profile directory auto-created if missing

### US-3: Robust Element Selection
**As a** user who experiences automation failures after Netflix UI updates,
**I want** element selection to fall back to accessibility-based methods,
**So that** minor UI changes don't break the cancellation flow.

**Acceptance Criteria:**
- [ ] CSS selectors tried first (current behavior)
- [ ] If CSS fails, ARIA role/name fallback is used
- [ ] Netflix selectors updated with ARIA fallbacks
- [ ] Works on mock pages with different selectors

### US-4: Multi-Service Architecture (Foundation)
**As a** developer extending SubTerminator to other services,
**I want** the engine and CLI to be service-agnostic,
**So that** I can add new services without modifying core code.

**Acceptance Criteria:**
- [ ] Engine accepts any `ServiceProtocol` implementation
- [ ] CLI uses service factory instead of hardcoded Netflix
- [ ] Checkpoint messages are service-agnostic
- [ ] Adding a new service only requires creating a new service class

## 3. Research Summary

### 3.1 Evaluated Browser Automation Solutions

| Tool | Architecture | Maturity | Suitability |
|------|--------------|----------|-------------|
| **OpenClaw** | Snapshot-based refs, Extension Relay | Active development, reported stability issues (see GitHub issues) | Good concepts, but stability concerns for production |
| **Browser-Use** | Hybrid DOM + Vision, Python | Active development | Good candidate for future fallback |
| **Skyvern** | Vision-only (no selectors) | Production-ready | Best for form-filling, complex infrastructure |
| **Stagehand** | AI-adaptive SDK | Newer, simpler | Alternative option |

*Note: Tool assessments based on GitHub repository reviews conducted 2026-02-04. Stability assessments are subjective judgments, not independently verified.*

### 3.2 Key Architectural Insights

#### Accessibility Tree vs DOM Selectors

Modern browser automation tools increasingly use the **Accessibility Tree** instead of CSS selectors:

| Traditional | Accessibility-Based |
|-------------|---------------------|
| `[data-uia="cancel"]` | `button "Cancel Membership"` |
| `.btn.btn-primary` | `button "Submit"` |
| Breaks on class changes | Survives restructuring |

**Claimed benefit:** Accessibility tree is significantly smaller than full DOM, reducing token usage for AI-based analysis. *Assumption: 80-90% reduction claimed by Stagehand documentation - needs verification during implementation.*

#### Connecting to Existing Browser Sessions

OpenClaw's Extension Relay mode demonstrates the value of connecting to existing logged-in browsers. **We can achieve this with Playwright's CDP connection** without external dependencies.

### 3.3 Current Generalization Analysis

*Methodology: Scores represent subjective assessment of code abstraction level. 10 = fully abstract with no service-specific code, 5 = requires minor changes for new service, 1 = completely hardcoded.*

| Component | Score | Issue |
|-----------|-------|-------|
| States | 10/10 | ✅ Generic cancellation flow |
| Protocols | 10/10 | ✅ ServiceProtocol is abstract |
| Claude Interpreter | 9/10 | ✅ Vision-based, any UI |
| Service Data Models | 9/10 | ✅ Reusable structures |
| Registry | 7/10 | ⚠️ Missing factory pattern |
| Heuristic Interpreter | 6/10 | ⚠️ Netflix-biased phrases |
| **Engine** | **3/10** | ❌ `NetflixService` hardcoded |
| **CLI** | **2/10** | ❌ Always instantiates Netflix |

**Overall: 6.5/10** - Good foundation, critical hardcodes blocking expansion.

## 4. Proposed Improvements

### 4.1 Browser Session Reuse (CDP Connection)

**Problem:** Users must log into Netflix every run.

**Solution:** Add CDP connection support to `PlaywrightBrowser.launch()`:
- `cdp_url` parameter to connect to existing Chrome
- `user_data_dir` parameter for persistent profiles
- Backward compatible: default behavior unchanged

**User workflow options:**
1. **CDP:** Start Chrome with `--remote-debugging-port=9222`, run SubTerminator with `--cdp-url`
2. **Persistent:** First run logs in, subsequent runs reuse saved session

### 4.2 Accessibility-Based Element Selection (ARIA Fallback)

**Problem:** CSS selectors break when Netflix changes class names/attributes.

**Solution:** Add ARIA-based fallback to `PlaywrightBrowser.click()`:
- Accept optional `fallback_role: tuple[str, str]` parameter
- CSS selectors tried first (preserves current behavior)
- ARIA role/name used if all CSS selectors fail
- Netflix selectors updated with role fallbacks

### 4.3 Service-Agnostic Refactoring

**Problem:** Engine and CLI hardcode `NetflixService`.

**Solution:**
1. **Engine:** Change type hint from `NetflixService` to `ServiceProtocol`
2. **Factory:** Create `create_service(service_id, target)` function
3. **CLI:** Use factory instead of direct instantiation
4. **Messages:** Make checkpoint prompts service-agnostic

## 5. Implementation Plan

*Note: Estimates assume developer familiar with Playwright and the codebase. Subject to refinement during design phase.*

### Phase 1: Browser Improvements

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| Add CDP connection to `PlaywrightBrowser` | 2 hours | Eliminates re-login friction | None |
| Add ARIA fallback to `click()` | 2 hours | Survives UI changes | None |
| Add `--cdp-url` CLI flag | 30 min | User-facing feature | CDP connection |
| Update Netflix selectors with role fallbacks | 1 hour | Immediate robustness | ARIA fallback |

**Total: ~5-6 hours** | *Phase 1 tasks can be parallelized (CDP + ARIA independent)*

### Phase 2: Service Generalization

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| Fix engine type annotation | 10 min | Removes type coupling | None |
| Create service factory | 30 min | Enables dynamic service creation | None |
| Update CLI to use factory | 30 min | Service selection works | Factory |
| Make checkpoint messages generic | 30 min | No "Netflix" in prompts | None |

**Total: ~2 hours** | *Phase 2 depends on Phase 1 completion for testing*

### Phase 3: Multi-Service Expansion (Future, Out of Scope)

Not included in this feature. Foundation only.

## 6. Success Criteria (Measurable)

| Criterion | Metric | Target |
|-----------|--------|--------|
| **CDP Connection** | Connection success rate | 100% when Chrome running with correct port |
| **CDP Latency** | Time to connect | < 5 seconds |
| **ARIA Fallback** | Success rate when CSS fails | 90%+ on mock pages with modified selectors |
| **Backward Compatibility** | Existing test pass rate | 100% (all ~420 tests) |
| **New Test Coverage** | New tests added | 10+ tests for CDP, ARIA, factory |
| **Service Abstraction** | Engine accepts mock service | Mock ServiceProtocol works in tests |

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **CDP Security Exposure** | Medium | High | CDP only binds to localhost by default. Document security best practices. Do not expose to network. |
| **Browser Version Compatibility** | Low | Medium | Test with Chrome 100+. Use Playwright's CDP abstraction which handles version differences. |
| **ARIA Labels Vary by Locale** | Medium | Medium | Use English locale for initial implementation. Note limitation in docs. Future: locale-aware selectors. |
| **Session State Corruption** | Low | Medium | Graceful handling if session invalid. Fall back to new browser. Clear error messages. |
| **Stealth Mode Not Applied** | Low | Low | When connecting via CDP, user's existing browser fingerprint is used. Document this behavior. |
| **Breaking Existing Flows** | Low | High | All existing tests must pass. No changes to default behavior. Feature flags for new features. |

## 8. Out of Scope

- Full OpenClaw integration (stability concerns based on GitHub issue reports)
- Full Skyvern integration (infrastructure complexity: requires PostgreSQL)
- Browser-Use integration (can add later as additional fallback tier)
- Proxy rotation / anti-bot features
- CAPTCHA solving
- Multi-service implementation (only foundation/abstraction in this feature)
- Non-English locale support for ARIA selectors

## 9. Trade-off Analysis

### Purpose-Built vs General-Purpose Agents

| Aspect | Our Approach | General Agent (Browser-Use/Skyvern) |
|--------|--------------|-------------------------------------|
| Human checkpoints | ✅ Built-in | ❌ Must add |
| Session audit trail | ✅ Built-in | ❌ Must add |
| Per-flow optimization | ✅ Can tune selectors | ⚠️ LLM cost every action |
| UI change resilience | ⚠️ ARIA helps but limited | ✅ Vision-based |
| New service effort | ~8 hours | ~1 hour (just describe task) |
| Per-transaction cost | ~$0.01-0.05 | ~$0.10-0.50 |

**Conclusion:** Purpose-built with ARIA fallback is the right balance for now. Can layer in Browser-Use as a third-tier fallback later if needed.

## 10. Testing Strategy

### Unit Tests
- CDP connection logic (mocked Playwright)
- Persistent profile logic (mocked context)
- ARIA fallback behavior (CSS fail → ARIA succeed)
- Service factory (known and unknown IDs)
- Engine with mock ServiceProtocol

### Integration Tests
- CLI with `--cdp-url` flag
- CLI with `--profile-dir` flag
- Mock server with modified selectors (ARIA fallback path)

### Manual Testing Checklist
- [ ] Start Chrome with remote debugging, connect via CDP
- [ ] Verify existing Netflix session is accessible
- [ ] Test profile persistence across runs
- [ ] Test ARIA fallback with temporarily broken selector

## 11. References

- [Playwright CDP Connection](https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp)
- [Playwright Persistent Context](https://playwright.dev/docs/api/class-browsertype#browser-type-launch-persistent-context)
- [Playwright getByRole](https://playwright.dev/docs/locators#locate-by-role)
- [Playwright ARIA Snapshots](https://playwright.dev/docs/aria-snapshots)
- [CDP Accessibility Domain](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/)
- [Puppetaria: Accessibility-first Automation](https://developer.chrome.com/blog/puppetaria/)
