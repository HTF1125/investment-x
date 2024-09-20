from typing import overload
import pandas as pd


@overload
def to_ema(
    px_last: pd.Series,
    span: int = 10,
) -> pd.Series: ...


@overload
def to_ema(
    px_last: pd.DataFrame,
    span: int = 10,
) -> pd.DataFrame: ...


def to_ema(
    px_last: pd.Series | pd.DataFrame,
    span: int = 10,
) -> pd.Series | pd.DataFrame:
    """
    Calculate the Exponential Moving Average (EMA) of a Series.

    Parameters:
        px_close (pd.Series): Series of prices.
        span (int): Span for EMA calculation. Defaults to 10.

    Returns:
        pd.Series: Series of EMA values.
    """
    return px_last.ewm(span=span).mean()
