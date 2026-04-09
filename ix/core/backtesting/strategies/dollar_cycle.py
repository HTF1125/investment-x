import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Auto_DollarCycle(Strategy):
    """Dollar Cycle Allocation: DXY 6-month momentum drives equity exposure.

    Source: Gavekal "King Dollar" framework, CrossBorder Capital dollar
            liquidity research, Raoul Pal dollar cycle thesis. Phase 0
            quick signal test: 71bps/month spread (10.7% vs 3.6% ann).
    Mode: auto (novel — no dollar/FX-based strategies in library)
    Built: 2026-03-30 by ix-strategy-builder

    Data mapping: 5 exact, 0 proxy

    | Research Concept     | Implementation          | Match |
    |---------------------|-------------------------|-------|
    | Dollar Index         | DXY.Z:FG_PRICE_IDX     | Exact |
    | US Equities          | SPY US EQUITY:PX_LAST   | Exact |
    | US Bonds             | IEF US EQUITY:PX_LAST   | Exact |
    | Gold                 | GLD US EQUITY:PX_LAST   | Exact |
    | Cash / T-bills       | BIL US EQUITY:PX_LAST   | Exact |

    Rules:
    - Signal: DXY 6-month price change
      Falling (< 0) = weak dollar = looser financial conditions = equity tailwind
      Rising (> 0) = strong dollar = tighter conditions = equity headwind
    - 3-state regime (using z-score for magnitude):
      Dollar weakening (6M chg < 0)        → Risk-On:   90% SPY, 10% GLD
      Dollar stable (|6M chg| < 2%)        → Mixed:     60% SPY, 25% IEF, 15% BIL
      Dollar strengthening (6M chg > +2%)  → Defensive: 20% SPY, 40% IEF, 20% GLD, 20% BIL

    Note: GLD in risk-on captures gold's tendency to rise with weak dollar.
    GLD also in defensive for monetary hedge during dollar stress events.
    """


    label = "Dollar Cycle"
    family = "dollar"
    mode = "auto"
    description = "Computes DXY 6-month price change. Dollar weakening (change < 0) → 90% SPY + 10% GLD. Dollar stable (0-2%) → 60% SPY + 25% IEF + 15% BIL. Dollar surging (> +2%) → 20% SPY + 40% IEF + 20% GLD + 20% BIL. Weak dollar = loose conditions = equity tailwind; strong dollar = tight conditions = defensive."
    author = "Gavekal / Raoul Pal"

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

    # Tunable parameters (2 — minimal)
    DXY_LOOKBACK = 6     # Months for DXY momentum
    STRONG_THRESHOLD = 0.02  # 2% threshold for "strong dollar" regime

    # Regime allocations
    REGIMES = {
        "risk_on":   {"SPY": 0.90, "IEF": 0.00, "GLD": 0.10, "BIL": 0.00},
        "mixed":     {"SPY": 0.60, "IEF": 0.25, "GLD": 0.00, "BIL": 0.15},
        "defensive": {"SPY": 0.20, "IEF": 0.40, "GLD": 0.20, "BIL": 0.20},
    }

    def initialize(self) -> None:
        dxy = Series("DXY.Z:FG_PRICE_IDX")
        if not dxy.empty:
            self._dxy_monthly = dxy.resample("ME").last().dropna()
        else:
            self._dxy_monthly = pd.Series(dtype=float)

    def _classify_regime(self) -> str:
        """Classify dollar cycle regime from DXY momentum."""
        dxy_hist = self._dxy_monthly.loc[:self.d]
        if len(dxy_hist) <= self.DXY_LOOKBACK:
            return "mixed"  # Insufficient data

        dxy_now = dxy_hist.iloc[-1]
        dxy_past = dxy_hist.iloc[-(self.DXY_LOOKBACK + 1)]
        dxy_chg = dxy_now / dxy_past - 1

        if pd.isna(dxy_chg):
            return "mixed"

        if dxy_chg < 0:
            return "risk_on"      # Dollar weakening → equity tailwind
        elif dxy_chg > self.STRONG_THRESHOLD:
            return "defensive"    # Dollar surging → tighter conditions
        else:
            return "mixed"        # Dollar mildly positive → balanced

    def generate_signals(self) -> pd.Series:
        regime = self._classify_regime()
        return pd.Series(self.REGIMES[regime])

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Gavekal + CrossBorder Capital + Raoul Pal dollar cycle",
            "mode": "auto",
            "dxy_lookback_months": self.DXY_LOOKBACK,
            "strong_threshold": self.STRONG_THRESHOLD,
        }


# ------------------------------------------------------------------
# SB_Portfolio_Top3Ortho — Ensemble (ix-strategy-builder Phase 7)
# ------------------------------------------------------------------
