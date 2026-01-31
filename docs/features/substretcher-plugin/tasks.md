# Implementation Tasks: SubStretcher Plugin

**Feature ID:** substretcher-plugin
**Version:** 1.0
**Date:** 2026-01-31
**Status:** Reviewed

Each task is designed to be completable in ~15 minutes or less.

---

## Legend

- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Complete
- `[!]` - Blocked

---

## Phase 1: Project Foundation

### 1.1 Initialize Project

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 1.1.1 | Create directory structure | `src/{cli,orchestrator,browser,ai,config,infra,types}` folders exist | 5m |
| 1.1.2 | Initialize package.json | `pnpm init` with name `substretcher`, version `0.1.0`, type `module` | 3m |
| 1.1.3 | Configure tsconfig.json | ES2022 target, strict mode, ESM, outDir `dist`, rootDir `src` | 5m |
| 1.1.4 | Create .gitignore | Includes: node_modules, dist, .env, *.log, .DS_Store | 2m |
| 1.1.5 | Add ESLint config | `eslint.config.js` with TypeScript rules, runs without errors | 5m |

**Checkpoint:** `pnpm tsc --noEmit` runs (even with no files)

### 1.2 Install Dependencies

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 1.2.1 | Install runtime deps | `pnpm add commander chalk cli-table3 ora yaml zod @anthropic-ai/sdk chrome-remote-interface uuid` succeeds | 3m |
| 1.2.2 | Install dev deps | `pnpm add -D typescript vitest @types/node tsx eslint` succeeds | 3m |
| 1.2.3 | Add npm scripts | `build`, `dev`, `test`, `lint` scripts in package.json | 5m |

**Checkpoint:** `pnpm build` produces empty dist folder

### 1.3 Define Type Definitions

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 1.3.1 | Create billing types | `src/types/billing.ts` with BillingInfo, ScanResult, CancelResult interfaces | 10m |
| 1.3.2 | Create config types | `src/types/config.ts` with ServiceConfig, NavigationStep, CancellationStep | 10m |
| 1.3.3 | Create state types | `src/types/state.ts` with ResumeState, AuditLogEntry interfaces | 8m |
| 1.3.4 | Create error types | `src/types/errors.ts` with ErrorType enum, ClassifiedError interface | 8m |
| 1.3.5 | Create index barrel | `src/types/index.ts` re-exports all types | 3m |

**Checkpoint:** `pnpm tsc --noEmit` passes

---

## Phase 2: Infrastructure Layer

### 2.1 Error Handler

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 2.1.1 | Create ErrorHandler class | `src/infra/ErrorHandler.ts` with constructor | 5m |
| 2.1.2 | Implement classify() | Takes Error, returns ClassifiedError with type, message, recoverable | 10m |
| 2.1.3 | Implement formatForUser() | Returns user-friendly message with suggested action | 8m |
| 2.1.4 | Implement shouldRetry() | Returns boolean based on error type | 5m |
| 2.1.5 | Add ErrorHandler tests | `tests/unit/error-handler.test.ts` with 5+ test cases | 10m |

**Checkpoint:** `pnpm test error-handler` passes

### 2.2 Audit Logger

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 2.2.1 | Create AuditLogger class | `src/infra/AuditLogger.ts` with configurable log path | 5m |
| 2.2.2 | Implement ensureDir() | Creates `~/.substretcher/` if not exists | 5m |
| 2.2.3 | Implement log() | Appends JSONL entry with timestamp | 10m |
| 2.2.4 | Implement sanitize() | Strips URLs to domains, masks card numbers, removes emails | 12m |
| 2.2.5 | Add AuditLogger tests | `tests/unit/audit-logger.test.ts` with sanitization tests | 10m |

**Checkpoint:** `pnpm test audit-logger` passes

### 2.3 File Exporter

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 2.3.1 | Create FileExporter class | `src/infra/FileExporter.ts` skeleton | 5m |
| 2.3.2 | Implement exportJSON() | Writes pretty-printed JSON to path | 8m |
| 2.3.3 | Implement exportCSV() | Writes CSV with header row per spec 4.6 | 10m |
| 2.3.4 | Implement escapeCSV() | Handles commas, quotes, newlines in values | 8m |
| 2.3.5 | Add FileExporter tests | `tests/unit/file-exporter.test.ts` for both formats | 10m |

