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


def _valid_motive(prices: np.ndarray, types: list[str], bullish: bool) -> bool:
    # Contiguous 6 pivots: p0..p5 define waves 1..5.
    p0, p1, p2, p3, p4, p5 = [float(x) for x in prices]
    if bullish:
        if types != ["L", "H", "L", "H", "L", "H"]:
            return False
        w1 = p1 - p0
        w3 = p3 - p2
        w5 = p5 - p4
        if min(w1, w3, w5) <= 0:
            return False
        if not (p0 < p2 < p1):
            return False
        if not (p2 < p4 < p3):
            return False
        if p4 <= p1:
            return False
        if p5 <= p3:
            return False
        if w3 <= min(w1, w5):
            return False
        return True

    if types != ["H", "L", "H", "L", "H", "L"]:
        return False
    w1 = p0 - p1
    w3 = p2 - p3
    w5 = p4 - p5
    if min(w1, w3, w5) <= 0:
        return False
    if not (p1 < p2 < p0):
        return False
    if not (p3 < p4 < p2):
        return False
    if p4 >= p1:
        return False
    if p5 >= p3:
        return False
    if w3 <= min(w1, w5):
        return False
    return True


def _find_motive_segment(piv: pd.DataFrame, max_lookback: int = 120) -> tuple[int, bool] | None:
    if len(piv) < 6:
        return None
    recent = piv.tail(max_lookback).reset_index(drop=True)
    offset = len(piv) - len(recent)
    candidates: list[tuple[int, float, bool]] = []
    for i in range(0, len(recent) - 5):
        seg = recent.iloc[i : i + 6]
        types = seg["Type"].tolist()
        if not _alternates_types(types):
            continue
        prices = seg["Price"].to_numpy(dtype=float)
        for bullish in (True, False):
            if _valid_motive(prices, types, bullish):
                score = abs(float(prices[-1] - prices[0]))
                candidates.append((i, score, bullish))
    if not candidates:
        return None
    # Prefer the latest valid pattern, then larger price displacement.
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    start_idx, _, bullish = candidates[0]
    return (start_idx + offset, bullish)


def _valid_abc(prices: np.ndarray, types: list[str], bullish_motive: bool) -> bool:
    a, b, c, d = [float(x) for x in prices]  # d is prior wave-5 pivot
    if bullish_motive:
        # after bullish motive ends at high d, correction is L-H-L
        if types != ["L", "H", "L"]:
            return False
        if not (a < d and b < d and c < b):
            return False
        return c <= a
    # after bearish motive ends at low d, correction is H-L-H
    if types != ["H", "L", "H"]:
        return False
    if not (a > d and b > d and c > b):
        return False
    return c >= a


def _extract_elliott_labels(piv: pd.DataFrame) -> tuple[pd.DataFrame | None, pd.DataFrame | None, bool | None]:
    found = _find_motive_segment(piv)
    if found is None:
        return None, None, None
    start, bullish = found
    motive = piv.iloc[start : start + 6].copy()
    correction = None
    if start + 9 <= len(piv):
        abc = piv.iloc[start + 6 : start + 9].copy()
        last_p5 = float(motive["Price"].iloc[-1])
        abc_prices = np.array(
            [float(abc["Price"].iloc[0]), float(abc["Price"].iloc[1]), float(abc["Price"].iloc[2]), last_p5]
        )
        abc_types = abc["Type"].tolist()
        if _valid_abc(abc_prices, abc_types, bullish_motive=bullish):
            correction = abc
    return motive, correction, bullish


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


