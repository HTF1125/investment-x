"""InflationRegime — standalone 2-state inflation regime.

2-state regime (Rising / Falling) driven by the shared inflation indicator
loader in :mod:`.loaders`.

States
------
- **Rising**   (Inflation_Z > 0): Inflationary pressures building. ISM prices
  paid rising, CPI 3M annualized above 2.5% target, breakeven expectations
  up, PCE core accelerating, wages growing fast, commodities in an uptrend.
  Historically negative for both bonds and equity multiples.
- **Falling**  (Inflation_Z ≤ 0): Disinflation. Price indicators cooling,
  commodities stable or down, wages decelerating. Typically supportive for
  long-duration assets (TLT, tech).

Indicators (8, all ``i_*``, loaded by :func:`loaders.load_inflation_indicators`)
    i_ISMPricesPaid (anchor 50) · i_CPI3MAnn (anchor 2.5%)
    i_Breakeven (anchor 2.5%)   · i_PCECore (anchor 2.5%)
    i_MedianCPI (anchor 2.5%)   · i_Wages (anchor 3.5%)
    i_WTI (anchor 0%)           · i_Commodities (anchor 0%)

Target & Justification
----------------------
Target:        CL1 Comdty (WTI front-month crude oil futures)
Horizon:       6 months forward return
Justification: WTI is the canonical commodity inflation proxy with the
               largest forward-return spread across inflation states. Tested
               against GLD/DBC/TIP/DBA/USO/SLV/XLE/CL1 at 3/6/12M horizons,
               WTI @ 6M produced the clearest signal: spread +9.38%, Welch
               p<0.001, permutation p<0.001, sign-consistent across eras.

               **Empirical state ordering inverts theoretical expectation:**
               Falling (inflation cooling) is the BEST forward state for
               WTI, not Rising. Mechanism: when inflation signals are
               already rising strongly, commodities have rallied and
               forward returns mean-revert mediocre. When inflation signals
               are falling, commodities have been dumped to cheap levels
               and forward returns recover. Same turning-point pattern
               observed in credit, dollar, and liquidity regimes.

               Mild circularity caveat: WTI YoY (i_WTI) is 1 of 8 inflation
               indicators in this regime, so the classification is not
               fully independent of the target. However, the classification
               uses current levels and the measurement uses forward returns,
               so there is no look-ahead bias — just a mild positive
               correlation between "current commodity-informed inflation
               state" and "current commodity valuations".
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime
from .loaders import load_inflation_indicators

log = logging.getLogger(__name__)


class InflationRegime(Regime):
    """2-state inflation regime over the ``i_*`` indicator set."""

    name = "Inflation"
    dimensions = ["Inflation"]
    states = ["Rising", "Falling"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        """Load the ``i_*`` indicator set from the shared inflation loader."""
        return load_inflation_indicators(z_window)

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Inflation": "i_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Simple 2-state mapping from Inflation probability.

        Inflation_P > 0.5 → Rising
        Inflation_P <= 0.5 → Falling
        """
        pi = dim_probs["Inflation"]
        return {
            "P_Rising":  pi,
            "P_Falling": 1.0 - pi,
        }
