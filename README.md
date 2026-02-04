# SubTerminator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CLI tool for automating subscription cancellations.**

SubTerminator navigates the frustrating cancellation flows of subscription services so you do not have to. It handles retention offers, exit surveys, and confusing dialogs while keeping you in control of the final decision.

---

> **Warning: Terms of Service**
>
> This tool automates browser interactions with subscription services. Many services prohibit automation in their Terms of Service. **Use at your own risk.** The authors are not responsible for any consequences including but not limited to account suspension or termination.
>
> This tool is intended for educational and personal use. Always review the Terms of Service of any service before using automation tools.

---

## Quick Start

Get up and running in 4 commands:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Install browser automation dependencies
uv run playwright install chromium

# Test with mock server (safe, no real account needed)
uv run subterminator cancel --service netflix --target mock --dry-run
```

## Installation

### Prerequisites

- Python 3.12 (managed via pyenv)
- uv (Python package manager)

### Install Steps

1. Install pyenv and uv:
   ```bash
   # Install pyenv (macOS with Homebrew)
   brew install pyenv

   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone and set up Python version:
   ```bash
   git clone https://github.com/your-repo/subterminator.git
   cd subterminator
   pyenv install 3.12  # If not already installed
   pyenv local 3.12    # Uses .python-version file
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

4. Install Playwright browsers:
   ```bash
   uv run playwright install chromium
   ```

5. (Optional) Set up your Anthropic API key for AI-powered page detection:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

### Uninstallation

To completely remove SubTerminator:

```bash
# Remove virtual environment
rm -rf .venv

# Remove Playwright browsers (optional, removes ~500MB)
uv run playwright uninstall chromium

# Or remove all Playwright browsers
uv run playwright uninstall --all

# Clean up configuration (optional)
rm -rf ./output  # Remove session artifacts
```

## Usage

### Interactive Mode (Default)

When you run `subterminator cancel` without specifying a service, an interactive menu appears:

```bash
# Interactive service selection
subterminator cancel

# Output:
# ? Select a service to cancel:
# ❯ Netflix - Video streaming service
#   Disney+ - Coming soon
#   Hulu - Coming soon
#   Spotify - Coming soon
#   ──────────────
#   Help - Show detailed service information
```

### Non-Interactive Mode

Use the `--service` flag to bypass the interactive menu:

```bash
# Specify service directly (live Netflix - USE WITH CAUTION)
subterminator cancel --service netflix

# Dry-run mode (stops at final confirmation)
subterminator cancel --service netflix --dry-run

# Test against mock server
subterminator cancel --service netflix --target mock

# Verbose output
subterminator cancel --service netflix --verbose

# Custom output directory
subterminator cancel --service netflix --output-dir ./my_sessions

# Headless mode (no browser window)
subterminator cancel --service netflix --headless
```

### Browser Session Reuse

Skip re-authentication by reusing an existing browser session:

```bash
# Option 1: Connect to Chrome with remote debugging enabled
# First, start Chrome with: chrome --remote-debugging-port=9222
subterminator cancel --service netflix --cdp-url http://localhost:9222

# Option 2: Use a persistent browser profile
# Session data (cookies, localStorage) will persist between runs
subterminator cancel --service netflix --profile-dir ~/.subterminator/chrome-profile
```

**Note:** `--cdp-url` and `--profile-dir` cannot be used together.

### Accessibility Options

```bash
# Plain mode (no colors or animations)
subterminator cancel --plain

# Force non-interactive mode (for scripts/CI)
subterminator cancel --service netflix --no-input
```

### Command Options

| Option | Short | Description |
|--------|-------|-------------|
| `--service` | `-s` | Service to cancel (bypasses interactive menu) |
| `--dry-run` | `-n` | Run without making actual changes (stops at final confirmation) |
| `--target` | `-t` | Target environment: `live` for real site, `mock` for local testing |
| `--headless` | | Run browser in headless mode (no visible window) |
| `--verbose` | `-V` | Show detailed progress information |
| `--output-dir` | `-o` | Directory for session artifacts (screenshots, logs) |
| `--no-input` | | Force non-interactive mode (requires `--service`) |
| `--plain` | | Disable colors and animations |
| `--cdp-url` | | Connect to existing Chrome via CDP URL |
| `--profile-dir` | | Use persistent browser profile directory |
| `--version` | `-v` | Show version and exit |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - cancellation completed |
| 1 | Failure - cancellation could not be completed |
| 2 | Aborted - user cancelled the operation |
| 3 | Invalid arguments |
| 4 | Configuration error |

## Configuration

SubTerminator can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Claude Vision AI detection | (none) |
| `SUBTERMINATOR_OUTPUT` | Output directory for session artifacts | `./output` |
| `SUBTERMINATOR_PAGE_TIMEOUT` | Page load timeout (ms) | `30000` |
| `SUBTERMINATOR_ELEMENT_TIMEOUT` | Element wait timeout (ms) | `10000` |
| `SUBTERMINATOR_NO_PROMPTS` | Disable interactive prompts | (not set) |
| `SUBTERMINATOR_PLAIN` | Disable colors and animations | (not set) |
| `NO_COLOR` | Standard: disable colors (any value) | (not set) |
| `CI` | Detected: disable interactive prompts | (not set) |

### Example Configuration

```bash
# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export SUBTERMINATOR_OUTPUT="./cancellation_sessions"
export SUBTERMINATOR_PAGE_TIMEOUT="60000"

