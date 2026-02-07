import pandas as pd
import yfinance as yf

from stock_backtester.types import PriceData


class DataError(Exception):
    pass


def validate_prices(df: pd.DataFrame, symbol: str) -> None:
    if df["close"].isna().any():
        bad_dates = df.index[df["close"].isna()].tolist()
        raise DataError(f"Invalid prices: NaN detected in {symbol} at {bad_dates}")
    if (df["close"] <= 0).any():
        bad_dates = df.index[df["close"] <= 0].tolist()
        raise DataError(
            f"Invalid prices: non-positive values in {symbol} at {bad_dates}"
        )
    if len(df) < 30:
        raise DataError(
            "Insufficient data for reliable estimation. Need at least 30 trading days"
        )


def align_dates(price_dfs: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    common = None
    for df in price_dfs.values():
        idx = df.index
        common = idx if common is None else common.intersection(idx)
    if common is None or len(common) == 0:
        raise DataError("No common trading days across symbols")
    return pd.DatetimeIndex(common.sort_values())


def fetch_prices(symbols: list[str], start_date: str, end_date: str) -> PriceData:
    if not symbols:
        raise DataError("No symbols provided")

    raw: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        df = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            multi_level_index=False,
        )
        if df is None or df.empty:
            raise DataError(f"No data for ticker {symbol}. Check symbol and date range")
        df.columns = df.columns.str.lower()
        raw[symbol] = df

    for symbol, df in raw.items():
        validate_prices(df, symbol)

    aligned = align_dates(raw)

    if len(aligned) < 30:
        raise DataError(
            "Insufficient data for reliable estimation. Need at least 30 trading days"
        )

    prices_dict: dict[str, pd.DataFrame] = {}
    for symbol, df in raw.items():
        prices_dict[symbol] = df.reindex(aligned)

    return PriceData(
        prices=prices_dict,
        symbols=symbols,
        source="yfinance",
        adjusted=True,
        aligned_dates=aligned,
    )
