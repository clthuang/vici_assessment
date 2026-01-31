# Architecture

## Overview

SubStretcher follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  src/cli/                                                    │
│  - Command parsing (Commander.js)                            │
│  - Output formatting (tables, spinners)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                       │
│  src/orchestrator/                                           │
│  - ScanOrchestrator: Multi-service scanning                  │
│  - CancelOrchestrator: Cancellation workflows                │
│  - ResumeManager: State persistence                          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│     Browser Layer        │     │      AI Layer            │
│  src/browser/            │     │  src/ai/                 │
│  - ChromeDevToolsAdapter │     │  - ClaudeAIExtractor     │
│  - CDP connection        │     │  - Vision API calls      │
│  - Page automation       │     │  - Prompt templates      │
└─────────────────────────┘     └─────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│  src/infra/                                                  │
│  - ErrorHandler: Error classification                        │
│  - AuditLogger: Secure logging                               │
│  - FileExporter: JSON/CSV export                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│  src/config/                                                 │
│  - YAMLConfigLoader: Service config loading                  │
│  - Zod schemas: Validation                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Types Layer                             │
│  src/types/                                                  │
│  - Type definitions                                          │
│  - Shared interfaces                                         │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### CLI Layer (`src/cli/`)

Entry point for user interaction.

| Module | Purpose |
|--------|---------|
| `index.ts` | Commander.js program definition |
| `commands/scan.ts` | Scan command handler |
| `commands/cancel.ts` | Cancel command handler |
| `commands/list.ts` | List services command |
| `commands/status.ts` | Connection status command |
| `output/table.ts` | Table formatting with cli-table3 |
| `output/progress.ts` | Spinner utilities with ora |

### Orchestration Layer (`src/orchestrator/`)

Coordinates browser and AI operations.

| Module | Purpose |
|--------|---------|
| `ScanOrchestrator` | Multi-service scan workflow |
| `CancelOrchestrator` | Cancellation workflow with confirmation |
| `ResumeManager` | Persist/restore scan progress |

**Key patterns:**
- Dependency injection for browser and AI adapters
- Resume state management for interrupted operations
- User prompts for login walls and confirmations

### Browser Layer (`src/browser/`)

Browser automation via Chrome DevTools Protocol.

| Module | Purpose |
|--------|---------|
| `BrowserAdapter` | Interface for browser operations |
| `ChromeDevToolsAdapter` | CDP implementation |
| `errors.ts` | Browser-specific errors |

**Key operations:**
- `connect()` - Connect to Chrome debug port
- `navigateTo(url)` - Navigate with timeout
- `takeScreenshot()` - Capture viewport
- `click(selector)` - Click element
- `clickAt(x, y)` - Click coordinates (for AI-guided clicks)
- `type(text)` - Type into focused element
- `waitForSelector(selector)` - Wait for element

### AI Layer (`src/ai/`)

AI-powered extraction using Claude Vision.

| Module | Purpose |
|--------|---------|
| `AIExtractor` | Interface for AI operations |
| `ClaudeAIExtractor` | Anthropic API implementation |
| `prompts.ts` | Prompt templates |

**Key operations:**
- `extractBillingInfo(screenshot, serviceName)` - Extract billing data
- `isLoggedIn(screenshot)` - Detect login walls
- `findElement(screenshot, description)` - Locate UI elements

### Infrastructure Layer (`src/infra/`)

Cross-cutting utilities.

| Module | Purpose |
|--------|---------|
| `ErrorHandler` | Classify and format errors |
| `AuditLogger` | JSONL audit trail with sanitization |
| `FileExporter` | JSON/CSV export |

### Configuration Layer (`src/config/`)

Service configuration loading and validation.

| Module | Purpose |
|--------|---------|
| `ConfigLoader` | Interface for config loading |
| `YAMLConfigLoader` | YAML file loader with caching |
| `schema.ts` | Zod validation schemas |

**Config search paths:**
1. `./services/` (project directory)
2. `~/.substretcher/services/` (user directory)

### Types Layer (`src/types/`)

Shared type definitions.

| Module | Purpose |
|--------|---------|
| `billing.ts` | BillingInfo, ScanResult, CancelResult |
| `config.ts` | ServiceConfig, NavigationStep, CancellationStep |
| `state.ts` | ResumeState, AuditLogEntry |
| `errors.ts` | ErrorType enum, ClassifiedError |

## Data Flow

### Scan Operation

```
User: substretcher scan netflix
         │
         ▼
┌─────────────────────┐
│ CLI parses command  │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ ScanOrchestrator    │
│ - Load config       │
│ - Check resume      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│ BrowserAdapter      │────►│ Navigate to billing │
│ - Connect to Chrome │     │ page                │
└─────────────────────┘     └─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Take screenshot     │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│ AIExtractor         │────►│ Claude Vision API   │
│ - Check auth status │     │                     │
│ - Extract billing   │     │                     │
└─────────────────────┘     └─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Format & display    │
│ results             │
└─────────────────────┘
```

### Cancel Operation

```
User: substretcher cancel netflix
         │
         ▼
┌─────────────────────┐
│ CancelOrchestrator  │
│ - Load config       │
│ - Verify cancel OK  │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Show pre-cancel     │
│ summary + confirm   │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ For each step:      │
│ - Find element (AI) │
│ - Perform action    │
│ - Wait              │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Verify success      │
│ Log to audit        │
└─────────────────────┘
```

## Error Handling

Errors are classified by `ErrorHandler`:

| ErrorType | Recoverable | User Action |
|-----------|-------------|-------------|
| `CHROME_NOT_RUNNING` | No | Start Chrome with debug port |
| `CONNECTION_LOST` | Yes | Reconnect automatically |
| `NAVIGATION_TIMEOUT` | Yes | Retry or skip service |
| `AUTH_REQUIRED` | Yes | Log in manually |
| `RATE_LIMITED` | Yes | Wait and retry |
| `CONFIG_INVALID` | No | Fix configuration |
| `SERVICE_NOT_FOUND` | No | Check service ID |

## Testing Strategy

| Layer | Test Type | Location |
|-------|-----------|----------|
| Infrastructure | Unit | `src/infra/*.test.ts` |
| Configuration | Unit | `src/config/*.test.ts` |
| Browser | Integration | Manual (requires Chrome) |
| AI | Integration | Manual (requires API key) |
| E2E | Manual | Full workflow testing |

Run tests:
```bash
pnpm test        # Unit tests
pnpm test:watch  # Watch mode
```
