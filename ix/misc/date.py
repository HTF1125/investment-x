from typing import Optional
import pandas as pd
from pandas.tseries.offsets import BDay


def now() -> pd.Timestamp:
    """Returns the current timestamp."""
    return pd.Timestamp("now")


def today() -> pd.Timestamp:
    """Returns today's date as a timestamp."""
    return pd.Timestamp("today")


def yesterday() -> pd.Timestamp:
    """Returns yesterday's date as a timestamp."""
    return today() - pd.DateOffset(days=1)


def last_business_day() -> pd.Timestamp:
    """
    Returns the last business day. If today is the first business day
    of the month, returns the last business day of the previous month.
    """
    last_bday = today() - BDay(1)
    return last_bday


def lastyear() -> pd.Timestamp:
    """Returns the date one year ago from today."""
    return today() - pd.DateOffset(years=1)


def to_timestamp(text: str) -> pd.Timestamp:
    """Parses a date string into a timestamp, with error handling."""
    try:
        return pd.Timestamp(text)
    except ValueError:
        raise ValueError(f"Invalid date format: {text}")


def onemonthlater(asofdate: Optional[pd.Timestamp] = None) -> pd.Timestamp:
    """Returns the date one month from today."""
    return asofdate or today() + pd.DateOffset(months=1)


def onemonthbefore() -> pd.Timestamp:
    """Returns the date one month before today."""
    return today() - pd.DateOffset(months=1)


def oneweekbefore() -> pd.Timestamp:
    """Returns the date one month before today."""
    return today() - pd.DateOffset(days=7)


def tomorrow() -> pd.Timestamp:
    """Returns tomorrow's date as a timestamp."""
    return today() + pd.DateOffset(days=1)


def get_relative_date(
    asofdate: pd.Timestamp,
    period: str = "1D",
) -> pd.Timestamp:
    if period == "1D":
        return asofdate - pd.DateOffset(days=1)
    if period == "1W":
        return asofdate - pd.DateOffset(days=7)
    if period == "1M":
        return asofdate - pd.DateOffset(months=1)
    if period == "3M":
        return asofdate - pd.DateOffset(months=3)
    if period == "6M":
        return asofdate - pd.DateOffset(months=6)
    if period == "1Y":
        return asofdate - pd.DateOffset(months=12)
    if period == "3Y":
        return asofdate - pd.DateOffset(months=12 * 3)
    if period == "MTD":
        return asofdate - pd.offsets.MonthBegin() - pd.DateOffset(days=1)
    if period == "YTD":
        return asofdate - pd.offsets.YearBegin() - pd.DateOffset(days=1)
    raise
