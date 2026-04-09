"""OHLCV-based technical indicators and chart helpers.

Pure computation functions extracted from the technical analysis router.
No FastAPI/HTTP dependencies — only numpy, pandas, and typing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def _normalize_yf(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        if ticker in data.columns.get_level_values(-1):
            data = data.xs(ticker, axis=1, level=-1)
        else:
            data.columns = data.columns.get_level_values(0)
    return data[["Open", "High", "Low", "Close", "Volume"]].dropna()


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.clip(lower=0.0, upper=100.0)


def _compute_squeeze_momentum(
    df: pd.DataFrame,
    bb_length: int = 20,
    bb_mult: float = 2.0,
    kc_length: int = 20,
    kc_mult: float = 1.5,
    use_true_range: bool = True,
) -> pd.DataFrame:
    """LazyBear Squeeze Momentum Indicator."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")

    # Bollinger Bands
    basis = close.rolling(bb_length).mean()
    bb_dev = bb_mult * close.rolling(bb_length).std()
    upper_bb = basis + bb_dev
    lower_bb = basis - bb_dev

    # Keltner Channels
    ma_kc = close.rolling(kc_length).mean()
    if use_true_range:
        prev_close = close.shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    else:
        tr = high - low
    range_ma = tr.rolling(kc_length).mean()
    upper_kc = ma_kc + range_ma * kc_mult
    lower_kc = ma_kc - range_ma * kc_mult

    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
    no_sqz = ~sqz_on & ~sqz_off

    # Momentum value: linear regression of delta source
    highest_high = high.rolling(kc_length).max()
    lowest_low = low.rolling(kc_length).min()
    mid_hl = (highest_high + lowest_low) / 2
    sma_close = close.rolling(kc_length).mean()
    delta = close - (mid_hl + sma_close) / 2

    # Linear regression (linreg) over kc_length
    val = pd.Series(index=close.index, dtype=float)
    arr = delta.to_numpy(dtype=float)
    for i in range(kc_length - 1, len(arr)):
        y = arr[i - kc_length + 1 : i + 1]
        if np.isnan(y).any():
            val.iloc[i] = np.nan
            continue
        x = np.arange(kc_length, dtype=float)
        m, b = np.polyfit(x, y, 1)
        val.iloc[i] = m * (kc_length - 1) + b

    val_prev = val.shift(1)
    colors = pd.Series("gray", index=close.index)
    colors[val > 0] = "lime"
    colors[(val > 0) & (val < val_prev)] = "green"
    colors[val < 0] = "red"
    colors[(val < 0) & (val > val_prev)] = "maroon"

    sqz_color = pd.Series("gray", index=close.index)
    sqz_color[no_sqz] = "blue"
    sqz_color[sqz_on] = "black"

    return pd.DataFrame({
        "val": val,
        "bar_color": colors,
        "sqz_on": sqz_on,
        "sqz_off": sqz_off,
        "no_sqz": no_sqz,
        "sqz_dot_color": sqz_color,
    }, index=close.index)


def _compute_supertrend(
    df: pd.DataFrame,
    atr_period: int = 10,
    multiplier: float = 3.0,
) -> pd.DataFrame:
    """Classic Supertrend indicator."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    hl2 = (high + low) / 2

    # ATR
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.ewm(span=atr_period, adjust=False).mean()

    up = hl2 - multiplier * atr
    dn = hl2 + multiplier * atr

    up_arr = up.to_numpy(dtype=float)
    dn_arr = dn.to_numpy(dtype=float)
    close_arr = close.to_numpy(dtype=float)
    trend = np.ones(len(close_arr), dtype=int)

    for i in range(1, len(close_arr)):
        if np.isnan(up_arr[i]) or np.isnan(dn_arr[i]) or np.isnan(close_arr[i]):
            trend[i] = trend[i - 1]
            continue
        # Adjust up/dn
        up_arr[i] = max(up_arr[i], up_arr[i - 1]) if close_arr[i - 1] > up_arr[i - 1] else up_arr[i]
        dn_arr[i] = min(dn_arr[i], dn_arr[i - 1]) if close_arr[i - 1] < dn_arr[i - 1] else dn_arr[i]
        if trend[i - 1] == -1 and close_arr[i] > dn_arr[i - 1]:
            trend[i] = 1
        elif trend[i - 1] == 1 and close_arr[i] < up_arr[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    trend_s = pd.Series(trend, index=close.index)
    up_s = pd.Series(np.where(trend == 1, up_arr, np.nan), index=close.index)
    dn_s = pd.Series(np.where(trend == -1, dn_arr, np.nan), index=close.index)

    buy_signal = (trend_s == 1) & (trend_s.shift(1) == -1)
    sell_signal = (trend_s == -1) & (trend_s.shift(1) == 1)

    return pd.DataFrame({
        "trend": trend_s,
        "up": up_s,
        "dn": dn_s,
        "buy": buy_signal,
        "sell": sell_signal,
    }, index=close.index)


def _compute_moving_averages(
    df: pd.DataFrame,
    configs: List[dict],
) -> List[dict]:
    """Return list of MA trace dicts. Each config: {type, period, color}."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    traces = []
    for cfg in configs:
        ma_type = cfg.get("type", "SMA")
        period = int(cfg.get("period", 20))
        color = cfg.get("color", "#94a3b8")
        if ma_type == "EMA":
            values = close.ewm(span=period, adjust=False).mean()
        elif ma_type == "WMA":
            weights = np.arange(1, period + 1, dtype=float)
            values = close.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
        else:  # SMA
            values = close.rolling(period).mean()
        dates = [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in df.index]
        traces.append({
            "name": f"{ma_type} {period}",
            "x": dates,
            "y": [None if np.isnan(v) else round(float(v), 4) for v in values],
            "color": color,
            "period": period,
            "type": ma_type,
        })
    return traces


