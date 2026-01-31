# Implementation Plan: SubStretcher Plugin

**Feature ID:** substretcher-plugin
**Version:** 1.0
**Date:** 2026-01-31
**Status:** Reviewed

---

## Overview

This plan breaks down the SubStretcher Plugin implementation into ordered phases with clear dependencies. Each phase builds on the previous one, enabling incremental testing and validation.

---

## Phase 1: Project Foundation

**Goal:** Set up project structure, dependencies, and type definitions

### 1.1 Initialize Project
- [ ] Create `substretcher-plugin/` directory structure per design Section 4
- [ ] Initialize `package.json` with project metadata
- [ ] Configure `tsconfig.json` for ES modules, strict mode
- [ ] Set up `.gitignore` (node_modules, dist, .env)
- [ ] Add ESLint configuration

**Dependencies:** None
**Output:** Empty project scaffold that compiles

### 1.2 Install Dependencies
- [ ] Install runtime dependencies (commander, chalk, cli-table3, ora, yaml, zod, @anthropic-ai/sdk, chrome-remote-interface, uuid)
- [ ] Install dev dependencies (typescript, vitest, @types/node, tsx, eslint)
- [ ] Verify all packages install without conflicts

**Dependencies:** 1.1
**Output:** `package.json` with all deps, `pnpm-lock.yaml`

### 1.3 Define Type Definitions
- [ ] Create `src/types/billing.ts` (BillingInfo, ScanResult, CancelResult)
- [ ] Create `src/types/config.ts` (ServiceConfig, NavigationStep, CancellationStep)
- [ ] Create `src/types/state.ts` (ResumeState, AuditLogEntry)
- [ ] Create `src/types/errors.ts` (error enums and ClassifiedError)

**Dependencies:** 1.1
**Output:** Compiled type definitions, no runtime code yet

---

## Phase 2: Infrastructure Layer

**Goal:** Build foundational utilities that other components depend on

### 2.1 Error Handler
- [ ] Implement `src/infra/ErrorHandler.ts`
- [ ] Create error classification logic (ErrorType enum)
- [ ] Implement `classify()`, `formatForUser()`, `shouldRetry()`
- [ ] Add unit tests for error classification

**Dependencies:** 1.3
**Output:** ErrorHandler with tests passing

### 2.2 Audit Logger
- [ ] Implement `src/infra/AuditLogger.ts`
- [ ] Create `~/.substretcher/` directory on first use
- [ ] Implement JSONL append logic
- [ ] Implement sanitization rules (URLs, card numbers, emails)
- [ ] Add unit tests for sanitization

**Dependencies:** 1.3 (uses AuditLogEntry type)
**Output:** AuditLogger with tests passing

### 2.3 File Exporter
- [ ] Implement `src/infra/FileExporter.ts`
- [ ] Implement JSON export (pretty-printed)
- [ ] Implement CSV export with field mapping per spec 4.6
- [ ] Handle CSV escaping (commas, quotes)
- [ ] Add unit tests for both formats

**Dependencies:** 1.3
**Output:** FileExporter with tests passing

---

## Phase 3: Configuration Layer

**Goal:** Load and validate service configurations

### 3.1 Zod Schemas
- [ ] Implement `src/config/schema.ts`
- [ ] Define ServiceConfigSchema with all fields
- [ ] Define NavigationStepSchema, CancellationStepSchema
- [ ] Export validation functions

**Dependencies:** 1.3
**Output:** Zod schemas that validate config objects

### 3.2 YAML Config Loader
- [ ] Implement `src/config/ConfigLoader.ts` (interface)
- [ ] Implement `src/config/YAMLConfigLoader.ts`
- [ ] Support `./services/` and `~/.substretcher/services/` paths
- [ ] Implement caching for loaded configs
- [ ] Handle validation errors gracefully
- [ ] Add unit tests

**Dependencies:** 3.1
**Output:** ConfigLoader with tests passing

### 3.3 Built-in Service Configs
- [ ] Create `services/netflix.yaml`
- [ ] Create `services/spotify.yaml`
- [ ] Create `services/chatgpt.yaml`
- [ ] Create `services/youtube.yaml`

**Dependencies:** 3.1 (schemas define structure)
**Output:** 4 service config files that pass validation

---

## Phase 4: Browser Adapter Layer

**Goal:** Abstract Chrome DevTools Protocol interactions

### 4.1 Browser Errors
- [ ] Implement `src/browser/errors.ts`
- [ ] Define ChromeNotRunningError, ConnectionLostError, NavigationTimeoutError, ElementNotFoundError

