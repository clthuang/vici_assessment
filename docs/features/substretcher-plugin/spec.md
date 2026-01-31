# Specification: SubStretcher Plugin

**Feature ID:** substretcher-plugin
**Version:** 1.0
**Date:** 2026-01-31
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

SubStretcher Plugin is a standalone CLI tool that automates subscription billing extraction and optional auto-cancellation. It connects to the user's running Chrome browser to navigate subscription service billing pages, extract billing information using AI-powered analysis, and optionally execute cancellation workflows.

### 1.2 Problem Statement

Users managing multiple subscriptions face these challenges:
- Billing information is scattered across different services
- Each service has unique UI patterns and navigation paths
- Manual cancellation workflows are tedious and vary by service
- No unified view of subscription costs and renewal dates

### 1.3 Solution

A CLI tool that:
1. Connects to user's existing Chrome browser (reusing logged-in sessions)
2. Navigates to billing pages using service-specific configurations
3. Uses Claude Vision to extract billing data regardless of UI changes
4. Optionally automates cancellation with user confirmation

---

## 2. Functional Requirements

### 2.1 Core Features

#### FR-1: Browser Connection
- **FR-1.1**: Connect to Chrome via remote debugging port (9222)
- **FR-1.2**: Detect if Chrome is running with debug mode enabled
- **FR-1.3**: Provide clear instructions if Chrome not available in debug mode
- **FR-1.4**: Support multiple tabs/pages within the connected browser

#### FR-2: Service Navigation
- **FR-2.1**: Load service configurations from YAML/JSON files
- **FR-2.2**: Navigate directly to billing URLs when provided
- **FR-2.3**: Follow navigation hints when direct URL unavailable
- **FR-2.4**: Detect and handle redirects (login walls, region blocks)

#### FR-3: Authentication Detection
- **FR-3.1**: Detect logged-in vs logged-out state using AI analysis
- **FR-3.2**: Prompt user to log in manually when login required
- **FR-3.3**: Wait for user confirmation before proceeding
- **FR-3.4**: Support skipping services when user declines to log in

#### FR-4: Billing Information Extraction
- **FR-4.1**: Capture screenshot of billing page
- **FR-4.2**: Use Claude Vision to analyze and extract:
  - Subscription status (active, cancelled, paused, trial)
  - Renewal/billing date
  - Cost (amount, currency, billing cycle)
  - Payment method (masked, e.g., "Visa ending 1234")
- **FR-4.3**: Return confidence score (0-1) for each extraction
- **FR-4.4**: Support hybrid extraction (CSS selectors + AI fallback)

#### FR-5: Auto-Cancellation (Opt-in)
- **FR-5.1**: Require explicit `--cancel` flag to enable cancellation mode
- **FR-5.2**: Show pre-cancellation summary (what will happen, end date)
- **FR-5.3**: Require `--confirm` or interactive confirmation before action
- **FR-5.4**: Execute cancellation steps using AI-guided navigation
- **FR-5.5**: Detect and report cancellation success/failure
- **FR-5.6**: Log all cancellation actions to audit trail

#### FR-6: Output & Export
- **FR-6.1**: Display results in CLI with formatted table
- **FR-6.2**: Export to JSON file (`--output results.json`)
- **FR-6.3**: Export to CSV file (`--output results.csv`)
- **FR-6.4**: Include timestamps for all extracted data

### 2.2 CLI Interface

```
substretcher <command> [services...] [options]

Commands:
  scan      Extract billing info from specified services
  cancel    Cancel subscription for specified service
  list      List available service configurations
  status    Show connection status to Chrome

Options:
  --output, -o <file>    Export results to file (JSON/CSV)
  --confirm              Skip confirmation prompts (for cancel)
  --verbose, -v          Show detailed progress
  --timeout <ms>         Page load timeout (default: 30000)
  --help, -h             Show help

Examples:
  substretcher scan netflix spotify
  substretcher scan --all --output subscriptions.json
  substretcher cancel netflix --confirm
  substretcher list
```

### 2.3 Service Configuration Schema

```yaml
# services/netflix.yaml
id: netflix
name: Netflix
domain: netflix.com
billingUrl: https://www.netflix.com/account

# Optional navigation hints
navigation:
  steps:
    - description: "Click profile icon"
      selector: "[data-uia='account-profile-link']"
    - description: "Click Account"
      selector: "[href*='/account']"

# Optional extraction hints (speeds up when UI is stable)
extraction:
  status:
    selector: ".membership-info .membership-status"
  renewalDate:
    selector: ".next-billing-date"
  cost:
    selector: ".plan-price"

# Cancellation flow
cancellation:
  enabled: true
  steps:
    - action: click
      description: "Cancel Membership button"
      selector: "[data-uia='cancel-button']"
    - action: click
      description: "Finish Cancellation"
      selector: "[data-uia='finish-cancellation']"
  successIndicator:
    text: "Your membership will end"
```

---

## 3. Non-Functional Requirements

### 3.1 Performance
- **NFR-1**: Page navigation timeout configurable (default 30s)
- **NFR-2**: AI extraction should complete within 10 seconds per page
- **NFR-3**: Multi-service scans run sequentially (not parallel) to avoid rate limiting

### 3.2 Security
- **NFR-4**: Never store or transmit user credentials
- **NFR-5**: Screenshots processed via Claude API, not stored locally
- **NFR-6**: Audit logs contain action descriptions, not sensitive data
- **NFR-7**: All cancellation actions require explicit user opt-in

### 3.3 Reliability
- **NFR-8**: Graceful handling when extraction fails (return partial data with low confidence)
- **NFR-9**: Clear error messages for common failure modes
- **NFR-10**: Resume capability for multi-service scans (skip completed services)

