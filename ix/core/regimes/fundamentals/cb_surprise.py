"""CBSurpriseRegime — 2-state central bank policy surprise regime.

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

Indicators (3, all cb_*)
    cb_OIS1Y          — 1-year OIS yield, 30-day change (primary signal)
    cb_OIS2Y          — 2-year OIS yield, 30-day change (longer horizon)
    cb_TerminalSpread — Front-end terminal rate spread, 30-day change

Publication lag: zero (market data).
Target: SPY 1M fwd. Locked (shortest horizon in the registry).
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

        # 1. cb_TRY2Y — 2y Treasury yield, 1-month change.
        #    INVERTED: rising yields = hawkish = negative z (dovish = pos).
        t2 = _load("TRYUS2Y:PX_YTM")
        if not t2.empty:
            rows["cb_TRY2Y"] = zscore(-t2.diff(1), z_window).rename("cb_TRY2Y")

        # 2. cb_TRY1Y — 1y Treasury yield, 1-month change.
        #    Shortest-maturity Treasury — closest to pure policy path.
        t1 = _load("TRYUS1Y:PX_YTM")
        if not t1.empty:
            rows["cb_TRY1Y"] = zscore(-t1.diff(1), z_window).rename("cb_TRY1Y")

        # 3. cb_SOFR — SOFR overnight rate, 1-month change.
        #    Front-end repo rate — moves with every FOMC action.
        sofr = _load("SOFR:PX_LAST")
        if not sofr.empty:
            rows["cb_SOFR"] = zscore(-sofr.diff(1), z_window).rename("cb_SOFR")

        # 4. cb_FFSpread — 2y Treasury minus effective Fed funds.
        #    When the spread is expanding, the market is pricing more
        #    hikes than are currently done → hawkish path surprise.
        eff = _load("FEDFUNDS:PX_LAST")
        if eff.empty:
            eff = _load("DFF:PX_LAST")
        if not t2.empty and not eff.empty:
            t2_m = t2.resample("ME").last()
            eff_m = eff.resample("ME").last().reindex(t2_m.index, method="ffill")
            spread = t2_m - eff_m
            rows["cb_FFSpread"] = zscore(-spread.diff(1), z_window).rename(
                "cb_FFSpread"
            )

        if not rows:
            log.warning(
                "CBSurprise: no indicators loaded. Expected DB codes: "
                "'TRYUS1Y/2Y:PX_YTM', 'SOFR:PX_LAST', 'FEDFUNDS:PX_LAST'."
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
