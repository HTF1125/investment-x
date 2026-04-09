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

Indicators (3, all cc_*)
    cc_CopperGold     — Copper/Gold ratio 6M momentum
    cc_OilMomentum    — WTI crude 12-1 month momentum
    cc_IndMetals      — Bloomberg Industrial Metals sub-index vs 200DMA

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

        # 2. cc_OilMomentum — WTI 12-minus-1 month momentum (skip latest
        #    month to avoid short-term noise, classic 12-1 momentum).
        oil = _load("CL1 COMDTY:PX_LAST")
        if not oil.empty:
            mom = oil.shift(1).pct_change(11) * 100.0
            rows["cc_OilMomentum"] = zscore(mom, z_window).rename("cc_OilMomentum")

        # 3. cc_XME — SPDR S&P Metals & Mining ETF vs 200DMA.
        #    Proxy for industrial metals exposure (primary constituents are
        #    copper / steel / aluminum miners). Positive = above 200DMA,
        #    negative = below. Captures broad cyclical commodity trend
        #    independent of energy. XME is the most liquid proxy in the DB
        #    for the Bloomberg Industrial Metals sub-index (BCOMIN) which
        #    is not seeded.
        xme = _load("XME US EQUITY:PX_LAST")
        if not xme.empty:
            sma200 = xme.rolling(10).mean()  # 10 month-end periods ≈ 200 trading days
            deviation = (xme / sma200.replace(0, pd.NA) - 1.0) * 100.0
            rows["cc_XME"] = zscore(deviation, z_window).rename("cc_XME")

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