**Checkpoint:** `pnpm test file-exporter` passes

---

## Phase 3: Configuration Layer

### 3.1 Zod Schemas

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 3.1.1 | Create schema file | `src/config/schema.ts` with zod import | 3m |
| 3.1.2 | Define NavigationStepSchema | description required, selector/action/waitAfter optional | 8m |
| 3.1.3 | Define CancellationStepSchema | action required, description required, others optional | 8m |
| 3.1.4 | Define ServiceConfigSchema | id, name, domain, billingUrl required; navigation, extraction, cancellation optional | 10m |
| 3.1.5 | Export parse functions | `parseServiceConfig()` function throwing on invalid | 5m |

**Checkpoint:** Schema validates example config object

### 3.2 YAML Config Loader

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 3.2.1 | Create ConfigLoader interface | `src/config/ConfigLoader.ts` with loadService, loadAllServices, listServiceIds | 5m |
| 3.2.2 | Create YAMLConfigLoader class | `src/config/YAMLConfigLoader.ts` implementing interface | 5m |
| 3.2.3 | Implement loadYAML() | Reads and parses YAML file | 8m |
| 3.2.4 | Implement loadService() | Searches paths, validates with schema, caches result | 12m |
| 3.2.5 | Implement loadAllServices() | Loads all .yaml files, skips invalid with warning | 10m |
| 3.2.6 | Add ConfigLoader tests | `tests/unit/config-loader.test.ts` | 10m |

**Checkpoint:** `pnpm test config-loader` passes

### 3.3 Built-in Service Configs

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 3.3.1 | Create services/ directory | `services/` folder at project root | 2m |
| 3.3.2 | Create netflix.yaml | Valid config with billingUrl, optional navigation/extraction hints | 10m |
| 3.3.3 | Create spotify.yaml | Valid config for Spotify account page | 10m |
| 3.3.4 | Create chatgpt.yaml | Valid config for ChatGPT subscription | 10m |
| 3.3.5 | Create youtube.yaml | Valid config for YouTube Premium | 10m |

**Checkpoint:** ConfigLoader can load all 4 services

---

## Phase 4: Browser Adapter Layer

### 4.1 Browser Errors

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 4.1.1 | Create errors file | `src/browser/errors.ts` | 3m |
| 4.1.2 | Define ChromeNotRunningError | Extends Error with helpful message about debug port | 5m |
| 4.1.3 | Define ConnectionLostError | Includes reconnection suggestion | 5m |
| 4.1.4 | Define NavigationTimeoutError | Includes URL and timeout value | 5m |
| 4.1.5 | Define ElementNotFoundError | Includes selector that wasn't found | 5m |

**Checkpoint:** Errors can be thrown and caught correctly

### 4.2 Browser Adapter Interface

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 4.2.1 | Create BrowserAdapter interface | `src/browser/BrowserAdapter.ts` with all method signatures | 10m |
| 4.2.2 | Add JSDoc documentation | Each method has @param, @returns, @throws docs | 10m |

**Checkpoint:** Interface compiles

### 4.3 Chrome DevTools Adapter

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 4.3.1 | Create adapter class | `src/browser/ChromeDevToolsAdapter.ts` skeleton | 5m |
| 4.3.2 | Implement connect() | Connects to CDP on port, throws ChromeNotRunningError if unavailable | 12m |
| 4.3.3 | Implement disconnect() | Cleanly closes CDP connection | 5m |
| 4.3.4 | Implement navigateTo() | Navigates and waits for load event with timeout | 12m |
| 4.3.5 | Implement takeScreenshot() | Captures viewport as PNG Buffer | 10m |
| 4.3.6 | Implement click() | Clicks element by selector | 10m |
| 4.3.7 | Implement clickAt() | Clicks at x,y coordinates | 8m |
| 4.3.8 | Implement type() | Types text into focused element | 8m |
| 4.3.9 | Implement waitForSelector() | Waits for element to appear | 10m |
| 4.3.10 | Implement waitForText() | Waits for text on page | 10m |
| 4.3.11 | Add adapter tests | `tests/integration/browser-adapter.test.ts` with mocked CDP | 15m |

**Checkpoint:** `pnpm test browser-adapter` passes

---

## Phase 5: AI Extraction Layer

