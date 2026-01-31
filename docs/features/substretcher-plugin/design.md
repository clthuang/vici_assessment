# Design: SubStretcher Plugin

**Feature ID:** substretcher-plugin
**Version:** 1.1
**Date:** 2026-01-31
**Status:** Reviewed

---

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User's Machine                               │
│                                                                      │
│  ┌──────────────┐         ┌──────────────────────────────────────┐  │
│  │   Chrome     │◄───────►│        SubStretcher CLI              │  │
│  │  (Debug Port)│  CDP    │                                      │  │
│  │              │         │  ┌────────────────────────────────┐  │  │
│  │  - Netflix   │         │  │  Orchestrator                  │  │  │
│  │  - Spotify   │         │  │  - Command routing             │  │  │
│  │  - etc.      │         │  │  - Session management          │  │  │
│  └──────────────┘         │  │  - Resume state                │  │  │
│                           │  └────────────────────────────────┘  │  │
│                           │              │                        │  │
│                           │  ┌───────────┴───────────┐            │  │
│                           │  │                       │            │  │
│                           │  ▼                       ▼            │  │
│                           │  ┌──────────┐  ┌─────────────────┐   │  │
│                           │  │ Browser  │  │  AI Extraction  │   │  │
│                           │  │ Adapter  │  │  Engine         │   │  │
│                           │  └──────────┘  └─────────────────┘   │  │
│                           └──────────────────────────────────────┘  │
│                                        │                             │
│  ┌─────────────────┐                   │                             │
│  │ ~/.substretcher │◄──────────────────┘                             │
│  │  - audit.log    │                                                 │
│  │  - resume.json  │                                                 │
│  │  - services/    │                                                 │
│  └─────────────────┘                                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
                           ┌─────────────────┐
                           │   Claude API    │
                           │   (Vision)      │
                           └─────────────────┘
```

### 1.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    cli/index.ts                          │    │
│  │  - Argument parsing (commander.js)                       │    │
│  │  - Command routing                                       │    │
│  │  - Output formatting                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestration Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  ScanOrchestrator│  │CancelOrchestrator│  │ ResumeManager│   │
│  │  - Multi-service │  │  - Confirmation  │  │  - State I/O │   │
│  │  - Progress      │  │  - Step execution│  │  - Recovery  │   │
│  │  - Aggregation   │  │  - Audit logging │  │              │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  BrowserAdapter  │  │  AIExtractor     │  │ ConfigLoader │   │
│  │  - CDP connect   │  │  - Screenshot    │  │  - YAML parse│   │
│  │  - Navigation    │  │  - Claude Vision │  │  - Validation│   │
│  │  - Screenshot    │  │  - Confidence    │  │  - Merge     │   │
│  │  - Interaction   │  │                  │  │              │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  AuditLogger     │  │  FileExporter    │  │ ErrorHandler │   │
│  │  - JSONL append  │  │  - JSON pretty   │  │  - Classify  │   │
│  │  - Sanitize      │  │  - CSV format    │  │  - Recovery  │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 CLI Layer

#### cli/index.ts
**Purpose:** Entry point, argument parsing, command routing

```typescript
// Dependencies
import { Command } from 'commander';

// Interface
interface CLIOptions {
  output?: string;      // --output, -o: Export path (JSON/CSV)
  all?: boolean;        // --all: Scan all configured services
  confirm?: boolean;    // --confirm: Skip confirmation prompts
  verbose?: boolean;    // --verbose, -v: Detailed progress
  timeout?: number;     // --timeout: Page load timeout (ms)
  fresh?: boolean;      // --fresh: Ignore resume state, start fresh
}

