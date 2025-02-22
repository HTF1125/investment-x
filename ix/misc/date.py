from typing import Optional
import pandas as pd
from pandas.tseries.offsets import BDay


def now() -> pd.Timestamp:
    """Returns the current timestamp."""
    return pd.Timestamp("now")


def today() -> pd.Timestamp:
    """Returns today's date as a timestamp with no time component."""
    return pd.Timestamp.now().normalize()


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


def to_timestamp(text: str, normalize: bool = False) -> pd.Timestamp:
    """Parses a date string into a timestamp, with error handling."""
    try:
        out = pd.Timestamp(text)
        if normalize:
            out = out.normalize()
        return out
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


def relative_timestamp(
    asofdate: pd.Timestamp,
    period: str = "1D",
    offset_1d: bool = False,
    normalize: bool = False,
) -> pd.Timestamp:
    """
    Calculate a relative date from the given timestamp based on the specified period.

    Parameters
    ----------
    asofdate : pd.Timestamp
        The reference date.
    period : str, optional
        The offset period. Supported values are:
          - "1D": 1 day
          - "1W": 1 week
          - "1M": 1 month
          - "3M": 3 months
          - "6M": 6 months
          - "1Y": 1 year
          - "3Y": 3 years
          - "MTD": Month-to-date (subtracts to the beginning of the month, then one day)
          - "YTD": Year-to-date (subtracts to the beginning of the year, then one day)
    offset_1d : bool, optional
        If True, adds an extra day to the computed offset.

    Returns
    -------
    pd.Timestamp
        The computed relative date.

    Raises
    ------
    ValueError
        If the period provided is not supported.
    """
    # Mapping for standard day and month offsets
    period_mapping = {
        "1D": pd.DateOffset(days=1),
        "1W": pd.DateOffset(days=7),
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(months=12),
        "3Y": pd.DateOffset(months=36),
        "5Y": pd.DateOffset(months=60),
    }

    if period in period_mapping:
        outdate = asofdate - period_mapping[period]
    elif period == "MTD":
        # Month-to-date: go to the month start then subtract one day
        outdate = asofdate - pd.offsets.MonthBegin() - pd.DateOffset(days=1)
    elif period == "YTD":
        # Year-to-date: go to the year start then subtract one day
        outdate = asofdate - pd.offsets.YearBegin() - pd.DateOffset(days=1)
    else:
        raise ValueError(f"Unsupported period: {period}")

    # Adjust by one day if offset_1d is True
    if offset_1d:
        outdate += pd.DateOffset(days=1)

    if normalize:
        outdate = outdate.normalize()

    return outdate


periods = {
    "1D": "One Day",
    "1W": "One Week",
    "1M": "One Month",
    "3M": "Three Months",
    "6M": "Six Months",
    "1Y": "One Year",
    "3Y": "Three Years",
    "5Y": "Five Years",
    "MTD": "Month-to-Date (Start of the Current Month)",
    "YTD": "Year-to-Date (Start of the Current Year)",
}
