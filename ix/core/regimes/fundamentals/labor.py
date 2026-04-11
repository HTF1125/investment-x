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

Indicators (2, all lb_*). 2026-04-12 rebuild after triage flagged
the previous 2-indicator set as WEAK_INDICATORS (both below the
|IC| ≥ 0.03 floor). New set uses JOLTS quits rate as the primary
cycle-peak signal and U6 acceleration as the cycle-trough complement:

    lb_JOLTS_Quits — JOLTS quits rate, 12M diff. Post-2010 |IC| 0.286
                     on SPY 6M fwd (strong). High quits = workers
                     confident = tight labor = late cycle. Negative
                     IC sign correctly identifies late-cycle peak as
                     bearish for forward returns (mean reversion).
    lb_U6_Accel    — U6 unemployment (broader than UNRATE), 3M diff
                     of 12M change, INVERTED. Captures cycle-trough
                     recoveries: positive z = U6 decelerating/falling
                     = labor improving = bullish at lows. Weaker than
                     JOLTS (|IC| 0.042) but orthogonal channel.

Publication lag: JOLTS + U6 both ~1 month reporting lag.
Target: SPY 6M fwd.
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

        # lb_JOLTS_Quits — JOLTS quits rate (JTSQUR), 12M diff. High quits
        # rate = workers confident enough to leave for better jobs = tight
        # labor market = late cycle. Atlanta Fed-cited leading indicator
        # of labor tightness turning points. 303 obs from 2000-12. The
        # composite IC on SPY 6M is NEGATIVE (-0.286) because peak labor
        # tightness is historically bearish for 6-month forward returns
        # via the mean-reversion / late-cycle-peak channel.
        quits = _load("JTSQUR", lag=1)
        if not quits.empty:
            rows["lb_JOLTS_Quits"] = zscore(quits.diff(12), z_window).rename(
                "lb_JOLTS_Quits"
            )

        # lb_U6_Accel — U6 broader unemployment rate, 3M diff of 12M diff,
        # INVERTED. U6 includes discouraged + marginally attached workers
        # and captures labor slack that UNRATE misses. Acceleration of
        # the 12M change is an early warning: U6 going from improving to
        # deteriorating flips sign 6-12M before the NBER recession call.
        # INVERTED so positive z = U6 improving = labor recovering from
        # trough = bullish forward return at the cycle low. 386 obs.
        u6 = _load("U6RATE", lag=1)
        if not u6.empty:
            u6_yoy = u6.diff(12)
            u6_accel = u6_yoy.diff(3)
            rows["lb_U6_Accel"] = zscore(-u6_accel, z_window).rename(
                "lb_U6_Accel"
            )

        # [DROPPED 2026-04-12: lb_NFPAccel — post-2010 IC +0.006 on SPY 6M
        #  (effectively noise) AND collinear with lb_U6_Accel at r=+0.89.
        #  Both of those are bad on their own; in combination they just
        #  double-count the same slack-improvement signal without adding
        #  information.]
        # [DROPPED 2026-04-12: lb_HiresRate — post-2010 IC -0.072 on
        #  SPY 6M, sign flipped from the original docstring's claimed
        #  +0.022. Replaced with lb_JOLTS_Quits above which measures a
        #  related but cleaner labor-tightness signal.]
        # [DROPPED earlier: lb_Claims4WMA / lb_UE_Trend / lb_UE_Level /
        #  lb_LFPR — see git history for per-indicator rationale.]

        if not rows:
            log.warning(
                "Labor: no indicators loaded. Expected DB codes: "
                "'JTSQUR', 'U6RATE'."
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