// Commands
scan(services: string[], options: CLIOptions): Promise<void>
cancel(service: string, options: CLIOptions): Promise<void>
list(): Promise<void>
status(): Promise<void>
```

**Responsibilities:**
- Parse CLI arguments using commander.js
- Validate input (service names exist, options valid)
- Route to appropriate orchestrator
- Format and display output (tables, progress)
- Handle SIGINT for graceful shutdown

### 2.2 Orchestration Layer

#### orchestrator/ScanOrchestrator.ts
**Purpose:** Coordinate multi-service scanning with resume support

```typescript
interface ScanOrchestratorDeps {
  browserAdapter: BrowserAdapter;
  aiExtractor: AIExtractor;
  configLoader: ConfigLoader;
  resumeManager: ResumeManager;
  auditLogger: AuditLogger;
}

class ScanOrchestrator {
  constructor(deps: ScanOrchestratorDeps);

  // Main entry point
  async scan(serviceIds: string[], options: ScanOptions): Promise<ScanResult>;

  // Internal methods
  private async scanService(serviceId: string): Promise<BillingInfo>;
  private async handleLoginWall(serviceId: string): Promise<boolean>;
  private aggregateResults(results: BillingInfo[]): ScanResult;
}
```

**Flow:**
1. Load resume state (if exists and not --fresh)
2. Filter out already-completed services
3. For each service:
   a. Log scan_start
   b. Navigate to billing page
   c. Check auth state
   d. Extract billing info (or handle login)
   e. Update resume state
   f. Log scan_complete
4. Clear resume state
5. Return aggregated results

#### orchestrator/CancelOrchestrator.ts
**Purpose:** Execute cancellation workflows with safety checks

```typescript
class CancelOrchestrator {
  constructor(deps: CancelOrchestratorDeps);

  async cancel(serviceId: string, options: CancelOptions): Promise<CancelResult>;

  private async showPreCancelSummary(billing: BillingInfo): Promise<void>;
  private async confirmCancellation(skipPrompt: boolean): Promise<boolean>;
  private async executeCancellationSteps(config: ServiceConfig): Promise<boolean>;
  private async verifySuccess(config: ServiceConfig): Promise<boolean>;
}
```

**Flow:**
1. Scan service to get current billing info
2. Show pre-cancellation summary (cost, end date)
3. Prompt for confirmation (unless --confirm)
4. Log cancel_start
5. Execute each cancellation step:
   a. Log cancel_step
   b. Find element (selector or AI)
   c. Perform action
   d. Wait for navigation/state change
6. Verify success indicator
7. Log cancel_complete or cancel_failed
8. Return result

#### orchestrator/ResumeManager.ts
**Purpose:** Persist and recover scan state

```typescript
class ResumeManager {
  private statePath = '~/.substretcher/resume-state.json';

  async loadState(): Promise<ResumeState | null>;
  async saveState(state: ResumeState): Promise<void>;
  async clearState(): Promise<void>;

  isServiceCompleted(state: ResumeState, serviceId: string): boolean;
  updateWithResult(state: ResumeState, result: BillingInfo): ResumeState;
}
```

### 2.3 Service Layer

#### browser/BrowserAdapter.ts
**Purpose:** Abstract Chrome DevTools Protocol interactions

```typescript
interface BrowserAdapter {
  // Connection
  connect(port?: number): Promise<void>;
  disconnect(): Promise<void>;
  isConnected(): boolean;

  // Navigation
  navigateTo(url: string): Promise<void>;
  getCurrentUrl(): Promise<string>;
  waitForNavigation(timeout?: number): Promise<void>;

  // Screenshot
  takeScreenshot(): Promise<Buffer>;

  // Interaction
  click(selector: string): Promise<void>;
  type(selector: string, text: string): Promise<void>;
  waitForSelector(selector: string, timeout?: number): Promise<void>;

  // Page info
  getPageContent(): Promise<string>;
  evaluateScript<T>(script: string): Promise<T>;
}

class ChromeDevToolsAdapter implements BrowserAdapter {
  private cdp: CDPSession | null = null;
  private pageId: string | null = null;

