# Brainstorm: VICI Claude Code 7-Day Challenge

**Date:** 2026-01-31
**Status:** Ready for Promotion

## Context

VICI assessment challenge - build one project in 7 days using Claude Code to demonstrate:
- Engineering design thinking
- Code quality and maintainability
- AI tool integration into practical products/workflows

## Challenge Options

### Easy: US Stock Backtesting System (美股回測系統)
- Historical stock data analysis
- Strategy testing framework
- Performance metrics and visualization

### Medium (Option A): Claude CLI → LiteLLM Endpoint
- Wrap Claude CLI as OpenAI-compatible API
- Enable use with tools expecting OpenAI format
- Proxy/adapter pattern

### Medium (Option B): GitHub CI/CD → Claude Skills
- Package GitHub Actions workflows as Claude Skills
- Enable Claude to trigger/manage CI/CD pipelines

### Hard: Browser Automation Tasks
- Examples: THSR ticket booking, NotebookLM presentations
- Requires handling auth, dynamic content, timing

---

## Selected Direction: SubStretcher Plugin

### Concept
A **standalone browser automation tool** that complements SubStretcher by:
- Navigating to subscription billing pages
- Extracting billing data (status, renewal date, cost)
- Auto-cancelling subscriptions (user opt-in)

### Why Standalone (not Chrome extension)?
- Cleaner demo for VICI assessment
- Uses Claude Code's chrome-devtools MCP directly
- No extension installation friction
- Can be run on-demand or scheduled

### Key User Flow
```
1. User runs plugin with target service(s)
2. Plugin opens browser, navigates to billing page
3. AI extracts subscription info
4. If auto-cancel enabled: walks through cancellation flow
5. Results saved/synced to SubStretcher (or standalone output)
```

---

## Feature: Intelligent Billing Extraction + Auto-Cancel

### Core Capabilities

| Capability | Description | AI Value |
|------------|-------------|----------|
| **Navigate to Billing** | From any page → billing page for a service | Handles varied site structures |
| **Extract Status** | Active, cancelled, paused, trial | Interprets varied UI patterns |
| **Extract Renewal Date** | Next billing date | Parses multiple date formats |
| **Extract Cost** | Price + currency + billing cycle | Handles localized formats |
| **Auto-Cancel** | Opt-in automated cancellation | Navigates multi-step flows |

### Auto-Cancel Design
- **Opt-in per service**: User explicitly enables auto-cancel for each subscription
- **Confirmation before action**: "About to cancel Netflix. Proceed? [Y/n]"
- **Rollback info**: Shows what will happen (e.g., "Access until Feb 15")
- **Audit trail**: Logs every action taken

### Why This Shows Engineering Design

1. **AI as Interpreter**: Sites don't have APIs - AI must read the page like a human
2. **Graceful Degradation**: When AI unsure, pause and ask user
3. **Extensibility**: Add new services via config, not code changes
4. **Safety First**: Auto-cancel requires explicit opt-in + confirmation

---

## Service Inventory Strategy

### Approach: Config-Driven with AI Fallback
```yaml
# Each service is a config file
services/
  netflix.yaml
  spotify.yaml
  chatgpt.yaml
  ...
```

### Service Config Structure
```yaml
id: netflix
name: Netflix
domain: netflix.com
billingUrl: https://www.netflix.com/account

# Navigation hints (optional - AI can figure it out)
navigation:
  - selector: "[data-uia='account-profile-link']"
    fallback: "Click profile icon"
  - selector: "[href*='billing']"
    fallback: "Click Membership & Billing"

# Extraction hints (optional - AI interprets page)
extraction:
  status:
    selector: ".membership-status"
    patterns: ["active", "cancelled", "on hold"]
  renewalDate:
    selector: ".next-billing-date"
    formats: ["MMMM D, YYYY", "MM/DD/YYYY"]
  cost:
    selector: ".plan-price"

# Auto-cancel flow
cancellation:
  enabled: true
  steps:
    - action: click
      target: "Cancel Membership button"
    - action: click
      target: "Finish Cancellation"
  confirmation: "Your membership will end on {endDate}"
```

### Inventory Priority (for demo)
| Priority | Service | Why |
|----------|---------|-----|
| P0 | Netflix | Well-known, stable UI |
| P0 | Spotify | Popular, different patterns |
| P1 | ChatGPT | Tech-savvy audience |
| P1 | YouTube Premium | Google ecosystem |
| P2 | Disney+ | Different billing flow |
| P2 | Cursor | Developer relevance |
| P3+ | Others | As time permits |

---

## Technical Approach Options

### Option A: Content Script + Selectors (Traditional)
```
User clicks "Sync" → Content script injected → CSS selectors extract data
```
**Pros**: Fast, no external dependencies
**Cons**: Brittle (selector changes break it), per-site maintenance

### Option B: Claude Vision + Screenshot (AI-First)
```
User clicks "Sync" → Screenshot taken → Claude analyzes image → Returns structured data
```
**Pros**: Resilient to UI changes, works on any site
**Cons**: Slower, requires API calls, cost per extraction