**Dependencies:** 2.1 (uses ErrorHandler patterns)
**Output:** Custom error classes

### 4.2 Browser Adapter Interface
- [ ] Implement `src/browser/BrowserAdapter.ts` (interface only)
- [ ] Document all methods with JSDoc

**Dependencies:** 4.1
**Output:** TypeScript interface

### 4.3 Chrome DevTools Adapter
- [ ] Implement `src/browser/ChromeDevToolsAdapter.ts`
- [ ] Implement `connect()` with port detection
- [ ] Implement `disconnect()` for clean shutdown
- [ ] Implement `navigateTo()` with timeout handling
- [ ] Implement `takeScreenshot()` returning PNG buffer
- [ ] Implement `click()`, `clickAt()`, `type()`
- [ ] Implement `waitForSelector()`, `waitForText()`
- [ ] Add integration tests with Chrome mocking

**Dependencies:** 4.2
**Output:** Working CDP adapter with tests

---

## Phase 5: AI Extraction Layer

**Goal:** Integrate Claude Vision for billing extraction

### 5.1 Prompt Templates
- [ ] Implement `src/ai/prompts.ts`
- [ ] Define EXTRACTION_PROMPT template
- [ ] Define AUTH_CHECK_PROMPT template
- [ ] Define ELEMENT_FIND_PROMPT template

**Dependencies:** 1.3
**Output:** Prompt template constants

### 5.2 AI Extractor Interface
- [ ] Implement `src/ai/AIExtractor.ts` (interface only)
- [ ] Define AuthCheckResult, ElementLocation types

**Dependencies:** 5.1
**Output:** TypeScript interface

### 5.3 Claude AI Extractor
- [ ] Implement `src/ai/ClaudeAIExtractor.ts`
- [ ] Implement `extractBillingInfo()` with confidence scoring
- [ ] Implement `isLoggedIn()` for auth detection
- [ ] Implement `findElement()` for AI-guided clicks
- [ ] Parse JSON responses safely (handle malformed)
- [ ] Add integration tests with recorded responses

**Dependencies:** 5.2
**Output:** Working Claude integration with tests

---

## Phase 6: Orchestration Layer

**Goal:** Coordinate scanning and cancellation workflows

### 6.1 Resume Manager
- [ ] Implement `src/orchestrator/ResumeManager.ts`
- [ ] Implement state persistence at `~/.substretcher/resume-state.json`
- [ ] Implement `loadState()`, `saveState()`, `clearState()`
- [ ] Implement `isServiceCompleted()`, `updateWithResult()`
- [ ] Add unit tests

**Dependencies:** 1.3 (uses ResumeState type)
**Output:** ResumeManager with tests

### 6.2 Scan Orchestrator
- [ ] Implement `src/orchestrator/ScanOrchestrator.ts`
- [ ] Implement constructor with dependency injection
- [ ] Implement main `scan()` method
- [ ] Implement `scanService()` for single service
- [ ] Implement `handleLoginWall()` for auth prompts
- [ ] Implement `aggregateResults()` for summary
- [ ] Integrate resume state (skip completed)
- [ ] Add unit tests with mocked dependencies

**Dependencies:** 4.3, 5.3, 6.1, 3.2, 2.2
**Output:** ScanOrchestrator with tests

### 6.3 Cancel Orchestrator
- [ ] Implement `src/orchestrator/CancelOrchestrator.ts`
- [ ] Implement `cancel()` main method
- [ ] Implement `showPreCancelSummary()`
- [ ] Implement `confirmCancellation()` with readline
- [ ] Implement `executeCancellationSteps()` (selector + AI fallback)
- [ ] Implement `verifySuccess()` checking success indicators
- [ ] Add unit tests with mocked dependencies

**Dependencies:** 6.2 (reuses scan for billing info), 2.2
**Output:** CancelOrchestrator with tests

---

## Phase 7: CLI Layer

**Goal:** Build command-line interface

### 7.1 Output Formatters
- [ ] Implement `src/cli/output/table.ts` (cli-table3 wrapper)
- [ ] Implement `src/cli/output/progress.ts` (ora wrapper)
- [ ] Format BillingInfo as table row
- [ ] Format ScanResult summary

**Dependencies:** 1.2 (chalk, cli-table3, ora)
**Output:** Output utilities

### 7.2 Command Handlers
- [ ] Implement `src/cli/commands/scan.ts`
- [ ] Implement `src/cli/commands/cancel.ts`
- [ ] Implement `src/cli/commands/list.ts`
- [ ] Implement `src/cli/commands/status.ts`
- [ ] Each handler wires up orchestrator + output

