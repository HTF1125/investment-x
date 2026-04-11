"""GlobalLiquidityRegime — non-US central bank liquidity cycle.

States
------
- **Easing**:     Global CB balance sheets expanding, G4 aggregate growing,
                  individual CB impulses positive. Tailwind for EM equities,
                  commodities, and risk assets with global beta.
- **Tightening**: Global CB balance sheets contracting. Headwind for EM
                  and commodities. Dollar strength typically accompanies.

Indicators (4, all ``gl_*``)
    gl_G4_BS_YoY        — G4 (Fed + ECB + BoJ + PBoC) aggregate balance
                          sheet YoY. The single most important global
                          liquidity indicator per Howell.
    gl_GlobalLiqIdx_YoY — Cross Border Capital style 13-CB global liquidity
                          index YoY. Captures the full global CB cycle
                          including BoE, BoC, RBA, RBI, SNB, etc.
    gl_GlobalLiqCycle   — Z-scored 3M momentum of global liquidity (Howell's
                          65-month cycle oscillator). Captures turning points
                          in the cycle.
    gl_CreditImpulse    — US bank credit impulse. Included because the US
                          credit channel transmits globally via the dollar
                          funding system. Also provides a domestic anchor
                          that improves the signal at shorter horizons.

Design principle
----------------
**This regime captures what the US-focused LiquidityRegime cannot: the
global CB cycle that drives emerging markets, commodities, and cross-border
capital flows.** Per Howell (Capital Wars, 2020), global liquidity leads
business cycles by ~15 months and asset markets by 6-12 months.

Orthogonality: this regime is designed to compose with the US-focused
LiquidityRegime. Their overlap is intentionally limited to CreditImpulse
(which anchors both). The G4/global indicators here are absent from the
US regime, and the US regime's Fed-specific plumbing (TGA, net liq,
bank loans) is absent here.

Target & Justification
----------------------
Target:   EEM US EQUITY (Emerging Markets ETF)
Horizon:  3 months forward return
Rationale: Non-US CB liquidity flows into EM equities via the portfolio-
          rebalancing channel and dollar funding conditions. PBoC (25-30%
          of global liquidity per Howell) directly drives EM Asia.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series, zscore

log = logging.getLogger(__name__)


class GlobalLiquidityRegime(Regime):
    """Global CB liquidity → 2-state regime (Easing / Tightening)."""

    name = "GlobalLiquidity"
    dimensions = ["GlobalLiquidity"]
    states = ["Easing", "Tightening"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # gl_GlobalLiqIdx_YoY — Cross Border Capital style 13-CB global
        # liquidity index YoY. Includes Fed + ECB + BoJ + PBoC + 9 more,
        # so it strictly subsumes the old gl_G4_BS_YoY signal. Post-2010
        # IC +0.119 on EEM 3M fwd (top of the set).
        try:
            from ix.core.indicators.liquidity import global_liquidity_index_yoy

            gli_yoy = global_liquidity_index_yoy().resample("ME").last()
            if not gli_yoy.empty:
                rows["gl_GlobalLiqIdx_YoY"] = zscore(
                    gli_yoy, z_window
                ).rename("gl_GlobalLiqIdx_YoY")
        except Exception as exc:
            log.warning("Global liquidity index YoY failed: %s", exc)

        # [DROPPED 2026-04-12: gl_G4_BS_YoY — triage found r=+0.98 with
        #  gl_GlobalLiqIdx_YoY (which already includes the G4 balance
        #  sheets plus 9 additional CBs). Keeping both double-counts the
        #  same aggregate. Kept the broader index since it has higher
        #  post-2010 IC on EEM 3M (+0.119 vs +0.090) and wider coverage.]

        # [DROPPED: gl_GlobalLiqCycle — pre IC -0.131 (DROP). Full IC +0.024.
        #  The 3M momentum of global liquidity oscillated chaotically pre-2010
        #  (pre-GFC global CB coordination was weak). The YoY measure above
        #  captures the cycle without the noise.]

        # Monitor-only DXY (strong dollar = global tightening proxy).
        # Excluded from composite — display only.
        dxy = load_series("DXY Curncy:PX_LAST")
        if dxy.empty:
            dxy = load_series("DX-Y.NYB:PX_LAST")
        if not dxy.empty:
            rows["m_DXY"] = zscore(-dxy, z_window).rename("m_DXY")

        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"GlobalLiquidity": "gl_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        glp = dim_probs["GlobalLiquidity"]
        return {
            "P_Easing": glp,
            "P_Tightening": 1.0 - glp,
        }
