"""
v5c Force Index Composite — Mean Reversion Signal for Equity ETFs

Combines three orthogonal oversold/overbought measurements:
  1. Range MR (55%): IBS + Williams %R(3) + IBS percentile rank(126d)
  2. Force Index (30%): Volume-confirmed price shocks (FI(1) z-score, inverted)
  3. ATR-Band (15%): Distance below volatility-adjusted lower band

Output: pulse (-100 to +100), trend regime (-1 to +1), position signal (0/0.9/1.0).

Architecture (v6):
  Base: 90% when pulse > -30
  Exit: pulse < -50 AND trend_regime < -0.5 (conditional — requires both)
  Boost: 100% when RSI(2) < 20 AND IBS < 0.20 AND price > SMA(200)
  Boost exit: RSI(2) > 65 or 14 days
"""

from typing import Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ix.db.client import get_timeseries
from ix.common import get_logger

logger = get_logger(__name__)


class ForceIndexComposite:
    """
    v5c Force Index Composite — equity mean-reversion signal with
    crash avoidance and oversold boost.

    Pulse > 0 = oversold (bullish for MR).
    Pulse < 0 = not oversold (neutral/bearish).
    Position: 90% base with conditional exit, boost to 100% on extreme oversold.
    """

    @classmethod
    def from_meta(
        cls,
        code: str,
        smooth_span: int = 3,
        base_alloc: float = 0.90,
        fi_lookback: int = 126,
    ) -> "ForceIndexComposite":
        """Create from a database code (e.g., 'SPY US EQUITY')."""
        px_close = get_timeseries(code=code, field="PX_LAST")
        px_high = get_timeseries(code=code, field="PX_HIGH")
        px_low = get_timeseries(code=code, field="PX_LOW")
        px_volume = get_timeseries(code=code, field="PX_VOLUME")
        if px_close.empty:
            raise ValueError(f"No price data for code: {code}")
        return cls(
            px_close=px_close,
            px_high=px_high,
            px_low=px_low,
            px_volume=px_volume,
            smooth_span=smooth_span,
            base_alloc=base_alloc,
            fi_lookback=fi_lookback,
        )

    def __init__(
        self,
        px_close: pd.Series,
        px_high: Optional[pd.Series] = None,
        px_low: Optional[pd.Series] = None,
        px_volume: Optional[pd.Series] = None,
        smooth_span: int = 3,
        base_alloc: float = 0.90,
        fi_lookback: int = 126,
    ) -> None:
        """
        Initialize ForceIndexComposite.

        :param px_close: Daily closing prices.
        :param px_high: Daily high prices (defaults to close if None).
        :param px_low: Daily low prices (defaults to close if None).
        :param px_volume: Daily volume (defaults to ones if None).
        :param smooth_span: EMA smoothing span for pulse (default 3).
        :param base_alloc: Base allocation fraction (default 0.90).
        :param fi_lookback: Force Index z-score lookback (default 126).
        """
        if not isinstance(px_close, pd.Series):
            raise TypeError("px_close must be a pandas Series.")
        if px_close.empty:
            raise ValueError("px_close cannot be empty.")
        if not pd.api.types.is_numeric_dtype(px_close):
            raise ValueError("px_close must contain numeric data.")

        self.px_close = px_close.astype(float).copy()
        self.px_high = (px_high if px_high is not None and not px_high.empty
                        else px_close).astype(float).copy()
        self.px_low = (px_low if px_low is not None and not px_low.empty
                       else px_close).astype(float).copy()
        self.px_volume = (px_volume if px_volume is not None and not px_volume.empty
                          else pd.Series(1.0, index=px_close.index)).astype(float).copy()

        self.smooth_span = smooth_span
        self.base_alloc = base_alloc
        self.fi_lookback = fi_lookback

        self._store: dict = {}
        self.df = pd.DataFrame()
        self._calculate_indicator()

    # ─── Cached properties ────────────────────────────────────────────

    @property
    def trend_regime(self) -> pd.Series:
        """Trend regime: smoothed avg of (price>SMA200) + (SMA50>SMA200), scaled to [-1,+1]."""
        if "trend_regime" not in self._store:
            c = self.px_close
            sma50 = c.rolling(50).mean()
            sma200 = c.rolling(200).mean()
            raw = (((c > sma200).astype(float) + (sma50 > sma200).astype(float)) / 2) * 2 - 1
            self._store["trend_regime"] = raw.ewm(span=10, adjust=False).mean()
        return self._store["trend_regime"]

    @property
    def comp1(self) -> pd.Series:
        """Range MR: IBS + Williams %R(3) + IBS percentile rank(126d)."""
        if "comp1" not in self._store:
            c, h, lo = self.px_close, self.px_high, self.px_low
            dr = (h - lo).clip(lower=1e-10)
            ibs = (c - lo) / dr
            ibs_mr = ((0.5 - ibs) * 2).clip(-1, 1)
            hh3, ll3 = h.rolling(3).max(), lo.rolling(3).min()
            wr_mr = ((((hh3 - c) / (hh3 - ll3).clip(lower=1e-10)) * -100 + 50) / -50).clip(-1, 1)
            ibs_p = ibs.rolling(self.fi_lookback, min_periods=50).rank(pct=True) * 100
            ibs_p_mr = ((50 - ibs_p) / 50).clip(-1, 1)
            self._store["comp1"] = 0.35 * ibs_mr + 0.35 * wr_mr + 0.30 * ibs_p_mr
        return self._store["comp1"]

    @property
    def comp2(self) -> pd.Series:
        """Force Index(1) z-score, inverted: large selling = bullish for MR."""
        if "comp2" not in self._store:
            fi1 = (self.px_close - self.px_close.shift(1)) * self.px_volume
            fi1_mean = fi1.rolling(self.fi_lookback, min_periods=50).mean()
            fi1_std = fi1.rolling(self.fi_lookback, min_periods=50).std().clip(lower=1e-10)
            fi1_z = ((fi1 - fi1_mean) / fi1_std).clip(-3, 3)
            self._store["comp2"] = (-fi1_z / 3).clip(-1, 1)
        return self._store["comp2"]

    @property
    def comp3(self) -> pd.Series:
        """ATR-Band distance: how far price stretched below lower band."""
        if "comp3" not in self._store:
            c, h, lo = self.px_close, self.px_high, self.px_low
            prev = c.shift(1)
            tr = pd.concat([h - lo, (h - prev).abs(), (lo - prev).abs()], axis=1).max(axis=1)
            atr = tr.ewm(span=10, adjust=False).mean()
            band = c.rolling(10).mean() - 1.5 * atr
            self._store["comp3"] = ((band - c) / atr.clip(lower=1e-10)).clip(-3, 3) / 3
        return self._store["comp3"]

    @property
    def pulse_raw(self) -> pd.Series:
        """Raw composite pulse before smoothing (-100 to +100)."""
        if "pulse_raw" not in self._store:
            raw = 0.55 * self.comp1 + 0.30 * self.comp2 + 0.15 * self.comp3
            boost = 1.0 + 0.3 * (raw * self.trend_regime).clip(-1, 1)
            self._store["pulse_raw"] = (raw * boost * 100).clip(-100, 100)
        return self._store["pulse_raw"]

    @property
    def pulse(self) -> pd.Series:
        """Smoothed composite pulse (-100 to +100)."""
        if "pulse" not in self._store:
            self._store["pulse"] = self.pulse_raw.ewm(
                span=self.smooth_span, adjust=False
            ).mean()
        return self._store["pulse"]

    @property
    def rsi2(self) -> pd.Series:
        """RSI(2) for boost entry/exit detection."""
        if "rsi2" not in self._store:
            delta = self.px_close.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            ag = gain.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
            al = loss.ewm(alpha=0.5, min_periods=2, adjust=False).mean()
            self._store["rsi2"] = 100 - (100 / (1 + ag / al.clip(lower=1e-10)))
        return self._store["rsi2"]

    @property
    def ibs(self) -> pd.Series:
        """Internal Bar Strength: (Close - Low) / (High - Low)."""
        if "ibs" not in self._store:
            dr = (self.px_high - self.px_low).clip(lower=1e-10)
            self._store["ibs"] = (self.px_close - self.px_low) / dr
        return self._store["ibs"]

    @property
    def position(self) -> pd.Series:
        """
        Position signal (0.0, 0.9, or 1.0) using the v6 architecture:
        90% base with conditional exit + 100% boost on extreme oversold.
        Shifted by 1 day for MOC execution.
        """
        if "position" not in self._store:
            p = self.pulse
            tr = self.trend_regime
            c = self.px_close
            rsi = self.rsi2
            ibs_v = self.ibs
            sma200 = c.rolling(200).mean()

            pos = pd.Series(0.0, index=p.index)
            base_in = False
            boost_in = False
            boost_hold = 0

            for i in range(252, len(p)):
                if pd.isna(p.iloc[i]):
                    continue
                pv = p.iloc[i]
                # Base layer
                if not base_in:
                    if pv >= -30:
                        base_in = True
                if base_in:
                    if pv < -50 and tr.iloc[i] < -0.5:
                        base_in = False
                    else:
                        pos.iloc[i] = self.base_alloc
                # Boost layer
                if boost_in:
                    boost_hold += 1
                    if boost_hold >= 28:
                        boost_in = False
                        boost_hold = 0
                    else:
                        pos.iloc[i] = 1.0
                else:
                    if (rsi.iloc[i] < 20 and
                            ibs_v.iloc[i] < 0.20 and
                            c.iloc[i] > sma200.iloc[i]):
                        pos.iloc[i] = 1.0
                        boost_in = True
                        boost_hold = 0

            self._store["position"] = pos.shift(1).fillna(0)
        return self._store["position"]

    # ─── Core compute ─────────────────────────────────────────────────

    def _calculate_indicator(self) -> None:
        """Compute all outputs and store in self.df."""
        self.df = pd.DataFrame({
            "close": self.px_close,
            "pulse": self.pulse,
            "pulse_raw": self.pulse_raw,
            "trend_regime": self.trend_regime,
            "comp1_range_mr": self.comp1,
            "comp2_force_index": self.comp2,
            "comp3_atr_band": self.comp3,
            "rsi2": self.rsi2,
            "ibs": self.ibs,
            "position": self.position,
        })

    # ─── Public helpers ───────────────────────────────────────────────

    def to_dataframe(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """Return computed indicator data as a DataFrame."""
        df = self.df.copy()
        if start is not None:
            df = df.loc[start:]
        if end is not None:
            df = df.loc[:end]
        return df

    def backtest(self, cost_bps: float = 10.0) -> pd.DataFrame:
        """
        Run backtest with trading costs. Returns DataFrame with:
        strategy_ret, bnh_ret, position, cumulative_strategy, cumulative_bnh.

        :param cost_bps: Round-trip trading cost in basis points (default 10).
        """
        daily_ret = self.px_close.pct_change()
        pos = self.position
        start = self.pulse.dropna().index[0]

        turnover = pos.diff().abs()
        cost = turnover * (cost_bps / 10000)
        strat_ret = (pos * daily_ret - cost).loc[start:]
        bnh_ret = daily_ret.loc[start:]

        cum_strat = (1 + strat_ret).cumprod()
        cum_bnh = (1 + bnh_ret).cumprod()

        return pd.DataFrame({
            "strategy_ret": strat_ret,
            "bnh_ret": bnh_ret,
            "position": pos.loc[start:],
            "cumulative_strategy": cum_strat,
            "cumulative_bnh": cum_bnh,
        })

    def perf_stats(self, cost_bps: float = 10.0) -> dict:
        """
        Compute performance statistics after trading costs.

        Returns dict with: sharpe, ann_return, bnh_return, relative_alpha,
        max_drawdown, volatility, calmar, exposure, turnover_per_year.
        """
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
            "years": round(len(r) / 252, 1),
        }

    # ─── Visualization ────────────────────────────────────────────────

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
        max_labels: int = 25,
    ) -> go.Figure:
        """
        Bloomberg terminal chart — 2 panels:
        Row 1: OHLC candlestick + pulse index scaled around price as a filled band.
               The pulse (-100 to +100) is mapped to a displacement around SMA(20),
               creating a band that wraps the candles:
               - Green fill above mid = pulse > 0 (oversold, bullish MR)
               - Red fill below mid   = pulse < 0 (extended, avoid)
               + entry/exit triangle markers
        Row 2: Position weight (0-100%)

        No SMA50, no SMA200, no white. Just OHLC + pulse band + weight.

        :param start: Start date filter.
        :param end: End date filter.
        :param max_labels: Max entry/exit markers to show (default 25).
        """
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            logger.warning("No data for the selected range.")
            return go.Figure()

        # ── Colors (no white — muted terminal palette) ────────────────
        BG = "rgba(0,0,0,0)"
        GRID = "rgba(148,163,184,0.06)"
        FONT = dict(family="'Space Mono', monospace", size=10, color="#94a3b8")
        GREEN, RED, ACCENT, DIM = "#22c55e", "#ef5350", "#6382ff", "#555a6e"
        UP, DN = "#26a69a", "#ef5350"
        MUTED = "rgba(148,163,184,0.25)"

        idx = df.index
        c = df["close"]
        h = self.px_high.reindex(idx)
        lo = self.px_low.reindex(idx)
        o_prices = ((h + lo + c) / 3).shift(1).fillna(c)
        pos = df["position"]
        pulse = df["pulse"]

        # ── BB bounds (faint envelope for context) ─────────────────────
        bb_mid = c.rolling(20).mean()
        bb_std = c.rolling(20).std().clip(lower=1e-10)
        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std

        # Detect contiguous pulse regimes for vrect shading
        pulse_bull = pulse >= 0

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.82, 0.18],
            vertical_spacing=0.008,
        )

        # ══════════════════════════════════════════════════════════════
        # ROW 1: OHLC + PULSE COLORED BACKGROUND ZONES
        # ══════════════════════════════════════════════════════════════

        # 1a. Pulse background — green/red vertical rectangles per regime
        #     No fill artifacts — vrect draws clean rectangles
        regime_changed = pulse_bull != pulse_bull.shift(1)
        segment_id = regime_changed.cumsum()
        valid = pulse_bull.dropna()
        for _, seg in valid.groupby(segment_id.reindex(valid.index)):
            is_bull = seg.iloc[0]
            x0 = seg.index[0]
            x1 = seg.index[-1]
            color = "rgba(34,197,94,0.08)" if is_bull else "rgba(239,83,80,0.08)"
            fig.add_vrect(
                x0=x0, x1=x1, fillcolor=color,
                layer="below", line_width=0, row=1, col=1,
            )

        # 1b. BB outer lines (faint boundary — no fill)
        fig.add_trace(go.Scatter(
            x=idx, y=bb_upper, mode="lines",
            line=dict(color=MUTED, width=0.6),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=bb_lower, mode="lines",
            line=dict(color=MUTED, width=0.6),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

        # 1c. OHLC Candlestick
        fig.add_trace(go.Candlestick(
            x=idx, open=o_prices, high=h, low=lo, close=c,
            increasing=dict(line=dict(color=UP, width=0.8), fillcolor=UP),
            decreasing=dict(line=dict(color=DN, width=0.8), fillcolor=DN),
            showlegend=False, name="OHLC",
        ), row=1, col=1)

        # 1d. Entry/exit markers
        prev_pos = pos.shift(1).fillna(0)
        entry_mask = (pos > 0) & (prev_pos == 0)
        exit_mask = (pos == 0) & (prev_pos > 0)
        entry_dates = idx[entry_mask][-max_labels:]
        exit_dates = idx[exit_mask][-max_labels:]

        if len(entry_dates) > 0:
            fig.add_trace(go.Scatter(
                x=entry_dates,
                y=lo.reindex(entry_dates) * 0.997,
                mode="markers", name="Entry",
                marker=dict(symbol="triangle-up", size=9, color=GREEN,
                            line=dict(width=0.5, color=GREEN)),
                hovertemplate="%{x|%Y-%m-%d}<br>BUY $%{text}<extra></extra>",
                text=[f"{c.loc[d]:,.2f}" for d in entry_dates],
            ), row=1, col=1)

        if len(exit_dates) > 0:
            fig.add_trace(go.Scatter(
                x=exit_dates,
                y=h.reindex(exit_dates) * 1.003,
                mode="markers", name="Exit",
                marker=dict(symbol="triangle-down", size=9, color=RED,
                            line=dict(width=0.5, color=RED)),
                hovertemplate="%{x|%Y-%m-%d}<br>SELL $%{text}<extra></extra>",
                text=[f"{c.loc[d]:,.2f}" for d in exit_dates],
            ), row=1, col=1)

        # 1e. Boost markers — diamond when position goes to 100%, hollow when back to 90%
        boost_start = (pos >= 1.0) & (pos.shift(1) < 1.0)
        boost_end = (pos < 1.0) & (pos > 0) & (pos.shift(1) >= 1.0)
        boost_on_dates = idx[boost_start][-max_labels:]
        boost_off_dates = idx[boost_end][-max_labels:]

        if len(boost_on_dates) > 0:
            fig.add_trace(go.Scatter(
                x=boost_on_dates,
                y=lo.reindex(boost_on_dates) * 0.994,
                mode="markers", name="Boost On",
                marker=dict(symbol="diamond", size=8, color="#f59e0b",
                            line=dict(width=0.5, color="#f59e0b")),
                hovertemplate="%{x|%Y-%m-%d}<br>BOOST 100%<br>$%{text}<extra></extra>",
                text=[f"{c.loc[d]:,.2f}" for d in boost_on_dates],
            ), row=1, col=1)

        if len(boost_off_dates) > 0:
            fig.add_trace(go.Scatter(
                x=boost_off_dates,
                y=lo.reindex(boost_off_dates) * 0.994,
                mode="markers", name="Boost Off",
                marker=dict(symbol="diamond-open", size=8, color="#f59e0b",
                            line=dict(width=1.5, color="#f59e0b")),
                hovertemplate="%{x|%Y-%m-%d}<br>BACK TO 90%<br>$%{text}<extra></extra>",
                text=[f"{c.loc[d]:,.2f}" for d in boost_off_dates],
            ), row=1, col=1)

        # ══════════════════════════════════════════════════════════════
        # ROW 2: POSITION WEIGHT
        # ══════════════════════════════════════════════════════════════
        fig.add_trace(go.Scatter(
            x=idx, y=pos * 100, mode="none", fill="tozeroy",
            fillcolor="rgba(99,130,255,0.12)",
            showlegend=False, hoverinfo="skip",
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=pos * 100, mode="lines", name="Weight",
            line=dict(color=ACCENT, width=1.5, shape="hv"),
        ), row=2, col=1)
        fig.add_hline(y=100, line_dash="dot", line_color="rgba(34,197,94,0.3)",
                       line_width=0.5, row=2, col=1)
        fig.add_hline(y=90, line_dash="dot", line_color="rgba(99,130,255,0.3)",
                       line_width=0.5, row=2, col=1)
        fig.add_hline(y=0, line_color="rgba(148,163,184,0.3)",
                       line_width=0.8, row=2, col=1)

        # ══════════════════════════════════════════════════════════════
        # LAYOUT — Bloomberg terminal, no white
        # ══════════════════════════════════════════════════════════════
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=BG,
            plot_bgcolor=BG,
            font=FONT,
            height=650,
            margin=dict(l=0, r=8, t=8, b=0),
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.01,
                xanchor="right", x=1,
                font=dict(size=9, color="#94a3b8"), bgcolor=BG,
            ),
            xaxis_rangeslider_visible=False,
            xaxis2_rangeslider_visible=False,
        )

        # Axes — right-side, subtle grid
        for row in [1, 2]:
            fig.update_xaxes(
                showgrid=True, gridcolor=GRID, zeroline=False, showline=False,
                tickfont=dict(color=DIM, size=9),
                rangebreaks=[dict(bounds=["sat", "mon"])],
                row=row, col=1,
            )
            fig.update_yaxes(
                showgrid=True, gridcolor=GRID, zeroline=False, showline=False,
                side="right", tickfont=dict(color=DIM, size=9),
                row=row, col=1,
            )

        # Weight axis
        fig.update_yaxes(
            row=2, col=1, range=[-5, 110],
            tickvals=[0, 50, 90, 100], ticktext=["0%", "50%", "90%", "100%"],
        )
        # Hide x-ticks on price panel
        fig.update_xaxes(showticklabels=False, row=1, col=1)

        # Panel label
        fig.add_annotation(
            text="PULSE INDEX",
            x=0.005, y=0.99, xref="paper", yref="paper",
            xanchor="left", showarrow=False,
            font=dict(size=10, color="#94a3b8", family="'Space Mono', monospace"),
        )
        fig.add_annotation(
            text="WEIGHT", x=0.005, y=0.14, xref="paper", yref="paper",
            xanchor="left", showarrow=False,
            font=dict(size=8, color=ACCENT, family="'Space Mono', monospace"),
        )

        return fig
