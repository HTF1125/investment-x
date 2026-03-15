from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from pandas.tseries.offsets import MonthEnd
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)


def _clean_series(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return clean
    try:
        clean = clean.sort_index()
    except Exception:
        logger.debug("Failed to sort series index", exc_info=True)
    return clean


def Resample(
    series: pd.Series,
    freq: str = "ME",
) -> pd.Series:
    """Resample series to target frequency using last value."""
    return series.resample(freq).last()


def PctChange(
    series: pd.Series,
    periods: int = 1,
) -> pd.Series:
    """Calculate percentage change over specified periods."""
    clean = _clean_series(series)
    out = clean.pct_change(periods=periods, fill_method=None)
    return out.replace([np.inf, -np.inf], np.nan).dropna()


def Diff(
    series: pd.Series,
    periods: int = 1,
) -> pd.Series:
    """Calculate difference over specified periods."""
    return series.diff(periods=periods)


def MovingAverage(
    series: pd.Series,
    window: int = 3,
) -> pd.Series:
    """Calculate moving average over specified window."""
    return series.rolling(window=window).mean()


def MonthEndOffset(
    series: pd.Series,
    months: int = 3,
) -> pd.Series:
    """Offset series index by months and align to month end."""
    series = series.copy()
    shifted = series.index + pd.DateOffset(months=months)
    series.index = shifted + MonthEnd(0)
    return series


def MonthsOffset(
    series: pd.Series,
    months: int,
) -> pd.Series:
    """Offset series index by specified number of months."""
    series = series.copy()
    shifted = series.index + pd.DateOffset(months=months)
    series.index = shifted
    return series


def Offset(
    series: pd.Series,
    months: int = 0,
    days: int = 0,
    start: Optional[str] = None,
) -> pd.Series:
    """Offset series index by specified months and/or days."""
    if start is not None:
        if series.empty:
            return series
        start_date = pd.to_datetime(start)
        shifted = series.index + (start_date - series.index[0])
    else:
        shifted = series.index + pd.DateOffset(months=months, days=days)
    series = series.copy()
    series.index = shifted
    return series


def StandardScalar(
    series: pd.Series,
    window: int = 20,
) -> pd.Series:
    """Standardize series using rolling mean and standard deviation."""
    clean = _clean_series(series)
    if clean.empty or window < 2:
        return pd.Series(dtype=float, name=getattr(series, "name", None))
    roll = clean.rolling(window=window)
    mean, std = roll.mean(), roll.std()
    z = clean.sub(mean).div(std.replace(0, np.nan))
    return z.replace([np.inf, -np.inf], np.nan).dropna()


def Clip(
    series: pd.Series,
    lower: Optional[float] = None,
    upper: Optional[float] = None,
) -> pd.Series:
    """Clip series values to specified lower and upper bounds."""
    return series.clip(lower=lower, upper=upper)


def Ffill(series: pd.Series) -> pd.Series:
    """Forward fill missing values in a series."""
    return series.ffill()


def Rebase(series: pd.Series) -> pd.Series:
    """Rebase series to start at 1.0 using first non-null value."""
    clean = _clean_series(series)
    if clean.empty:
        return clean
    base = clean.iloc[0]
    if not np.isfinite(base) or base == 0:
        return pd.Series(dtype=float, name=getattr(series, "name", None))
    return clean / base


def Drawdown(series: pd.Series, window: Optional[int] = None) -> pd.Series:
    """Calculate drawdown from peak (rolling or expanding)."""
    clean = _clean_series(series)
    if clean.empty:
        return clean
    if window:
        peak = clean.rolling(window=window, min_periods=1).max()
    else:
        peak = clean.expanding(min_periods=1).max()
    return clean.div(peak).sub(1.0).replace([np.inf, -np.inf], np.nan)


def find_best_window(series: pd.Series, max_lag: Optional[int] = None) -> int:
    """
    Automatically find the dominant cycle length (best window size)
    using the autocorrelation function.
    """
    if max_lag is None:
        max_lag = min(365, len(series) // 2)
    ac = [series.autocorr(lag) for lag in range(1, max_lag)]
    best_window = np.argmax(ac) + 1
    return best_window


def CycleForecast(
    series: pd.Series, forecast_steps: int = 12, window_size: Optional[int] = None
) -> pd.Series:

    series = series.dropna()
    t = np.arange(len(series))
    y = series.values
    y_centered = y - y.mean()

    if window_size is None:
        window_size = find_best_window(series)
        window_size = max(window_size, 8)
        window_size = min(window_size, len(series) // 2)

    freqs = []
    for i in range(0, len(y) - window_size + 1, max(1, window_size // 2)):
        window = y_centered[i : i + window_size]
        yf = np.fft.fft(window)
        xf = np.fft.fftfreq(window_size)
        idx_peak = np.argmax(np.abs(yf[1 : window_size // 2])) + 1
        freqs.append(abs(xf[idx_peak]))
    freq_trend = np.interp(t, np.linspace(0, len(t) - 1, len(freqs)), freqs)

    def sine_model_varfreq(t, A, phi, C):
        phase = 2 * np.pi * np.cumsum(freq_trend)
        return A * np.sin(phase + phi) + C

    popt, _ = curve_fit(
        sine_model_varfreq,
        t,
        y,
        p0=[(y.max() - y.min()) / 2, 0, y.mean()],
        maxfev=10000,
    )

    t_forecast = np.arange(len(t) + forecast_steps)
    freq_forecast = np.concatenate(
        [freq_trend, np.full(forecast_steps, freq_trend[-1])]
    )
    phase_forecast = 2 * np.pi * np.cumsum(freq_forecast)
    y_fitted = popt[0] * np.sin(phase_forecast + popt[1]) + popt[2]

    full_index = pd.date_range(
        series.index[0], periods=len(t_forecast), freq=pd.infer_freq(series.index)
    )
    fitted_series = pd.Series(y_fitted, index=full_index)

    return fitted_series


def NumPositivePercentByRow(df: pd.DataFrame):
    """Return a Series giving the percentage of positive entries per row (ignoring NaN)."""
    positive = (df > 0).sum(axis=1)
    total = df.notna().sum(axis=1)
    return (positive / total * 100).fillna(0)


def Regime1(series: pd.Series) -> pd.Series:
    """Calculate regime classification based on MACD histogram."""
    from ix import core

    macd = core.MACD(px=series).histogram
    regime = core.Regime1(series=macd).to_dataframe()["regime"]
    return regime
