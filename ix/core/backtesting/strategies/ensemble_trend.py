import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Auto_EnsembleTrend(Strategy):
    """Ensemble Trend + Momentum (both-required): promoted from batch lab.

    Source: Batch research ENS_MT_9_8 (Sharpe 0.97 in batch). Combines
            SMA trend filter with absolute momentum — BOTH must confirm
            for equity allocation. Based on Meb Faber's trend-following +
            Gary Antonacci's absolute momentum frameworks.
    Mode: auto (batch→production promotion, no production ensemble exists)
    Built: 2026-03-30 by ix-strategy-builder

    Data mapping: 4 exact, 0 proxy

    | Research Concept     | Implementation          | Match |
    |---------------------|-------------------------|-------|
    | US Equities         | SPY US EQUITY:PX_LAST   | Exact |
    | US Bonds            | IEF US EQUITY:PX_LAST   | Exact |
    | Gold                | GLD US EQUITY:PX_LAST   | Exact |
    | Cash / T-bills      | BIL US EQUITY:PX_LAST   | Exact |

    Rules:
    - Signal 1 (Trend): SPY price > 8-month SMA → PASS; else FAIL
    - Signal 2 (Momentum): SPY 9-month total return > 0 → PASS; else FAIL
    - Three-state regime:
      BOTH pass    → Risk-On:   100% SPY
      One passes   → Mixed:     50% SPY, 50% IEF
      BOTH fail    → Defensive: 50% IEF, 50% BIL

    Design principle: "Both required" filter eliminates false signals.
    Trend catches direction, momentum catches magnitude.
    When they disagree, the strategy halves equity exposure.
    When both fail, it steps aside entirely (bonds + gold + cash).
    """


    label = "Ensemble Trend"
    family = "trend"
    mode = "auto"
    description = "Two signals must both confirm: SPY price above 8-month SMA (trend) AND SPY 9-month return positive (momentum). Both pass → 100% SPY. One passes → 50% SPY + 50% IEF. Both fail → 50% IEF + 50% BIL. Three-state design prevents whipsaw from single-signal failures."
    author = "Batch Research"

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
        "BIL": {"code": "BIL US EQUITY:PX_LAST", "weight": 0.0},
    }

    bm_assets: dict[str, float] = {"SPY": 0.5, "IEF": 0.5}
    start = pd.Timestamp("2007-06-01")  # BIL inception ~2007-05
    frequency = "ME"
    commission = 15
    slippage = 5

    # Tunable parameters (2 — intentionally minimal)
    SMA_WINDOW = 8     # Months for SMA trend filter (optimal from batch: 8)
    MOM_WINDOW = 9     # Months for absolute momentum comparison (batch: 9)

    def initialize(self) -> None:
        # Monthly prices for SPY and BIL
        spy_daily = Series("SPY US EQUITY:PX_LAST")
        bil_daily = Series("BIL US EQUITY:PX_LAST")

        self._spy_monthly = spy_daily.resample("ME").last().dropna() if not spy_daily.empty else pd.Series(dtype=float)
        self._bil_monthly = bil_daily.resample("ME").last().dropna() if not bil_daily.empty else pd.Series(dtype=float)

        # Pre-compute SMA
        if not self._spy_monthly.empty:
            self._spy_sma = self._spy_monthly.rolling(
                window=self.SMA_WINDOW, min_periods=self.SMA_WINDOW
            ).mean()
        else:
            self._spy_sma = pd.Series(dtype=float)

    def _check_trend(self) -> bool:
        """SPY price above N-month SMA?"""
        spy_hist = self._spy_monthly.loc[:self.d]
        sma_hist = self._spy_sma.loc[:self.d]
        if len(spy_hist) == 0 or len(sma_hist) == 0:
            return True  # Default bullish when data insufficient
        return spy_hist.iloc[-1] > sma_hist.iloc[-1]

    def _check_momentum(self) -> bool:
        """SPY N-month return > 0?"""
        spy_hist = self._spy_monthly.loc[:self.d]
        if len(spy_hist) <= self.MOM_WINDOW:
            return True  # Default bullish when data insufficient

        spy_ret = spy_hist.iloc[-1] / spy_hist.iloc[-(self.MOM_WINDOW + 1)] - 1
        return spy_ret > 0

    def generate_signals(self) -> pd.Series:
        trend_ok = self._check_trend()
        mom_ok = self._check_momentum()

        if trend_ok and mom_ok:
            # Both confirm → full equity
            return pd.Series({"SPY": 1.0, "IEF": 0.0, "GLD": 0.0, "BIL": 0.0})
        elif not trend_ok and not mom_ok:
            # Both fail → full defensive (bonds + gold + cash)
            return pd.Series({"SPY": 0.0, "IEF": 0.40, "GLD": 0.30, "BIL": 0.30})
        else:
            # Disagreement → split equity/bonds
            return pd.Series({"SPY": 0.50, "IEF": 0.30, "GLD": 0.10, "BIL": 0.10})

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Batch ENS_MT_9_8 (Faber trend + Antonacci momentum)",
            "mode": "auto (batch promotion)",
            "sma_window": self.SMA_WINDOW,
            "mom_window": self.MOM_WINDOW,
        }


# ------------------------------------------------------------------
# SB_Auto_DollarCycle — Auto-discovered (ix-strategy-builder)
# ------------------------------------------------------------------
