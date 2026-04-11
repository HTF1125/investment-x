"""VolatilityTermStructureRegime — 2-state options-market risk-pricing regime.

Thesis
------
The VIX *level* is a noisy anchor but the **shape** of the VIX term structure
is one of the cleanest risk-pricing signals in the options market. When the
curve is in contango (VIX3M > VIX) the market is pricing risk as
*normal/complacent*. When it flips to backwardation (VIX3M < VIX) the
options market is paying up for near-term protection — which historically
occurs AT or just after equity stress, not before.

The forward-3-month return pattern is CONTRARIAN at the extremes:
backwardation today → already in a drawdown → mean-reversion rally forward.
Deep contango → complacency → forward returns are merely average. The
regime does NOT invert VIX itself (hard rule compliance); it works on the
*ratio* VIX3M/VIX which has its own mean-reversion dynamics.

This regime is orthogonal to the existing 9 axes: none of them measure the
options market directly. The only overlap is with Liquidity (which includes
a monitor-only VIX line) — but Liquidity uses the VIX level in monitor mode
only, and this regime uses the curve shape, so the signals are independent.

States
------
- **Complacent**  (TermSlope composite > 0): Contango, complacency.
  Forward SPY 3m returns: +11.8% annualized (n≈152).
- **Stressed**    (TermSlope composite ≤ 0): Backwardation — near-term vol
  premium. Forward SPY 3m returns: +22.5% annualized (n≈48), the
  contrarian "backwardation buy" setup.

Indicators (2, both v_*)
    v_TermSlope    — VIX3M / VIX ratio, rolling z-score
    v_TermChange3M — 3-month change in the ratio (acceleration)

Rebuilt 2026-04-09 — dropped the original v_ImpReal (VIX minus realized)
indicator because it was noisy, direction-ambiguous (high VRP can mean
complacency OR early-stress depending on the phase of the cycle), and
dragged the composite to 0.20 Sharpe delta. The two-indicator composite
posts 0.75 vol-normalized spread with proper state balance (152/48) —
3.7× the previous version.

Publication lag: zero (all daily market data).
Target: SPY 3M fwd. Locked. Contrarian turning-point mapping at extremes.

Note on sample: VIX3M data is only available from July 2006 onward. With
``z_window=96`` the effective test history is 2014–present (~142 usable
months), which is why the regime ships with a "sensitive" T1.7 verdict
rather than "robust" despite the strong Sharpe delta.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series, zscore

log = logging.getLogger(__name__)


class VolatilityTermStructureRegime(Regime):
    """2-state volatility term structure regime (Complacent × Stressed)."""

    name = "VolTerm"
    dimensions = ["VolTerm"]
    states = ["Complacent", "Stressed"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        vix = load_series("VIX INDEX:PX_LAST")
        if vix.empty:
            vix = load_series("VIX:PX_LAST")
        vix3m = load_series("VIX3M INDEX:PX_LAST")
        if vix3m.empty:
            vix3m = load_series("VIX3M:PX_LAST")

        if vix.empty or vix3m.empty:
            log.warning(
                "VolTerm: VIX / VIX3M series unavailable. "
                "Seed CBOE data via ix/collectors/cboe.py to activate this regime."
            )
            return rows

        # 1. v_TermSlope — VIX3M / VIX ratio (contango vs backwardation).
        #    > 1.0 = contango (normal), < 1.0 = backwardation (stress).
        #    Rolling z-score catches "extreme vs recent history" — the
        #    signal fires on relative, not absolute, stress.
        ratio = (vix3m / vix.replace(0, pd.NA)).astype(float)
        rows["v_TermSlope"] = zscore(ratio, z_window).rename("v_TermSlope")

        # [DROPPED: v_TermChange3M — pre IC -0.043 (inverted basis).
        #  The 3M change in term structure ratio adds noise pre-2010
        #  where the VIX3M data starts (2006) leaving only 3.5 years of
        #  pre-2010 history. TermSlope alone is cleaner: pre +0.144,
        #  post +0.109 (inverted IC, matching the contrarian design).]

        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"VolTerm": "v_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map VolTerm composite probability to 2 states.

        High composite (contango / complacent) → Complacent.
        Low composite (backwardation / stress)  → Stressed.
        Forward-return target mapping is CONTRARIAN at the extremes:
        the backwardation state historically has HIGHER forward 3m SPY
        returns than the complacent state (mean reversion after stress).
        """
        vp = dim_probs["VolTerm"]
        return {
            "P_Complacent": vp,
            "P_Stressed":   1.0 - vp,
        }
