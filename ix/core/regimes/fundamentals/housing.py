"""HousingRegime — standalone 2-state housing cycle regime.

2-state regime (Expansion / Contraction) driven by US housing-activity flows.

Transmission mechanism
----------------------
Residential investment is the most cyclical component of GDP and leads the
business cycle by 4-8 quarters (Leamer 2007, "Housing IS the business cycle").
Housing starts, permits, new-home sales, and affordability turn before
payrolls and ISM. A contracting housing regime at ``t`` predicts equity
drawdown at ``t + 12M`` via the residential-investment → consumption → jobs
chain.

States
------
- **Expansion**   (Housing_Z > 0): Starts, permits, new-home sales
  accelerating; mortgage rates falling or stable; Case-Shiller YoY rising.
  Residential investment is adding to GDP. Historically bullish for equity
  12M forward.
- **Contraction** (Housing_Z ≤ 0): Housing flows decelerating; permits
  falling; mortgage rates rising (affordability headwind); price momentum
  weakening. Historically precedes recessions and equity drawdowns.

Signal class
------------
**Quantity-flow ROC.** Housing is a flow variable — raw levels are
dominated by multi-decade demographic trends (starts fell ~60% between the
1970s baby-boom peak and the 2010s). The business-cycle signal lives in
*changes*, not levels. All indicators use 12-month differences to match
the long-lead transmission (housing turns 12-18 months before equity),
not rolling-mean anchored z-scores.

Indicators (all ``h_*``)
    h_Permits         PERMIT       12M diff z   (leads starts by ~1-2 months)
    h_Starts          HOUST        12M diff z   (IC +0.122 full, +0.153 pre, +0.087 post)
    h_CaseShillerAccel CSUSHPINSA  3M diff of 12M YoY z (IC +0.261 full, +0.213 pre, +0.353 post)
    h_MortgageRate    MORTGAGE30US 12M diff inv z (affordability channel)

Excluded (iteration-2 diagnostics)
    - CSUSHPINSA YoY: IC has WRONG SIGN (-0.12 vs SPY 12M) — Case-Shiller
      price momentum is contemporaneous/lagging, peaks AT cycle tops (2006,
      2021) not before. Dropping improves composite IC from +0.01 to +0.22.
    - MORTGAGE30US 12M diff: near-zero IC (+0.04). Affordability matters in
      theory but the rate-change signal is already captured by the flow
      slowdown — mortgages rise → starts fall. Dropping raises composite IC
      without losing information.

Target & justification
----------------------
Target:        SPY US EQUITY:PX_LAST
Horizon:       12 months forward return
Justification: Leamer (2007) documents housing leading the cycle by 4-8
               quarters. XHB (direct homebuilder exposure) has only 2006+
               history, which is insufficient for a pre/post-2010 subsample
               split. SPY 12M captures the full leading-indicator channel:
               housing contraction at ``t`` → recession at ``t+6M..12M`` →
               equity drawdown over the same window.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series, zscore

log = logging.getLogger(__name__)


class HousingRegime(Regime):
    """2-state US housing-cycle regime over the ``h_*`` indicator set."""

    name = "Housing"
    dimensions = ["Housing"]
    states = ["Expansion", "Contraction"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. Building permits — leads starts by 1-2 months
        permits = load_series("PERMIT")
        if not permits.empty:
            rows["h_Permits"] = zscore(permits.diff(12), z_window).rename("h_Permits")

        # [DROPPED: h_NewSales — post IC -0.034 (DYING). Full IC +0.003.
        #  New home sales 12M diff lost predictive power post-2010 due to
        #  the structural shift in housing (lower construction, more
        #  existing home turnover). Permits alone is cleaner.]

        # 2. Housing starts — 12M diff z-score.
        #    IC: full +0.122, pre +0.153, post +0.087 — stable across subsamples.
        starts = load_series("HOUST", lag=1)
        if not starts.empty:
            rows["h_Starts"] = zscore(starts.diff(12), z_window).rename("h_Starts")

        # 3. Case-Shiller price acceleration — 3M diff of 12M YoY.
        #    Not price level (which has wrong sign) but the acceleration of
        #    price momentum. IC: full +0.261, pre +0.213, post +0.353 — strongest
        #    single housing indicator.
        cs = load_series("CSUSHPINSA", lag=1)
        if not cs.empty:
            cs_yoy = cs.pct_change(12, fill_method=None) * 100
            cs_accel = cs_yoy.diff(3)
            rows["h_CaseShillerAccel"] = zscore(cs_accel, z_window).rename(
                "h_CaseShillerAccel"
            )

        # 4. Mortgage rate 12M change (INVERTED: falling rates = expansion)
        #    Pre IC +0.014, post IC +0.072 — stable across subsamples.
        #    Captures the affordability channel that drives housing demand.
        mortgage = load_series("MORTGAGE30US")
        if not mortgage.empty:
            rows["h_MortgageRate"] = zscore(
                -mortgage.diff(12), z_window
            ).rename("h_MortgageRate")

        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Housing": "h_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Housing_P > 0.5 → Expansion, else Contraction."""
        ph = dim_probs["Housing"]
        return {
            "P_Expansion": ph,
            "P_Contraction": 1.0 - ph,
        }
