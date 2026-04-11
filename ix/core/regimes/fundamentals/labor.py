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

        # [DROPPED: lb_Claims4WMA — post IC -0.111 (DYING). Full IC +0.011.
        #  Claims 4WMA is too noisy as a standalone labor indicator for SPY.
        #  Claims data is covered by GrowthRegime monitor-only channel.]

        # [DROPPED: lb_UE_Trend — post IC -0.099 (DYING). Full IC +0.003.
        #  The Sahm proxy only fires 1-2x per decade and the single post-2010
        #  firing (COVID 2020) was a V-recovery with strong forward returns,
        #  inverting the expected signal. Replaced by lb_HiresRate which
        #  has more granular cycle information.]

        # [DROPPED: lb_UE_Level — post IC -0.096 (DYING). Full IC +0.013.
        #  Raw unemployment level is too slow-moving and has structural
        #  drift (COVID spike distorted the rolling z-score).]

        # [DROPPED: lb_LFPR — post IC -0.012 (DYING). Full IC +0.027.
        #  LFPR has a multi-decade secular decline that overwhelms the
        #  cyclical signal. Not reliably predictive for SPY 3M.]

        # 1. lb_HiresRate — JOLTS hires rate, 12M diff. Rising hires =
        #    expanding labor demand. Pre IC +0.018, post IC +0.022 — both
        #    positive across subsamples unlike claims/UE/LFPR.
        hires = _load("JTSHIR", lag=1)
        if not hires.empty:
            rows["lb_HiresRate"] = zscore(hires.diff(12), z_window).rename(
                "lb_HiresRate"
            )

        # 2. lb_NFPAccel — Payrolls acceleration (3M diff of 12M YoY).
        #    Captures whether job growth is accelerating or decelerating.
        #    Pre IC +0.076, post IC +0.087 — strong and stable.
        #    Unlike raw payrolls level (which has structural drift),
        #    the acceleration signal is cycle-neutral.
        nfp = _load("PAYEMS", lag=1)
        if not nfp.empty:
            nfp_yoy = nfp.pct_change(12, fill_method=None) * 100
            nfp_accel = nfp_yoy.diff(3)
            rows["lb_NFPAccel"] = zscore(nfp_accel, z_window).rename(
                "lb_NFPAccel"
            )

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