  // Implementation uses chrome-devtools MCP or direct CDP
}
```

**Error Handling:**
- `ChromeNotRunningError`: Chrome not found on debug port
- `ConnectionLostError`: CDP connection dropped
- `NavigationTimeoutError`: Page load exceeded timeout
- `ElementNotFoundError`: Selector not found

#### ai/AIExtractor.ts
**Purpose:** Use Claude Vision to extract billing information

```typescript
interface AIExtractor {
  // Main extraction
  extractBillingInfo(
    screenshot: Buffer,
    serviceConfig: ServiceConfig
  ): Promise<BillingInfo>;

  // Auth detection
  isLoggedIn(screenshot: Buffer, serviceName: string): Promise<AuthState>;

  // Element finding (for cancellation)
  findElement(
    screenshot: Buffer,
    description: string
  ): Promise<ElementLocation | null>;
}

interface AuthState {
  loggedIn: boolean;
  confidence: number;
  reason: string;
}

interface ElementLocation {
  x: number;
  y: number;
  confidence: number;
}

class ClaudeAIExtractor implements AIExtractor {
  constructor(private apiKey: string);

  // Implementation
  private async callClaudeVision(
    screenshot: Buffer,
    prompt: string
  ): Promise<string>;

  private parseBillingResponse(response: string): Partial<BillingInfo>;
}
```

**Prompt Templates:**

```typescript
const EXTRACTION_PROMPT = `
Analyze this screenshot of a subscription billing page for {serviceName}.
Extract the following information:

1. Subscription Status: (active, cancelled, paused, trial, or unknown)
2. Renewal Date: The next billing date (format as ISO 8601)
3. Cost: Amount, currency, and billing cycle (weekly/monthly/annual)
4. Payment Method: Card type and last 4 digits if visible

Return as JSON:
{
  "status": "...",
  "renewalDate": "YYYY-MM-DD" or null,
  "cost": { "amount": number, "currency": "USD", "cycle": "monthly" } or null,
  "paymentMethod": "Visa ****1234" or null,
  "confidence": 0.0-1.0
}
`;

const AUTH_CHECK_PROMPT = `
Is the user logged in to {serviceName}?
Look for: profile icons, username, account menus, logged-in indicators.
Look for: login buttons, sign-in prompts, auth walls.

Return as JSON:
{
  "loggedIn": true/false,
  "confidence": 0.0-1.0,
  "reason": "explanation"
}
`;
```

#### config/ConfigLoader.ts
**Purpose:** Load and validate service configurations

```typescript
interface ConfigLoader {
  loadService(serviceId: string): Promise<ServiceConfig>;
  loadAllServices(): Promise<ServiceConfig[]>;
  validateConfig(config: unknown): ServiceConfig;
  getConfigPaths(): string[];
}

class YAMLConfigLoader implements ConfigLoader {
  private configDirs: string[] = [
    './services',                    // Project default
    '~/.substretcher/services',      // User custom
  ];

  private cache: Map<string, ServiceConfig> = new Map();

  // Implementation
  private async loadYAML(path: string): Promise<unknown>;
  private mergeWithDefaults(config: Partial<ServiceConfig>): ServiceConfig;
}
```

**Validation Schema (Zod):**

```typescript
const ServiceConfigSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  domain: z.string().min(1),
  billingUrl: z.string().url(),
  navigation: z.object({
    steps: z.array(NavigationStepSchema)
  }).optional(),
  extraction: z.object({
    status: z.object({ selector: z.string() }).optional(),
    renewalDate: z.object({ selector: z.string() }).optional(),
    cost: z.object({ selector: z.string() }).optional(),
  }).optional(),
  cancellation: z.object({
    enabled: z.boolean(),
    steps: z.array(CancellationStepSchema),
    successIndicator: z.object({
      text: z.string().optional(),
      selector: z.string().optional(),
    }),
  }).optional(),
});
```

### 2.4 Infrastructure Layer

#### infra/AuditLogger.ts
**Purpose:** Append-only audit trail for actions

```typescript
class AuditLogger {
  private logPath = '~/.substretcher/audit.log';

