from __future__ import annotations

import json
from typing import Dict, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import yfinance as yf
from fastapi import APIRouter, HTTPException, Query
from plotly.subplots import make_subplots

router = APIRouter()


class TDSequentialClean:
    def __init__(
        self,
        show_setup_from: int = 9,
        show_countdown_from: int = 13,
        label_cooldown_bars: int = 0,
        setup_lookback: int = 4,
        setup_len: int = 9,
        countdown_lookback: int = 2,
        countdown_len: int = 13,
        suppress_setup_when_cd_active: bool = False,
        cancel_on_opposite_setup9: bool = True,
    ):
        self.show_setup_from = show_setup_from
        self.show_countdown_from = show_countdown_from
        self.label_cooldown_bars = label_cooldown_bars
        self.setup_lookback = setup_lookback
        self.setup_len = setup_len
        self.countdown_lookback = countdown_lookback
        self.countdown_len = countdown_len
        self.suppress_setup_when_cd_active = suppress_setup_when_cd_active
        self.cancel_on_opposite_setup9 = cancel_on_opposite_setup9

    def _cooldown_mask(self, base_mask: pd.Series) -> pd.Series:
        if self.label_cooldown_bars <= 0:
            return base_mask
        keep = np.zeros(len(base_mask), dtype=bool)
        cooldown = 0
        for i, flag in enumerate(base_mask.to_numpy()):
            if cooldown > 0:
                cooldown -= 1
                continue
            if flag:
                keep[i] = True
                cooldown = self.label_cooldown_bars
        return pd.Series(keep, index=base_mask.index)

    def compute(self, close: pd.Series) -> pd.DataFrame:
        close = pd.to_numeric(close, errors="coerce").astype(float).dropna().sort_index()
        if len(close) < 20:
            raise ValueError("close series too short")
        n = len(close)
        bear_cond = close > close.shift(self.setup_lookback)
        bull_cond = close < close.shift(self.setup_lookback)
        bear_setup = np.zeros(n, dtype=int)
        bull_setup = np.zeros(n, dtype=int)
        bs = us = 0
        for i in range(n):
            bs = bs + 1 if bool(bear_cond.iloc[i]) else 0
            us = us + 1 if bool(bull_cond.iloc[i]) else 0
            bear_setup[i] = bs if 1 <= bs <= self.setup_len else 0
            bull_setup[i] = us if 1 <= us <= self.setup_len else 0

        bear_cd_cond = close >= close.shift(self.countdown_lookback)
        bull_cd_cond = close <= close.shift(self.countdown_lookback)
        bear_cd = np.zeros(n, dtype=int)
        bull_cd = np.zeros(n, dtype=int)
        bear_cd_active = np.zeros(n, dtype=bool)
        bull_cd_active = np.zeros(n, dtype=bool)
        bear_active = bull_active = False
        bear_count = bull_count = 0
        for i in range(n):
            if bear_setup[i] == self.setup_len:
                bear_active = True
                bear_count = 0
                if self.cancel_on_opposite_setup9:
                    bull_active = False
                    bull_count = 0
            if bull_setup[i] == self.setup_len:
                bull_active = True
                bull_count = 0
                if self.cancel_on_opposite_setup9:
                    bear_active = False
                    bear_count = 0
            bear_cd_active[i] = bear_active
            bull_cd_active[i] = bull_active
            if bear_active:
                if bear_count < self.countdown_len and bool(bear_cd_cond.iloc[i]):
                    bear_count += 1
                bear_cd[i] = bear_count
                if bear_count >= self.countdown_len:
                    bear_active = False
            if bull_active:
                if bull_count < self.countdown_len and bool(bull_cd_cond.iloc[i]):
                    bull_count += 1
                bull_cd[i] = bull_count
                if bull_count >= self.countdown_len:
                    bull_active = False

        return pd.DataFrame(
            {
                "close": close,
                "bear_setup": bear_setup,
                "bull_setup": bull_setup,
                "bear_cd": bear_cd,
                "bull_cd": bull_cd,
                "bear_cd_active": bear_cd_active,
                "bull_cd_active": bull_cd_active,
            },
            index=close.index,
        )


