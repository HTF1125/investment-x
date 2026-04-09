"""LaborRegime — 2-state labor market cycle regime.

Thesis
------
The labor market is the single most reliable late-cycle timing signal
in the US macro dataset. The Sahm Rule — triggered when the 3-month
average unemployment rate rises 0.5 percentage points above its
trailing 12-month low — has a 100% hit rate on NBER-dated recessions
since 1950. The 4-week initial claims trend provides the higher-
frequency leading edge.

This regime is *deliberately slow*. It does not exist to time the
next 3-week move; it exists to tell the rest of the system "we are
entering a labor-driven recession window." When paired with a
fast-moving growth or positioning axis in a 2-axis composite, it
gates out the false positives that purely short-term signals generate
near cycle tops.

**Orthogonality vs existing Growth axis:** Growth includes claims
already, so ρ is expected to be moderately high (~0.5). What Labor
adds: the Sahm rule non-linearity, the unemployment rate trend, and
labor force participation — all of which Growth does NOT include.
The orthogonality bar (|ρ| ≤ 0.60) should hold; verify post-build.

States
------
- **Tight**          (Labor_Z > +0.5σ): Unemployment low and falling,
  claims falling, Sahm = 0. Peak-cycle conditions. Forward SPY 3m:
  average to modestly negative (already-priced environment).
- **Deteriorating**  (Labor_Z ≤ +0.5σ): Unemployment rising or Sahm
  triggered, claims rising. Recession window. Forward SPY 3m: negative,
  fat left tail. This is the actionable state.

Indicators (4, all lb_*)
    lb_Claims4WMA   — Initial claims, 4-week moving average (FRED ICSA)
    lb_UE_Trend     — Unemployment rate, 3-month vs 12-month (Sahm proxy)
    lb_UE_Level     — Unemployment rate, level z-score (context)
    lb_LFPR         — Labor force participation rate (structural)

Publication lag: Claims 1 week, UNRATE 1 month, LFPR 1 month.
Target: SPY 3M fwd. Locked.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class LaborRegime(Regime):
    """2-state labor market cycle regime (Tight × Deteriorating)."""

    name = "Labor"
    dimensions = ["Labor"]
    states = ["Tight", "Deteriorating"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. lb_Claims4WMA — Initial jobless claims, 4-week MA. Inverted
        #    sign: falling claims = tight labor market = positive z.
        claims = _load("ICSA")
        if not claims.empty:
            claims_4w = claims.rolling(4).mean()
            rows["lb_Claims4WMA"] = zscore(-claims_4w, z_window).rename("lb_Claims4WMA")

        # 2. lb_UE_Trend — Sahm rule proxy. 3-month average unemployment
        #    MINUS 12-month trailing minimum. When this goes above 0.5 the
        #    Sahm rule has triggered. Inverted: rising Sahm measure =
        #    deteriorating labor market = negative z.
        ue = _load("UNRATE", lag=1)  # 1-month publication lag
        if not ue.empty:
            ue_3m = ue.rolling(3).mean()
            ue_12m_min = ue.rolling(12).min()
            sahm = ue_3m - ue_12m_min
            rows["lb_UE_Trend"] = zscore(-sahm, z_window).rename("lb_UE_Trend")

        # 3. lb_UE_Level — raw unemployment rate, INVERTED. Low level =
        #    tight labor = positive z.
        if not ue.empty:
            rows["lb_UE_Level"] = zscore(-ue, z_window).rename("lb_UE_Level")

        # 4. lb_LFPR — labor force participation rate. Rising LFPR =
        #    workers re-entering = strong labor market.
        lfpr = _load("CIVPART", lag=1)
        if not lfpr.empty:
            rows["lb_LFPR"] = zscore(lfpr, z_window).rename("lb_LFPR")

        if not rows:
            log.warning(
                "Labor: no indicators loaded. Seed ICSA / UNRATE / CIVPART "
                "from FRED."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Labor": "lb_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Labor composite probability to 2 states.

        Tight          = claims low, UE low, Sahm = 0, LFPR rising.
        Deteriorating  = claims rising, UE rising, Sahm triggered.
        Coincident mapping — Deteriorating state has strongly negative
        forward returns historically (every recession since 1950).
        """
        lp = dim_probs["Labor"]
        return {
            "P_Tight":         lp,
            "P_Deteriorating": 1.0 - lp,
        }
