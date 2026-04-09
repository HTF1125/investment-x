import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Consensus_MacroTrend(Strategy):
    """Macro Trend Composite: ISM momentum + price trend for equity/bond allocation.

    Source: Synthesized from (1) S&P Global / QuantifiedStrategies ISM
            momentum research, (2) Faber 10-month SMA trend-following,
            (3) Quantpedia bear market avoidance series.
    Mode: synthesize
    Built: 2026-03-28 by ix-strategy-builder
    Data mapping: 3 exact, 1 exact (macro indicator), 0 proxy

    Rules:
    - Signal 1 (macro): ISM Manufacturing PMI 3-month MA direction
      (rising = expansionary momentum, falling = contractionary)
    - Signal 2 (trend): SPY price > 10-month SMA
    - Both positive → 100% SPY (risk-on)
    - Mixed signals → 50% SPY, 50% IEF (balanced/neutral)
    - Both negative → 100% IEF (risk-off, bonds)
    - ISM shifted 7 days for publication lag (1 week).
    """


    label = "Macro Trend"
    family = "macro"
    mode = "synthesize"
    description = "Two binary signals: ISM Manufacturing PMI 3-month MA direction (rising = expansionary) and SPY price vs 10-month SMA (above = uptrend). Both positive → 100% SPY. Mixed → 50% SPY + 50% IEF. Both negative → 100% IEF. ISM lagged 1 month for publication delay."
    author = "Consensus"

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
    }

    bm_assets: dict[str, float] = {"SPY": 0.5, "IEF": 0.5}
    start = pd.Timestamp("2003-01-01")
    frequency = "ME"
    commission = 15
    slippage = 5

    ISM_MA_WINDOW = 3  # 3-month moving average of ISM
    SMA_DAYS = 210     # ~10-month SMA

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self._prices = prices

        # SPY 10-month SMA
        self._sma = prices["SPY"].rolling(window=self.SMA_DAYS, min_periods=180).mean()

        # ISM Manufacturing PMI — load from FactSet
        ism_raw = Series("ISMPMI_M:PX_LAST")
        # Publication lag: ISM released ~1 week after month end
        self._ism = ism_raw.shift(1)  # Shift 1 period (monthly data, so 1 month conservative)
        # 3-month moving average of ISM
        self._ism_ma = self._ism.rolling(window=self.ISM_MA_WINDOW, min_periods=2).mean()

    def generate_signals(self) -> pd.Series:
        if self.d not in self._prices.index:
            return pd.Series({"SPY": 0.5, "IEF": 0.5})

        # Signal 1: ISM momentum (3-month MA rising)
        ism_now = self._ism_ma.asof(self.d)
        ism_prev = self._ism_ma.shift(1).asof(self.d) if len(self._ism_ma) > 1 else float("nan")
        ism_rising = (
            pd.notna(ism_now) and pd.notna(ism_prev) and ism_now > ism_prev
        )

        # Signal 2: SPY trend (price > 10-month SMA)
        spy_px = self._prices["SPY"].asof(self.d)
        spy_sma = self._sma.asof(self.d)
        trend_up = (
            pd.notna(spy_px) and pd.notna(spy_sma) and spy_px > spy_sma
        )

        # Binary regime allocation
        if ism_rising and trend_up:
            return pd.Series({"SPY": 1.0, "IEF": 0.0})  # Risk-on
        elif ism_rising or trend_up:
            return pd.Series({"SPY": 0.5, "IEF": 0.5})  # Mixed/neutral
        else:
            return pd.Series({"SPY": 0.0, "IEF": 1.0})  # Risk-off

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Synthesized: ISM momentum + Faber trend",
            "mode": "synthesize",
            "ism_ma_window": self.ISM_MA_WINDOW,
            "sma_days": self.SMA_DAYS,
        }


# ------------------------------------------------------------------
# SB_Auto_CreditCycle — Auto-discovered (ix-strategy-builder)
# ------------------------------------------------------------------