def _compute_bollinger_bands(
    df: pd.DataFrame,
    length: int = 20,
    mult: float = 2.0,
) -> dict:
    """Bollinger Bands: middle (SMA), upper, lower."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    middle = close.rolling(length).mean()
    std = close.rolling(length).std()
    upper = middle + mult * std
    lower = middle - mult * std
    dates = [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in df.index]
    return {
        "middle": [None if np.isnan(v) else round(float(v), 4) for v in middle],
        "upper": [None if np.isnan(v) else round(float(v), 4) for v in upper],
        "lower": [None if np.isnan(v) else round(float(v), 4) for v in lower],
        "dates": dates,
    }


def _compute_vwap(df: pd.DataFrame) -> dict:
    """Cumulative VWAP."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    volume = pd.to_numeric(df["Volume"], errors="coerce")
    typical_price = (high + low + close) / 3
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum().replace(0, np.nan)
    vwap = cum_tp_vol / cum_vol
    dates = [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in df.index]
    return {
        "vwap": [None if np.isnan(v) else round(float(v), 4) for v in vwap],
        "dates": dates,
    }


def _compute_stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
    smooth_k: int = 3,
) -> dict:
    """Stochastic Oscillator -- smoothed %K and %D."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    raw_k = 100 * (close - lowest_low) / denom
    k = raw_k.rolling(smooth_k).mean()
    d = k.rolling(d_period).mean()
    dates = [dd.isoformat() if hasattr(dd, "isoformat") else str(dd) for dd in df.index]
    return {
        "k": [None if np.isnan(v) else round(float(v), 2) for v in k],
        "d": [None if np.isnan(v) else round(float(v), 2) for v in d],
        "dates": dates,
    }


def _compute_atr(
    df: pd.DataFrame,
    period: int = 14,
) -> dict:
    """Average True Range."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    dates = [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in df.index]
    return {
        "atr": [None if np.isnan(v) else round(float(v), 4) for v in atr],
        "dates": dates,
    }


def _fmt_price(val: float) -> str:
    """Format price for labels: comma-separated for >=1000, 1dp for >=100, 2dp otherwise."""
    if val >= 1000:
        return f"{val:,.0f}"
    elif val >= 100:
        return f"{val:.1f}"
    else:
        return f"{val:.2f}"


def _find_support_resistance(
    highs: pd.Series,
    lows: pd.Series,
    window: int = 20,
    n_levels: int = 5,
    cluster_pct: float = 0.015,
) -> List[float]:
    """Detect key support/resistance levels from swing highs/lows."""
    levels: List[float] = []
    for i in range(window, len(highs) - window):
        if highs.iloc[i] == highs.iloc[i - window : i + window + 1].max():
            levels.append(float(highs.iloc[i]))
    for i in range(window, len(lows) - window):
        if lows.iloc[i] == lows.iloc[i - window : i + window + 1].min():
            levels.append(float(lows.iloc[i]))
    if not levels:
        return []
    levels.sort()
    clustered: List[float] = []
    current_cluster: List[float] = [levels[0]]
    for i in range(1, len(levels)):
        if (levels[i] - current_cluster[0]) / current_cluster[0] <= cluster_pct:
            current_cluster.append(levels[i])
        else:
            clustered.append(float(np.mean(current_cluster)))
            current_cluster = [levels[i]]
    clustered.append(float(np.mean(current_cluster)))
    current_price = float(highs.iloc[-1])
    clustered.sort(key=lambda x: abs(x - current_price))
    return clustered[:n_levels]


def _find_swing_points(series: pd.Series, window: int = 15) -> List[int]:
    """Return indices of swing points (local extrema)."""
    points = []
    for i in range(window, len(series) - window):
        seg = series.iloc[i - window : i + window + 1]
        if series.iloc[i] == seg.max() or series.iloc[i] == seg.min():
            points.append(i)
    return points


def _fit_trendline(
    dates: list, values: pd.Series, indices: List[int], is_high: bool
) -> Optional[Dict[str, Any]]:
    """Fit a trendline through the 2 most recent swing highs or lows.
    Returns dict with x0, y0, x1, y1 for plotting, or None."""
    if len(indices) < 2:
        return None
    # Take the last two points
    i1, i2 = indices[-2], indices[-1]
    y1, y2 = float(values.iloc[i1]), float(values.iloc[i2])
    # Extend line to the right edge
    slope = (y2 - y1) / (i2 - i1) if i2 != i1 else 0
    y_end = y2 + slope * (len(values) - 1 - i2)
    return {
        "x0": dates[i1],
        "y0": y1,
        "x1": dates[-1],
        "y1": y_end,
        "color": "rgba(239,68,68,0.45)" if is_high else "rgba(34,197,94,0.45)",
    }
