from unittest.mock import patch

import pandas as pd
import pytest


def _mock_yf_response(closes: list[float], symbol: str = "TEST") -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=len(closes))
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes,
            "Low": closes,
            "Close": closes,
            "Volume": [1e6] * len(closes),
        },
        index=dates,
    )


class TestFetchPrices:
    @patch("stock_backtester.data.yf")
    def test_fetch_valid_single_symbol(self, mock_yf):
        from stock_backtester.data import fetch_prices

        mock_yf.download.return_value = _mock_yf_response(
            [100.0 + i for i in range(50)]
        )
        result = fetch_prices(["TEST"], "2020-01-01", "2020-04-01")
        assert "TEST" in result.prices
        assert list(result.prices["TEST"].columns) == [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

    @patch("stock_backtester.data.yf")
    def test_column_normalization(self, mock_yf):
        from stock_backtester.data import fetch_prices

        mock_yf.download.return_value = _mock_yf_response(
            [100.0 + i for i in range(50)]
        )
        result = fetch_prices(["TEST"], "2020-01-01", "2020-04-01")
        for col in result.prices["TEST"].columns:
            assert col == col.lower()

    @patch("stock_backtester.data.yf")
    def test_fetch_empty_response(self, mock_yf):
        from stock_backtester.data import DataError, fetch_prices

        mock_yf.download.return_value = pd.DataFrame()
        with pytest.raises(DataError, match="No data for ticker"):
            fetch_prices(["TEST"], "2020-01-01", "2020-04-01")

    @patch("stock_backtester.data.yf")
    def test_fetch_nan_prices(self, mock_yf):
        from stock_backtester.data import DataError, fetch_prices

        closes = [100.0] * 50
        closes[10] = float("nan")
        mock_yf.download.return_value = _mock_yf_response(closes)
        with pytest.raises(DataError, match="NaN"):
            fetch_prices(["TEST"], "2020-01-01", "2020-04-01")

    @patch("stock_backtester.data.yf")
    def test_fetch_non_positive_prices(self, mock_yf):
        from stock_backtester.data import DataError, fetch_prices

        closes = [100.0] * 50
        closes[5] = -1.0
        mock_yf.download.return_value = _mock_yf_response(closes)
        with pytest.raises(DataError, match="non-positive"):
            fetch_prices(["TEST"], "2020-01-01", "2020-04-01")

    @patch("stock_backtester.data.yf")
    def test_fetch_insufficient_bars(self, mock_yf):
        from stock_backtester.data import DataError, fetch_prices

        mock_yf.download.return_value = _mock_yf_response([100.0] * 10)
        with pytest.raises(DataError, match="Insufficient data"):
            fetch_prices(["TEST"], "2020-01-01", "2020-01-15")

    @patch("stock_backtester.data.yf")
    def test_multi_symbol_alignment(self, mock_yf):
        from stock_backtester.data import fetch_prices

        dates_a = pd.bdate_range("2020-01-01", periods=60)
        dates_b = pd.bdate_range("2020-01-10", periods=60)

        def side_effect(symbol, **kwargs):
            if symbol == "A":
                return pd.DataFrame(
                    {
                        "Open": 100.0,
                        "High": 100.0,
                        "Low": 100.0,
                        "Close": 100.0,
                        "Volume": 1e6,
                    },
                    index=dates_a,
                )
            else:
                return pd.DataFrame(
                    {
                        "Open": 100.0,
                        "High": 100.0,
                        "Low": 100.0,
                        "Close": 100.0,
                        "Volume": 1e6,
                    },
                    index=dates_b,
                )

        mock_yf.download.side_effect = side_effect
        result = fetch_prices(["A", "B"], "2020-01-01", "2020-04-01")
        # Inner join: only dates common to both
        assert len(result.aligned_dates) > 0
        assert len(result.aligned_dates) < 60

    @patch("stock_backtester.data.yf")
    def test_no_common_dates(self, mock_yf):
        from stock_backtester.data import DataError, fetch_prices

        dates_a = pd.bdate_range("2020-01-01", periods=40)
        dates_b = pd.bdate_range("2021-01-01", periods=40)

        def side_effect(symbol, **kwargs):
            if symbol == "A":
                return pd.DataFrame(
                    {
                        "Open": 100.0,
                        "High": 100.0,
                        "Low": 100.0,
                        "Close": 100.0,
                        "Volume": 1e6,
                    },
                    index=dates_a,
                )
            else:
                return pd.DataFrame(
                    {
                        "Open": 100.0,
                        "High": 100.0,
                        "Low": 100.0,
                        "Close": 100.0,
                        "Volume": 1e6,
                    },
                    index=dates_b,
                )

        mock_yf.download.side_effect = side_effect
        with pytest.raises(DataError, match="No common trading days"):
            fetch_prices(["A", "B"], "2020-01-01", "2022-01-01")
