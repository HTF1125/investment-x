from typing import overload
import pandas as pd


@overload
def to_sma(
    px_last: pd.Series,
    window: int = 10,
) -> pd.Series: ...


@overload
def to_sma(
    px_last: pd.DataFrame,
    window: int = 10,
) -> pd.DataFrame: ...


def to_sma(
    px_last: pd.Series | pd.DataFrame,
    window: int = 10,
) -> pd.Series | pd.DataFrame:
    """
    Calculate the Simple Moving Average (SMA) of a Series.

    Parameters:
        px_close (pd.Series): Series of prices.
        window (int): Window size for SMA calculation. Defaults to 10.

    Returns:
        pd.Series: Series of SMA values.
    """
    return px_last.rolling(window).mean()
