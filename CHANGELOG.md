# Changelog

All notable changes to SubTerminator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

- **CLI Syntax Change**: The positional service argument is removed. The old syntax `subterminator cancel netflix` no longer works. Use `subterminator cancel --service netflix` or interactive mode with just `subterminator cancel`.

### Added

- **Interactive Service Selection Menu**: Running `subterminator cancel` without arguments now displays an interactive menu for selecting a service
- **`--service` / `-s` flag**: Bypass interactive menu by specifying service directly (e.g., `--service netflix`)
- **`--no-input` flag**: Force non-interactive mode for scripts and CI/CD pipelines
- **`--plain` flag**: Disable colors and animations for accessibility
- **Service Registry**: Services are now managed through a central registry showing availability status
- **Coming Soon Services**: Disney+, Hulu, and Spotify are listed as "coming soon" in the menu
- **Fuzzy Suggestions**: Typos in service names now suggest the closest match (e.g., "netflixx" suggests "netflix")
- **Environment Variables**: New variables `SUBTERMINATOR_NO_PROMPTS` and `SUBTERMINATOR_PLAIN` for controlling interactive mode and accessibility
- **`questionary` dependency**: Added for interactive terminal prompts
- CI/CD auto-merge pipeline for streamlined development workflow
  - Auto-creates PRs when `feature/*` or `fix/*` branches pass CI
  - Auto-merges PRs after approval (requires branch protection)
  - 85% test coverage enforcement
  - Squash merge with automatic branch deletion

## [0.1.0] - 2026-02-03

### Added

- Initial release of SubTerminator CLI
- Netflix subscription cancellation support
- `subterminator cancel netflix` command with options:
  - `--dry-run` / `-n`: Stop before final confirmation
  - `--target mock|live`: Use mock server or real Netflix
  - `--headless`: Run browser in headless mode
  - `--verbose` / `-V`: Detailed output
  - `--output-dir`: Custom session artifacts directory
- State machine-based navigation through cancellation flow
- Heuristic page detection (URL patterns, text matching)
- Claude Vision AI fallback for unknown pages
- Human-in-the-loop checkpoints:
  - Authentication pause for manual login
  - Final confirmation requiring typed "confirm"
- Session logging with screenshots at each step
- Mock server for local testing (`--target mock`)
- Third-party billing detection (iTunes, Google Play, carriers)
- Comprehensive test suite (373 tests, 84% coverage)

### Developer Features

- Mock Netflix pages for testing all flow variants
- Protocol-based architecture for easy testing
- Layered design: CLI → Engine → Browser/AI → Services
- Full type hints with mypy strict mode
- GitHub Actions CI workflow

### Security

- Terms of Service warning on startup
- No credential storage
- Screenshots saved locally only
- Human confirmation required for irreversible actions
