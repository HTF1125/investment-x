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

Indicators (2, all ``h_*``). Rebuilt 2026-04-12 after the all-regimes
triage found 2 of the prior 4 indicators below the |IC| ≥ 0.03 floor
on the registered SPY 12M fwd target:

    h_CaseShillerAccel CSUSHPINSA  3M diff of 12M YoY z — post-2010 IC +0.227
    h_MortgageRate    MORTGAGE30US 12M diff inverted z — post-2010 IC +0.130

Dropped (2026-04-12 triage)
    - h_Starts (HOUST 12M diff): post-2010 IC -0.014 (sign flipped from
      the prior docstring's claimed +0.087). Starts data is captured
      upstream by the Case-Shiller acceleration signal and the mortgage
      rate channel; keeping it added collinearity without incremental IC.
    - h_Permits (PERMIT 12M diff): post-2010 IC -0.006. Permits lead
      starts by 1-2 months but at the 12M horizon that lead is washed
      out. Same story as Starts — redundant with the surviving two.

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

        # h_CaseShillerAccel — Case-Shiller home price acceleration
        # (3M diff of 12M YoY %). Not price level (which has the WRONG
        # sign — Case-Shiller peaks AT cycle tops, not before), but the
        # ACCELERATION of price momentum. Post-2010 IC +0.227 on SPY 12M
        # fwd — the strongest housing indicator in the set.
        cs = load_series("CSUSHPINSA", lag=1)
        if not cs.empty:
            cs_yoy = cs.pct_change(12, fill_method=None) * 100
            cs_accel = cs_yoy.diff(3)
            rows["h_CaseShillerAccel"] = zscore(cs_accel, z_window).rename(
                "h_CaseShillerAccel"
            )

        # h_MortgageRate — 30y fixed mortgage rate, 12M change, INVERTED.
        # Falling rates = rising affordability = housing expansion.
        # Post-2010 IC +0.130 on SPY 12M fwd (second-strongest).
        mortgage = load_series("MORTGAGE30US")
        if not mortgage.empty:
            rows["h_MortgageRate"] = zscore(
                -mortgage.diff(12), z_window
            ).rename("h_MortgageRate")

        # [DROPPED 2026-04-12: h_Permits / h_Starts — see module docstring
        #  for triage rationale. Both below the 0.03 |IC| floor on SPY 12M
        #  fwd post-2010 (Permits -0.006, Starts -0.014) and redundant with
        #  the surviving two indicators via the permits→starts→prices→rates
        #  transmission chain.]
        # [DROPPED earlier: h_NewSales — post IC -0.034, structural shift
        #  in housing turnover post-2010 (less construction, more existing-
        #  home sales).]

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
