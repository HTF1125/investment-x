"""Technical analysis chart construction (Plotly)."""

from __future__ import annotations

from io import BytesIO
from typing import Dict, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from ix.core.technical.elliott_wave import (
    TDSequentialClean,
    _find_swings,
    _extract_best_elliott,
)
from ix.core.technical.ohlcv_indicators import (
    _compute_rsi,
    _compute_squeeze_momentum,
)


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


def _build_figure(
    df: pd.DataFrame,
    ticker: str,
    show_setup_from: int,
    show_countdown_from: int,
    label_cooldown_bars: int,
    visible_start: Optional[pd.Timestamp] = None,
    visible_end: Optional[pd.Timestamp] = None,
    show_macd: bool = True,
    show_rsi: bool = True,
    show_sqz: bool = False,
    sqz_bb_len: int = 20,
    sqz_bb_mult: float = 2.0,
    sqz_kc_len: int = 20,
    sqz_kc_mult: float = 1.5,
) -> go.Figure:
    rows = 1
    if show_macd:
        rows += 1
    if show_rsi:
        rows += 1
    if show_sqz:
        rows += 1

    next_row = 2
    macd_row = next_row if show_macd else None
    if show_macd:
        next_row += 1
    rsi_row = next_row if show_rsi else None
    if show_rsi:
        next_row += 1
    sqz_row = next_row if show_sqz else None

    # Calculate row heights
    if rows == 4:
        row_heights = [0.55, 0.16, 0.15, 0.14]
    elif rows == 3 and show_sqz and not (show_macd and show_rsi):
        row_heights = [0.66, 0.19, 0.15]
    elif rows == 3:
        row_heights = [0.62, 0.23, 0.15]
    elif rows == 2 and show_sqz:
        row_heights = [0.78, 0.22]
    elif rows == 2:
        row_heights = [0.75, 0.25]
    else:
        row_heights = [1.0]

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04 if rows > 1 else 0,
        row_heights=row_heights,
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
            increasing_line_color="#26a69a",
            increasing_fillcolor="#26a69a",
            decreasing_line_color="#ef5350",
            decreasing_fillcolor="#ef5350",
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

    # MACD Subplot
    if show_macd:
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
            row=macd_row,
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
            row=macd_row,
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
            row=macd_row,
            col=1,
        )
        fig.add_hline(y=0, line_width=1, line_color="rgba(148,163,184,0.55)", row=macd_row, col=1)
        fig.update_yaxes(title_text="MACD", row=macd_row, col=1)

    # RSI Subplot
    if show_rsi:
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
            row=rsi_row,
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
            row=rsi_row,
            col=1,
        )
        fig.add_hline(y=70, line_width=1, line_color="rgba(244,63,94,0.75)", line_dash="dot", row=rsi_row, col=1)
        fig.add_hline(y=50, line_width=1, line_color="rgba(148,163,184,0.45)", line_dash="dash", row=rsi_row, col=1)
        fig.add_hline(y=30, line_width=1, line_color="rgba(34,197,94,0.75)", line_dash="dot", row=rsi_row, col=1)
        fig.update_yaxes(
            title_text="RSI",
            range=[0, 100],
            tickmode="array",
            tickvals=[30, 50, 70],
            ticktext=["30", "50", "70"],
            row=rsi_row,
            col=1,
        )

    if show_sqz:
        sqz = _compute_squeeze_momentum(
            df,
            bb_length=sqz_bb_len,
            bb_mult=sqz_bb_mult,
            kc_length=sqz_kc_len,
            kc_mult=sqz_kc_mult,
        )
        sqz_bar_color_map = {
            "lime": "#4ade80",
            "green": "#16a34a",
            "red": "#f87171",
            "maroon": "#991b1b",
            "gray": "#64748b",
        }
        sqz_dot_color_map = {
            "blue": "#38bdf8",
            "black": "#1e293b",
            "gray": "#64748b",
        }
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=sqz["val"],
                marker_color=[sqz_bar_color_map.get(c, "#64748b") for c in sqz["bar_color"]],
                name="SQZ Mom",
                legendgroup="squeeze",
                hovertemplate="SQZ: %{y:.4f}<extra></extra>",
            ),
            row=sqz_row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=[0.0] * len(df.index),
                mode="markers",
                marker=dict(
                    color=[sqz_dot_color_map.get(c, "#64748b") for c in sqz["sqz_dot_color"]],
                    size=4,
                    symbol="cross-thin",
                    line=dict(
                        width=1.5,
                        color=[sqz_dot_color_map.get(c, "#64748b") for c in sqz["sqz_dot_color"]],
                    ),
                ),
                name="SQZ State",
                legendgroup="squeeze",
                showlegend=False,
                hovertemplate="SQZ State<extra></extra>",
            ),
            row=sqz_row,
            col=1,
        )
        fig.add_hline(y=0, line_width=1, line_color="rgba(148,163,184,0.55)", row=sqz_row, col=1)
        fig.update_yaxes(title_text="SQZ", row=sqz_row, col=1)

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

            if show_macd:
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                macd_signal = macd_line.ewm(span=9, adjust=False).mean()
                macd_hist = macd_line - macd_signal
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
                        fig.update_yaxes(range=[y2_min - pad2, y2_max + pad2], row=macd_row, col=1)

            if show_sqz:
                sqz_sub = _compute_squeeze_momentum(
                    df,
                    bb_length=sqz_bb_len,
                    bb_mult=sqz_bb_mult,
                    kc_length=sqz_kc_len,
                    kc_mult=sqz_kc_mult,
                ).loc[mask, ["val"]].dropna(how="all")
                if not sqz_sub.empty:
                    sqz_min = float(sqz_sub["val"].min())
                    sqz_max = float(sqz_sub["val"].max())
                    if np.isfinite(sqz_min) and np.isfinite(sqz_max):
                        if sqz_max == sqz_min:
                            sqz_min -= 1.0
                            sqz_max += 1.0
                        sqz_pad = (sqz_max - sqz_min) * 0.18
                        fig.update_yaxes(range=[sqz_min - sqz_pad, sqz_max + sqz_pad], row=sqz_row, col=1)

            for r in range(1, rows + 1):
                fig.update_xaxes(range=[visible_start, visible_end], row=r, col=1)

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
    return fig


def _render_chart_to_image(fig: go.Figure) -> BytesIO:
    """Render Plotly figure to a high-res PNG buffer."""
    img_bytes = pio.to_image(fig, format="png", width=1200, height=700, scale=2)
    return BytesIO(img_bytes)


def _clean_markdown(md_text: str) -> str:
    """Simple cleanup of markdown symbols for basic PDF/PPTX rendering."""
    # Remove bold/italic markers
    text = md_text.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
    # Remove header markers but keep text
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(line.lstrip("#").strip())
    return "\n".join(cleaned_lines)