def _find_swings(df: pd.DataFrame, window: int) -> pd.DataFrame:
    high = df["High"]
    low = df["Low"]
    if isinstance(high, pd.DataFrame):
        high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame):
        low = low.iloc[:, 0]
    is_high = high.eq(high.rolling(window * 2 + 1, center=True).max())
    is_low = low.eq(low.rolling(window * 2 + 1, center=True).min())
    points = []
    for i in range(len(df)):
        d = df.index[i]
        if bool(is_high.iloc[i]):
            points.append((d, float(high.iloc[i]), "H"))
        if bool(is_low.iloc[i]):
            points.append((d, float(low.iloc[i]), "L"))
    if not points:
        return pd.DataFrame(columns=["Date", "Price", "Type"])
    swings = pd.DataFrame(points, columns=["Date", "Price", "Type"]).sort_values("Date")
    cleaned = []
    for _, p in swings.iterrows():
        if not cleaned:
            cleaned.append(p)
            continue
        last = cleaned[-1]
        if p["Type"] == last["Type"]:
            if (p["Type"] == "H" and p["Price"] > last["Price"]) or (p["Type"] == "L" and p["Price"] < last["Price"]):
                cleaned[-1] = p
        else:
            cleaned.append(p)
    return pd.DataFrame(cleaned)


def _wave_labels(n: int) -> list[str]:
    seq = ["(1)", "(2)", "(3)", "(4)", "(5)", "(a)", "(b)", "(c)"]
    return seq[:n] if n <= len(seq) else seq + [f"({i})" for i in range(6, 6 + n - len(seq))]

def _alternates_types(types: list[str]) -> bool:
    return all(types[i] != types[i - 1] for i in range(1, len(types)))


def _score_to_target(value: float, target: float, spread: float) -> float:
    if spread <= 0 or not np.isfinite(value):
        return 0.0
    return max(0.0, 1.0 - abs(value - target) / spread)


def _evaluate_motive(prices: np.ndarray, types: list[str], bullish: bool) -> tuple[bool, float]:
    # Contiguous 6 pivots: p0..p5 define waves 1..5.
    p0, p1, p2, p3, p4, p5 = [float(x) for x in prices]
    tol = max((max(prices) - min(prices)) * 0.005, 1e-9)

    if bullish:
        if types != ["L", "H", "L", "H", "L", "H"]:
            return False, float("-inf")
        w1 = p1 - p0
        w2 = p1 - p2
        w3 = p3 - p2
        w4 = p3 - p4
        w5 = p5 - p4
        if min(w1, w2, w3, w4, w5) <= 0:
            return False, float("-inf")
        if p2 <= p0 + tol:
            return False, float("-inf")
        if p4 < p1 - tol:
            return False, float("-inf")
        if p5 <= p3 + tol * 0.3:
            return False, float("-inf")
        if w3 < min(w1, w5) + tol:
            return False, float("-inf")
    else:
        if types != ["H", "L", "H", "L", "H", "L"]:
            return False, float("-inf")
        w1 = p0 - p1
        w2 = p2 - p1
        w3 = p2 - p3
        w4 = p4 - p3
        w5 = p4 - p5
        if min(w1, w2, w3, w4, w5) <= 0:
            return False, float("-inf")
        if p2 >= p0 - tol:
            return False, float("-inf")
        if p4 > p1 + tol:
            return False, float("-inf")
        if p5 >= p3 - tol * 0.3:
            return False, float("-inf")
        if w3 < min(w1, w5) + tol:
            return False, float("-inf")

    r2 = w2 / w1
    r4 = w4 / w3
    ext3 = w3 / w1
    ext5 = w5 / w1
    if not (0.15 <= r2 <= 0.95):
        return False, float("-inf")
    if not (0.10 <= r4 <= 0.90):
        return False, float("-inf")
    if ext3 < 1.0 or ext5 < 0.20:
        return False, float("-inf")

    impulse_legs = np.array([w1, w3, w5], dtype=float)
    if impulse_legs.min() < impulse_legs.max() * 0.12:
        return False, float("-inf")

    displacement = abs(p5 - p0) / (impulse_legs.sum() + 1e-9)
    score = 2.0
    score += _score_to_target(r2, target=0.618, spread=0.50)
    score += _score_to_target(r4, target=0.382, spread=0.35)
    score += _score_to_target(ext3, target=1.618, spread=1.10)
    score += _score_to_target(ext5, target=1.000, spread=0.90)
    score += min(1.0, displacement)
    return True, score


