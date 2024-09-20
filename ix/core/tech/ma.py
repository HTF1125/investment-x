import pandas as pd
from .. import perf



def to_rsi(
    px_close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI) for each element in a time series.

    Parameters:
        px_close (pd.Series): Series of closing prices.
        window (int): Window size for RSI calculation. Defaults to 14.

    Returns:
        pd.Series: Series of RSI values.
    """
    delta = px_close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def to_typical_price(
    px_high: pd.Series,
    px_low: pd.Series,
    px_close: pd.Series,
) -> pd.Series:
    data = pd.concat([px_high, px_low, px_close], axis=1)
    return data.mean(axis=1)


def to_stdev(
    px_close: pd.Series,
    window: int = 10,
) -> pd.Series:
    return perf.to_log_return(px_close).rolling(window).std()


def to_bb_middle(
    px_high: pd.Series,
    px_low: pd.Series,
    px_close: pd.Series,
    window: int = 10,
) -> pd.Series:
    typical_price = to_typical_price(px_high=px_high, px_low=px_low, px_close=px_close)
    return to_sma(typical_price, window)


def to_bb_upper(
    px_high: pd.Series,
    px_low: pd.Series,
    px_close: pd.Series,
    window: int = 10,
    multiplier: float = 1.5,
) -> pd.Series:
    typical_price = to_typical_price(px_high=px_high, px_low=px_low, px_close=px_close)
    sma = to_sma(typical_price, window)
    stdev = to_stdev(typical_price, window)
    bb_upper = sma + multiplier * stdev
    return bb_upper


def to_bb_lower(
    px_high: pd.Series,
    px_low: pd.Series,
    px_close: pd.Series,
    window: int = 10,
    multiplier: float = 1.5,
) -> pd.Series:
    typical_price = to_typical_price(px_high=px_high, px_low=px_low, px_close=px_close)
    sma = to_sma(typical_price, window)
    stdev = to_stdev(typical_price, window)
    return sma - multiplier * stdev


def to_true_range(
    px_high: pd.Series,
    px_low: pd.Series,
    px_close: pd.Series,
) -> pd.Series:
    """
    Compute True Range for each period.

    Parameters:
        px_high (pd.Series): Series of high prices.
        px_low (pd.Series): Series of low prices.
        px_close (pd.Series): Series of close prices.

    Returns:
        pd.Series: True Range for each period.
    """
    high_low = px_high - px_low
    high_close = (px_high - px_close.shift()).abs()
    low_close = (px_low - px_close.shift()).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


def to_average_true_range(
    px_high: pd.Series,
    px_low: pd.Series,
    px_close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Compute the Average True Range (ATR).

    Parameters:
        px_high (pd.Series): Series of high prices.
        px_low (pd.Series): Series of low prices.
        px_close (pd.Series): Series of close prices.
        period (int): The number of periods to consider. Defaults to 14.

    Returns:
        float: The Average True Range.
    """
    true_range = to_true_range(px_high, px_low, px_close)
    atr = true_range.ewm(span=period, adjust=False).mean()
    return atr