  async log(entry: Omit<AuditLogEntry, 'timestamp'>): Promise<void>;
  async readRecent(count: number): Promise<AuditLogEntry[]>;

  // Sanitize sensitive data before logging
  private sanitize(details: string): string;
}
```

**Sanitization Rules:**
- Strip full URLs (keep domain only)
- Mask any card numbers (keep last 4)
- Remove email addresses
- Limit string lengths

#### infra/FileExporter.ts
**Purpose:** Export results to JSON/CSV files

```typescript
class FileExporter {
  async exportJSON(result: ScanResult, path: string): Promise<void>;
  async exportCSV(result: ScanResult, path: string): Promise<void>;

  // CSV field order (from spec 4.6):
  // serviceId,serviceName,status,renewalDate,amount,currency,cycle,paymentMethod,confidence,extractedAt
  // Field mapping: cost.amount→amount, cost.currency→currency, cost.cycle→cycle
  // Null values: empty strings, errors array: omitted (JSON only)
  private formatForCSV(billing: BillingInfo): string[];
  private escapeCSV(value: string): string;
}
```

#### infra/ErrorHandler.ts
**Purpose:** Classify errors and determine recovery actions

```typescript
enum ErrorType {
  CHROME_NOT_RUNNING = 'chrome_not_running',
  CONNECTION_LOST = 'connection_lost',
  NAVIGATION_TIMEOUT = 'navigation_timeout',
  AUTH_REQUIRED = 'auth_required',
  EXTRACTION_FAILED = 'extraction_failed',
  RATE_LIMITED = 'rate_limited',
  UNKNOWN = 'unknown',
}

interface ClassifiedError {
  type: ErrorType;
  message: string;
  recoverable: boolean;
  userAction?: string;
}

class ErrorHandler {
  classify(error: Error): ClassifiedError;
  formatForUser(classified: ClassifiedError): string;
  shouldRetry(classified: ClassifiedError): boolean;
}
```

---

## 3. Data Flow Diagrams

### 3.1 Scan Flow

```
User                CLI                 ScanOrch            Browser            AI
 │                   │                     │                   │                │
 │ scan netflix      │                     │                   │                │
 │──────────────────►│                     │                   │                │
 │                   │ scan([netflix])     │                   │                │
 │                   │────────────────────►│                   │                │
 │                   │                     │ connect()         │                │
 │                   │                     │──────────────────►│                │
 │                   │                     │◄──────────────────│                │
 │                   │                     │                   │                │
 │                   │                     │ navigateTo(url)   │                │
 │                   │                     │──────────────────►│                │
 │                   │                     │◄──────────────────│                │
 │                   │                     │                   │                │
 │                   │                     │ takeScreenshot()  │                │
 │                   │                     │──────────────────►│                │
 │                   │                     │◄──────────────────│                │
 │                   │                     │                   │                │
 │                   │                     │ extractBilling(screenshot)        │
 │                   │                     │───────────────────────────────────►│
 │                   │                     │◄───────────────────────────────────│
 │                   │                     │                   │                │
 │                   │◄────────────────────│                   │                │
 │ [table output]    │                     │                   │                │
 │◄──────────────────│                     │                   │                │
