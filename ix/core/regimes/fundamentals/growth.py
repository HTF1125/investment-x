"""GrowthRegime — standalone 2-state growth regime.

2-state regime (Expansion / Contraction) driven by the shared growth
indicator loader in :mod:`.loaders`.

States
------
- **Expansion**    (Growth_Z > 0): Economic growth accelerating. Claims falling,
  ISM new orders expanding, OECD CLI rising, LEI positive, payrolls YoY up,
  building permits advancing. Historically bullish for risk assets.
- **Contraction**  (Growth_Z ≤ 0): Economic growth decelerating. Rising claims,
  contracting ISM, falling LEI. Historically the worst environment for
  equities — recessions cluster here.

Indicators (all ``g_*``, loaded by :func:`loaders.load_growth_indicators`)
    g_InitialClaims · g_ISMNewOrders · g_OECDCLI · g_LEI
    g_Payrolls · g_CLIDiffusion · g_Permits · g_ISM_NO_Inv
    (+ m_ISMServices monitor-only, g_Claims4WMA excluded from composite)

Target & Justification
----------------------
Target:        SPY US EQUITY (S&P 500)
Horizon:       3 months forward return
Justification: Growth indicators lead equity returns by 2-3 months on average.
               Prior joint Growth × Inflation testing showed SPY @ 3M is the
               strongest horizon for the Growth composite (Goldilocks +4.22%
               vs Stagflation -0.85% = 5.07% spread, p<0.0001). Isolating
               Growth alone should preserve most of that edge — Stagflation +
               Deflation both have Growth_Z < 0 and are the two weakest
               macro states.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime
from .loaders import GROWTH_EXCLUDE_FROM_COMPOSITE, load_growth_indicators

log = logging.getLogger(__name__)


class GrowthRegime(Regime):
    """2-state growth regime over the ``g_*`` indicator set."""

    name = "Growth"
    dimensions = ["Growth"]
    states = ["Expansion", "Contraction"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        """Load the ``g_*`` indicator set from the shared growth loader."""
        return load_growth_indicators(z_window)

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Growth": "g_"}

    def _exclude_from_composite(self) -> set[str]:
        """Monitor-only columns excluded from the composite z-score."""
        return GROWTH_EXCLUDE_FROM_COMPOSITE

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Simple 2-state mapping from Growth probability.

        Growth_P > 0.5 → Expansion
        Growth_P <= 0.5 → Contraction
        """
        pg = dim_probs["Growth"]
        return {
            "P_Expansion":   pg,
            "P_Contraction": 1.0 - pg,
        }
