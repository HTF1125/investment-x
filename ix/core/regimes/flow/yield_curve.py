"""YieldCurveRegime — 2-state yield-curve slope regime (Steep × Flat).

Decomposes the US Treasury yield curve into a single composable axis regime.
The yield curve is the most empirically validated leading recession indicator
in macro (Estrella & Mishkin 1996, 1998+; NY Fed recession probability model).

States
------
- **Steep**  (YieldCurve_Z > 0): Slope above rolling history AND/OR steepening.
  Late-recession recovery, early-cycle, or expansion phase. Historically the
  best 12M forward equity environment (post-inversion re-steepening captures
  the equity rebound that follows Fed cutting cycles).
- **Flat**   (YieldCurve_Z ≤ 0): Slope below rolling history AND/OR flattening.
  Late-cycle, restrictive monetary stance, or recession warning. Captures both
  the academic Estrella signal (flat/inverted → recession 12M out) and the
  empirical drawdown precursor.

Indicators (3, all yc_*)
    yc_3m10y     — 10Y - 3M Treasury (Estrella canonical, longest history)
    yc_2s10s     — 10Y - 2Y Treasury (modern bond-market focus)
    yc_5s30s     — 30Y - 5Y Treasury (long-end / term-premium component)

Each is a PURE level z-score of the slope vs rolling 5-year history. This
mirrors the CreditLevelRegime / DollarLevelRegime pattern: the slope LEVEL
is the academic signal (Estrella inversion threshold), and adding ROC dilutes
the recession-warning content.

Note: A YieldCurveTrendRegime (3M/6M ROC of slopes, Steepening × Flattening)
was attempted as a Level/Trend pair but FAILED Tier 1 across 5 iterations
(best result TLT @ 6M with spread +3.89%, robust on Welch/permutation but
under the 5% T1.4 bar). See ix/core/regimes/_drafts/yield_curve_trend.py and
the LEARNINGS.md entry for diagnostic.

Target & Justification
----------------------
Target:        SPY US EQUITY (S&P 500)
Horizon:       12 months forward return
Justification: Estrella & Mishkin (NY Fed) calibrate the recession probability
               model at the 12-month horizon (3m10y < 0 → ~50% recession
               probability 12M out). Equity drawdowns lag inversion by 6-18
               months as the recession transmits, so a 12M forward window
               captures the full inversion → recession → recovery arc.

Calibration
-----------
Locked params (registered defaults): z_window=60, sensitivity=2.0,
smooth_halflife=2, confirm_months=3. The 60-month (5-year) z-window matches
the financial-conditions regime convention from the SKILL.md (vs the 96-month
default for slow macro regimes) — yield curve slope cycles run ~3-5 years.

Validated results (locked target SPY @ 12M):
    Tier 1: 6/6 (coverage 100%, persistence 19m, spread +6.37%, p<0.001)
    Tier 2: 4/6 (DD avoid 68%, conviction 65, OOS delta 8%; T2.1/T2.3 fail
                  on SPY-specific structural carry, same as credit/dollar)
    Robustness: 4/4 (sign-consistent across 2010 split, perm p=0.001)
    Pattern: Flat (+14.3% n=244) > Steep (+7.9% n=144) — contrarian
              turning-point pattern matches credit (Recovery>LateCycle),
              dollar (Bottoming>Weakness), inflation (Falling>Rising).

Source
------
Estrella, A. & Mishkin, F.S. (1998). "Predicting U.S. Recessions: Financial
Variables as Leading Indicators." Review of Economics and Statistics 80(1).
NY Fed Yield Curve Recession Probability Model.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class YieldCurveRegime(Regime):
    """2-state yield-curve slope regime (Steep × Flat)."""

    name = "YieldCurve"
    dimensions = ["YieldCurve"]
    states = ["Steep", "Flat"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 3m10y — Estrella canonical recession leading indicator (since 1953/1975)
        t10 = _load("TRYUS10Y:PX_YTM")
        t3m = _load("TRYUS3M:PX_YTM")
        if not t10.empty and not t3m.empty:
            slope_3m10y = t10.reindex(t3m.index, method="ffill") - t3m
            rows["yc_3m10y"] = zscore(slope_3m10y, z_window).rename("yc_3m10y")

        # 2s10s — modern bond-market standard (since 1986)
        t2y = _load("TRYUS2Y:PX_YTM")
        if not t10.empty and not t2y.empty:
            slope_2s10s = t10.reindex(t2y.index, method="ffill") - t2y
            rows["yc_2s10s"] = zscore(slope_2s10s, z_window).rename("yc_2s10s")

        # 5s30s — long-end term-premium component (since 1977)
        t5y = _load("TRYUS5Y:PX_YTM")
        t30y = _load("TRYUS30Y:PX_YTM")
        if not t5y.empty and not t30y.empty:
            slope_5s30s = t30y.reindex(t5y.index, method="ffill") - t5y
            rows["yc_5s30s"] = zscore(slope_5s30s, z_window).rename("yc_5s30s")

        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"YieldCurve": "yc_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map YieldCurve probability to 2 slope states.

        YieldCurve_P high → slope above rolling history → Steep
        YieldCurve_P low  → slope below rolling history → Flat (or inverted)
        """
        yc = dim_probs["YieldCurve"]
        return {
            "P_Steep": yc,
            "P_Flat":  1.0 - yc,
        }
