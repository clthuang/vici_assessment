import pytest

from stock_backtester.types import BacktestConfig, OutputFormat


def test_frozen_rejects_setattr():
    config = BacktestConfig(
        symbols=["AAPL"],
        start_date="2020-01-01",
        end_date="2025-01-01",
        strategy_name="equal-weight",
        strategy_params={},
        commission_per_share=0.001,
        slippage_k=0.5,
        ruin_threshold=0.01,
        drawdown_level=0.50,
        output_format=OutputFormat.TABLE,
    )
    with pytest.raises(AttributeError):
        config.symbols = ["MSFT"]  # type: ignore[misc]


def test_backtest_config_no_defaults():
    with pytest.raises(TypeError):
        BacktestConfig(symbols=["AAPL"])  # type: ignore[call-arg]


def test_output_format_values():
    assert OutputFormat.TABLE.value == "table"
    assert OutputFormat.JSON.value == "json"