# Now run subterminator
subterminator cancel --service netflix
```

## Migration from v1.x

In v2.0, the CLI syntax changed from a positional argument to a `--service` flag:

```bash
# Old syntax (v1.x) - NO LONGER WORKS
subterminator cancel netflix

# New syntax (v2.0+)
subterminator cancel --service netflix
# Or use short form:
subterminator cancel -s netflix
```

**Why the change?** The new interactive menu makes service selection easier and more discoverable. The `--service` flag allows you to bypass the menu when needed for scripts or automation.

**CI/CD Migration:** Add `--service` to your existing commands:

```bash
# Before
subterminator cancel netflix --dry-run

# After
subterminator cancel --service netflix --dry-run
```

## What to Expect

When you run SubTerminator, here is what happens:

1. **Opens Netflix account page** - A browser window opens and navigates to the Netflix account settings page.

2. **Detects current state** - The tool analyzes the page to determine if you are:
   - Logged in with an active subscription
   - Logged out (requires authentication)
   - Already cancelled (no action needed)
   - In an unexpected state

3. **Clicks through cancellation flow** - If active, the tool:
   - Clicks the "Cancel Membership" link
   - Handles any retention offers by declining them
   - Completes exit surveys with generic responses
   - Navigates past any intermediate pages

4. **Pauses for human input when needed**:
   - **Login**: If not logged in, you will see a prompt to log in manually (including 2FA if needed)
   - **Final confirmation**: Before clicking the final cancel button, you must type `confirm` to proceed

5. **Saves screenshots at each step** - All screenshots and logs are saved to the output directory for debugging and verification.

### Example Session Output

```
SubTerminator v0.1.0

WARNING: This tool automates browser interactions with subscription services.
Use at your own risk. The service's Terms of Service may prohibit automation.

[*] Starting Netflix cancellation...
[*] Navigating to account page...
[*] Detected: ACTIVE subscription
[*] Clicking cancel membership link...
[*] Handling retention offer...
[*] Completing exit survey...
[*] Reached final confirmation page

==========================================
FINAL CONFIRMATION REQUIRED
==========================================
Review the browser window carefully.
Type 'confirm' to proceed with cancellation: confirm

[*] Submitting cancellation...
[+] Cancellation complete!
    Effective date: March 1, 2026
    Screenshots saved to: ./output/netflix_20260203_143052/
```

## Troubleshooting

### "Element not found"

This error typically means Netflix has updated their UI and the selectors need updating.

**What to do:**
1. Check the screenshot in the output directory to see the current page state
2. Try running with `--verbose` for more details
3. Complete the cancellation manually using the open browser window
4. Report the issue with the screenshot attached

### "Login required"

The tool detected that you are not logged in.

**What to do:**
1. When prompted, log in manually in the browser window
2. Complete any 2FA/verification steps
3. Press Enter when you see your account page
4. The tool will continue from where it left off

### "Third-party billing detected"

Your Netflix subscription is billed through iTunes, Google Play, or another provider.

**What to do:**
1. You cannot cancel directly through Netflix
2. Cancel through your billing provider:
   - **iTunes**: Settings > Apple ID > Subscriptions
   - **Google Play**: Play Store > Subscriptions
   - **Other providers**: Check your billing statements

### "Timeout waiting for page"

The page took too long to load.

**What to do:**
1. Check your internet connection
2. Try increasing the timeout: `export SUBTERMINATOR_PAGE_TIMEOUT=60000`
3. Try again - this may be a temporary issue

### Browser does not open

Playwright browsers may not be installed.

**What to do:**
```bash
uv run playwright install chromium
```

### AI detection not working

You may not have set your Anthropic API key.

**What to do:**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Note: AI detection is optional. The tool will use heuristic detection if no API key is set.

## Supported Services

| Service | Status | Notes |
|---------|--------|-------|
| Netflix | ✅ Available | Full cancellation automation |
| Disney+ | 🔜 Coming Soon | In development |
| Hulu | 🔜 Coming Soon | Planned |
| Spotify | 🔜 Coming Soon | Planned |

Run `subterminator cancel` to see all services in the interactive menu.

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=subterminator
```

### Project Structure

```
src/subterminator/
  cli/           # Command-line interface
  core/          # Core engine, browser automation, AI detection
  services/      # Service-specific implementations (Netflix, mock)
  utils/         # Configuration, logging, exceptions
tests/
  unit/          # Unit tests
  integration/   # Integration tests
  e2e/           # End-to-end tests
```

## License

MIT License - see LICENSE file for details.

---

**Disclaimer:** This tool is provided as-is for educational purposes. The authors make no guarantees about its functionality or compliance with any service's Terms of Service.
