from __future__ import annotations

import pandas as pd


def _prepare_pivot(series: pd.Series, exclude_years=None, rebase: bool = False) -> pd.DataFrame:
    s = series.resample("D").last().ffill()
    s.index = pd.to_datetime(s.index)
    df = s.dropna().to_frame(name="value")
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day
    df = df[~((df["month"] == 2) & (df["day"] == 29))]
    pivot = df.pivot_table(index=["month", "day"], columns="year", values="value")

    if exclude_years:
        pivot = pivot.drop(columns=exclude_years, errors="ignore")

    if rebase:
        pivot = pivot.div(pivot.iloc[0]).sub(1)

    return pivot


def _calculate_statistics(pivot: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"Average": pivot.mean(axis=1)})


def calendar_year_seasonality(series: pd.Series, exclude_years=None) -> pd.DataFrame:
    """Analyze seasonality of a daily time series by calendar day across years."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Input series must have a DateTimeIndex.")
    pivot = _prepare_pivot(series, exclude_years=exclude_years, rebase=False)
    latest_year = pivot.columns.max()
    current_year_series = pivot[latest_year].rename(str(latest_year))
    stats = _calculate_statistics(pivot)
    return pd.concat([stats, current_year_series], axis=1)


def calendar_year_seasonality_rebased(series: pd.Series, exclude_years=None) -> pd.DataFrame:
    """Rebased seasonality of a daily time series by calendar day across years."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Input series must have a DateTimeIndex.")
    pivot = _prepare_pivot(series, exclude_years=exclude_years, rebase=True)
    latest_year = pivot.columns.max()
    current_year_series = pivot[latest_year].rename(str(latest_year))
    stats = _calculate_statistics(pivot)
    return pd.concat([stats, current_year_series], axis=1)


# Backward-compatible wrapper
class CalendarYearSeasonality:
    def __init__(self, series: pd.Series):
        if not isinstance(series.index, pd.DatetimeIndex):
            raise ValueError("Input series must have a DateTimeIndex.")
        self._series = series

    def seasonality(self, exclude_years=None, include_stats=True) -> pd.DataFrame:
        return calendar_year_seasonality(self._series, exclude_years=exclude_years)

    def rebased(self, exclude_years=None) -> pd.DataFrame:
        return calendar_year_seasonality_rebased(self._series, exclude_years=exclude_years)
