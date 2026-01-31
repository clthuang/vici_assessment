# Contributing Guide

## Development Setup

### Prerequisites

- Node.js 18+
- pnpm
- Chrome browser
- Anthropic API key (for integration testing)

### Clone and Install

```bash
git clone <repo-url>
cd substretcher-plugin
pnpm install
```

### Build

```bash
pnpm build     # Compile TypeScript to dist/
pnpm clean     # Remove dist/
```

### Run in Development

```bash
# Run directly with tsx (no build needed)
pnpm dev scan netflix

# Or run built version
pnpm build
node dist/cli/index.js scan netflix
```

### Testing

```bash
pnpm test        # Run all tests once
pnpm test:watch  # Watch mode
pnpm lint        # ESLint
```

## Project Structure

```
substretcher-plugin/
├── src/
│   ├── ai/                 # AI extraction (Claude Vision)
│   │   ├── AIExtractor.ts      # Interface
│   │   ├── ClaudeAIExtractor.ts # Implementation
│   │   └── prompts.ts          # Prompt templates
│   ├── browser/            # Browser automation (CDP)
│   │   ├── BrowserAdapter.ts   # Interface
│   │   ├── ChromeDevToolsAdapter.ts # Implementation
│   │   └── errors.ts           # Custom errors
│   ├── cli/                # Command-line interface
│   │   ├── commands/           # Command handlers
│   │   ├── output/             # Formatters
│   │   └── index.ts            # Entry point
│   ├── config/             # Configuration loading
│   │   ├── ConfigLoader.ts     # Interface
│   │   ├── YAMLConfigLoader.ts # Implementation
│   │   └── schema.ts           # Zod schemas
│   ├── infra/              # Infrastructure utilities
│   │   ├── AuditLogger.ts      # Audit logging
│   │   ├── ErrorHandler.ts     # Error classification
│   │   └── FileExporter.ts     # JSON/CSV export
│   ├── orchestrator/       # Business logic
│   │   ├── ScanOrchestrator.ts
│   │   ├── CancelOrchestrator.ts
│   │   └── ResumeManager.ts
│   └── types/              # Type definitions
│       ├── billing.ts
│       ├── config.ts
│       ├── errors.ts
│       └── state.ts
├── services/               # Built-in service configs
│   ├── netflix.yaml
│   ├── spotify.yaml
│   ├── chatgpt.yaml
│   └── youtube.yaml
├── docs/                   # Documentation
└── dist/                   # Compiled output (gitignored)
```

## Adding a New Service

1. Create `services/<service-id>.yaml`:

```yaml
id: new-service
name: New Service
domain: newservice.com
billingUrl: https://newservice.com/account/billing

# Optional: Navigation to reach billing page
navigation:
  steps:
    - description: "Click account icon"
      selector: "#account-menu"
    - description: "Click billing"
      selector: "a[href*='billing']"
      waitAfter: 2000

# Optional: CSS selectors for extraction hints
extraction:
  status:
    selector: ".subscription-status"
  renewalDate:
    selector: ".next-payment"
  cost:
    selector: ".plan-price"

# Optional: Cancellation workflow
cancellation:
  enabled: true
  steps:
    - action: click
      description: "Click cancel button"
      selector: "#cancel-btn"
    - action: click
      description: "Confirm cancellation"
      selector: "#confirm"
      requiresConfirmation: true
  successIndicator:
    text: "Subscription cancelled"
```

2. Test the configuration:

```bash
pnpm dev list                    # Verify it loads
pnpm dev scan new-service        # Test extraction
```

## Adding a New Command

1. Create `src/cli/commands/newcommand.ts`:

```typescript
import type { SomeOptions } from '../../types/index.js';

export async function newCommand(options: SomeOptions): Promise<void> {
  // Implementation
}
```

2. Export from `src/cli/commands/index.ts`:

```typescript
export { newCommand } from './newcommand.js';
```

3. Register in `src/cli/index.ts`:

```typescript
program
  .command('newcmd')
  .description('Description of new command')
  .option('-f, --flag', 'Option description')
  .action(async (options) => {
    await newCommand(options);
  });
```

## Adding a New Browser Method

1. Add to interface `src/browser/BrowserAdapter.ts`:

```typescript
export interface BrowserAdapter {
  // ... existing methods
  newMethod(param: string): Promise<Result>;
}
```

2. Implement in `src/browser/ChromeDevToolsAdapter.ts`:

```typescript
async newMethod(param: string): Promise<Result> {
  if (!this.client) {
    throw new ChromeNotRunningError();
  }

  const { SomeDomain } = this.client;
  // CDP implementation
}
```

## Code Style

### TypeScript

- Strict mode enabled
- ES2022 target, ESM modules
- Explicit types on public APIs
- Use interfaces for contracts

### Linting

```bash
pnpm lint          # Check
pnpm lint --fix    # Auto-fix
```

ESLint is configured with TypeScript rules. Key rules:
- No unused variables
- No explicit `any`
- Consistent returns

### File Naming

- `PascalCase.ts` for classes
- `camelCase.ts` for modules/utilities
- `*.test.ts` for tests (co-located)

### Imports

```typescript
// External packages first
import { z } from 'zod';
import chalk from 'chalk';

// Internal imports with .js extension (ESM requirement)
import type { ServiceConfig } from '../types/index.js';
import { ErrorHandler } from '../infra/index.js';
```

## Testing Guidelines

### Unit Tests

Co-locate tests with source files:

```
src/infra/
├── ErrorHandler.ts
├── ErrorHandler.test.ts
```

Test pattern:

```typescript
import { describe, it, expect } from 'vitest';
import { ErrorHandler } from './ErrorHandler.js';

describe('ErrorHandler', () => {
  describe('classify', () => {
    it('should classify connection errors', () => {
      const handler = new ErrorHandler();
      const result = handler.classify(new Error('ECONNREFUSED'));
      expect(result.type).toBe('chrome_not_running');
    });
  });
});
```

### Integration Tests

Require external dependencies (Chrome, API). Run manually:

```bash
# Start Chrome first
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Run integration test
ANTHROPIC_API_KEY=sk-ant-... pnpm dev scan netflix
```

## Error Handling

Use the `ErrorHandler` for classification:

```typescript
import { ErrorHandler } from '../infra/index.js';

const errorHandler = new ErrorHandler();

try {
  await riskyOperation();
} catch (err) {
  const classified = errorHandler.classify(err as Error);

  if (classified.recoverable) {
    // Retry or skip
  } else {
    // Show user action
    console.error(errorHandler.formatForUser(classified));
  }
}
```

## Submitting Changes

1. Create a feature branch
2. Make changes with tests
3. Run `pnpm lint && pnpm test`
4. Submit PR with description

### Commit Message Format

```
type: short description

- Detail 1
- Detail 2
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
