"""Dollar regimes — split into two composable 1D axis regimes.

The dollar cycle is one of the longest, most persistent macro cycles
(typical bull/bear phases run 7-10 years). Dollar appreciation/depreciation
shocks are the dominant driver of cross-border capital flows and EM equity
performance — Obstfeld & Zhou (2022) find that dollar appreciation explains
~20% of EM equity price variance over 8-quarter horizons.

Following the broader 1D-only framework used by ``growth`` and ``inflation``,
the dollar is decomposed into two **independently composable** axis regimes:

* :class:`DollarLevelRegime` — how STRONG is the dollar vs its rolling
  history (Strong / Weak). 2-state, axis category.
* :class:`DollarTrendRegime` — is the dollar APPRECIATING or depreciating
  (Appreciating / Depreciating). 2-state, axis category.

Composing them via the multi-axis composer reproduces the original 4-state
phase regime mechanically (e.g. ``Strong+Appreciating`` is the textbook
"Strength" state, ``Weak+Depreciating`` is "Weakness", etc.) — but the
user controls whether they want a single dimension, both, or to mix dollar
axes with growth/inflation/credit.

Indicators
----------
The same 3 input series feed both regimes — the difference is purely the
transform applied (anchored level z-score vs ROC z-score):

Level dimension (lv_*) — **anchored** level z-score at basis-year 100:
    lv_DXY        — DXY index (DXY INDEX:PX_LAST), Bloomberg, since 1971
    lv_TWUSD      — Trade-Weighted USD Broad (DTWEXBGS), FRED
    lv_TWUSD_AFE  — Trade-Weighted Advanced FX (DTWEXAFEGS), FRED

The anchor (100) is the basis-year value common to all three indices. Using
an anchored z-score instead of a rolling z-score eliminates the drift
problem that crushed the previous version: the rolling 8y mean caught up to
a decade of structural dollar strength post-2014, so "Strong" stopped
firing decisively. Anchoring at the basis value means a reading AT 100 is
always z=0 regardless of recent cycle, identical to the inflation regime's
anchoring methodology.

Trend dimension (tr_*) — pure 3M absolute ROC z-score:
    tr_DXY        — 3M absolute change in DXY
    tr_TWUSD      — 3M absolute change in Broad TW USD
    tr_TWUSD_AFE  — 3M absolute change in Advanced FX TW USD

Source
------
- Obstfeld, M. & Zhou, H. (2022) "The Global Dollar Cycle"
  Brookings BPEA Conference Drafts, September 2022.
  NBER Working Paper 31004.
- RBC Wealth Management: Dollar cycles average 7-10 years; bull cycles
  ~+65%, bear cycles ~-40%.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore, zscore_anchored, zscore_roc


# Basis-year structural anchor for the trade-weighted dollar indices.
# DXY was normalized to 100 in March 1973; DTWEXBGS and DTWEXAFEGS were
# normalized to 100 in January 2006. All three share the same basis value,
# so a single anchor produces a mechanical "above/below the index design
# origin" reading.
DOLLAR_LEVEL_ANCHOR: float = 100.0

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Shared loaders — split by dimension so the two 1D regimes can each
# pull only what they need.
# ─────────────────────────────────────────────────────────────────────────────


def _load_level_indicators(z_window: int) -> dict[str, pd.Series]:
    """Anchored level z-scores for DXY + Trade-Weighted USD baskets.

    Anchor = 100 (basis-year value shared by all three indices). Rolling
    std dev is still used for scale so magnitudes stay comparable to other
    regimes, but the zero point is fixed at the basis value instead of the
    drifting rolling mean.
    """
    rows: dict[str, pd.Series] = {}

    dxy_daily = _load("DXY INDEX:PX_LAST")
    if not dxy_daily.empty:
        dxy = dxy_daily.resample("ME").last()
        rows["lv_DXY"] = zscore_anchored(
            dxy, DOLLAR_LEVEL_ANCHOR, z_window
        ).rename("lv_DXY")

    twusd_daily = _load("DTWEXBGS")
    if not twusd_daily.empty:
        twusd = twusd_daily.resample("ME").last()
        rows["lv_TWUSD"] = zscore_anchored(
            twusd, DOLLAR_LEVEL_ANCHOR, z_window
        ).rename("lv_TWUSD")

    twusd_afe_daily = _load("DTWEXAFEGS")
    if not twusd_afe_daily.empty:
        twusd_afe = twusd_afe_daily.resample("ME").last()
        rows["lv_TWUSD_AFE"] = zscore_anchored(
            twusd_afe, DOLLAR_LEVEL_ANCHOR, z_window
        ).rename("lv_TWUSD_AFE")

    return rows


def _load_trend_indicators(z_window: int) -> dict[str, pd.Series]:
    """3-month absolute ROC z-scores for the same dollar baskets.

    3M wins on raw spread (7.8%) and DD avoidance (89%) per the original
    Tier 1 sweep. Longer trends increase persistence but dilute the
    turning-point signal that drives forward-return separation.
    """
    rows: dict[str, pd.Series] = {}

    dxy_daily = _load("DXY INDEX:PX_LAST")
    if not dxy_daily.empty:
        dxy = dxy_daily.resample("ME").last()
        rows["tr_DXY"] = zscore_roc(dxy, z_window, use_pct=False).rename("tr_DXY")

    twusd_daily = _load("DTWEXBGS")
    if not twusd_daily.empty:
        twusd = twusd_daily.resample("ME").last()
        rows["tr_TWUSD"] = zscore_roc(
            twusd, z_window, use_pct=False
        ).rename("tr_TWUSD")

    twusd_afe_daily = _load("DTWEXAFEGS")
    if not twusd_afe_daily.empty:
        twusd_afe = twusd_afe_daily.resample("ME").last()
        rows["tr_TWUSD_AFE"] = zscore_roc(
            twusd_afe, z_window, use_pct=False
        ).rename("tr_TWUSD_AFE")

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# DollarLevelRegime — 2-state Strong/Weak from absolute level
# ─────────────────────────────────────────────────────────────────────────────


class DollarLevelRegime(Regime):
    """2-state dollar level regime (Strong vs Weak vs basis-year 100).

    Target & justification: EEM US EQUITY @ 6M forward return. An anchored
    z-score of DXY + trade-weighted USD baskets vs the basis-year value
    of 100 captures structural dollar richness/cheapness without drifting
    with the cycle itself. A rolling 8y z-score fails because an 8y
    window is roughly one dollar cycle — the rolling mean converges to
    whatever the dollar has been doing recently, so "Strong" stops firing
    after a decade of strength. The anchored version fires whenever the
    dollar is meaningfully above/below its structural reference,
    preserving the mean-reverting forward-return signal.
    """

    name = "DollarLevel"
    dimensions = ["Level"]
    states = ["Strong", "Weak"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        return _load_level_indicators(z_window)

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Level": "lv_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Level probability to 2 dollar level states.

        Level_P high → dollar STRONG (above rolling history)
        Level_P low  → dollar WEAK
        """
        lv = dim_probs["Level"]
        return {
            "P_Strong": lv,
            "P_Weak":   1.0 - lv,
        }


# ─────────────────────────────────────────────────────────────────────────────
# DollarTrendRegime — 2-state Appreciating/Depreciating from 3M momentum
# ─────────────────────────────────────────────────────────────────────────────


class DollarTrendRegime(Regime):
    """2-state dollar trend regime (Appreciating vs Depreciating).

    Target & justification: EEM US EQUITY @ 6M forward return. The 3M ROC
    of trade-weighted USD captures the turning-point signal — the original
    Tier 1 sweep showed that the rate of change drives forward-return
    separation more cleanly than the level alone.
    """

    name = "DollarTrend"
    dimensions = ["Trend"]
    states = ["Appreciating", "Depreciating"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        return _load_trend_indicators(z_window)

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Trend": "tr_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Trend probability to 2 dollar trend states.

        Trend_P high → dollar APPRECIATING
        Trend_P low  → dollar DEPRECIATING
        """
        tr = dim_probs["Trend"]
        return {
            "P_Appreciating": tr,
            "P_Depreciating": 1.0 - tr,
        }
