# SubStretcher

A CLI tool for extracting subscription billing information and automating cancellations using browser automation and AI.

## Features

- **Billing Extraction** - Extract subscription status, renewal dates, and costs from any service
- **AI-Powered** - Uses Claude Vision to understand billing pages regardless of UI changes
- **Auto-Cancel** - Automated cancellation workflows with user confirmation
- **Resume Support** - Continue interrupted scans from where you left off
- **Export** - Save results as JSON or CSV

## Prerequisites

- Node.js 18+
- Chrome browser
- Anthropic API key

## Installation

### Quick Install (Recommended)

Run the interactive installation script:

```bash
cd substretcher-plugin
./install.sh
```

The script will:
- Check prerequisites (Node.js 18+, pnpm)
- Install dependencies and build the project
- Optionally link the global `substretcher` command
- Create data directories (`~/.substretcher/`)
- Help configure your API key
- Create a Chrome helper script

Use `./install.sh --yes` for non-interactive mode with default options.

### Manual Installation

```bash
# Clone and install
cd substretcher-plugin
pnpm install
pnpm build

# Link globally (optional)
pnpm link --global
```

## Setup

### 1. Start Chrome with Remote Debugging

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

> **Note:** The default debug port is 9222. You can use a different port if needed—SubStretcher will attempt to connect to port 9222 by default.

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Verify Connection

```bash
substretcher status
```

## Usage

### Scan Subscriptions

```bash
# Scan specific services
substretcher scan netflix spotify

# Scan all configured services
substretcher scan --all

# Export to file
substretcher scan --all --output subscriptions.json
substretcher scan --all --output subscriptions.csv

# Verbose output
substretcher scan netflix -v

# Start fresh (ignore resume state)
substretcher scan --all --fresh
```

### Cancel Subscription

```bash
# Cancel with confirmation prompt
substretcher cancel netflix

# Skip confirmation (use with caution)
substretcher cancel netflix --confirm
```

### List Services

```bash
substretcher list
```

### Check Status

```bash
substretcher status
```

## Command Reference

| Command | Description |
|---------|-------------|
| `scan [services...]` | Extract billing info from services |
| `cancel <service>` | Cancel a subscription |
| `list` | Show available service configurations |
| `status` | Check Chrome connection |

### Scan Options

| Option | Description |
|--------|-------------|
| `--all` | Scan all configured services |
| `-o, --output <file>` | Export results (JSON/CSV based on extension) |
| `-v, --verbose` | Show detailed progress |
| `--timeout <ms>` | Page load timeout (default: 30000) |
| `--fresh` | Ignore resume state |

### Cancel Options

| Option | Description |
|--------|-------------|
| `--confirm` | Skip confirmation prompt |
| `-v, --verbose` | Show detailed progress |
| `--timeout <ms>` | Page load timeout (default: 30000) |

## Service Configurations

Built-in configurations are provided for:
- Netflix
- Spotify
- ChatGPT
- YouTube Premium

### Custom Service Configuration

Create a YAML file (`.yaml` or `.yml`) in `~/.substretcher/services/` or the `services/` directory:

```yaml
id: example-service
name: Example Service
domain: example.com
billingUrl: https://example.com/billing

navigation:
  steps:
    - description: "Click account menu"
      selector: "#account-menu"
    - description: "Click billing"
      selector: "a[href*='billing']"
      waitAfter: 2000

extraction:
  status:
    selector: ".subscription-status"
  renewalDate:
    selector: ".next-billing-date"
  cost:
    selector: ".plan-price"

cancellation:
  enabled: true
  steps:
    - action: click
      description: "Click cancel button"
      selector: "#cancel-subscription"
    - action: click
      description: "Confirm cancellation"
      selector: "#confirm-cancel"
      requiresConfirmation: true
  successIndicator:
    text: "Successfully cancelled"
```

## Output Format

### JSON Export

```json
{
  "scannedAt": "2024-01-15T10:30:00Z",
  "services": [
    {
      "serviceId": "netflix",
      "serviceName": "Netflix",
      "status": "active",
      "renewalDate": "2024-02-15",
      "cost": {
        "amount": 15.99,
        "currency": "USD",
        "cycle": "monthly"
      },
      "paymentMethod": "Visa ****1234",
      "confidence": 0.95,
      "extractedAt": "2024-01-15T10:30:05Z",
      "errors": []
    }
  ],
  "summary": {
    "total": 4,
    "successful": 4,
    "failed": 0,
    "skipped": 0,
    "totalMonthlyCost": 45.97,
    "currency": "USD"
  }
}
```

### CSV Export

```csv
serviceId,serviceName,status,renewalDate,amount,currency,cycle,paymentMethod,confidence,extractedAt
netflix,Netflix,active,2024-02-15,15.99,USD,monthly,Visa ****1234,0.95,2024-01-15T10:30:05Z
```

### Confidence Score

The `confidence` field (0-1) indicates how certain the AI is about the extracted data:

| Range | Level | Recommendation |
|-------|-------|----------------|
| 0.9–1.0 | High | Data is reliable |
| 0.7–0.9 | Medium | Review for accuracy |
| < 0.7 | Low | Manual verification recommended |

## Data Storage

SubStretcher stores data in `~/.substretcher/`:

| File | Purpose |
|------|---------|
| `audit.log` | Cancellation audit trail (JSONL) |
| `resume-state.json` | Resume state for interrupted scans |
| `services/` | Custom service configurations |

## Troubleshooting

### Chrome Not Detected

```
Error: Chrome is not running with remote debugging enabled
```

**Solution:** Start Chrome with `--remote-debugging-port=9222`

### Login Required

When a service requires login, SubStretcher will:
1. Detect the login wall
2. Prompt you to log in manually
3. Wait for confirmation before continuing

### API Key Missing

```
Error: ANTHROPIC_API_KEY environment variable not set
```

**Solution:** `export ANTHROPIC_API_KEY=sk-ant-...`

### Resume Interrupted Scans

When a scan is interrupted (e.g., by Ctrl+C or an error), SubStretcher automatically saves progress:

- Progress is stored in `~/.substretcher/resume.json`
- Running the same scan again skips already-completed services
- Use `--fresh` to ignore saved state and start over

```bash
# Resume interrupted scan
substretcher scan --all

# Start fresh, ignoring previous progress
substretcher scan --all --fresh
```

## Security Notes

- Audit logs sanitize sensitive data (card numbers masked, emails removed)
- API keys are never logged
- All browser automation happens in your existing Chrome session
- No data is sent to external services except the Anthropic API for extraction

## License

MIT