```

### 3.2 Cancel Flow

```
User                CLI              CancelOrch          Browser            AI
 │                   │                   │                  │                │
 │ cancel netflix    │                   │                  │                │
 │──────────────────►│                   │                  │                │
 │                   │ cancel(netflix)   │                  │                │
 │                   │──────────────────►│                  │                │
 │                   │                   │ [scan first]     │                │
 │                   │                   │─────────────────►│───────────────►│
 │                   │                   │◄─────────────────│◄───────────────│
 │                   │                   │                  │                │
 │ [show summary]    │                   │                  │                │
 │◄──────────────────│◄──────────────────│                  │                │
 │                   │                   │                  │                │
 │ confirm? [y/N]    │                   │                  │                │
 │◄──────────────────│                   │                  │                │
 │ y                 │                   │                  │                │
 │──────────────────►│──────────────────►│                  │                │
 │                   │                   │                  │                │
 │                   │                   │ [for each step]  │                │
 │                   │                   │ findElement()    │                │
 │                   │                   │─────────────────────────────────►│
 │                   │                   │◄─────────────────────────────────│
 │                   │                   │ click(location)  │                │
 │                   │                   │─────────────────►│                │
 │                   │                   │◄─────────────────│                │
 │                   │                   │                  │                │
 │ [success/fail]    │                   │                  │                │
 │◄──────────────────│◄──────────────────│                  │                │
```

---

## 4. Directory Structure

```
substretcher-plugin/
├── src/
│   ├── cli/
│   │   ├── index.ts              # Entry point, argument parsing
│   │   ├── commands/
│   │   │   ├── scan.ts           # Scan command handler
│   │   │   ├── cancel.ts         # Cancel command handler
│   │   │   ├── list.ts           # List command handler
│   │   │   └── status.ts         # Status command handler
│   │   └── output/
│   │       ├── table.ts          # Table formatting
│   │       └── progress.ts       # Progress indicators
│   │
│   ├── orchestrator/
│   │   ├── ScanOrchestrator.ts
│   │   ├── CancelOrchestrator.ts
│   │   └── ResumeManager.ts
│   │
│   ├── browser/
│   │   ├── BrowserAdapter.ts     # Interface
│   │   ├── ChromeDevToolsAdapter.ts
│   │   └── errors.ts             # Browser-specific errors
│   │
│   ├── ai/
│   │   ├── AIExtractor.ts        # Interface
│   │   ├── ClaudeAIExtractor.ts
│   │   └── prompts.ts            # Prompt templates
│   │
│   ├── config/
│   │   ├── ConfigLoader.ts       # Interface
│   │   ├── YAMLConfigLoader.ts
│   │   └── schema.ts             # Zod schemas
│   │
│   ├── infra/
│   │   ├── AuditLogger.ts
│   │   ├── FileExporter.ts
│   │   └── ErrorHandler.ts
│   │
│   └── types/
│       ├── billing.ts            # BillingInfo, ScanResult
│       ├── config.ts             # ServiceConfig, steps
│       └── state.ts              # ResumeState, AuditLogEntry
│
├── services/                     # Built-in service configs
│   ├── netflix.yaml
│   ├── spotify.yaml
│   ├── chatgpt.yaml
│   └── youtube.yaml
│
├── tests/
│   ├── unit/
│   │   ├── config.test.ts
│   │   ├── exporter.test.ts
│   │   └── error-handler.test.ts
│   └── integration/
│       ├── browser-adapter.test.ts
│       └── ai-extractor.test.ts
│
├── package.json
├── tsconfig.json
└── README.md
```

---

## 5. Interface Contracts

### 5.1 BrowserAdapter Interface

```typescript
// browser/BrowserAdapter.ts

export interface BrowserAdapter {
  /**
   * Connect to Chrome via CDP
   * @param port - Debug port (default: 9222)
   * @throws ChromeNotRunningError if Chrome not available
   */
  connect(port?: number): Promise<void>;

  /**
   * Gracefully disconnect from Chrome
   */
  disconnect(): Promise<void>;

  /**
   * Check if currently connected
   */
  isConnected(): boolean;

  /**
   * Navigate to URL and wait for load
   * @throws NavigationTimeoutError if timeout exceeded
   */
  navigateTo(url: string, timeout?: number): Promise<void>;

  /**
   * Capture visible viewport as PNG
   * @returns Buffer containing PNG image data
   */
  takeScreenshot(): Promise<Buffer>;

  /**
   * Click element by CSS selector
   * @throws ElementNotFoundError if selector not found
   */
  click(selector: string): Promise<void>;