def _build_figure(
    df: pd.DataFrame,
    ticker: str,
    show_setup_from: int,
    show_countdown_from: int,
    label_cooldown_bars: int,
    visible_start: Optional[pd.Timestamp] = None,
    visible_end: Optional[pd.Timestamp] = None,
) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.78, 0.22])
    ohlc_hover = [
        (
            f"{ticker.upper()} Bars<br>"
            f"Date: {d.strftime('%Y-%m-%d')}<br>"
            f"Open: {o:.2f}<br>"
            f"High: {h:.2f}<br>"
            f"Low: {l:.2f}<br>"
            f"Close: {c:.2f}"
        )
        for d, o, h, l, c in zip(df.index, df["Open"], df["High"], df["Low"], df["Close"])
    ]
    fig.add_trace(
        go.Ohlc(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=f"{ticker.upper()} Bars",
            increasing_line_color="#00d1b2",
            decreasing_line_color="#ff4d6d",
            line_width=1.2,
            showlegend=True,
            hovertext=ohlc_hover,
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )

    swings_map: Dict[int, pd.DataFrame] = {4: _find_swings(df, 4), 8: _find_swings(df, 8), 16: _find_swings(df, 16)}
    layers = {4: ("#ef4444", 1.1), 8: ("#3b82f6", 1.6), 16: ("#e5e7eb", 1.2)}
    top_pos = "top center"
    bottom_pos = "bottom center"
    for length, (color, width) in layers.items():
        piv = swings_map[length].tail(40)
        if len(piv) < 2:
            continue
        fig.add_trace(
            go.Scatter(
                x=piv["Date"],
                y=piv["Price"],
                mode="lines+markers",
                line=dict(color=color, width=width),
                marker=dict(size=5, color=color),
                name=f"ZigZag {length}",
                hovertemplate=f"{length}-ZZ: %{{y:.2f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )
    zz8 = swings_map[8]
    motive, correction, bullish = _extract_elliott_labels(zz8)
    if motive is not None:
        wave_color = "#3b82f6" if bullish else "#ef4444"
        motive_labels = ["", "(1)", "(2)", "(3)", "(4)", "(5)"]
        motive_pos = [top_pos if t == "H" else bottom_pos for t in motive["Type"].tolist()]
        fig.add_trace(
            go.Scatter(
                x=motive["Date"],
                y=motive["Price"],
                mode="lines+markers+text",
                line=dict(color=wave_color, width=2.0),
                marker=dict(size=7, color=wave_color),
                text=motive_labels,
                textposition=motive_pos,
                textfont=dict(size=16, color=wave_color),
                name="Elliott Motive",
                hovertemplate="Motive: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        _add_fib_zone(fig, motive)
    if correction is not None:
        corr_color = "#3b82f6" if bullish else "#ef4444"
        corr_pos = [top_pos if t == "H" else bottom_pos for t in correction["Type"].tolist()]
        fig.add_trace(
            go.Scatter(
                x=correction["Date"],
                y=correction["Price"],
                mode="lines+markers+text",
                line=dict(color=corr_color, width=1.8),
                marker=dict(size=6, color=corr_color),
                text=["(a)", "(b)", "(c)"],
                textposition=corr_pos,
                textfont=dict(size=15, color=corr_color),
                name="Elliott Correction",
                hovertemplate="Correction: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    td = TDSequentialClean(show_setup_from=show_setup_from, show_countdown_from=show_countdown_from, label_cooldown_bars=label_cooldown_bars)
    tdf = td.compute(df["Close"])
    y = tdf["close"].to_numpy()
    dy = np.nanmedian(np.abs(np.diff(y))) if len(y) > 2 else np.nanstd(y) * 0.01
    if not np.isfinite(dy) or dy <= 0:
        dy = max(np.nanstd(y) * 0.01, 1.0)
    above = tdf["close"] + dy * 2.0
    below = tdf["close"] - dy * 2.0
    bear_setup_mask = td._cooldown_mask(tdf["bear_setup"] >= td.show_setup_from)
    bull_setup_mask = td._cooldown_mask(tdf["bull_setup"] >= td.show_setup_from)
    bear_cd_mask = td._cooldown_mask(tdf["bear_cd"] >= td.show_countdown_from)
    bull_cd_mask = td._cooldown_mask(tdf["bull_cd"] >= td.show_countdown_from)
    if bear_setup_mask.any():
        fig.add_trace(go.Scatter(x=tdf.index[bear_setup_mask], y=above[bear_setup_mask], mode="text", text=tdf.loc[bear_setup_mask, "bear_setup"].astype(int).astype(str), textfont=dict(color="#ff4d4d", size=11), showlegend=False, hoverinfo="skip"), row=1, col=1)
    if bull_setup_mask.any():
        fig.add_trace(go.Scatter(x=tdf.index[bull_setup_mask], y=below[bull_setup_mask], mode="text", text=tdf.loc[bull_setup_mask, "bull_setup"].astype(int).astype(str), textfont=dict(color="#00ff99", size=11), showlegend=False, hoverinfo="skip"), row=1, col=1)
    if bear_cd_mask.any():
        fig.add_trace(go.Scatter(x=tdf.index[bear_cd_mask], y=above[bear_cd_mask] + dy * 1.2, mode="text", text=tdf.loc[bear_cd_mask, "bear_cd"].astype(int).astype(str), textfont=dict(color="#ff4d4d", size=13), showlegend=False, hoverinfo="skip"), row=1, col=1)
    if bull_cd_mask.any():
        fig.add_trace(go.Scatter(x=tdf.index[bull_cd_mask], y=below[bull_cd_mask] - dy * 1.2, mode="text", text=tdf.loc[bull_cd_mask, "bull_cd"].astype(int).astype(str), textfont=dict(color="#00ff99", size=13), showlegend=False, hoverinfo="skip"), row=1, col=1)

    osc = df["Close"].pct_change(5).mul(100)
    bar_colors = np.where(osc >= 0, "rgba(34,197,94,0.75)", "rgba(239,68,68,0.75)")
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=osc,
            marker_color=bar_colors,
            name="Wave Momentum (5D %)",
            hovertemplate="Wave Momentum: %{y:.2f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(148,163,184,0.55)", row=2, col=1)

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

            osc_sub = osc.loc[mask]
            if not osc_sub.dropna().empty:
                y2_min = float(osc_sub.min())
                y2_max = float(osc_sub.max())
                if np.isfinite(y2_min) and np.isfinite(y2_max):
                    if y2_max == y2_min:
                        y2_min -= 1.0
                        y2_max += 1.0
                    pad2 = (y2_max - y2_min) * 0.15
                    fig.update_yaxes(range=[y2_min - pad2, y2_max + pad2], row=2, col=1)
            fig.update_xaxes(range=[visible_start, visible_end], row=1, col=1)
            fig.update_xaxes(range=[visible_start, visible_end], row=2, col=1)


    fig.update_layout(
        template=None,
        paper_bgcolor="#050913",
        plot_bgcolor="#070d1a",
        font=dict(family="Ubuntu, Inter, Roboto, sans-serif", color="#dbeafe", size=12),
        margin=dict(l=70, r=20, t=20, b=20),
        title=dict(text=""),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(15,23,42,0.92)", bordercolor="rgba(148,163,184,0.35)", font=dict(color="#e2e8f0", size=11)),
        legend=dict(
            orientation="v",
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(15,23,42,0.70)",
            bordercolor="rgba(148,163,184,0.35)",
            borderwidth=1,
            font=dict(size=10),
        ),
        xaxis_rangeslider_visible=False,
        bargap=0.15,
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