**Dependencies:** 6.2, 6.3, 7.1, 3.2
**Output:** Command handler functions

### 7.3 CLI Entry Point
- [ ] Implement `src/cli/index.ts`
- [ ] Configure commander.js with all commands
- [ ] Add all CLI options (--output, --all, --confirm, --verbose, --timeout, --fresh)
- [ ] Implement SIGINT handler for graceful shutdown
- [ ] Add shebang and make executable
- [ ] Configure `bin` field in package.json

**Dependencies:** 7.2
**Output:** Working CLI entry point

---

## Phase 8: Integration & Polish

**Goal:** End-to-end testing and documentation

### 8.1 E2E Testing
- [ ] Test full scan workflow with Netflix
- [ ] Test login wall detection and prompt
- [ ] Test multi-service scan with failures
- [ ] Test resume after interruption
- [ ] Test JSON/CSV export
- [ ] Document test results

**Dependencies:** All previous phases
**Output:** E2E test report

### 8.2 Documentation
- [ ] Write README.md with installation, usage, examples
- [ ] Document service config format
- [ ] Document ANTHROPIC_API_KEY requirement
- [ ] Document Chrome debug port setup
- [ ] Add troubleshooting section

**Dependencies:** 8.1 (know what works)
**Output:** Comprehensive README

### 8.3 Final Polish
- [ ] Run ESLint, fix any issues
- [ ] Verify all tests pass
- [ ] Test npm pack / install
- [ ] Tag release version

**Dependencies:** 8.2
**Output:** Release-ready package

---

## Dependency Graph

```
Phase 1: Foundation
  1.1 ──► 1.2
  1.1 ──► 1.3

Phase 2: Infrastructure (depends on 1.3)
  1.3 ──► 2.1
  1.3 ──► 2.2
  1.3 ──► 2.3

Phase 3: Configuration (depends on 1.3)
  1.3 ──► 3.1 ──► 3.2
  3.1 ──► 3.3

Phase 4: Browser (depends on 2.1)
  2.1 ──► 4.1 ──► 4.2 ──► 4.3

Phase 5: AI (depends on 1.3)
  1.3 ──► 5.1 ──► 5.2 ──► 5.3

Phase 6: Orchestration (depends on 4.3, 5.3, 3.2, 2.2)
  1.3 ──► 6.1
  [4.3, 5.3, 3.2, 2.2, 6.1] ──► 6.2 ──► 6.3

Phase 7: CLI (depends on 6.2, 6.3)
  [6.2, 6.3] ──► 7.1 ──► 7.2 ──► 7.3

Phase 8: Integration (depends on 7.3)
  7.3 ──► 8.1 ──► 8.2 ──► 8.3
```

---

## Critical Path

The minimum path to a working `substretcher scan` command:

1. **1.1** → **1.2** → **1.3** (Foundation)
2. **2.1** (ErrorHandler - needed by browser)
3. **3.1** → **3.2** → **3.3** (Config loading)
4. **4.1** → **4.2** → **4.3** (Browser adapter)
5. **5.1** → **5.2** → **5.3** (AI extraction)
6. **6.1** → **6.2** (Scan orchestration)
7. **7.1** → **7.2** → **7.3** (CLI)

Estimated: 18 tasks on critical path

---

## Parallelization Opportunities

These can be done in parallel once their dependencies are met:

| After | Can parallelize |
|-------|-----------------|
| 1.3 | 2.1, 2.2, 2.3, 3.1, 5.1 |
| 3.1 | 3.2, 3.3 |
| 4.2 | 4.3 (if mock testing first) |
| 5.2 | 5.3 (if mock testing first) |
| 6.2 | 6.3 |

---

## Risk Mitigation Checkpoints

| Checkpoint | After Phase | Verify |
|------------|-------------|--------|
| Types compile | 1.3 | `tsc --noEmit` passes |
| Infra works | 2.3 | Unit tests pass |
| Configs load | 3.3 | Can load Netflix config |
| Browser connects | 4.3 | Can connect to Chrome |
| AI extracts | 5.3 | Can call Claude API |
| Scan works | 6.2 | Can scan one service |
| CLI works | 7.3 | `substretcher scan netflix` runs |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-31 | Claude | Initial plan |
| 1.1 | 2026-01-31 | Claude | Fixed dependency inaccuracies (2.2, 6.1 now correctly independent) |