  /**
   * Click at specific coordinates
   */
  clickAt(x: number, y: number): Promise<void>;

  /**
   * Type text into focused element
   */
  type(text: string): Promise<void>;

  /**
   * Wait for element to appear
   * @throws ElementNotFoundError if timeout exceeded
   */
  waitForSelector(selector: string, timeout?: number): Promise<void>;

  /**
   * Wait for text to appear on page
   */
  waitForText(text: string, timeout?: number): Promise<boolean>;
}
```

### 5.2 AIExtractor Interface

```typescript
// ai/AIExtractor.ts

export interface AIExtractor {
  /**
   * Extract billing information from screenshot
   * @param screenshot - PNG image buffer
   * @param config - Service configuration with hints
   * @returns Extracted billing info with confidence score
   */
  extractBillingInfo(
    screenshot: Buffer,
    config: ServiceConfig
  ): Promise<BillingInfo>;

  /**
   * Check if user is logged in
   * @param screenshot - PNG image buffer
   * @param serviceName - Human-readable service name
   */
  isLoggedIn(
    screenshot: Buffer,
    serviceName: string
  ): Promise<AuthCheckResult>;

  /**
   * Find clickable element by description
   * Used for AI-guided cancellation when no selector available
   * @param screenshot - PNG image buffer
   * @param description - Human description of element
   * @returns Coordinates or null if not found
   */
  findElement(
    screenshot: Buffer,
    description: string
  ): Promise<ElementLocation | null>;
}

export interface AuthCheckResult {
  loggedIn: boolean;
  confidence: number;  // 0-1
  reason: string;      // Explanation for debugging
}

export interface ElementLocation {
  x: number;          // Pixel X coordinate
  y: number;          // Pixel Y coordinate
  width?: number;     // Element width (if determinable)
  height?: number;    // Element height (if determinable)
  confidence: number; // 0-1
}
```

### 5.3 ConfigLoader Interface

```typescript
// config/ConfigLoader.ts

export interface ConfigLoader {
  /**
   * Load single service by ID
   * @throws ServiceNotFoundError if not found
   * @throws ConfigValidationError if invalid
   */
  loadService(serviceId: string): Promise<ServiceConfig>;

  /**
   * Load all available services
   * Skips invalid configs (logs warning)
   */
  loadAllServices(): Promise<ServiceConfig[]>;

  /**
   * List all service IDs
   */
  listServiceIds(): Promise<string[]>;

  /**
   * Get paths being searched for configs
   */
  getConfigPaths(): string[];
}
```

---

## 6. Error Handling Strategy

### 6.1 Error Classification

| Error Type | Recoverable | User Action | Example |
|------------|-------------|-------------|---------|
| `CHROME_NOT_RUNNING` | No | Launch Chrome with --remote-debugging-port=9222 | CDP connection refused |
| `CONNECTION_LOST` | Yes (retry) | None (auto-retry) | Network hiccup |
| `NAVIGATION_TIMEOUT` | Yes (skip) | Check network | Page load > 30s |
| `AUTH_REQUIRED` | Yes (prompt) | Log in manually | Login wall detected |
| `EXTRACTION_FAILED` | Yes (partial) | None | AI couldn't parse |
| `RATE_LIMITED` | Yes (backoff) | Wait | 429 response |
| `CONFIG_INVALID` | No | Fix config file | Schema validation |

### 6.2 Recovery Strategies

```typescript
// Retry with exponential backoff
async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts || !isRetryable(error)) throw error;
      await sleep(baseDelay * Math.pow(2, attempt - 1));
    }
  }
  throw new Error('Unreachable');
}

