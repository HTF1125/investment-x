import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots


class TDSequentialClean:
    def __init__(
        self,
        setup_lookback: int = 4,
        setup_len: int = 9,
        countdown_lookback: int = 2,
        countdown_len: int = 13,
        show_setup_from: int = 9,
        show_countdown_from: int = 13,
        suppress_setup_when_cd_active: bool = False,
        cancel_on_opposite_setup9: bool = True,
        label_cooldown_bars: int = 0,
    ):
        self.setup_lookback = setup_lookback
        self.setup_len = setup_len
        self.countdown_lookback = countdown_lookback
        self.countdown_len = countdown_len
        self.show_setup_from = show_setup_from
        self.show_countdown_from = show_countdown_from
        self.suppress_setup_when_cd_active = suppress_setup_when_cd_active
        self.cancel_on_opposite_setup9 = cancel_on_opposite_setup9
        self.label_cooldown_bars = label_cooldown_bars

    @staticmethod
    def _to_series(close: pd.Series) -> pd.Series:
        s = pd.to_numeric(close, errors="coerce").astype(float).dropna().sort_index()
        if len(s) < 20:
            raise ValueError("close series too short (need >= 20 points)")
        return s

    def compute(self, close: pd.Series) -> pd.DataFrame:
        close = self._to_series(close)
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

        bear_active = False
        bull_active = False
        bear_count = 0
        bull_count = 0

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


