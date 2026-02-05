# SubTerminator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CLI tool for automating subscription cancellations.**

SubTerminator navigates the frustrating cancellation flows of subscription services so you don't have to. It handles retention offers, exit surveys, and confusing dialogs while keeping you in control of the final decision.

> **Warning: Terms of Service**
>
> This tool automates browser interactions with subscription services. Many services prohibit automation in their Terms of Service. **Use at your own risk.** The authors are not responsible for any consequences including account suspension or termination.

---

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync && uv run playwright install chromium

# Run with dry-run mode (safe, stops at final confirmation)
uv run subterminator cancel --service netflix --dry-run
```

## Installation

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/your-repo/subterminator.git
cd subterminator
uv sync
uv run playwright install chromium

# Required: Set up API key for LLM orchestration
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Usage

### Interactive Mode

```bash
subterminator cancel  # Opens interactive service menu
```

### Non-Interactive Mode

```bash
subterminator cancel --service netflix              # Live (USE WITH CAUTION)
subterminator cancel --service netflix --dry-run   # Stop at final confirmation
subterminator cancel --service netflix --headless  # Run without visible browser
```

### Browser Session Persistence

```bash
# Use a persistent browser profile (keeps login sessions)
subterminator cancel --service netflix --profile-dir ~/.subterminator/chrome-profile
```

### Command Options

| Option | Short | Description |
|--------|-------|-------------|
| `--service` | `-s` | Service to cancel (bypasses interactive menu) |
| `--dry-run` | `-n` | Stop at final confirmation |
| `--headless` | | Run browser without visible window |
| `--verbose` | `-V` | Show detailed progress |
| `--profile-dir` | | Use persistent browser profile |
| `--plain` | | Disable colors and animations |
| `--no-input` | | Force non-interactive mode |
| `--model` | | LLM model override (default: claude-sonnet-4-20250514) |
| `--max-turns` | | Maximum orchestration turns (default: 20) |
| `--no-checkpoint` | | Disable human checkpoints |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Claude LLM (required) | (none) |
| `SUBTERMINATOR_MODEL` | LLM model | `claude-sonnet-4-20250514` |

## What to Expect

1. **Opens account page** - Browser navigates to service's account settings
2. **Detects state** - Determines if logged in, active subscription, or already cancelled
3. **Automates cancellation flow** - Clicks through retention offers and exit surveys
4. **Pauses for human input** - Login (if needed) and final confirmation require your action
5. **Saves artifacts** - Screenshots and logs saved to output directory

## Supported Services

| Service | Status | Notes |
|---------|--------|-------|
| Netflix | ✅ Available | Full cancellation automation |
| Disney+ | 🔜 Coming Soon | In development |
| Hulu | 🔜 Coming Soon | Planned |
| Spotify | 🔜 Coming Soon | Planned |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (cancellation completed) |
| 1 | Failure (cancellation failed) |
| 2 | User cancelled (via Ctrl+C or menu) |
| 3 | Invalid service |
| 5 | MCP connection error |
| 130 | SIGINT during orchestration |

## Development

See [README_FOR_DEV.md](README_FOR_DEV.md) for developer documentation.

```bash
uv sync --group dev
uv run pytest                    # Run tests
uv run pytest --cov=subterminator  # With coverage
uv run ruff check src/           # Lint
```

## License

MIT License - see LICENSE file for details.

---

**Disclaimer:** This tool is provided as-is for educational purposes. The authors make no guarantees about its functionality or compliance with any service's Terms of Service.
