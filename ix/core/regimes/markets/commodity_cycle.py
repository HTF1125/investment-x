"""CommodityCycleRegime — 2-state industrial commodity cycle regime.

Thesis
------
Industrial commodities lead the real economy's cyclical expansions and
contractions. Copper is "Dr. Copper" for a reason — it tops before
growth data, it bottoms before growth data, and its ratio to gold
(the anti-growth asset) is a cleaner signal than either alone.

This regime blends three cyclical-commodity signals:
  1. Copper/gold ratio (momentum) — cyclical leadership
  2. WTI crude 12-1 month momentum — energy cycle
  3. Industrial metals sub-index vs its 200DMA — broad cyclical

All three moving in the same direction is the confirmation. When they
disagree (e.g. copper/gold rising but oil falling), the regime stays
Neutral rather than force a direction.

**Orthogonality:** overlaps partially with Inflation (WTI component)
and Dollar-Trend (commodity prices are dollar-sensitive). The
composite should still be orthogonal at the ρ < 0.60 bar because
copper/gold ratio and industrial metals are not in either existing
regime. Verify post-build.

States
------
- **Reflation** (CC_Z > 0): Copper/gold rising, oil rising, metals
  above 200DMA. Global cyclical reflation underway. Forward SPY 3m:
  positive, cyclical sectors outperform.
- **Deflation** (CC_Z ≤ 0): Cyclical commodities rolling over.
  Global demand weakening. Forward SPY 3m: negative, defensive
  sectors outperform.

Indicators (2, all cc_*)
    cc_CopperGold     — Copper/Gold ratio 6M momentum
    cc_Copper_6M      — Copper 6M momentum (IC +0.105, stable pre/post)

Publication lag: zero (futures markets).
Target: SPY 3M fwd. Locked. Coincident mapping.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class CommodityCycleRegime(Regime):
    """2-state commodity cycle regime (Reflation × Deflation)."""

    name = "CommodityCycle"
    dimensions = ["Commodity"]
    states = ["Reflation", "Deflation"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. cc_CopperGold — 6-month momentum of copper/gold ratio.
        #    Copper is cyclical, gold is counter-cyclical — the ratio
        #    rising means risk-on demand growth; falling means the
        #    opposite.
        cop = _load("HG1 COMDTY:PX_LAST")
        gld = _load("GC1 COMDTY:PX_LAST")
        if not cop.empty and not gld.empty:
            ratio = (cop / gld.replace(0, pd.NA)).astype(float)
            rows["cc_CopperGold"] = zscore(ratio.pct_change(6) * 100.0, z_window).rename(
                "cc_CopperGold"
            )

        # [DROPPED: cc_XME — post IC -0.030 (DYING). Full IC only +0.007.
        #  XME vs 200DMA is too noisy — mining equities have stock-specific
        #  risk that dilutes the commodity cycle signal. CopperGold alone
        #  is cleaner (full IC +0.040, pre +0.126, post +0.055).]

        # 2. cc_Copper_6M — Copper 6-month momentum. Industrial bellwether.
        #    IC: full +0.105, pre +0.090, post +0.139 — stable and strong.
        if not cop.empty:
            rows["cc_Copper_6M"] = zscore(
                cop.pct_change(6, fill_method=None) * 100.0, z_window
            ).rename("cc_Copper_6M")

        if not rows:
            log.warning(
                "CommodityCycle: no indicators loaded. Check HG1 / GC1 / CL1 / "
                "BCOMIN Bloomberg codes."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Commodity": "cc_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Commodity composite probability to 2 states.

        Reflation = cyclical commodities rising, copper > gold, oil up,
                    metals above 200DMA. Coincident with risk-on equity
                    periods.
        Deflation = the inverse. Coincident with defensive leadership.
        """
        cp = dim_probs["Commodity"]
        return {
            "P_Reflation": cp,
            "P_Deflation": 1.0 - cp,
        }
