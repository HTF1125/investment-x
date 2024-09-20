from typing import overload
import pandas as pd


@overload
def to_rsi(
    px_last: pd.Series,
    window: int = 10,
) -> pd.Series: ...


@overload
def to_rsi(
    px_last: pd.DataFrame,
    window: int = 10,
) -> pd.DataFrame: ...


def to_rsi(
    px_last: pd.Series | pd.DataFrame,
    window: int = 14,
) -> pd.Series | pd.DataFrame:
    """
    Calculate the Relative Strength Index (RSI) for each element in a time series.

    Parameters:
        px_close (pd.Series): Series of closing prices.
        window (int): Window size for RSI calculation. Defaults to 14.

    Returns:
        pd.Series: Series of RSI values.
    """
    delta = px_last.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