### 5.1 Prompt Templates

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 5.1.1 | Create prompts file | `src/ai/prompts.ts` | 3m |
| 5.1.2 | Define EXTRACTION_PROMPT | Template with {serviceName} placeholder, requests JSON output | 10m |
| 5.1.3 | Define AUTH_CHECK_PROMPT | Template for login detection, requests JSON output | 8m |
| 5.1.4 | Define ELEMENT_FIND_PROMPT | Template for finding clickable element by description | 8m |

**Checkpoint:** Prompts exported and contain {placeholders}

### 5.2 AI Extractor Interface

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 5.2.1 | Create AIExtractor interface | `src/ai/AIExtractor.ts` with method signatures | 8m |
| 5.2.2 | Define AuthCheckResult type | loggedIn, confidence, reason fields | 5m |
| 5.2.3 | Define ElementLocation type | x, y, width?, height?, confidence fields | 5m |

**Checkpoint:** Interface compiles

### 5.3 Claude AI Extractor

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 5.3.1 | Create extractor class | `src/ai/ClaudeAIExtractor.ts` with constructor taking API key | 5m |
| 5.3.2 | Implement callClaudeVision() | Private method calling Anthropic API with image | 12m |
| 5.3.3 | Implement extractBillingInfo() | Sends screenshot, parses response to BillingInfo | 15m |
| 5.3.4 | Implement isLoggedIn() | Checks auth state, returns AuthCheckResult | 10m |
| 5.3.5 | Implement findElement() | Returns coordinates for described element | 10m |
| 5.3.6 | Implement safeParseJSON() | Handles malformed JSON gracefully | 8m |
| 5.3.7 | Add extractor tests | `tests/integration/ai-extractor.test.ts` with recorded responses | 15m |

**Checkpoint:** `pnpm test ai-extractor` passes

---

## Phase 6: Orchestration Layer

### 6.1 Resume Manager

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 6.1.1 | Create ResumeManager class | `src/orchestrator/ResumeManager.ts` with state path | 5m |
| 6.1.2 | Implement loadState() | Reads JSON from disk, returns null if not exists | 8m |
| 6.1.3 | Implement saveState() | Writes ResumeState to JSON file | 8m |
| 6.1.4 | Implement clearState() | Deletes resume state file | 5m |
| 6.1.5 | Implement isServiceCompleted() | Checks if serviceId in completed array | 5m |
| 6.1.6 | Implement updateWithResult() | Adds result to state, marks service completed | 8m |
| 6.1.7 | Add ResumeManager tests | `tests/unit/resume-manager.test.ts` | 10m |

**Checkpoint:** `pnpm test resume-manager` passes

### 6.2 Scan Orchestrator

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 6.2.1 | Create ScanOrchestrator class | `src/orchestrator/ScanOrchestrator.ts` with DI constructor | 5m |
| 6.2.2 | Implement scan() entry point | Takes serviceIds and options, returns ScanResult | 10m |
| 6.2.3 | Implement scanService() | Navigates, screenshots, extracts for single service | 15m |
| 6.2.4 | Implement handleLoginWall() | Prompts user, waits for input, verifies login | 12m |
| 6.2.5 | Implement aggregateResults() | Computes summary (totals, monthly cost) | 10m |
| 6.2.6 | Integrate resume state | Load at start, save after each service, clear on complete | 12m |
| 6.2.7 | Add ScanOrchestrator tests | `tests/unit/scan-orchestrator.test.ts` with mocks | 15m |

**Checkpoint:** `pnpm test scan-orchestrator` passes

### 6.3 Cancel Orchestrator

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 6.3.1 | Create CancelOrchestrator class | `src/orchestrator/CancelOrchestrator.ts` with DI constructor | 5m |
| 6.3.2 | Implement cancel() entry point | Takes serviceId and options, returns CancelResult | 10m |
| 6.3.3 | Implement showPreCancelSummary() | Displays billing info and cancellation effects | 8m |
| 6.3.4 | Implement confirmCancellation() | Uses readline for user input, returns boolean | 10m |
| 6.3.5 | Implement executeCancellationSteps() | Iterates steps, finds elements, performs actions | 15m |
| 6.3.6 | Implement verifySuccess() | Checks for success indicator text/selector | 10m |
| 6.3.7 | Add CancelOrchestrator tests | `tests/unit/cancel-orchestrator.test.ts` with mocks | 15m |

**Checkpoint:** `pnpm test cancel-orchestrator` passes

