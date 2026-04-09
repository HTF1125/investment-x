"""DataFrame formatting, timezone normalization, and date helpers."""

from __future__ import annotations

import math
from collections import OrderedDict
from datetime import datetime
from typing import List, Optional

import pandas as pd


def normalize_timezone(ts: pd.Timestamp) -> pd.Timestamp:
    """Strip timezone info from a Timestamp."""
    try:
        return ts.tz_localize(None)
    except Exception:
        try:
            return ts.tz_convert(None)
        except Exception:
            return ts


def _apply_date_bounds(
    series: pd.Series, start_date: Optional[str], end_date: Optional[str]
) -> pd.Series:
    """Filter a Series by optional start/end date bounds."""
    if start_date:
        start_dt = pd.to_datetime(start_date, errors="coerce")
        if start_dt:
            series = series.loc[series.index >= start_dt]
    if end_date:
        end_dt = pd.to_datetime(end_date, errors="coerce")
        if end_dt:
            series = series.loc[series.index <= end_dt]
    return series


def normalize_dataframe_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Strip timezone info from a DataFrame's DatetimeIndex."""
    try:
        df.index = pd.DatetimeIndex(df.index).tz_localize(None)
    except Exception:
        try:
            df.index = pd.DatetimeIndex(df.index).tz_convert(None)
        except Exception:
            pass
    return df


def format_dataframe_to_column_dict(
    df: pd.DataFrame,
    series_list: List[pd.Series],
    start_date: Optional[str],
    end_date: Optional[str],
) -> OrderedDict:
    """Convert a DataFrame into column-oriented OrderedDict for JSON response.

    This is a pure-data function: the router wraps the result in a Response.
    """
    df.index.name = "Date"

    # Optional date bounds
    start_ts = pd.to_datetime(start_date, errors="coerce") if start_date else None
    end_ts = pd.to_datetime(end_date, errors="coerce") if end_date else None

    # Normalize timezone info
    df = normalize_dataframe_tz(df)

    # Resample to daily frequency, drop all-NaN rows (weekends/holidays)
    df = df.resample("D").last().dropna(how="all")

    if isinstance(start_ts, pd.Timestamp):
        start_ts = normalize_timezone(start_ts)
    if isinstance(end_ts, pd.Timestamp):
        end_ts = normalize_timezone(end_ts)

    # Apply slicing if bounds are valid
    if isinstance(start_ts, pd.Timestamp):
        df = df[df.index >= start_ts]
    if isinstance(end_ts, pd.Timestamp):
        df = df[df.index <= end_ts]

    # Reorder columns to preserve input order
    present_in_order = [s.name for s in series_list if s.name in df.columns]
    seen_present: set = set()
    present_in_order = [
        c
        for c in present_in_order
        if not (c in seen_present or seen_present.add(c))
    ]
    df = df[present_in_order]

    # Sort dates ascending
    df = df.sort_index(ascending=True)

    return _dataframe_to_column_dict(df)


def format_favorites_dataframe(
    series_list: List[pd.Series],
    start_date: Optional[str],
    end_date: Optional[str],
) -> OrderedDict:
    """Concatenate favorite timeseries and return column-oriented OrderedDict."""
    if not series_list:
        return OrderedDict({"Date": []})

    df = pd.concat(series_list, axis=1)
    df.index.name = "Date"

    # Optional date slicing
    start_ts = pd.to_datetime(start_date, errors="coerce") if start_date else None
    end_ts = pd.to_datetime(end_date, errors="coerce") if end_date else None

    # Normalize timezone info
    df = normalize_dataframe_tz(df)

    df = df.resample("D").last()

    if isinstance(start_ts, pd.Timestamp):
        start_ts = normalize_timezone(start_ts)
    if isinstance(end_ts, pd.Timestamp):
        end_ts = normalize_timezone(end_ts)

    # Apply slicing if bounds are valid
    if isinstance(start_ts, pd.Timestamp):
        df = df[df.index >= start_ts]
    if isinstance(end_ts, pd.Timestamp):
        df = df[df.index <= end_ts]

    # Sort dates ascending
    df = df.sort_index(ascending=True)

    return _dataframe_to_column_dict(df)


def _dataframe_to_column_dict(df: pd.DataFrame) -> OrderedDict:
    """Convert a DataFrame to an OrderedDict of columns (JSON-serialisable)."""
    df_indexed = df.reset_index()
    column_dict = OrderedDict()

    for col in df_indexed.columns:
        values = df_indexed[col].tolist()
        cleaned_values = []
        for v in values:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                cleaned_values.append(None)
            elif isinstance(v, (pd.Timestamp, datetime)):
                cleaned_values.append(v.isoformat())
            else:
                cleaned_values.append(v)
        column_dict[col] = cleaned_values

    return column_dict
