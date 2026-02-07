# Changelog

All notable changes to Stock Backtester will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-07

### Added

- Vectorized backtesting engine with transaction cost modeling (commission + slippage)
- Kelly criterion optimal fraction and ruin probability analysis
- Monte Carlo simulation with bootstrap resampling and configurable path count
- CLI (`backtest`) with three commands:
  - `run` -- historical backtest against real market data via yfinance
  - `simulate` -- Monte Carlo stress testing with confidence intervals
  - `verify` -- known-answer verification suite for 8 acceptance criteria
- Table and JSON output formats for all commands
- Equal-weight portfolio strategy
- 88 tests at 93% code coverage