---

## Phase 7: CLI Layer

### 7.1 Output Formatters

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 7.1.1 | Create table formatter | `src/cli/output/table.ts` wrapping cli-table3 | 8m |
| 7.1.2 | Implement formatBillingTable() | Formats BillingInfo[] as table string | 10m |
| 7.1.3 | Implement formatSummary() | Formats scan summary (totals, cost) | 8m |
| 7.1.4 | Create progress utilities | `src/cli/output/progress.ts` wrapping ora | 8m |
| 7.1.5 | Implement createSpinner() | Returns spinner with start/stop/succeed/fail | 8m |

**Checkpoint:** Formatters produce readable output

### 7.2 Command Handlers

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 7.2.1 | Create scan command | `src/cli/commands/scan.ts` wiring orchestrator + output | 12m |
| 7.2.2 | Create cancel command | `src/cli/commands/cancel.ts` wiring orchestrator + output | 12m |
| 7.2.3 | Create list command | `src/cli/commands/list.ts` listing available services | 8m |
| 7.2.4 | Create status command | `src/cli/commands/status.ts` checking Chrome connection | 8m |

**Checkpoint:** Each command function exported

### 7.3 CLI Entry Point

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 7.3.1 | Create CLI entry point | `src/cli/index.ts` with commander program | 5m |
| 7.3.2 | Configure scan command | `substretcher scan [services...]` with all options | 10m |
| 7.3.3 | Configure cancel command | `substretcher cancel <service>` with --confirm | 8m |
| 7.3.4 | Configure list command | `substretcher list` | 5m |
| 7.3.5 | Configure status command | `substretcher status` | 5m |
| 7.3.6 | Add SIGINT handler | Gracefully stops on Ctrl+C | 8m |
| 7.3.7 | Configure bin in package.json | `"bin": { "substretcher": "./dist/cli/index.js" }` | 5m |
| 7.3.8 | Add shebang | `#!/usr/bin/env node` at top of entry point | 3m |

**Checkpoint:** `pnpm build && ./dist/cli/index.js --help` works

---

## Phase 8: Integration & Polish

### 8.1 E2E Testing

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 8.1.1 | Test scan single service | `substretcher scan netflix` extracts billing info | 15m |
| 8.1.2 | Test login wall handling | Detects login requirement, prompts, continues | 15m |
| 8.1.3 | Test multi-service scan | Scans multiple services, aggregates results | 15m |
| 8.1.4 | Test resume functionality | Interrupt scan, resume, skips completed | 15m |
| 8.1.5 | Test JSON export | `--output subs.json` creates valid file | 10m |
| 8.1.6 | Test CSV export | `--output subs.csv` creates valid file | 10m |
| 8.1.7 | Document test results | Update tasks.md with pass/fail notes | 10m |

**Checkpoint:** All E2E tests pass manually

### 8.2 Documentation

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 8.2.1 | Write README overview | Project description, features, installation | 10m |
| 8.2.2 | Document usage examples | Scan, cancel, list commands with examples | 10m |
| 8.2.3 | Document configuration | Service config YAML format | 10m |
| 8.2.4 | Document prerequisites | Chrome debug port, ANTHROPIC_API_KEY | 8m |
| 8.2.5 | Add troubleshooting section | Common errors and solutions | 10m |

**Checkpoint:** README is complete and accurate

### 8.3 Final Polish

| ID | Task | Acceptance Criteria | Est |
|----|------|---------------------|-----|
| 8.3.1 | Run ESLint | `pnpm lint` passes with no errors | 10m |
| 8.3.2 | Run all tests | `pnpm test` passes | 10m |
| 8.3.3 | Test npm pack | `npm pack` creates tarball, installs correctly | 10m |
| 8.3.4 | Tag release | `git tag v0.1.0` | 5m |

**Checkpoint:** Package is release-ready

---

## Task Summary

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 1. Foundation | 13 | ~1h |
| 2. Infrastructure | 15 | ~2h |
| 3. Configuration | 12 | ~1.5h |
| 4. Browser | 13 | ~2h |
| 5. AI | 11 | ~1.5h |
| 6. Orchestration | 21 | ~3h |
| 7. CLI | 13 | ~2h |
| 8. Integration | 15 | ~2.5h |
| **Total** | **113** | **~15.5h** |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-31 | Claude | Initial task breakdown |
