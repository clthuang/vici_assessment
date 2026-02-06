# PRD: Browser Automation Architecture Improvements

**Status:** Draft
**Created:** 2026-02-04
**Updated:** 2026-02-04
**Type:** Architecture Investigation & Refactoring Plan

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

## 2. Research Summary

### 2.1 Evaluated Browser Automation Solutions

| Tool | Architecture | Maturity | Suitability |
|------|--------------|----------|-------------|
| **OpenClaw** | Snapshot-based refs, Extension Relay | Unstable (crashes, security CVE) | Good concepts, risky for production |
| **Browser-Use** | Hybrid DOM + Vision, Python | Active development | Good candidate for fallback |
| **Skyvern** | Vision-only (no selectors) | Production-ready | Best for form-filling, complex infra |
| **Stagehand** | AI-adaptive SDK | Newer, simpler | Alternative option |

*GitHub star counts not independently verified - should not be primary decision criterion.*

### 2.2 Key Architectural Insights

#### From OpenClaw: Accessibility Tree > DOM Selectors

OpenClaw and modern tools use the **Accessibility Tree** instead of CSS selectors:

| Traditional | Accessibility-Based |
|-------------|---------------------|
| `[data-uia="cancel"]` | `button "Cancel Membership"` |
| `.btn.btn-primary` | `button "Submit"` |
| Breaks on class changes | Survives restructuring |

**Key benefit:** 80-90% smaller token usage, stable across layout changes.

#### From OpenClaw: Connecting to Existing Browser Sessions

OpenClaw's Extension Relay mode enables controlling a user's existing logged-in Chrome:
- No re-authentication needed
- Access to existing cookies/sessions
- User clicks extension icon to "attach" tab

**We can achieve this with Playwright's CDP connection** (no OpenClaw dependency).

### 2.3 Current Generalization Analysis

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

## 3. Proposed Improvements

### 3.1 Browser Session Reuse (CDP Connection)

**Problem:** Users must log into Netflix every run.

**Solution:** Add CDP connection support to `PlaywrightBrowser`:

```python
async def launch(self, cdp_url: str | None = None, user_data_dir: str | None = None) -> None:
    """Launch browser or connect to existing via CDP.

    Args:
        cdp_url: Connect to existing Chrome (e.g., "http://localhost:9222")
        user_data_dir: Use persistent browser profile for session persistence
    """
    self._playwright = await async_playwright().start()

    if cdp_url:
        # Connect to user's existing Chrome
        self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        contexts = self._browser.contexts
        self._page = contexts[0].pages[0] if contexts and contexts[0].pages else await contexts[0].new_page()
    elif user_data_dir:
        # Persistent profile (saves login state between runs)
        context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir, headless=self.headless
        )
        self._page = context.pages[0] if context.pages else await context.new_page()
    else:
        # Current behavior - new instance
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)
```

**User workflow options:**
1. **CDP:** Start Chrome with `--remote-debugging-port=9222`, run SubTerminator with `--cdp-url`
2. **Persistent:** First run logs in, subsequent runs reuse saved session

### 3.2 Accessibility-Based Element Selection (ARIA Fallback)

**Problem:** CSS selectors break when Netflix changes class names/attributes.

**Solution:** Add ARIA-based fallback to `PlaywrightBrowser.click()`:

```python
async def click(
    self,
    selector: str | list[str],
    fallback_role: tuple[str, str] | None = None
) -> None:
    """Click element. Falls back to accessibility role if selectors fail.

    Args:
        selector: CSS selector(s) to try
        fallback_role: (role, name) for accessibility-based fallback
                       e.g., ("button", "Cancel Membership")
    """
    # Try CSS selectors first (current behavior)
    selectors = [selector] if isinstance(selector, str) else selector
    for sel in selectors:
        try:
            element = await self._page.wait_for_selector(sel, timeout=5000)
            if element:
                await element.scroll_into_view_if_needed()
                await element.click()
                return
        except Exception:
            continue

    # Fallback to accessibility-based selection
    if fallback_role:
        role, name = fallback_role
        try:
            await self._page.get_by_role(role, name=name).click()
            return
        except Exception:
            pass

    raise ElementNotFound(f"Element not found: selectors={selectors}, role={fallback_role}")
```