def _valid_motive(prices: np.ndarray, types: list[str], bullish: bool) -> bool:
    valid, _ = _evaluate_motive(prices, types, bullish)
    return valid


def _find_motive_segment(piv: pd.DataFrame, max_lookback: int = 120) -> tuple[int, bool, float] | None:
    if len(piv) < 6:
        return None
    recent = piv.tail(max_lookback).reset_index(drop=True)
    offset = len(piv) - len(recent)
    pivot_scale = np.nanmedian(np.abs(np.diff(recent["Price"].to_numpy(dtype=float))))
    if not np.isfinite(pivot_scale) or pivot_scale <= 0:
        pivot_scale = 1.0
    candidates: list[tuple[int, bool, float]] = []
    for i in range(0, len(recent) - 5):
        seg = recent.iloc[i : i + 6]
        types = seg["Type"].tolist()
        if not _alternates_types(types):
            continue
        prices = seg["Price"].to_numpy(dtype=float)
        for bullish in (True, False):
            valid, base_score = _evaluate_motive(prices, types, bullish)
            if valid:
                displacement = abs(float(prices[-1] - prices[0])) / pivot_scale
                recency = (i + 5) / max(6, len(recent))
                total_score = base_score + min(3.0, displacement * 0.20) + recency * 0.60
                candidates.append((i, bullish, total_score))
    if not candidates:
        return None
    # Prefer strongest structure score, then latest start.
    candidates.sort(key=lambda x: (x[2], x[0]), reverse=True)
    start_idx, bullish, total_score = candidates[0]
    return (start_idx + offset, bullish, total_score)


def _evaluate_abc(prices: np.ndarray, types: list[str], bullish_motive: bool) -> tuple[bool, float]:
    a, b, c, d = [float(x) for x in prices]  # d is prior wave-5 pivot
    tol = max(abs(d - a) * 0.005, 1e-9)
    if bullish_motive:
        # after bullish motive ends at high d, correction is L-H-L
        if types != ["L", "H", "L"]:
            return False, float("-inf")
        if not (a < d - tol and b < d - tol and c < b - tol * 0.2):
            return False, float("-inf")
        if c > a + tol:
            return False, float("-inf")
        leg1 = d - a
        leg2 = b - a
        leg3 = b - c
    else:
        # after bearish motive ends at low d, correction is H-L-H
        if types != ["H", "L", "H"]:
            return False, float("-inf")
        if not (a > d + tol and b > d + tol and c > b + tol * 0.2):
            return False, float("-inf")
        if c < a - tol:
            return False, float("-inf")
        leg1 = a - d
        leg2 = a - b
        leg3 = c - b

    if min(leg1, leg2, leg3) <= 0:
        return False, float("-inf")
    retr_b = leg2 / leg1
    ext_c = leg3 / leg2
    if not (0.15 <= retr_b <= 0.95):
        return False, float("-inf")
    if not (0.40 <= ext_c <= 2.80):
        return False, float("-inf")

    score = 1.0
    score += _score_to_target(retr_b, target=0.618, spread=0.45)
    score += _score_to_target(ext_c, target=1.000, spread=0.90)
    if bullish_motive and c <= a - tol:
        score += 0.40
    if (not bullish_motive) and c >= a + tol:
        score += 0.40
    return True, score


def _valid_abc(prices: np.ndarray, types: list[str], bullish_motive: bool) -> bool:
    valid, _ = _evaluate_abc(prices, types, bullish_motive)
    return valid


