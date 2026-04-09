import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Auto_VolRegime(Strategy):
    """Volatility Regime Allocation: VIX term structure + VIX stress level.

    Source: CBOE VIX term structure research, Quantpedia "Exploiting Term
            Structure of VIX Futures", AQR "Understanding the Volatility
            Risk Premium" (2018).
    Mode: auto (novel — no volatility-based strategies in existing library)
    Built: 2026-03-29 by ix-strategy-builder

    Data mapping: 6 exact, 0 proxy

    | Research Concept     | Implementation           | Match |
    |---------------------|--------------------------|-------|
    | VIX Spot            | VIX INDEX:PX_LAST        | Exact |
    | VIX 3-Month         | VIX3M INDEX:PX_LAST      | Exact |
    | US Equities         | SPY US EQUITY:PX_LAST    | Exact |
    | US Bonds            | IEF US EQUITY:PX_LAST    | Exact |
    | Gold                | GLD US EQUITY:PX_LAST    | Exact |
    | Cash / T-bills      | BIL US EQUITY:PX_LAST    | Exact |

    Rules:
    - Signal 1: VIX term structure = VIX / VIX3M
      Contango (< 1.0) = normal/calm. Backwardation (>= 1.0) = stress.
      VIX in contango 89% of the time; backwardation is rare but severe.
    - Signal 2: VIX absolute level (>= 30 = acute stress even in contango)
    - 3 regimes:
      Risk-On  (contango + VIX < 30)     → 100% SPY
      Cautious (contango + VIX >= 30)    → 50% SPY, 30% IEF, 10% GLD, 10% BIL
      Defensive (backwardation)          → 10% SPY, 40% IEF, 30% GLD, 20% BIL
    """


    label = "Vol Regime"
    family = "volatility"
    mode = "auto"
    description = "Uses VIX/VIX3M term structure ratio and absolute VIX level. VIX backwardation (VIX > VIX3M) or VIX > 30 → defensive: 20% SPY + 40% IEF + 20% GLD + 20% BIL. VIX contango + VIX < 20 → risk-on: 90% SPY + 10% GLD. Otherwise → mixed: 60% SPY + 25% IEF + 15% BIL."
    author = "CBOE / AQR"

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
        "BIL": {"code": "BIL US EQUITY:PX_LAST", "weight": 0.0},
    }

    bm_assets: dict[str, float] = {"SPY": 0.5, "IEF": 0.5}
    start = pd.Timestamp("2007-06-01")  # VIX3M from 2006-07, BIL from 2007-05
    frequency = "ME"
    commission = 15
    slippage = 5

    # Tunable parameters (2 — intentionally simple)
    BACKWARDATION_THRESHOLD = 1.0   # VIX/VIX3M above this = backwardation
    VIX_STRESS_LEVEL = 30           # VIX above this = stressed even in contango

    # Regime allocations
    REGIMES = {
        "risk_on":   {"SPY": 1.00, "IEF": 0.00, "GLD": 0.00, "BIL": 0.00},
        "cautious":  {"SPY": 0.50, "IEF": 0.30, "GLD": 0.10, "BIL": 0.10},
        "defensive": {"SPY": 0.10, "IEF": 0.40, "GLD": 0.30, "BIL": 0.20},
    }

    def initialize(self) -> None:
        # VIX and VIX3M for term structure
        self._vix = Series("VIX INDEX:PX_LAST")
        self._vix3m = Series("VIX3M INDEX:PX_LAST")

        # Pre-compute term structure ratio
        if not self._vix.empty and not self._vix3m.empty:
            aligned = pd.concat([self._vix, self._vix3m], axis=1).dropna()
            self._ts_ratio = aligned.iloc[:, 0] / aligned.iloc[:, 1]
        else:
            self._ts_ratio = pd.Series(dtype=float)

    def _classify_regime(self) -> str:
        """Classify current volatility regime from term structure and VIX level."""
        ts_hist = self._ts_ratio.loc[:self.d]
        if len(ts_hist) == 0:
            return "risk_on"
        ts_now = ts_hist.iloc[-1]

        if pd.isna(ts_now):
            return "risk_on"

        # Backwardation → always defensive
        if ts_now >= self.BACKWARDATION_THRESHOLD:
            return "defensive"

        # Contango — check absolute VIX level for stress
        vix_hist = self._vix.loc[:self.d]
        if len(vix_hist) > 0:
            vix_now = vix_hist.iloc[-1]
            if pd.notna(vix_now) and vix_now >= self.VIX_STRESS_LEVEL:
                return "cautious"

        return "risk_on"

    def generate_signals(self) -> pd.Series:
        regime = self._classify_regime()
        return pd.Series(self.REGIMES[regime])

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "CBOE + Quantpedia + AQR VRP research",
            "mode": "auto",
            "backwardation_threshold": self.BACKWARDATION_THRESHOLD,
            "vix_stress_level": self.VIX_STRESS_LEVEL,
        }


# ------------------------------------------------------------------
# SB_Auto_EnsembleTrend — Auto-discovered (ix-strategy-builder)
# ------------------------------------------------------------------