**Service selector format update:**
```python
SELECTORS = {
    "cancel_link": {
        "css": ["[data-uia='action-cancel-membership']"],
        "role": ("link", "Cancel Membership"),
    },
    "finish_button": {
        "css": ["[data-uia='confirm-cancel-btn']"],
        "role": ("button", "Finish Cancellation"),
    },
}
```

### 3.3 Service-Agnostic Refactoring

**Problem:** Engine and CLI hardcode `NetflixService`.

**Solution:** Two changes:

#### 3.3.1 Engine Type Fix

```python
# engine.py - Change line 70
# FROM:
def __init__(self, service: NetflixService, ...):

# TO:
def __init__(self, service: ServiceProtocol, ...):
```

Also remove `from subterminator.services.netflix import NetflixService` import.

#### 3.3.2 Service Factory Pattern

```python
# services/__init__.py or registry.py
from subterminator.services.netflix import NetflixService
# from subterminator.services.spotify import SpotifyService  # Future

SERVICE_FACTORY: dict[str, Callable[[str], ServiceProtocol]] = {
    "netflix": lambda target: NetflixService(target=target),
    # "spotify": lambda target: SpotifyService(target=target),  # Future
}

def create_service(service_id: str, target: str = "live") -> ServiceProtocol:
    """Factory function to create service instances."""
    if service_id not in SERVICE_FACTORY:
        raise ValueError(f"Unknown service: {service_id}")
    return SERVICE_FACTORY[service_id](target)
```

#### 3.3.3 CLI Update

```python
# cli/main.py - Replace hardcoded instantiation
# FROM:
service_obj = NetflixService(target=target)

# TO:
from subterminator.services import create_service
service_obj = create_service(selected_service, target=target)
```

## 4. Implementation Plan

### Phase 1: Browser Improvements (Recommended for Assessment)

| Task | Effort | Impact |
|------|--------|--------|
| Add CDP connection to `PlaywrightBrowser` | 2 hours | Eliminates re-login friction |
| Add ARIA fallback to `click()` | 2 hours | Survives UI changes |
| Add `--cdp-url` CLI flag | 30 min | User-facing feature |
| Update Netflix selectors with role fallbacks | 1 hour | Immediate robustness |

**Total: ~5-6 hours**

### Phase 2: Service Generalization (Post-Assessment)

| Task | Effort | Impact |
|------|--------|--------|
| Fix engine type annotation | 10 min | Removes type coupling |
| Create service factory | 30 min | Enables dynamic service creation |
| Update CLI to use factory | 30 min | Service selection works |
| Make checkpoint messages generic | 30 min | No "Netflix" in prompts |

**Total: ~2 hours**

### Phase 3: Multi-Service Expansion (Future)

| Task | Effort | Impact |
|------|--------|--------|
| Create SpotifyService | 2 hours | Second service support |
| Create Spotify mock pages | 2 hours | Testing capability |
| Create HuluService | 2 hours | Third service |
| Tune heuristics per service | 2 hours | Faster detection |

**Total: ~8 hours per service**

## 5. Success Criteria

1. **Session Reuse**: User can connect to existing logged-in Chrome via CDP
2. **Selector Resilience**: When CSS selectors fail, ARIA fallback finds element
3. **Service Agnostic**: Engine accepts any `ServiceProtocol` implementation
4. **No Regression**: All existing tests pass
5. **Testable**: Mock pages can test ARIA fallback with modified selectors

## 6. Out of Scope

- Full OpenClaw integration (stability concerns)
- Full Skyvern integration (infrastructure complexity)
- Browser-Use integration (can add later as additional fallback)
- Proxy rotation / anti-bot features
- CAPTCHA solving

## 7. Trade-off Analysis

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

## 8. References

- [Playwright ARIA Snapshots](https://playwright.dev/docs/aria-snapshots)
- [Playwright Locators - getByRole](https://playwright.dev/docs/locators#locate-by-role)
- [Playwright CDP Connection](https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp)
- [OpenClaw Browser Documentation](https://docs.openclaw.ai/tools/browser)
- [Browser-Use GitHub](https://github.com/browser-use/browser-use)
- [Skyvern GitHub](https://github.com/Skyvern-AI/skyvern)
- [CDP Accessibility Domain](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/)
- [Puppetaria: Accessibility-first Automation](https://developer.chrome.com/blog/puppetaria/)
