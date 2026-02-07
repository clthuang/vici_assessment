import json
from unittest.mock import patch

import pandas as pd
from typer.testing import CliRunner

runner = CliRunner()


def _mock_download(ticker, **kwargs):
    """Mock yfinance.download that returns valid price data per symbol."""
    if ticker == "INVALID_SYMBOL_XYZ":
        return pd.DataFrame()
    n = 60
    dates = pd.bdate_range("2020-01-01", periods=n)
    closes = [100.0 * (1.01**t) for t in range(n)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes,
            "Low": closes,
            "Close": closes,
            "Volume": [1e6] * n,
        },
        index=dates,
    )


class TestCLIVerify:
    def test_cli_verify(self):
        from stock_backtester.cli import app

        result = runner.invoke(app, ["verify"])
        assert result.exit_code == 0
        assert "PASS" in result.output


class TestCLIRunJson:
    @patch("stock_backtester.data.yf.download", side_effect=_mock_download)
    def test_cli_run_json(self, mock_yf):
        from stock_backtester.cli import app

        result = runner.invoke(app, ["run", "--symbols", "TEST", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert isinstance(parsed, dict)
        assert "metrics" in parsed


class TestCLISimulate:
    @patch("stock_backtester.data.yf.download", side_effect=_mock_download)
    def test_cli_simulate(self, mock_yf):
        from stock_backtester.cli import app

        result = runner.invoke(
            app, ["simulate", "--symbols", "TEST", "--paths", "10", "--seed", "42"]
        )
        assert result.exit_code == 0
        assert "ruin" in result.output.lower()


class TestCLIInvalidSymbol:
    @patch("stock_backtester.data.yf.download", side_effect=_mock_download)
    def test_cli_invalid_symbol(self, mock_yf):
        from stock_backtester.cli import app

        result = runner.invoke(app, ["run", "--symbols", "INVALID_SYMBOL_XYZ"])
        assert result.exit_code == 1


class TestCLIHelp:
    def test_cli_help(self):
        from stock_backtester.cli import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output or "usage" in result.output
