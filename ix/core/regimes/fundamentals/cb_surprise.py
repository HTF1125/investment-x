"""CBSurpriseRegime — 3-state central bank policy surprise regime.

Thesis
------
Markets price an expected policy path into OIS / Fed funds futures.
The *surprise* — actual path minus expected path — is what moves
risk assets in the 1–3 month window after each FOMC meeting. Hawkish
surprises (OIS reprices higher than expected) are a headwind for
equities; dovish surprises (OIS reprices lower) are a tailwind.

The signal is fast-decaying: it has high IC in the first 1–3 months
and decays to zero by 6 months. This is the shortest-duration regime
in the registry and is intended primarily for pairing with other
faster signals rather than as a standalone tilt.

**Hard rule compliance:** this does not invert any contrarian gauge.
The signal is the raw repricing of the OIS path, which is directionally
tradeable: hawkish surprise → lower forward equity returns, and vice
versa. It also does not use Global M2 or any other banned indicator.

States
------
- **Dovish**   (CBS_Z > +0.5σ): OIS path has moved LOWER than expected
  over the last 30 days. Forward SPY 1m: strongly positive.
- **Neutral**  (−0.5σ ≤ CBS_Z ≤ +0.5σ): OIS has moved roughly in line
  with pre-meeting expectations. No signal.
- **Hawkish**  (CBS_Z < −0.5σ): OIS path has moved HIGHER than expected.
  Forward SPY 1m: strongly negative. This is the actionable state.

Indicators (5, all cb_*). Post-2010 Spearman IC on SPY 3M fwd:
    cb_FFSpread_3M    — 2Y-Fed funds spread, 3M change (inverted; IC +0.249)
    cb_TRY1Y          — 1Y Treasury yield, 1M change (inverted; IC +0.197)
    cb_TRY2Y          — 2Y Treasury yield, 1M change (inverted; IC +0.161)
    cb_YCSpread       — 10Y-2Y spread, 1M change (steepening = dovish; IC +0.148)
    cb_SOFR           — SOFR overnight rate, 1M change (inverted; weak on SPY
                        but dominant on duration — IEF 6M IC +0.481, TLT 6M +0.342)

Publication lag: **zero** (market data). Downstream validators should pass
``data_lag_months=0`` — at the default ``lag=1`` duration targets lose
~0.26 Cohen's d vs lag=0.

Target: SPY 3M fwd. Signal also strong on duration (IEF 3M, TLT 3M) but
registered against SPY to match the original thesis (policy surprise
primarily moves equities 1-3M out).

History / audit notes
---------------------
- 2026-04-12 audit rebuilt the indicator set:
  * Dropped cb_FFSpread (1M diff) — post-2010 IC +0.134, collinear with
    cb_TRY2Y at r=+0.76. Replaced with the 3M-diff variant which carries
    nearly double the IC without the front-end noise.
  * Re-added cb_TRY1Y — originally dropped for pre-2010 IC −0.017, but
    post-2010 IC is +0.197 (rank 2 on SPY 3M). High collinearity with
    cb_TRY2Y (r=+0.85) is a known cost; composite dilution to be revisited
    if per-indicator IC-weighting is added to the base pipeline.
- 2026-04-12: dropped ``smooth_halflife`` from 3 → 1. The previous setting
  produced a degenerate regime (4 Dovish / 576 Neutral / 7 Hawkish over 587
  months, 98.1% Neutral — cohens_d undefined). hl=1 is the only smoothing
  level that produces usable tail-state counts; see
  ``scripts/_cb_surprise_audit_report.md`` section 0 for quantitative
  evidence. The trade-off is noisier month-to-month state flips, which is
  acceptable because this is a fast-decaying signal that's meant to trade
  episodically rather than sit in one state for quarters.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class CBSurpriseRegime(Regime):
    """3-state central bank surprise regime (Dovish × Neutral × Hawkish)."""

    name = "CBSurprise"
    dimensions = ["CBSurprise"]
    states = ["Dovish", "Neutral", "Hawkish"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # OIS data is not in the DB. We proxy the policy surprise signal
        # using Treasury yield CHANGES at the front end of the curve
        # (1y, 2y) and SOFR/FEDFUNDS path changes. When yields move more
        # than the market expected, the same signal shows up in these
        # series as in OIS. The proxy is not as clean as a true OIS path
        # surprise but carries most of the information content at the
        # 1-3 month horizon we care about.

        # cb_TRY2Y — 2y Treasury yield, 1-month change.
        # INVERTED: rising yields = hawkish = negative z (dovish = pos).
        # Post-2010 IC +0.161 on SPY 3M.
        t2 = _load("TRYUS2Y:PX_YTM")
        if not t2.empty:
            rows["cb_TRY2Y"] = zscore(-t2.diff(1), z_window).rename("cb_TRY2Y")

        # cb_TRY1Y — 1y Treasury yield, 1-month change.
        # Re-added 2026-04-12 after audit — post-2010 IC +0.197 (rank 2 on
        # SPY 3M). Was originally dropped for pre-2010 IC -0.017 at the
        # zero-bound; pre-2010 noise is accepted because the composite
        # z-score baseline carries it. Collinear with cb_TRY2Y at r=+0.85;
        # both kept because TRY1Y has higher post-2010 IC but TRY2Y has
        # better fundamental interpretation (2y OIS-equivalent tenor).
        t1 = _load("TRYUS1Y:PX_YTM")
        if not t1.empty:
            rows["cb_TRY1Y"] = zscore(-t1.diff(1), z_window).rename("cb_TRY1Y")

        # cb_SOFR — SOFR overnight rate, 1-month change.
        # Front-end repo rate — moves with every FOMC action. Post-2010 IC
        # is weak on SPY (-0.017) but dominant on duration: IEF 6M +0.481,
        # TLT 6M +0.342. Kept because it anchors the composite on the
        # shortest-tenor policy signal available in the DB.
        sofr = _load("SOFR:PX_LAST")
        if not sofr.empty:
            rows["cb_SOFR"] = zscore(-sofr.diff(1), z_window).rename("cb_SOFR")

        # cb_FFSpread_3M — 2y Treasury minus effective Fed funds, 3-month diff.
        # When the spread is EXPANDING, the market is pricing more hikes
        # than are currently done → hawkish path surprise. 3M diff replaces
        # the 1M diff from the original regime after audit (2026-04-12)
        # showed post-2010 IC +0.249 (top of entire candidate set) vs the
        # 1M version's +0.134. Only r=+0.51 with cb_TRY2Y — complementary
        # slow-trend component on top of cb_TRY2Y's fast-level signal.
        eff = _load("FEDFUNDS:PX_LAST")
        if eff.empty:
            eff = _load("DFF:PX_LAST")
        if not t2.empty and not eff.empty:
            eff_m = eff.reindex(t2.index, method="ffill")
            spread = t2 - eff_m
            rows["cb_FFSpread_3M"] = zscore(-spread.diff(3), z_window).rename(
                "cb_FFSpread_3M"
            )

        # [DROPPED 2026-04-12: cb_FFSpread (1M diff variant) — post-2010 IC
        #  +0.134, weaker than cb_FFSpread_3M's +0.249 and collinear with
        #  cb_TRY2Y at r=+0.76. Replaced by the 3M variant above.]
        # [DROPPED: cb_TRY10Y — individual IC passes (full +0.049, pre +0.027,
        #  post +0.076) but COMPOSITE IC worsens when added alongside TRY2Y
        #  (full -0.007, pre -0.007). 10Y yield change is too correlated with
        #  the 2Y signal, diluting it. YCSpread (10Y-2Y) captures the
        #  incremental information from the 10Y tenor without the redundancy.]

        # cb_YCSpread — 10Y-2Y spread 1-month change.
        # Steepening = dovish surprise (market pricing rate cuts at front end).
        # Post-2010 IC +0.148 on SPY 3M. Only composite member with near-zero
        # correlation against the other four inputs (orthogonal signal).
        t10y2y = _load("T10Y2Y")
        if not t10y2y.empty:
            rows["cb_YCSpread"] = zscore(t10y2y.diff(1), z_window).rename(
                "cb_YCSpread"
            )

        if not rows:
            log.warning(
                "CBSurprise: no indicators loaded. Expected DB codes: "
                "'TRYUS1Y/2Y:PX_YTM', 'SOFR:PX_LAST', 'FEDFUNDS:PX_LAST', "
                "'T10Y2Y:PX_LAST'."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"CBSurprise": "cb_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map CBSurprise composite probability to 3 states.

        Because the inputs are inverted, high composite = dovish.

        Dovish  (P > 0.70): yields fell more than expected → risk on
        Neutral (0.30 ≤ P ≤ 0.70): no signal
        Hawkish (P < 0.30): yields rose more than expected → risk off
        """
        p = dim_probs["CBSurprise"]
        p_dovish = ((p - 0.70) / 0.30).clip(lower=0, upper=1)
        p_hawkish = ((0.30 - p) / 0.30).clip(lower=0, upper=1)
        p_neutral = (1.0 - p_dovish - p_hawkish).clip(lower=0)
        total = (p_dovish + p_neutral + p_hawkish).clip(lower=1e-9)
        return {
            "P_Dovish":  p_dovish / total,
            "P_Neutral": p_neutral / total,
            "P_Hawkish": p_hawkish / total,
        }
