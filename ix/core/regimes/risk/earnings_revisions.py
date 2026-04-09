"""EarningsRevisionsRegime — 2-state bottom-up earnings regime.

Thesis
------
Sell-side analysts collectively are a noisy but forward-looking signal.
When revisions are broadly tilting up (more upgrades than downgrades),
corporate earnings momentum is accelerating — forward equity returns are
strong. When the revision breadth collapses, earnings are rolling over
and forward returns suffer. Revision breadth historically LEADS the macro
Growth composite by 1–2 months at turning points because analysts see
company-specific order books before aggregate data catches up.

This is the *bottom-up* fundamental regime, orthogonal to the *top-down*
Growth regime which uses ISM / claims / LEI. Both can be in different
states, and those disagreements are informative — they typically resolve
in favor of the revisions signal over a 3-month window.

States
------
- **Accelerating**  (Revisions_Z > 0): Revision breadth positive — more
  upgrades than downgrades across the index. Earnings momentum improving.
  Forward SPY 3m: strong, positive skew.
- **Decelerating**  (Revisions_Z ≤ 0): Revision breadth negative — more
  downgrades. Earnings momentum failing. Forward SPY 3m: flat to negative,
  with fat left tail.

Indicators (3, all e_*)
    e_RBI               — Revision Breadth Index: (#up − #down) / total, 4w roll
    e_EPS3M             — 3-month change in SPX consensus forward EPS
    e_GuideSpread       — Positive-guide − negative-guide count, quarterly

Publication lag: 1 week for RBI (compustat/IBES typical), 1 month for
aggregated EPS revisions.
Target: SPY 3M fwd. Locked.

Status: DRAFT — requires an earnings revisions data feed (FactSet,
Refinitiv/IBES, or Bloomberg). If none of the expected codes return data,
the regime silently degrades. Until a feed is connected this regime will
appear in the registry but emit a warning on load.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class EarningsRevisionsRegime(Regime):
    """2-state earnings revision breadth regime (Accelerating × Decelerating)."""

    name = "EarningsRevisions"
    dimensions = ["Revisions"]
    states = ["Accelerating", "Decelerating"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. e_RBI_1M — Revision Breadth Index, 1-month window.
        #    (# up-revisions − # down-revisions) / (# up + # down)
        #    across SPX constituents. Primary fast-acting signal.
        up_1m = _load("SPX INDEX:EARNINGS_REVISION_UP_1M")
        do_1m = _load("SPX INDEX:EARNINGS_REVISION_DO_1M")
        if not up_1m.empty and not do_1m.empty:
            total = (up_1m + do_1m).replace(0, pd.NA).astype(float)
            rbi = (up_1m - do_1m) / total
            rows["e_RBI_1M"] = zscore(rbi, z_window).rename("e_RBI_1M")

        # 2. e_FY1_1M — FactSet cumulative FY1 EPS estimate up-revisions
        #    minus down-revisions over the trailing 1 month. A forward-
        #    looking version of RBI — when the forward FY1 estimate is
        #    being revised up more than down, forward returns are stronger.
        fy1_up_1m = _load("SPX INDEX:FMA_COS_UP_EPS_FY1_1M")
        fy1_do_1m = _load("SPX INDEX:FMA_COS_DOWN_EPS_FY1_1M")
        if not fy1_up_1m.empty and not fy1_do_1m.empty:
            total = (fy1_up_1m + fy1_do_1m).replace(0, pd.NA).astype(float)
            breadth = (fy1_up_1m - fy1_do_1m) / total
            rows["e_FY1_1M"] = zscore(breadth, z_window).rename("e_FY1_1M")

        # 3. e_FY1_3M — Same FactSet signal over 3 months. Slower-moving,
        #    confirms the 1M signal. When 1M and 3M agree, the signal is
        #    high-conviction; when they disagree the regime sits neutral.
        fy1_up_3m = _load("SPX INDEX:FMA_COS_UP_EPS_FY1_3M")
        fy1_do_3m = _load("SPX INDEX:FMA_COS_DOWN_EPS_FY1_3M")
        if not fy1_up_3m.empty and not fy1_do_3m.empty:
            total = (fy1_up_3m + fy1_do_3m).replace(0, pd.NA).astype(float)
            breadth_3m = (fy1_up_3m - fy1_do_3m) / total
            rows["e_FY1_3M"] = zscore(breadth_3m, z_window).rename("e_FY1_3M")

        if not rows:
            log.warning(
                "EarningsRevisions: no indicators loaded. Expected DB codes: "
                "'SPX INDEX:EARNINGS_REVISION_UP/DO_1M' and "
                "'SPX INDEX:FMA_COS_UP/DOWN_EPS_FY1_1M/3M'."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Revisions": "e_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Revisions composite to 2 states.

        Accelerating = revision breadth tilted up, forward returns strong.
        Decelerating = revision breadth tilted down, forward returns weak.
        This is a COINCIDENT signal (not contrarian): the state direction
        matches the forward return direction.
        """
        rp = dim_probs["Revisions"]
        return {
            "P_Accelerating": rp,
            "P_Decelerating": 1.0 - rp,
        }