### 3.4 Extensibility
- **NFR-11**: Add new services via config files, no code changes required
- **NFR-12**: Service configs loadable from custom directory

---

## 4. Data Models

### 4.1 Billing Info

```typescript
interface BillingInfo {
  serviceId: string;
  serviceName: string;
  status: 'active' | 'cancelled' | 'paused' | 'trial' | 'unknown';
  renewalDate: string | null;  // ISO 8601 date
  cost: {
    amount: number;
    currency: string;  // ISO 4217 code (USD, EUR, etc.)
    cycle: 'weekly' | 'monthly' | 'annual' | 'unknown';
  } | null;
  paymentMethod: string | null;  // Masked, e.g., "Visa ****1234"
  confidence: number;  // 0-1
  extractedAt: string;  // ISO 8601 timestamp
  errors: string[];    // Any extraction warnings/errors
}
```

### 4.2 Service Config

```typescript
interface ServiceConfig {
  id: string;
  name: string;
  domain: string;
  billingUrl: string;
  navigation?: {
    steps: NavigationStep[];
  };
  extraction?: {
    status?: { selector: string };
    renewalDate?: { selector: string };
    cost?: { selector: string };
  };
  cancellation?: {
    enabled: boolean;
    steps: CancellationStep[];
    successIndicator: {
      text?: string;
      selector?: string;
    };
  };
}
```

### 4.3 Scan Result

```typescript
interface ScanResult {
  scannedAt: string;  // ISO 8601 timestamp
  services: BillingInfo[];
  summary: {
    total: number;
    successful: number;
    failed: number;
    skipped: number;
    totalMonthlyCost: number;  // Normalized to monthly
    currency: string;
  };
}
```

---

## 5. Acceptance Criteria

### AC-1: Chrome Connection
- [ ] Tool detects when Chrome is not running with debug port
- [ ] Clear error message with instructions to launch Chrome correctly
- [ ] Successful connection shows "Connected to Chrome" message

### AC-2: Single Service Scan
- [ ] `substretcher scan netflix` navigates to Netflix billing page
- [ ] Extracts status, renewal date, and cost
- [ ] Displays formatted result in terminal
- [ ] Handles login-required state gracefully

### AC-3: Multi-Service Scan
- [ ] `substretcher scan netflix spotify chatgpt` processes all three
- [ ] Shows progress for each service
- [ ] Summarizes total monthly cost at end
- [ ] Continues to next service if one fails

### AC-4: JSON Export
- [ ] `substretcher scan --all -o subs.json` creates valid JSON file
- [ ] JSON matches ScanResult schema
- [ ] File is human-readable (pretty-printed)

### AC-5: Service Configuration
- [ ] `substretcher list` shows all available service configs
- [ ] Adding new YAML file to services/ makes it available
- [ ] Invalid config files show clear validation errors

### AC-6: Auto-Cancel
- [ ] `substretcher cancel netflix` shows warning and prompts for confirmation
- [ ] Without `--confirm`, user must type 'yes' to proceed
- [ ] With `--confirm`, proceeds automatically
- [ ] Shows success/failure message after cancellation attempt
- [ ] Audit log entry created for the action

### AC-7: Login Handling
- [ ] Tool detects login wall and pauses
- [ ] Prompts user: "Please log in to Netflix and press Enter"
- [ ] After login, continues extraction
- [ ] User can press 'q' to skip service

### AC-8: Error Handling
- [ ] Network timeout shows "Connection timed out" message
- [ ] Page not found shows "Could not navigate to billing page"
- [ ] AI extraction failure returns partial data with confidence < 0.5
- [ ] All errors logged to stderr, not stdout

---

## 6. Scope Boundaries

### 6.1 In Scope
- CLI interface for scanning and cancellation
- Chrome DevTools Protocol integration
- Claude Vision for page analysis
- YAML-based service configuration
- JSON/CSV export
- Audit logging for cancellation actions

### 6.2 Out of Scope
- Chrome extension implementation
- GUI/web interface
- SubStretcher sync (future enhancement)
- Automatic service discovery
- Multi-browser support (Firefox, Safari)
- Headless mode (requires visible browser)
- Credential management

### 6.3 Future Considerations
- SubStretcher extension sync via local API
- Scheduled scans via cron/launchd
- Notification when subscription is about to renew
- Cost trend analysis over time

---

## 7. Dependencies

### 7.1 External Dependencies
- **Chrome browser** with remote debugging enabled
- **Claude API** with vision capability
- **chrome-devtools MCP** for browser automation

### 7.2 Internal Dependencies
- Service configuration files (YAML)
- TypeScript runtime (Node.js 18+)

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Service UI changes break extraction | Medium | High | AI-first approach resilient to changes |
| Cancellation flow changes | High | Medium | AI-guided navigation adapts; fallback to manual |
| Rate limiting by services | Low | Medium | Sequential processing with delays |
| Chrome debug port security | Medium | Low | Document security implications; local-only by default |
| Claude API costs | Low | High | Cache screenshots; batch similar pages |

---

## 9. Test Strategy

### 9.1 Unit Tests
- Service config parsing and validation
- Data model transformations
- CLI argument parsing

### 9.2 Integration Tests
- Chrome connection lifecycle
- Screenshot capture and AI extraction (with mock)
- Export file generation

### 9.3 E2E Tests (Manual)
- Full scan workflow on 2-3 real services
- Cancellation flow on test account
- Error recovery scenarios

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Services supported at launch | 4-6 (Netflix, Spotify, ChatGPT, YouTube) |
| Extraction accuracy | >90% for supported services |
| Time to scan single service | <30 seconds |
| Cancellation success rate | >80% when service supports it |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-31 | Claude | Initial specification |