def _best_abc_after_motive(
    piv: pd.DataFrame,
    motive_end_idx: int,
    bullish_motive: bool,
    max_forward: int = 8,
) -> tuple[pd.DataFrame | None, float]:
    if motive_end_idx + 3 > len(piv):
        return None, float("-inf")
    start_min = motive_end_idx + 1
    start_max = min(len(piv) - 3, motive_end_idx + max_forward)
    if start_min > start_max:
        return None, float("-inf")

    last_p5 = float(piv["Price"].iloc[motive_end_idx])
    best: tuple[pd.DataFrame, float] | None = None
    for start in range(start_min, start_max + 1):
        abc = piv.iloc[start : start + 3].copy()
        abc_prices = np.array(
            [float(abc["Price"].iloc[0]), float(abc["Price"].iloc[1]), float(abc["Price"].iloc[2]), last_p5]
        )
        abc_types = abc["Type"].tolist()
        valid, base_score = _evaluate_abc(abc_prices, abc_types, bullish_motive=bullish_motive)
        if not valid:
            continue
        delay_penalty = (start - start_min) * 0.08
        total = base_score - delay_penalty
        if best is None or total > best[1]:
            best = (abc, total)

    if best is None:
        return None, float("-inf")
    return best


def _extract_elliott_labels(
    piv: pd.DataFrame,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, bool | None, float]:
    found = _find_motive_segment(piv)
    if found is None:
        return None, None, None, float("-inf")
    start, bullish, motive_score = found
    motive = piv.iloc[start : start + 6].copy()
    correction, correction_score = _best_abc_after_motive(
        piv=piv,
        motive_end_idx=start + 5,
        bullish_motive=bullish,
    )
    total_score = motive_score + (correction_score if correction is not None else 0.0)
    return motive, correction, bullish, total_score


def _extract_best_elliott(
    swings_map: Dict[int, pd.DataFrame]
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, bool | None, int | None]:
    degree_bias = {4: 0.05, 8: 0.20, 16: 0.15}
    best: tuple[float, int, pd.DataFrame, pd.DataFrame | None, bool] | None = None
    for length, piv in swings_map.items():
        if piv is None or len(piv) < 6:
            continue
        motive, correction, bullish, score = _extract_elliott_labels(piv)
        if motive is None or bullish is None:
            continue
        adjusted = score + degree_bias.get(length, 0.0)
        if best is None or adjusted > best[0]:
            best = (adjusted, length, motive, correction, bullish)
    if best is None:
        return None, None, None, None
    _, length, motive, correction, bullish = best
    return motive, correction, bullish, length


def _add_fib_zone(fig: go.Figure, piv: pd.DataFrame) -> None:
    if len(piv) < 2:
        return
    p0 = float(piv["Price"].iloc[-2])
    p1 = float(piv["Price"].iloc[-1])
    diff = abs(p1 - p0)
    if diff <= 0:
        return
    x0 = piv["Date"].iloc[-1]
    x1 = piv["Date"].iloc[-1] + (piv["Date"].iloc[-1] - piv["Date"].iloc[-2]) * 2
    levels = [0.5, 0.618, 0.764, 0.854]
    sign = -1 if p1 > p0 else 1
    ys = [p1 + sign * diff * lv for lv in levels]
    for i, y in enumerate(ys):
        fig.add_hline(y=y, line_width=1, line_dash="dot", line_color="rgba(96,165,250,0.55)" if i < 2 else "rgba(239,68,68,0.55)", row=1, col=1)
    fig.add_shape(
        type="rect",
        xref="x",
        yref="y",
        x0=x0,
        x1=x1,
        y0=min(ys[-2:]),
        y1=max(ys[-2:]),
        fillcolor="rgba(59,130,246,0.12)",
        line=dict(color="rgba(59,130,246,0.35)", width=1),
    )


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