def _find_swings(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
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
        idx = df.index[i]
        if bool(is_high.iloc[i]):
            points.append((idx, float(high.iloc[i]), "H"))
        if bool(is_low.iloc[i]):
            points.append((idx, float(low.iloc[i]), "L"))

    if not points:
        return pd.DataFrame(columns=["Date", "Price", "Type"])

    swings = pd.DataFrame(points, columns=["Date", "Price", "Type"]).sort_values("Date")

    # Deduplicate consecutive same-type pivots by keeping the more extreme one.
    cleaned = []
    for _, p in swings.iterrows():
        if not cleaned:
            cleaned.append(p)
            continue
        last = cleaned[-1]
        if p["Type"] == last["Type"]:
            if (p["Type"] == "H" and p["Price"] > last["Price"]) or (
                p["Type"] == "L" and p["Price"] < last["Price"]
            ):
                cleaned[-1] = p
        else:
            cleaned.append(p)
    return pd.DataFrame(cleaned)


def _wave_labels(n: int) -> list[str]:
    seq = ["(1)", "(2)", "(3)", "(4)", "(5)", "(a)", "(b)", "(c)"]
    if n <= len(seq):
        return seq[:n]
    extra = [f"({i})" for i in range(6, 6 + (n - len(seq)))]
    return seq + extra


def _add_fib_zone(fig: go.Figure, piv: pd.DataFrame, row: int = 1, col: int = 1) -> None:
    if len(piv) < 2:
        return
    p0 = float(piv["Price"].iloc[-2])
    p1 = float(piv["Price"].iloc[-1])
    x0 = piv["Date"].iloc[-1]
    x1 = piv["Date"].iloc[-1] + (piv["Date"].iloc[-1] - piv["Date"].iloc[-2]) * 2
    diff = abs(p1 - p0)
    if diff == 0:
        return
    levels = [0.5, 0.618, 0.764, 0.854]
    sign = -1 if p1 > p0 else 1
    fib_vals = [p1 + sign * diff * lv for lv in levels]
    for i, y in enumerate(fib_vals):
        fig.add_hline(
            y=y,
            line_width=1,
            line_color="rgba(96,165,250,0.5)" if i < 2 else "rgba(239,68,68,0.5)",
            line_dash="dot",
            row=row,
            col=col,
        )
    fig.add_shape(
        type="rect",
        xref="x",
        yref="y",
        x0=x0,
        x1=x1,
        y0=min(fib_vals[-2:]),
        y1=max(fib_vals[-2:]),
        fillcolor="rgba(59,130,246,0.12)",
        line=dict(color="rgba(59,130,246,0.35)", width=1),
    )


def build_chart(
    df: pd.DataFrame,
    swings_map: dict[int, pd.DataFrame],
    ticker: str,
    td: TDSequentialClean | None = None,
) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.78, 0.22],
    )

    fig.add_trace(
        go.Ohlc(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker.upper(),
            increasing_line_color="#00d1b2",
            decreasing_line_color="#ff4d6d",
            line_width=1.2,
        ),
        row=1,
        col=1,
    )

    # Elliott-wave-style multi-zigzag overlays (lengths 4, 8, 16).
    layers = {
        4: ("#ef4444", 1.1, False),
        8: ("#3b82f6", 1.6, True),
        16: ("#e5e7eb", 1.2, False),
    }
    for length, (color, width, with_labels) in layers.items():
        piv = swings_map.get(length, pd.DataFrame()).tail(9).copy()
        if len(piv) < 2:
            continue
        labels = _wave_labels(len(piv))
        bottom_labels = {"(2)", "(4)", "(a)", "(c)"}
        text_positions = (
            [("bottom center" if lbl.lower() in bottom_labels else "top center") for lbl in labels]
            if with_labels
            else None
        )
        fig.add_trace(
            go.Scatter(
                x=piv["Date"],
                y=piv["Price"],
                mode="lines+markers+text" if with_labels else "lines",
                line=dict(color=color, width=width),
                marker=dict(size=5, color=color),
                text=labels if with_labels else None,
                textposition=text_positions if text_positions is not None else "top center",
                textfont=dict(size=13, color=color),
                name=f"ZigZag {length}",
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        if length == 8:
            _add_fib_zone(fig, piv, row=1, col=1)

    # TD Sequential overlay labels.
    if td is not None:
        tdf = td.compute(df["Close"])
        y = tdf["close"].to_numpy()
        dy = np.nanmedian(np.abs(np.diff(y))) if len(y) > 2 else np.nanstd(y) * 0.01
        if not np.isfinite(dy) or dy <= 0:
            dy = max(np.nanstd(y) * 0.01, 1.0)

        above = tdf["close"] + dy * 2.0
        below = tdf["close"] - dy * 2.0

        bear_setup_mask = tdf["bear_setup"] >= td.show_setup_from
        bull_setup_mask = tdf["bull_setup"] >= td.show_setup_from
        if td.suppress_setup_when_cd_active:
            bear_setup_mask &= ~tdf["bear_cd_active"]
            bull_setup_mask &= ~tdf["bull_cd_active"]
        bear_setup_mask = td._cooldown_mask(bear_setup_mask)
        bull_setup_mask = td._cooldown_mask(bull_setup_mask)

        bear_cd_mask = td._cooldown_mask(tdf["bear_cd"] >= td.show_countdown_from)
        bull_cd_mask = td._cooldown_mask(tdf["bull_cd"] >= td.show_countdown_from)

        if bear_setup_mask.any():
            vals = tdf.loc[bear_setup_mask, "bear_setup"].astype(int).astype(str)
            fig.add_trace(
                go.Scatter(
                    x=tdf.index[bear_setup_mask],
                    y=above[bear_setup_mask],
                    mode="text",
                    text=vals,
                    textfont=dict(color="#ff4d4d", size=11),
                    name="TD Bear Setup",
                    showlegend=False,
                    hovertemplate="TD Bear Setup: %{text}<extra></extra>",
                ),
                row=1,
                col=1,
            )
        if bull_setup_mask.any():
            vals = tdf.loc[bull_setup_mask, "bull_setup"].astype(int).astype(str)
            fig.add_trace(
                go.Scatter(
                    x=tdf.index[bull_setup_mask],
                    y=below[bull_setup_mask],
                    mode="text",
                    text=vals,
                    textfont=dict(color="#00ff99", size=11),
                    name="TD Bull Setup",
                    showlegend=False,
                    hovertemplate="TD Bull Setup: %{text}<extra></extra>",
                ),
                row=1,
                col=1,
            )
        if bear_cd_mask.any():
            vals = tdf.loc[bear_cd_mask, "bear_cd"].astype(int).astype(str)
            fig.add_trace(
                go.Scatter(
                    x=tdf.index[bear_cd_mask],
                    y=above[bear_cd_mask] + dy * 1.2,
                    mode="text",
                    text=vals,
                    textfont=dict(color="#ff4d4d", size=13),
                    name="TD Bear CD",
                    showlegend=False,
                    hovertemplate="TD Bear CD: %{text}<extra></extra>",
                ),
                row=1,
                col=1,
            )
        if bull_cd_mask.any():
            vals = tdf.loc[bull_cd_mask, "bull_cd"].astype(int).astype(str)
            fig.add_trace(
                go.Scatter(
                    x=tdf.index[bull_cd_mask],
                    y=below[bull_cd_mask] - dy * 1.2,
                    mode="text",
                    text=vals,
                    textfont=dict(color="#00ff99", size=13),
                    name="TD Bull CD",
                    showlegend=False,
                    hovertemplate="TD Bull CD: %{text}<extra></extra>",
                ),
                row=1,
                col=1,
            )

    # Histogram panel (wave momentum proxy).
    osc = df["Close"].pct_change(5).mul(100)
    bar_colors = np.where(osc >= 0, "rgba(34,197,94,0.75)", "rgba(239,68,68,0.75)")
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=osc,
            marker_color=bar_colors,
            name="Wave Momentum (5D %)",
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template=None,
        paper_bgcolor="#050913",
        plot_bgcolor="#070d1a",
        font=dict(family="Ubuntu, Inter, Roboto, sans-serif", color="#dbeafe", size=12),
        margin=dict(l=20, r=20, t=50, b=20),
        title=dict(
            text=f"{ticker.upper()} Elliott Wave (Approx, Lux-style) + Momentum Histogram",
            x=0.01,
            xanchor="left",
        ),
        legend=dict(
            orientation="h",
            x=0.01,
            y=1.02,
            bgcolor="rgba(15,23,42,0.7)",
            bordercolor="rgba(148,163,184,0.35)",
            borderwidth=1,
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
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        linecolor="rgba(226,232,240,0.65)",
        showline=True,
        mirror=True,
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(148,163,184,0.55)", row=2, col=1)
    return fig


@st.cache_data(ttl=900, show_spinner=False)
def load_price(ticker: str, period: str, interval: str) -> pd.DataFrame:
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if data.empty:
        return data
    if isinstance(data.columns, pd.MultiIndex):
        # yfinance may return OHLCV as a MultiIndex even for one ticker.
        if ticker in data.columns.get_level_values(-1):
            data = data.xs(ticker, axis=1, level=-1)
        else:
            data.columns = data.columns.get_level_values(0)
    return data[["Open", "High", "Low", "Close", "Volume"]].dropna()


def main():
    st.set_page_config(page_title="Elliott Wave Plotly", layout="wide")
    st.title("Elliott Wave Plotly (yfinance)")

    c1, c2, c3 = st.columns([1.6, 1, 1])
    with c1:
        ticker = st.text_input("Ticker", value="SPY").strip().upper() or "SPY"
    with c2:
        period = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=2)
    with c3:
        interval = st.selectbox("Interval", ["1d", "1wk"], index=0)

    c4, c5, c6 = st.columns([1, 1, 1])
    with c4:
        show_setup_from = st.selectbox("TD Setup From", [1, 5, 7, 9], index=3)
    with c5:
        show_countdown_from = st.selectbox("TD Countdown From", [9, 10, 11, 12, 13], index=4)
    with c6:
        label_cooldown = st.slider("TD Label Cooldown", min_value=0, max_value=10, value=0)

    df = load_price(ticker, period, interval)
    if df.empty:
        st.error(f"No data returned for ticker '{ticker}'.")
        return

    swings_map = {
        4: _find_swings(df, window=4 if interval == "1d" else 3),
        8: _find_swings(df, window=8 if interval == "1d" else 5),
        16: _find_swings(df, window=16 if interval == "1d" else 8),
    }
    td = TDSequentialClean(
        show_setup_from=show_setup_from,
        show_countdown_from=show_countdown_from,
        label_cooldown_bars=label_cooldown,
    )
    fig = build_chart(df, swings_map, ticker, td=td)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bars are OHLC. Elliott-wave overlays are algorithmic approximations inspired by Lux-style zigzag logic.")


if __name__ == "__main__":
    main()
