# Changelog

All notable changes to SubTerminator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
