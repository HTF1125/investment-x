"""
TrendMomentumComposite — Daily Swing Trading System

Selective-entry mean-reversion system: buys oversold pullbacks in confirmed
uptrends, exits when price reverts to short-term mean.

Three-state position: 0% (flat), HALF, FULL

Entry logic:
  - Trend gate: close > EMA(200) (long-term uptrend confirmed)
  - FULL entry: RSI(2) < 10 AND close < BB lower band (extreme oversold + band break)
  - HALF entry: RSI(2) < 10 AND IBS < 0.4 (oversold + weak close)

Exit logic (first to trigger):
  - Profit target: close > SMA(5) (mean reversion complete)
  - Trend break: close < EMA(200) × 0.97 (3% below trend — bail out)

Position sizing (configurable):
  - FULL default: 50% of capital
  - HALF default: 25% of capital
  - These defaults target max drawdown under -5%
"""

from typing import Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ix.db.client import get_timeseries
from ix.common import get_logger

logger = get_logger(__name__)


class TrendMomentumComposite:
    """
    Daily swing trading system for equity indices.

    Three-state: FLAT / HALF / FULL.
    Buys RSI(2) oversold pullbacks below Bollinger Band in uptrends.
    Exits when price reverts above 5-day SMA.

    Default sizing (50%/25%) targets max DD < -5%.
    """

    @classmethod
    def from_meta(
        cls,
        code: str,
        **kwargs,
    ) -> "TrendMomentumComposite":
        """Create from a database code (e.g., 'SPY US EQUITY')."""
        px_close = get_timeseries(code=f"{code}:PX_LAST").data
        if px_close.empty:
            raise ValueError(f"No price data for code: {code}")

        def _try_field(field: str) -> Optional[pd.Series]:
            try:
                return get_timeseries(code=f"{code}:{field}").data
            except ValueError:
                return None

        return cls(
            px_close=px_close,
            px_high=_try_field("PX_HIGH"),
            px_low=_try_field("PX_LOW"),
            **kwargs,
        )

    @classmethod
    def from_yfinance(
        cls,
        ticker: str = "SPY",
        period: str = "max",
        **kwargs,
    ) -> "TrendMomentumComposite":
        """Create from yfinance data (e.g., 'SPY')."""
        import yfinance as yf
        data = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if data.empty:
            raise ValueError(f"No yfinance data for ticker: {ticker}")
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        return cls(
            px_close=data["Close"],
            px_high=data["High"],
            px_low=data["Low"],
            **kwargs,
        )

    def __init__(
        self,
        px_close: pd.Series,
        px_high: Optional[pd.Series] = None,
        px_low: Optional[pd.Series] = None,
        # Trend filter
        ema_trend: int = 200,
        trend_break_pct: float = 0.03,
        # Entry thresholds
        entry_rsi: float = 10.0,
        entry_ibs: float = 0.4,
        bb_window: int = 20,
        bb_std: float = 2.0,
        # Exit
        sma_exit: int = 5,
        # Position sizing
        full_size: float = 0.50,
        half_size: float = 0.25,
    ) -> None:
        if not isinstance(px_close, pd.Series):
            raise TypeError("px_close must be a pandas Series.")
        if px_close.empty:
            raise ValueError("px_close cannot be empty.")
        if not pd.api.types.is_numeric_dtype(px_close):
            raise ValueError("px_close must contain numeric data.")

        self.px_close = px_close.astype(float).copy()
        self.px_high = (
            px_high if px_high is not None and not px_high.empty else px_close
        ).astype(float).copy()
        self.px_low = (
            px_low if px_low is not None and not px_low.empty else px_close
        ).astype(float).copy()

        # Parameters
        self.ema_trend = ema_trend
        self.trend_break_pct = trend_break_pct
        self.entry_rsi = entry_rsi
        self.entry_ibs = entry_ibs
        self.bb_window = bb_window
        self.bb_std_mult = bb_std
        self.sma_exit = sma_exit
        self.full_size = full_size
        self.half_size = half_size

        self._store: dict = {}
        self.df = pd.DataFrame()
        self._trades: list = []
        self._calculate_indicator()

    # ─── Indicators ──────────────────────────────────────────────────

    @property
    def ema200(self) -> pd.Series:
        if "ema200" not in self._store:
            self._store["ema200"] = self.px_close.ewm(
                span=self.ema_trend, adjust=False
            ).mean()
        return self._store["ema200"]

    @property
    def sma5(self) -> pd.Series:
        if "sma5" not in self._store:
            self._store["sma5"] = self.px_close.rolling(self.sma_exit).mean()
        return self._store["sma5"]

    @property
    def rsi2(self) -> pd.Series:
        """RSI(2) — ultra-short-term overbought/oversold."""
        if "rsi2" not in self._store:
            delta = self.px_close.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            ag = gain.ewm(alpha=1 / 2, min_periods=2, adjust=False).mean()
            al = loss.ewm(alpha=1 / 2, min_periods=2, adjust=False).mean()
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
    def bb_lower(self) -> pd.Series:
        """Lower Bollinger Band."""
        if "bb_lower" not in self._store:
            mid = self.px_close.rolling(self.bb_window).mean()
            std = self.px_close.rolling(self.bb_window).std()
            self._store["bb_lower"] = mid - self.bb_std_mult * std
        return self._store["bb_lower"]

    @property
    def trend_up(self) -> pd.Series:
        """Trend gate: price > EMA(200)."""
        if "trend_up" not in self._store:
            self._store["trend_up"] = self.px_close > self.ema200
        return self._store["trend_up"]

    # ─── Trade simulation ────────────────────────────────────────────

    @property
    def position(self) -> pd.Series:
        """Three-state position (0 / half_size / full_size), shifted 1 day."""
        if "position" not in self._store:
            self._run_simulation()
        return self._store["position"]

    @property
    def signal(self) -> pd.Series:
        """Raw signal state: 0 (flat), 1 (half), 2 (full)."""
        if "signal" not in self._store:
            self._run_simulation()
        return self._store["signal"]

    @property
    def trades(self) -> list:
        """List of trade dicts with entry/exit dates, returns, exit reasons."""
        if "position" not in self._store:
            self._run_simulation()
        return self._trades

    def _run_simulation(self) -> None:
        """Walk-forward trade simulation."""
        c = self.px_close
        rsi = self.rsi2
        ibs_v = self.ibs
        bb_lo = self.bb_lower
        ema = self.ema200
        sma = self.sma5

        n = len(c)
        pos = np.zeros(n)
        sig = np.zeros(n, dtype=int)
        trades = []

        in_trade = False
        trade_size = 0.0
        signal_state = 0
        entry_price = 0.0
        entry_date = None
        hold_days = 0

        warmup = max(self.ema_trend, 252)

        for i in range(warmup, n):
            if pd.isna(c.iloc[i]) or pd.isna(rsi.iloc[i]):
                if in_trade:
                    pos[i] = trade_size
                    sig[i] = signal_state
                continue

            price = c.iloc[i]

            if in_trade:
                hold_days += 1
                exit_reason = None

                # Exit: trend break (3% below EMA200)
                if price < ema.iloc[i] * (1 - self.trend_break_pct):
                    exit_reason = "trend_break"
                # Exit: profit target (close > SMA5)
                elif price > sma.iloc[i]:
                    exit_reason = "profit_target"

                if exit_reason:
                    trade_ret = (price / entry_price - 1) * trade_size
                    trades.append({
                        "entry_date": entry_date,
                        "exit_date": c.index[i],
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(price, 2),
                        "size": trade_size,
                        "signal": signal_state,
                        "return_pct": round(trade_ret * 100, 2),
                        "hold_days": hold_days,
                        "exit_reason": exit_reason,
                    })
                    in_trade = False
                    trade_size = 0.0
                    signal_state = 0
                    pos[i] = 0.0
                    sig[i] = 0
                else:
                    pos[i] = trade_size
                    sig[i] = signal_state
            else:
                # Only enter if trend is up
                if price <= ema.iloc[i]:
                    continue

                rsi_val = rsi.iloc[i]
                if rsi_val < self.entry_rsi:
                    # FULL: RSI oversold + below Bollinger Band
                    if price < bb_lo.iloc[i]:
                        trade_size = self.full_size
                        signal_state = 2
                    # HALF: RSI oversold + weak close (IBS)
                    elif ibs_v.iloc[i] < self.entry_ibs:
                        trade_size = self.half_size
                        signal_state = 1
                    else:
                        continue

                    in_trade = True
                    entry_price = price
                    entry_date = c.index[i]
                    hold_days = 0
                    pos[i] = trade_size
                    sig[i] = signal_state

        self._trades = trades
        pos_series = pd.Series(pos, index=c.index)
        sig_series = pd.Series(sig, index=c.index)
        self._store["position"] = pos_series.shift(1).fillna(0.0)
        self._store["signal"] = sig_series.shift(1).fillna(0).astype(int)

    # ─── Core compute ────────────────────────────────────────────────

    def _calculate_indicator(self) -> None:
        self.df = pd.DataFrame({
            "close": self.px_close,
            "ema200": self.ema200,
            "sma5": self.sma5,
            "rsi2": self.rsi2,
            "ibs": self.ibs,
            "bb_lower": self.bb_lower,
            "trend_up": self.trend_up,
            "signal": self.signal,
            "position": self.position,
        })

    # ─── Public helpers ──────────────────────────────────────────────

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

    def trade_log(self) -> pd.DataFrame:
        """Return trades as a DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)

    def backtest(self, cost_bps: float = 10.0) -> pd.DataFrame:
        """Run backtest with trading costs."""
        daily_ret = self.px_close.pct_change()
        pos = self.position
        start_idx = max(self.ema_trend, 252)
        valid = pos.iloc[start_idx:]
        if valid.empty:
            return pd.DataFrame()
        start = valid.index[0]

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
        """Compute performance statistics after trading costs."""
        bt = self.backtest(cost_bps=cost_bps)
        if bt.empty:
            return {}
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

        to = pos.diff().abs().sum() / 2 / (len(r) / 252)
        exp = pos.mean()

        # Trade stats
        tlog = self.trade_log()
        n_trades = len(tlog)
        if n_trades > 0:
            win_rate = (tlog["return_pct"] > 0).mean() * 100
            avg_win = tlog.loc[tlog["return_pct"] > 0, "return_pct"].mean() if (tlog["return_pct"] > 0).any() else 0
            avg_loss = tlog.loc[tlog["return_pct"] <= 0, "return_pct"].mean() if (tlog["return_pct"] <= 0).any() else 0
            avg_hold = tlog["hold_days"].mean()
            exit_reasons = tlog["exit_reason"].value_counts().to_dict()
        else:
            win_rate = avg_win = avg_loss = avg_hold = 0
            exit_reasons = {}

        return {
            "sharpe": round(sharpe, 3),
            "ann_return": round(ann * 100, 2),
            "bnh_return": round(bnh_ann * 100, 2),
            "max_drawdown": round(mdd * 100, 2),
            "volatility": round(vol * 100, 2),
            "calmar": round(calmar, 2),
            "exposure": round(exp * 100, 1),
            "turnover_per_year": round(to, 1),
            "years": round(len(r) / 252, 1),
            "total_trades": n_trades,
            "win_rate": round(win_rate, 1),
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
            "avg_hold_days": round(avg_hold, 1),
            "exit_reasons": exit_reasons,
        }

    # ─── Visualization ───────────────────────────────────────────────

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
        max_labels: int = 50,
    ) -> go.Figure:
        """
        3-panel chart:
        Row 1: Candlestick + EMA(200) + BB lower + trade markers
        Row 2: RSI(2) with entry threshold
        Row 3: Position (0 / half / full)
        """
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            return go.Figure()

        BG = "rgba(0,0,0,0)"
        GRID = "rgba(148,163,184,0.06)"
        FONT = dict(family="'Space Mono', monospace", size=10, color="#94a3b8")
        GREEN, RED, ACCENT, DIM = "#22c55e", "#ef5350", "#6382ff", "#555a6e"
        UP, DN = "#26a69a", "#ef5350"
        AMBER = "#f59e0b"

        idx = df.index
        c = df["close"]
        h = self.px_high.reindex(idx)
        lo = self.px_low.reindex(idx)
        o_prices = ((h + lo + c) / 3).shift(1).fillna(c)
        rsi = df["rsi2"]
        pos = df["position"]

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.60, 0.20, 0.20],
            vertical_spacing=0.008,
        )

        # ═══ ROW 1: OHLC + EMA200 + BB lower + trades ═══

        # Trend background
        trend_bull = df["trend_up"]
        regime_changed = trend_bull != trend_bull.shift(1)
        segment_id = regime_changed.cumsum()
        valid = trend_bull.dropna()
        for _, seg in valid.groupby(segment_id.reindex(valid.index)):
            is_bull = seg.iloc[0]
            x0, x1 = seg.index[0], seg.index[-1]
            color = "rgba(34,197,94,0.05)" if is_bull else "rgba(239,83,80,0.05)"
            fig.add_vrect(
                x0=x0, x1=x1, fillcolor=color,
                layer="below", line_width=0, row=1, col=1,
            )

        # EMA(200)
        fig.add_trace(go.Scatter(
            x=idx, y=df["ema200"], mode="lines", name="EMA 200",
            line=dict(color="rgba(245,158,11,0.5)", width=1),
            hoverinfo="skip",
        ), row=1, col=1)

        # SMA(5)
        fig.add_trace(go.Scatter(
            x=idx, y=df["sma5"], mode="lines", name="SMA 5",
            line=dict(color="rgba(148,163,184,0.3)", width=0.8, dash="dot"),
            hoverinfo="skip",
        ), row=1, col=1)

        # BB lower
        fig.add_trace(go.Scatter(
            x=idx, y=df["bb_lower"], mode="lines", name="BB Lower",
            line=dict(color="rgba(239,83,80,0.3)", width=0.8, dash="dash"),
            hoverinfo="skip",
        ), row=1, col=1)

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=idx, open=o_prices, high=h, low=lo, close=c,
            increasing=dict(line=dict(color=UP, width=0.8), fillcolor=UP),
            decreasing=dict(line=dict(color=DN, width=0.8), fillcolor=DN),
            showlegend=False, name="OHLC",
        ), row=1, col=1)

        # Trade markers
        tlog = self.trade_log()
        if not tlog.empty:
            start_ts = idx[0] if start is None else pd.Timestamp(start)
            end_ts = idx[-1] if end is None else pd.Timestamp(end)
            visible = tlog[
                (tlog["entry_date"] >= start_ts) & (tlog["entry_date"] <= end_ts)
            ].tail(max_labels)

            if len(visible) > 0:
                # Entries — green (full) or blue (half)
                for _, t in visible.iterrows():
                    clr = GREEN if t["signal"] == 2 else ACCENT
                    sym = "triangle-up"
                    label = "FULL" if t["signal"] == 2 else "HALF"
                    fig.add_trace(go.Scatter(
                        x=[t["entry_date"]],
                        y=[t["entry_price"] * 0.996],
                        mode="markers", showlegend=False,
                        marker=dict(symbol=sym, size=8, color=clr,
                                    line=dict(width=0.5, color=clr)),
                        hovertemplate=(
                            f"%{{x|%Y-%m-%d}}<br>BUY {label} $%{{y:,.2f}}"
                            "<extra></extra>"
                        ),
                    ), row=1, col=1)

                # Exits
                exit_colors = {
                    "profit_target": GREEN,
                    "trend_break": RED,
                }
                for _, t in visible.iterrows():
                    clr = exit_colors.get(t["exit_reason"], DIM)
                    fig.add_trace(go.Scatter(
                        x=[t["exit_date"]],
                        y=[t["exit_price"] * 1.004],
                        mode="markers", showlegend=False,
                        marker=dict(symbol="triangle-down", size=8, color=clr,
                                    line=dict(width=0.5, color=clr)),
                        hovertemplate=(
                            f"%{{x|%Y-%m-%d}}<br>EXIT $%{{y:,.2f}}"
                            f"<br>{t['exit_reason']} ({t['return_pct']:+.1f}%)"
                            "<extra></extra>"
                        ),
                    ), row=1, col=1)

        # ═══ ROW 2: RSI(2) ═══

        fig.add_trace(go.Scatter(
            x=idx, y=rsi, mode="lines", name="RSI(2)",
            line=dict(color=ACCENT, width=1.2),
        ), row=2, col=1)
        fig.add_hline(y=self.entry_rsi, line_dash="dot",
                       line_color="rgba(34,197,94,0.5)", line_width=0.8,
                       row=2, col=1,
                       annotation_text=f"Entry < {self.entry_rsi:.0f}",
                       annotation_position="bottom right",
                       annotation_font=dict(size=8, color=DIM))

        # ═══ ROW 3: POSITION ═══

        fig.add_trace(go.Scatter(
            x=idx, y=pos * 100, mode="none", fill="tozeroy",
            fillcolor="rgba(99,130,255,0.12)",
            showlegend=False, hoverinfo="skip",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=pos * 100, mode="lines", name="Weight",
            line=dict(color=ACCENT, width=1.5, shape="hv"),
        ), row=3, col=1)
        fig.add_hline(y=self.full_size * 100, line_dash="dot",
                       line_color="rgba(34,197,94,0.3)", line_width=0.5,
                       row=3, col=1)
        fig.add_hline(y=self.half_size * 100, line_dash="dot",
                       line_color="rgba(99,130,255,0.3)", line_width=0.5,
                       row=3, col=1)

        # ═══ LAYOUT ═══

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=FONT, height=750,
            margin=dict(l=0, r=8, t=8, b=0),
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.01,
                xanchor="right", x=1,
                font=dict(size=9, color="#94a3b8"), bgcolor=BG,
            ),
            xaxis_rangeslider_visible=False,
            xaxis2_rangeslider_visible=False,
            xaxis3_rangeslider_visible=False,
        )

        for row in [1, 2, 3]:
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

        fig.update_yaxes(row=2, col=1, range=[-5, 105],
                         tickvals=[0, 10, 50, 100])
        full_pct = int(self.full_size * 100)
        half_pct = int(self.half_size * 100)
        fig.update_yaxes(
            row=3, col=1, range=[-3, full_pct + 10],
            tickvals=[0, half_pct, full_pct],
            ticktext=["0%", f"{half_pct}%", f"{full_pct}%"],
        )
        fig.update_xaxes(showticklabels=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, row=2, col=1)

        fig.add_annotation(
            text="SWING TRADES", x=0.005, y=0.99,
            xref="paper", yref="paper", xanchor="left", showarrow=False,
            font=dict(size=10, color="#94a3b8", family="'Space Mono', monospace"),
        )
        fig.add_annotation(
            text="RSI(2)", x=0.005, y=0.37,
            xref="paper", yref="paper", xanchor="left", showarrow=False,
            font=dict(size=8, color=ACCENT, family="'Space Mono', monospace"),
        )
        fig.add_annotation(
            text="POSITION", x=0.005, y=0.17,
            xref="paper", yref="paper", xanchor="left", showarrow=False,
            font=dict(size=8, color=ACCENT, family="'Space Mono', monospace"),
        )

        return fig