// Graceful degradation for extraction
async function extractWithFallback(
  screenshot: Buffer,
  config: ServiceConfig
): Promise<BillingInfo> {
  try {
    return await aiExtractor.extractBillingInfo(screenshot, config);
  } catch (error) {
    return {
      serviceId: config.id,
      serviceName: config.name,
      status: 'unknown',
      renewalDate: null,
      cost: null,
      paymentMethod: null,
      confidence: 0,
      extractedAt: new Date().toISOString(),
      errors: [error.message],
    };
  }
}
```

---

## 7. Dependencies

### 7.1 Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `commander` | ^12.0.0 | CLI argument parsing |
| `chalk` | ^5.0.0 | Terminal colors |
| `cli-table3` | ^0.6.0 | Table formatting |
| `ora` | ^8.0.0 | Spinners/progress |
| `yaml` | ^2.0.0 | YAML parsing |
| `zod` | ^3.0.0 | Schema validation |
| `@anthropic-ai/sdk` | ^0.30.0 | Claude API |
| `chrome-remote-interface` | ^0.33.0 | CDP client |
| `uuid` | ^9.0.0 | Resume state IDs |

### 7.2 Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `typescript` | ^5.0.0 | Language |
| `vitest` | ^2.0.0 | Testing |
| `@types/node` | ^20.0.0 | Node types |
| `tsx` | ^4.0.0 | TS execution |
| `eslint` | ^9.0.0 | Linting |

### 7.3 External Dependencies

- **Chrome browser**: User must have Chrome installed
- **Claude API**: Requires `ANTHROPIC_API_KEY` environment variable
- **Node.js**: v18+ required (for fetch, native ESM)

---

## 8. Security Considerations

### 8.1 Credential Handling
- **Never** accept or store user passwords
- Rely entirely on existing browser sessions
- Clear warning if user attempts to pass credentials

### 8.2 Screenshot Privacy
- Screenshots sent to Claude API over HTTPS
- Not persisted to disk
- Not logged in audit trail

### 8.3 Audit Log Sanitization
- Strip full URLs (domain only)
- Mask card numbers (show last 4)
- Remove email addresses
- Truncate long strings

### 8.4 Debug Port Security
- Default to localhost only (127.0.0.1:9222)
- Document risk of exposing debug port
- Recommend firewall rules

---

## 9. Testing Strategy

### 9.1 Unit Tests

**ConfigLoader tests:**
```typescript
describe('YAMLConfigLoader', () => {
  it('loads valid service config');
  it('throws on missing required fields');
  it('merges with defaults');
  it('searches multiple directories');
});
```

**ErrorHandler tests:**
```typescript
describe('ErrorHandler', () => {
  it('classifies CDP connection errors');
  it('classifies timeout errors');
  it('determines retry eligibility');
});
```

### 9.2 Integration Tests (with mocks)

**BrowserAdapter tests:**
```typescript
describe('ChromeDevToolsAdapter', () => {
  it('connects to Chrome on debug port');
  it('navigates and waits for load');
  it('captures screenshot as PNG');
  it('handles connection loss gracefully');
});
```

**AIExtractor tests:**
```typescript
describe('ClaudeAIExtractor', () => {
  // Use recorded responses
  it('extracts billing from Netflix screenshot');
  it('detects logged-out state');
  it('handles ambiguous pages gracefully');
});
```

### 9.3 E2E Tests (manual checklist)

- [ ] Full scan of Netflix with valid login
- [ ] Scan with login wall → prompt → continue
- [ ] Multi-service scan with one failure
- [ ] Cancel flow on test account
- [ ] Resume interrupted scan
- [ ] JSON/CSV export verification

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude API rate limits | Scan delays | Implement backoff, cache screenshots |
| Site layout changes | Extraction fails | AI-first design adapts; low confidence fallback |
| CDP API changes | Build breaks | Pin chrome-remote-interface version |
| User closes Chrome mid-scan | Lost progress | Resume state persisted after each service |
| Cancellation clicks wrong element | Unintended action | Confirmation prompt, audit logging |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-31 | Claude | Initial design |
| 1.1 | 2026-01-31 | Claude | Added --fresh flag documentation, CSV field mapping comments |