### Option C: Hybrid (Recommended)
```
1. Try CSS selectors first (fast path)
2. If extraction fails/uncertain → fall back to Claude Vision
3. Claude validates and fills gaps
```
**Pros**: Best of both worlds - fast when possible, smart when needed
**Cons**: More complex implementation

---

## Implementation Sketch

### Phase 1: Navigation
```typescript
// Service config defines paths
{
  "netflix": {
    "billingPath": ["Account", "Membership & Billing"],
    "billingUrl": "https://www.netflix.com/account"
  }
}

// Content script or browser automation navigates
async function navigateToBilling(serviceId: string) {
  const service = getService(serviceId);
  if (currentUrl.includes(service.domain)) {
    // Already on site - follow navigation steps
    await followNavigationPath(service.billingPath);
  } else {
    // Open billing URL directly
    await chrome.tabs.create({ url: service.billingUrl });
  }
}
```

### Phase 2: Extraction
```typescript
interface BillingInfo {
  status: 'active' | 'cancelled' | 'paused' | 'trial' | 'unknown';
  renewalDate: string | null;      // ISO date
  cost: {
    amount: number;
    currency: string;
    cycle: 'monthly' | 'annual' | 'weekly';
  } | null;
  paymentMethod: string | null;    // "Visa ending 1234"
  confidence: number;              // 0-1, AI's confidence in extraction
  extractedAt: string;             // timestamp
}

async function extractBillingInfo(serviceId: string): Promise<BillingInfo> {
  // 1. Try CSS selectors
  const selectorResult = await trySelectorsExtraction(serviceId);
  if (selectorResult.confidence > 0.9) return selectorResult;

  // 2. Fall back to AI vision
  const screenshot = await captureVisibleTab();
  const aiResult = await analyzeWithClaude(screenshot, serviceId);

  // 3. Merge results, prefer higher confidence
  return mergeExtractions(selectorResult, aiResult);
}
```

### Phase 3: Auto-Cancel Flow
```typescript
// Multi-step cancellation with AI guidance
async function guideCancellation(serviceId: string) {
  const steps = getService(serviceId).cancellationSteps;

  for (const step of steps) {
    // AI identifies the element to click
    const element = await findElementByDescription(step.description);

    if (step.requiresConfirmation) {
      await promptUser(`Click "${step.label}" to continue`);
    }

    await element.click();
    await waitForNavigation();
  }
}
```

---

## Architecture: SubStretcher Plugin

```
┌─────────────────────────────────────────────────────────────┐
│                   SubStretcher Plugin                        │
│              (Standalone CLI / Claude Skill)                 │
├─────────────────────────────────────────────────────────────┤
│  CLI Interface                                               │
│  - `substretcher scan netflix spotify`                      │
│  - `substretcher cancel netflix --confirm`                  │
│  - Interactive mode for multi-service scan                  │
├─────────────────────────────────────────────────────────────┤
│  Orchestrator                                                │
│  - Loads service configs                                    │
│  - Manages browser session                                  │
│  - Coordinates extraction + cancellation                    │
├─────────────────────────────────────────────────────────────┤
│  Browser Automation Layer                                    │
│  - Uses chrome-devtools MCP (or Playwright fallback)        │
│  - Screenshot capture                                       │
│  - Element interaction                                      │
├─────────────────────────────────────────────────────────────┤
│  AI Extraction Engine                                        │
│  - Claude Vision analyzes screenshots                       │
│  - Interprets page content                                  │
│  - Decides next actions                                     │
├─────────────────────────────────────────────────────────────┤
│  Service Configs (YAML/JSON)                                │
│  - Per-service navigation hints                             │
│  - Extraction selectors (optional)                          │
│  - Cancellation flows                                       │
├─────────────────────────────────────────────────────────────┤
│  Output                                                      │
│  - JSON/CSV export                                          │
│  - Sync to SubStretcher extension (optional)                │
│  - Audit log of all actions                                 │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Language**: TypeScript (consistency with SubStretcher)
- **Browser Control**: chrome-devtools MCP (primary) or Playwright (fallback)
- **AI**: Claude API with vision capability
- **Config**: YAML service definitions
- **Output**: JSON results, optional SubStretcher sync

---

## VICI Criteria Alignment

| Criteria | How This Demonstrates It |
|----------|-------------------------|
| **Engineering Design** | Config-driven services, AI fallback pattern, safety-first auto-cancel |
| **Code Quality** | Clean separation (orchestrator/browser/AI), testable components |
| **AI Integration** | Claude Vision as the "brain" - interprets pages, makes decisions |

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Scope | Inventory-driven - add services to demonstrate breadth |
| Auto-Cancel | Fully automated with explicit opt-in + confirmation |
| Integration | Standalone plugin (not Chrome extension) |
| Tech | TypeScript + chrome-devtools MCP + Claude Vision |

## Remaining Considerations

1. **Auth Handling**: User must be logged in; plugin detects logged-out state and prompts
2. **Rate Limiting**: Respect sites' terms, add delays between actions
3. **Error Recovery**: What happens when cancellation flow changes mid-stream?

---

## Next Steps

Ready to promote to feature and begin specification phase:
1. Create feature directory structure
2. Write formal spec with acceptance criteria
3. Design architecture in detail
4. Create implementation plan

Use `/specify` to continue.

