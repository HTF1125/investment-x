"""
Weekly Regime Composite — Slow-frequency equity timing indicator.

Three weekly signals vote on regime (bullish/bearish):
  1. Golden Cross: 10-week SMA > 40-week SMA (trend)
  2. TSMOM 52w: 52-week return > 0 (momentum)
  3. Coppock Curve: monthly momentum oscillator > 0 (cycle)

Position rule: LONG when ANY signal is bullish (vote >= 1).
             FLAT only when ALL three turn bearish simultaneously.

Design principles:
  - All signals computed on WEEKLY bars
  - Position changes only on Fridays (max 4/month by construction)
  - In practice: ~0.1 trades/month (~1-2 per year)
  - Stay invested 85% of time, exit only during genuine bear markets
  - No daily MR, no boost layer, no hysteresis — just 3 slow signals voting

Performance (30yr, 10 bps cost):
  SPY: Sharpe 0.623 | Ann 9.5% | +13.5% vs B&H | MDD -34.1%
  QQQ: Sharpe 0.580 | Ann 8.8% | MDD -34.1%
"""

from typing import Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ix.db.client import get_timeseries
from ix.common import get_logger

logger = get_logger(__name__)


class WeeklyRegimeComposite:
    """
    Weekly regime indicator — 3-signal consensus for equity timing.

    Long when ANY of the 3 signals is bullish (vote >= 1).
    Flat only when ALL 3 are bearish (vote == 0).
    Position changes only on Fridays.
    """

    @classmethod
    def from_meta(cls, code: str) -> "WeeklyRegimeComposite":
        """Create from a database code."""
        px_close = get_timeseries(code=code, field="PX_LAST")
        px_high = get_timeseries(code=code, field="PX_HIGH")
        px_low = get_timeseries(code=code, field="PX_LOW")
        px_volume = get_timeseries(code=code, field="PX_VOLUME")
        if px_close.empty:
            raise ValueError(f"No price data for code: {code}")
        return cls(px_close=px_close, px_high=px_high, px_low=px_low, px_volume=px_volume)

    def __init__(
        self,
        px_close: pd.Series,
        px_high: Optional[pd.Series] = None,
        px_low: Optional[pd.Series] = None,
        px_volume: Optional[pd.Series] = None,
    ) -> None:
        if not isinstance(px_close, pd.Series):
            raise TypeError("px_close must be a pandas Series.")
        if px_close.empty:
            raise ValueError("px_close cannot be empty.")

        self.px_close = px_close.astype(float).copy()
        self.px_high = (px_high if px_high is not None and not px_high.empty
                        else px_close).astype(float).copy()
        self.px_low = (px_low if px_low is not None and not px_low.empty
                       else px_close).astype(float).copy()
        self.px_volume = (px_volume if px_volume is not None and not px_volume.empty
                          else pd.Series(1.0, index=px_close.index)).astype(float).copy()

        self._store: dict = {}
        self.df = pd.DataFrame()

        # Build weekly bars
        daily = pd.DataFrame({
            'Open': self.px_close.shift(1).fillna(self.px_close),
            'High': self.px_high, 'Low': self.px_low,
            'Close': self.px_close, 'Volume': self.px_volume,
        })
        self._weekly = daily.resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum',
        }).dropna()

        self._calculate_indicator()

    # ─── Cached properties (all computed on weekly bars) ──────────────

    @property
    def weekly_close(self) -> pd.Series:
        return self._weekly['Close']

    @property
    def golden_cross(self) -> pd.Series:
        """Signal 1: 10-week SMA > 40-week SMA."""
        if "gc" not in self._store:
            c = self.weekly_close
            sma10 = c.rolling(10).mean()
            sma40 = c.rolling(40).mean()
            self._store["gc"] = (sma10 > sma40).astype(float)
            self._store["sma10w"] = sma10
            self._store["sma40w"] = sma40
        return self._store["gc"]

    @property
    def tsmom(self) -> pd.Series:
        """Signal 2: 52-week return > 0."""
        if "tsmom" not in self._store:
            c = self.weekly_close
            self._store["tsmom"] = (c.pct_change(52) > 0).astype(float)
            self._store["ret52w"] = c.pct_change(52)
        return self._store["tsmom"]

    @property
    def coppock(self) -> pd.Series:
        """Signal 3: Coppock Curve > 0."""
        if "cop" not in self._store:
            c = self.weekly_close
            roc14 = c.pct_change(56) * 100
            roc11 = c.pct_change(44) * 100
            copp_raw = roc14 + roc11
            weights = np.arange(1, 41)
            copp = copp_raw.rolling(40).apply(
                lambda x: np.dot(x, weights[-len(x):]) / weights[-len(x):].sum(), raw=True)
            self._store["cop"] = (copp > 0).astype(float)
            self._store["coppock_val"] = copp
        return self._store["cop"]

    @property
    def vote(self) -> pd.Series:
        """Vote count: 0-3 (how many signals are bullish)."""
        if "vote" not in self._store:
            self._store["vote"] = self.golden_cross + self.tsmom + self.coppock
        return self._store["vote"]

    @property
    def position_weekly(self) -> pd.Series:
        """Weekly position: 1.0 when vote >= 1, 0.0 when vote == 0."""
        if "pos_w" not in self._store:
            self._store["pos_w"] = (self.vote >= 1).astype(float)
        return self._store["pos_w"]

    @property
    def position(self) -> pd.Series:
        """Daily position (forward-filled from weekly, shifted for MOC)."""
        if "pos_d" not in self._store:
            pos_w = self.position_weekly
            pos_d = pos_w.reindex(self.px_close.index).ffill().fillna(0)
            self._store["pos_d"] = pos_d.shift(1).fillna(0)
        return self._store["pos_d"]

    @property
    def regime(self) -> pd.Series:
        """Regime label: 'Risk-On' (vote>=1) or 'Risk-Off' (vote==0)."""
        if "regime" not in self._store:
            v = self.vote.reindex(self.px_close.index).ffill().fillna(0)
            self._store["regime"] = v.map(
                lambda x: "Risk-On" if x >= 1 else "Risk-Off")
        return self._store["regime"]

    # ─── Core compute ─────────────────────────────────────────────────

    def _calculate_indicator(self) -> None:
        # Trigger computation
        _ = self.golden_cross, self.tsmom, self.coppock, self.vote

        # Weekly dataframe
        self._weekly_df = pd.DataFrame({
            "close": self.weekly_close,
            "golden_cross": self.golden_cross,
            "tsmom_52w": self.tsmom,
            "coppock": self.coppock,
            "vote": self.vote,
            "position": self.position_weekly,
        })

        # Daily dataframe
        vote_daily = self.vote.reindex(self.px_close.index).ffill().fillna(0)
        self.df = pd.DataFrame({
            "close": self.px_close,
            "vote": vote_daily,
            "position": self.position,
            "regime": self.regime,
        })

    # ─── Public helpers ───────────────────────────────────────────────

    def to_dataframe(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        df = self.df.copy()
        if start is not None:
            df = df.loc[start:]
        if end is not None:
            df = df.loc[:end]
        return df

    def backtest(self, cost_bps: float = 10.0) -> pd.DataFrame:
        daily_ret = self.px_close.pct_change()
        pos = self.position
        start_idx = self.vote.dropna().index[0]
        # Map back to daily index
        start_daily = self.px_close.index[self.px_close.index >= start_idx][0]

        turnover = pos.diff().abs()
        cost = turnover * (cost_bps / 10000)
        strat_ret = (pos * daily_ret - cost).loc[start_daily:]
        bnh_ret = daily_ret.loc[start_daily:]

        return pd.DataFrame({
            "strategy_ret": strat_ret,
            "bnh_ret": bnh_ret,
            "position": pos.loc[start_daily:],
            "cumulative_strategy": (1 + strat_ret).cumprod(),
            "cumulative_bnh": (1 + bnh_ret).cumprod(),
        })

    def perf_stats(self, cost_bps: float = 10.0) -> dict:
        bt = self.backtest(cost_bps=cost_bps)
        r = bt["strategy_ret"].dropna()
        br = bt["bnh_ret"].dropna()
        pos = bt["position"]

        if len(r) < 50:
            return {}

        ann = (1 + r).prod() ** (252 / len(r)) - 1
        vol = r.std() * np.sqrt(252)
        sharpe = ann / vol if vol > 0 else 0
        cum = (1 + r).cumprod()
        mdd = (cum / cum.cummax() - 1).min()
        calmar = ann / abs(mdd) if mdd != 0 else 0
        bnh_ann = (1 + br).prod() ** (252 / len(br)) - 1
        rel_alpha = (ann / bnh_ann - 1) if bnh_ann > 0.001 else 0
        to = pos.diff().abs().sum() / 2 / (len(r) / 252)
        exp = pos.mean()
        changes = (pos.diff().abs() > 0.01).sum()
        tpm = changes / (len(r) / 21)

        return {
            "sharpe": round(sharpe, 3),
            "ann_return": round(ann * 100, 2),
            "bnh_return": round(bnh_ann * 100, 2),
            "relative_alpha": round(rel_alpha * 100, 1),
            "max_drawdown": round(mdd * 100, 2),
            "volatility": round(vol * 100, 2),
            "calmar": round(calmar, 2),
            "exposure": round(exp * 100, 1),
            "turnover_per_year": round(to, 1),
            "trades_per_month": round(tpm, 1),
            "years": round(len(r) / 252, 1),
        }

    # ─── Visualization ────────────────────────────────────────────────

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> go.Figure:
        """
        Bloomberg terminal chart — 2 panels:
        Row 1 (80%): OHLC candlestick + 10w/40w SMA + regime background zones
                     + entry/exit markers
        Row 2 (20%): Vote count (0-3) as step line
        """
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            return go.Figure()

        BG = "rgba(0,0,0,0)"
        GRID = "rgba(148,163,184,0.06)"
        FONT = dict(family="'Space Mono', monospace", size=10, color="#94a3b8")
        GREEN, RED, ACCENT, DIM = "#22c55e", "#ef5350", "#6382ff", "#555a6e"
        UP, DN = "#26a69a", "#ef5350"

        idx = df.index
        c = df["close"]
        h = self.px_high.reindex(idx)
        lo = self.px_low.reindex(idx)
        o_prices = c.shift(1).fillna(c)
        pos = df["position"]
        vote = df["vote"]

        # Weekly SMAs forward-filled to daily
        sma10w = self._store.get("sma10w", pd.Series(dtype=float))
        sma40w = self._store.get("sma40w", pd.Series(dtype=float))
        sma10w_d = sma10w.reindex(idx).ffill()
        sma40w_d = sma40w.reindex(idx).ffill()

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.80, 0.20],
            vertical_spacing=0.008,
        )

        # ── ROW 1: OHLC + REGIME ZONES ───────────────────────────────

        # Regime background (vrect — clean rectangles)
        is_on = pos > 0
        regime_changed = is_on != is_on.shift(1)
        segment_id = regime_changed.cumsum()
        for _, seg in is_on.groupby(segment_id):
            bull = seg.iloc[0]
            x0, x1 = seg.index[0], seg.index[-1]
            color = "rgba(34,197,94,0.06)" if bull else "rgba(239,83,80,0.06)"
            fig.add_vrect(x0=x0, x1=x1, fillcolor=color, layer="below",
                          line_width=0, row=1, col=1)

        # OHLC
        fig.add_trace(go.Candlestick(
            x=idx, open=o_prices, high=h, low=lo, close=c,
            increasing=dict(line=dict(color=UP, width=0.8), fillcolor=UP),
            decreasing=dict(line=dict(color=DN, width=0.8), fillcolor=DN),
            showlegend=False, name="OHLC",
        ), row=1, col=1)

        # Weekly SMAs
        fig.add_trace(go.Scatter(
            x=idx, y=sma10w_d, mode="lines", name="10w SMA",
            line=dict(color="#2dd4bf", width=1.5), opacity=0.6,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=sma40w_d, mode="lines", name="40w SMA",
            line=dict(color="rgba(148,163,184,0.4)", width=1.5),
        ), row=1, col=1)

        # Entry/exit markers (all signals across full history)
        prev_pos = pos.shift(1).fillna(0)
        entry_dates = idx[(pos > 0) & (prev_pos == 0)]
        exit_dates = idx[(pos == 0) & (prev_pos > 0)]

        if len(entry_dates) > 0:
            fig.add_trace(go.Scatter(
                x=entry_dates, y=lo.reindex(entry_dates) * 0.997,
                mode="markers", name="Entry",
                marker=dict(symbol="triangle-up", size=10, color=GREEN,
                            line=dict(width=0.5, color=GREEN)),
                hovertemplate="%{x|%Y-%m-%d}<br>RISK-ON<extra></extra>",
            ), row=1, col=1)
        if len(exit_dates) > 0:
            fig.add_trace(go.Scatter(
                x=exit_dates, y=h.reindex(exit_dates) * 1.003,
                mode="markers", name="Exit",
                marker=dict(symbol="triangle-down", size=10, color=RED,
                            line=dict(width=0.5, color=RED)),
                hovertemplate="%{x|%Y-%m-%d}<br>RISK-OFF<extra></extra>",
            ), row=1, col=1)

        # ── ROW 2: VOTE COUNT ────────────────────────────────────────
        vote_colors = vote.map({0: RED, 1: "#f59e0b", 2: "#2dd4bf", 3: GREEN}).fillna(DIM)
        fig.add_trace(go.Scatter(
            x=idx, y=vote, mode="lines", name="Vote",
            line=dict(color=ACCENT, width=2, shape="hv"),
        ), row=2, col=1)
        fig.add_hline(y=1, line_dash="dot", line_color="rgba(34,197,94,0.3)",
                       line_width=0.8, row=2, col=1)
        fig.add_hline(y=0, line_color="rgba(148,163,184,0.3)",
                       line_width=0.8, row=2, col=1)

        # Layout
        fig.update_layout(
            template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
            font=FONT, height=600,
            margin=dict(l=0, r=8, t=8, b=0),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="right", x=1, font=dict(size=9), bgcolor=BG),
            xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False,
        )
        for row in [1, 2]:
            fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                             showline=False, tickfont=dict(color=DIM, size=9),
                             rangebreaks=[dict(bounds=["sat", "mon"])], row=row, col=1)
            fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                             showline=False, side="right",
                             tickfont=dict(color=DIM, size=9), row=row, col=1)
        fig.update_yaxes(row=2, col=1, range=[-0.3, 3.3],
                         tickvals=[0, 1, 2, 3], ticktext=["0", "1", "2", "3"])
        fig.update_xaxes(showticklabels=False, row=1, col=1)

        fig.add_annotation(
            text="WEEKLY REGIME", x=0.005, y=0.99,
            xref="paper", yref="paper", xanchor="left", showarrow=False,
            font=dict(size=10, color="#94a3b8", family="'Space Mono', monospace"),
        )
        fig.add_annotation(
            text="VOTE (3 signals)", x=0.005, y=0.16,
            xref="paper", yref="paper", xanchor="left", showarrow=False,
            font=dict(size=8, color=ACCENT, family="'Space Mono', monospace"),
        )

        return fig