def _build_figure(
    df: pd.DataFrame,
    ticker: str,
    show_setup_from: int,
    show_countdown_from: int,
    label_cooldown_bars: int,
    visible_start: Optional[pd.Timestamp] = None,
    visible_end: Optional[pd.Timestamp] = None,
) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.62, 0.23, 0.15],
    )

    ohlc_hover = [
        (
            f"Date: {d.strftime('%Y-%m-%d')}<br>"
            f"Open: {o:.2f}<br>"
            f"High: {h:.2f}<br>"
            f"Low: {l:.2f}<br>"
            f"Close: {c:.2f}"
        )
        for d, o, h, l, c in zip(df.index, df["Open"], df["High"], df["Low"], df["Close"])
    ]
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=f"{ticker.upper()} Price",
            increasing_line_color="#22c55e",
            increasing_fillcolor="rgba(34,197,94,0.55)",
            decreasing_line_color="#f43f5e",
            decreasing_fillcolor="rgba(244,63,94,0.55)",
            line_width=1.0,
            whiskerwidth=0.2,
            legendgroup="price",
            text=ohlc_hover,
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )

    close = pd.to_numeric(df["Close"], errors="coerce")
    ma_layers = [
        ("MA 5", 5, "#22c55e", 1.5),
        ("MA 20", 20, "#f59e0b", 1.7),
        ("MA 200", 200, "#8b5cf6", 1.9),
    ]
    for name, window, color, width in ma_layers:
        ma = close.rolling(window=window, min_periods=window).mean()
        if ma.notna().any():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=ma,
                    mode="lines",
                    line=dict(color=color, width=width),
                    name=name,
                    legendgroup="price",
                    hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>",
                ),
                row=1,
                col=1,
            )

    close_values = close.to_numpy(dtype=float)
    dy = np.nanmedian(np.abs(np.diff(close_values))) if len(close_values) > 2 else np.nanstd(close_values) * 0.01
    if not np.isfinite(dy) or dy <= 0:
        dy = max(np.nanstd(close_values) * 0.01, 1.0)

    swings_map: Dict[int, pd.DataFrame] = {4: _find_swings(df, 4), 8: _find_swings(df, 8), 16: _find_swings(df, 16)}
    motive, correction, bullish, wave_degree = _extract_best_elliott(swings_map)

    if wave_degree and wave_degree in swings_map and len(swings_map[wave_degree]) >= 2:
        piv = swings_map[wave_degree].tail(36)
        fig.add_trace(
            go.Scatter(
                x=piv["Date"],
                y=piv["Price"],
                mode="lines",
                line=dict(color="rgba(148,163,184,0.35)", width=1.0, dash="dot"),
                name="Wave Backbone",
                showlegend=False,
                hovertemplate="Backbone: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    if motive is not None:
        wave_color = "#22c55e" if bullish else "#f43f5e"
        fig.add_trace(
            go.Scatter(
                x=motive["Date"],
                y=motive["Price"],
                mode="lines+markers",
                line=dict(color=wave_color, width=2.1),
                marker=dict(size=6, color=wave_color),
                name="Elliott 1-5",
                legendgroup="elliott",
                hovertemplate="Wave: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        motive_y = [
            float(price + (dy * 1.35 if t == "H" else -dy * 1.35))
            for price, t in zip(motive["Price"], motive["Type"])
        ]
        fig.add_trace(
            go.Scatter(
                x=motive["Date"],
                y=motive_y,
                mode="text",
                text=["0", "1", "2", "3", "4", "5"],
                textfont=dict(size=12, color=wave_color),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    if correction is not None:
        corr_color = "#38bdf8" if bullish else "#fb7185"
        fig.add_trace(
            go.Scatter(
                x=correction["Date"],
                y=correction["Price"],
                mode="lines+markers",
                line=dict(color=corr_color, width=1.9),
                marker=dict(size=5, color=corr_color),
                name="Elliott A-B-C",
                legendgroup="elliott",
                hovertemplate="Correction: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        corr_y = [
            float(price + (dy * 1.1 if t == "H" else -dy * 1.1))
            for price, t in zip(correction["Price"], correction["Type"])
        ]
        fig.add_trace(
            go.Scatter(
                x=correction["Date"],
                y=corr_y,
                mode="text",
                text=["A", "B", "C"],
                textfont=dict(size=11, color=corr_color),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    td = TDSequentialClean(
        show_setup_from=show_setup_from,
        show_countdown_from=show_countdown_from,
        label_cooldown_bars=label_cooldown_bars,
    )
    tdf = td.compute(df["Close"])
    above = tdf["close"] + dy * 1.9
    below = tdf["close"] - dy * 1.9
    bear_setup_mask = td._cooldown_mask(tdf["bear_setup"] >= td.show_setup_from)
    bull_setup_mask = td._cooldown_mask(tdf["bull_setup"] >= td.show_setup_from)
    bear_cd_mask = td._cooldown_mask(tdf["bear_cd"] >= td.show_countdown_from)
    bull_cd_mask = td._cooldown_mask(tdf["bull_cd"] >= td.show_countdown_from)
    if bear_setup_mask.any():
        fig.add_trace(
            go.Scatter(
                x=tdf.index[bear_setup_mask],
                y=above[bear_setup_mask],
                mode="text",
                text=tdf.loc[bear_setup_mask, "bear_setup"].astype(int).astype(str),
                textfont=dict(color="#fb7185", size=10),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
    if bull_setup_mask.any():
        fig.add_trace(
            go.Scatter(
                x=tdf.index[bull_setup_mask],
                y=below[bull_setup_mask],
                mode="text",
                text=tdf.loc[bull_setup_mask, "bull_setup"].astype(int).astype(str),
                textfont=dict(color="#34d399", size=10),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
    if bear_cd_mask.any():
        fig.add_trace(
            go.Scatter(
                x=tdf.index[bear_cd_mask],
                y=above[bear_cd_mask] + dy,
                mode="text",
                text=tdf.loc[bear_cd_mask, "bear_cd"].astype(int).astype(str),
                textfont=dict(color="#f43f5e", size=11),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
    if bull_cd_mask.any():
        fig.add_trace(
            go.Scatter(
                x=tdf.index[bull_cd_mask],
                y=below[bull_cd_mask] - dy,
                mode="text",
                text=tdf.loc[bull_cd_mask, "bull_cd"].astype(int).astype(str),
                textfont=dict(color="#10b981", size=11),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    hist_prev = macd_hist.shift(1)
    hist_colors = np.where(
        macd_hist >= 0,
        np.where(macd_hist >= hist_prev, "rgba(16,185,129,0.85)", "rgba(16,185,129,0.45)"),
        np.where(macd_hist <= hist_prev, "rgba(244,63,94,0.85)", "rgba(244,63,94,0.45)"),
    )
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=macd_hist,
            marker_color=hist_colors,
            name="MACD Hist",
            showlegend=False,
            hovertemplate="MACD Hist: %{y:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=macd_line,
            mode="lines",
            line=dict(color="#38bdf8", width=1.8),
            name="MACD",
            legendgroup="macd",
            hovertemplate="MACD: %{y:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=macd_signal,
            mode="lines",
            line=dict(color="#f59e0b", width=1.5),
            name="Signal",
            legendgroup="macd",
            hovertemplate="Signal: %{y:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(148,163,184,0.55)", row=2, col=1)

    rsi = _compute_rsi(close, period=14)
    rsi_mean = rsi.rolling(window=9, min_periods=9).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=rsi,
            mode="lines",
            line=dict(color="#60a5fa", width=1.8),
            name="RSI 14",
            legendgroup="rsi",
            hovertemplate="RSI 14: %{y:.1f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=rsi_mean,
            mode="lines",
            line=dict(color="#f59e0b", width=1.4, dash="dot"),
            name="RSI Mean",
            legendgroup="rsi",
            hovertemplate="RSI Mean: %{y:.1f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line_width=1, line_color="rgba(244,63,94,0.75)", line_dash="dot", row=3, col=1)
    fig.add_hline(y=50, line_width=1, line_color="rgba(148,163,184,0.45)", line_dash="dash", row=3, col=1)
    fig.add_hline(y=30, line_width=1, line_color="rgba(34,197,94,0.75)", line_dash="dot", row=3, col=1)

    # Visible window controls display range only (does not slice source data).
    if visible_start is not None and visible_end is not None and visible_start < visible_end:
        mask = (df.index >= visible_start) & (df.index <= visible_end)
        if mask.any():
            sub = df.loc[mask]
            y1_min = float(sub["Low"].min())
            y1_max = float(sub["High"].max())
            if np.isfinite(y1_min) and np.isfinite(y1_max) and y1_max > y1_min:
                pad1 = (y1_max - y1_min) * 0.08
                fig.update_yaxes(range=[y1_min - pad1, y1_max + pad1], row=1, col=1)

            macd_sub = pd.concat(
                [macd_line.loc[mask], macd_signal.loc[mask], macd_hist.loc[mask]],
                axis=1,
            ).dropna(how="all")
            if not macd_sub.empty:
                y2_min = float(macd_sub.min().min())
                y2_max = float(macd_sub.max().max())
                if np.isfinite(y2_min) and np.isfinite(y2_max):
                    if y2_max == y2_min:
                        y2_min -= 1.0
                        y2_max += 1.0
                    pad2 = (y2_max - y2_min) * 0.18
                    fig.update_yaxes(range=[y2_min - pad2, y2_max + pad2], row=2, col=1)

            fig.update_xaxes(range=[visible_start, visible_end], row=1, col=1)
            fig.update_xaxes(range=[visible_start, visible_end], row=2, col=1)
            fig.update_xaxes(range=[visible_start, visible_end], row=3, col=1)

    fig.update_layout(
        template=None,
        paper_bgcolor="#050913",
        plot_bgcolor="#070d1a",
        font=dict(family="Ubuntu, Inter, Roboto, sans-serif", color="#dbeafe", size=12),
        margin=dict(l=72, r=22, t=60, b=24),
        title=dict(text=""),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.92)",
            bordercolor="rgba(148,163,184,0.35)",
            font=dict(color="#e2e8f0", size=11),
        ),
        legend=dict(
            orientation="h",
            x=0.01,
            y=1.02,
            xanchor="left",
            yanchor="bottom",
            bgcolor="rgba(15,23,42,0.68)",
            bordercolor="rgba(148,163,184,0.35)",
            borderwidth=1,
            font=dict(size=10),
            traceorder="normal",
            itemclick="toggleothers",
            itemdoubleclick="toggle",
        ),
        xaxis_rangeslider_visible=False,
        bargap=0.12,
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        linecolor="rgba(226,232,240,0.65)",
        showline=True,
        mirror=True,
        rangebreaks=[dict(bounds=["sat", "mon"])],
        showspikes=False,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        linecolor="rgba(226,232,240,0.65)",
        showline=True,
        mirror=True,
        automargin=True,
        showspikes=False,
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(
        title_text="RSI",
        range=[0, 100],
        tickmode="array",
        tickvals=[30, 50, 70],
        ticktext=["30", "50", "70"],
        row=3,
        col=1,
    )
    return fig


@router.get("/technical/elliott")
def technical_elliott(
    ticker: str = Query("SPY"),
    period: str = Query("2y"),
    interval: str = Query("1d"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    setup_from: int = Query(9, ge=1, le=9),
    countdown_from: int = Query(13, ge=1, le=13),
    label_cooldown: int = Query(0, ge=0, le=20),
):
    try:
        tk = ticker.strip().upper()
        raw = yf.download(tk, period=period, interval=interval, auto_adjust=False, progress=False)
        if raw is None or raw.empty:
            raise HTTPException(status_code=404, detail=f"No data for ticker '{ticker}'.")
        df = _normalize_yf(raw, tk)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No OHLC data for ticker '{ticker}'.")
        vis_start = pd.to_datetime(start) if start else None
        vis_end = pd.to_datetime(end) if end else None
        fig = _build_figure(
            df,
            tk,
            setup_from,
            countdown_from,
            label_cooldown,
            visible_start=vis_start,
            visible_end=vis_end,
        )
        return json.loads(pio.to_json(fig, engine="json"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build technical chart: {e}")
