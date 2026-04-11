"""Credit regimes — split into two composable 1D axis regimes.

The credit cycle is one of the most reliable forward-return signals in
macro: corporate spreads transmit to default cycles, equity drawdowns,
and forward returns over 3-9 month horizons (Verdad Capital research).

Following the broader 1D-only framework used by ``growth`` and ``inflation``,
the credit cycle is decomposed into two **independently composable** axis
regimes:

* :class:`CreditLevelRegime` — how WIDE are spreads vs their rolling
  history (Wide / Tight). 2-state, axis category.
* :class:`CreditTrendRegime` — are spreads RISING or falling
  (Widening / Tightening). 2-state, axis category.

Composing them via the multi-axis composer reproduces the original 4-state
Verdad credit cycle (Expansion / LateCycle / Stress / Recovery) mechanically
— but the user controls whether they want a single dimension, both, or to
mix credit axes with growth/inflation/dollar.

Indicators
----------
The same 3 input series feed both regimes — the difference is purely the
transform applied (level z-score vs ROC z-score):

Level dimension (lv_*) — pure level z-score:
    lv_HY_OAS    — ICE BofA HY Master OAS (BAMLH0A0HYM2)
    lv_IG_OAS    — ICE BofA IG Corporate OAS (BAMLC0A0CM)
    lv_BBB_OAS   — ICE BofA BBB Corporate OAS (BAMLC0A4CBBB)

Trend dimension (tr_*) — pure 3-month ROC z-score:
    tr_HY_OAS    — 3m absolute change in HY OAS
    tr_IG_OAS    — 3m absolute change in IG OAS
    tr_BBB_OAS   — 3m absolute change in BBB OAS

Credit trend is **designed as a phase_pair building block** (see ``phase_pair``
on the registration). As a standalone signal against HYG@6M it posts only
0.21 Sharpe delta (below the T1.4 bar) because of the continuation-vs-reversion
ambiguity inherent in HY ETF forward returns. Composed with ``credit_level``
via the :class:`MultiDimRegimeAnalyzer` composition path, the 4-state joint
regime (the Verdad credit cycle: Expansion/LateCycle/Stress/Recovery) recovers
clean separation. Use it composed, not standalone.

Source
------
Verdad Capital Research, "The Best Macro Indicator: Credit Spreads"
Cliffwater LLC: HY spread regime classification
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore, zscore_roc

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Shared loaders — split by dimension so the two 1D regimes can each
# pull only what they need.
# ─────────────────────────────────────────────────────────────────────────────


def _load_level_indicators(z_window: int) -> dict[str, pd.Series]:
    """Pure level z-score for HY option-adjusted spread.

    2026-04-12 rebuild: dropped the IG and BBB level variants after the
    all-regimes triage found:
    - lv_IG_OAS ↔ lv_BBB_OAS: r = +0.99 (IG and BBB indices are
      effectively identical as level z-scores)
    - lv_HY_OAS ↔ lv_BBB_OAS: r = +0.94
    - lv_HY_OAS ↔ lv_IG_OAS:  r = +0.93
    All three had strong individual IC on HYG 6M (+0.44 to +0.48) but
    they were triple-counting the same credit-spread level signal.
    Kept lv_HY_OAS because (a) it's the highest |IC| at +0.482 and
    (b) HY is the highest-beta credit segment so it's the most sensitive
    to cycle turning points.
    """
    rows: dict[str, pd.Series] = {}

    hy_daily = _load("BAMLH0A0HYM2")
    if not hy_daily.empty:
        hy = hy_daily.resample("ME").last()
        rows["lv_HY_OAS"] = zscore(hy, z_window).rename("lv_HY_OAS")

    return rows


def _load_trend_indicators(z_window: int) -> dict[str, pd.Series]:
    """3-month absolute ROC z-scores for IG OAS.

    Captures the turning-point signal that drives forward-return
    separation. Longer windows go stale; shorter windows are noisy;
    acceleration (2nd derivative) introduces more variance than signal.
    The 3-month diff is empirically the best single-window choice —
    tested against 1m, 6m, and acceleration.

    2026-04-12 rebuild: dropped the HY and BBB ROC variants after the
    all-regimes triage found:
    - tr_IG_OAS ↔ tr_BBB_OAS: r = +1.00 (IG and BBB indices are
      effectively identical at the ROC level)
    - tr_HY_OAS ↔ tr_BBB_OAS: r = +0.93
    - tr_HY_OAS ↔ tr_IG_OAS:  r = +0.93
    Three near-duplicate inputs were triple-counting the same credit-
    spread turning-point signal. The regime is a known-weak standalone
    signal (post-2010 IC -0.032 on HYG 6M, all three below the
    |IC| ≥ 0.03 floor) designed to pair with CreditLevelRegime via the
    phase_pair mechanism; this single-input trend dimension keeps the
    building-block semantics without the redundant IC drag.
    """
    rows: dict[str, pd.Series] = {}

    ig_daily = _load("BAMLC0A0CM")
    if not ig_daily.empty:
        ig = ig_daily.resample("ME").last()
        rows["tr_IG_OAS"] = zscore_roc(
            ig, z_window, use_pct=False
        ).rename("tr_IG_OAS")

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# CreditLevelRegime — 2-state Wide/Tight from absolute spread level
# ─────────────────────────────────────────────────────────────────────────────


class CreditLevelRegime(Regime):
    """2-state credit level regime (spreads Wide vs Tight vs rolling history).

    Target & justification: HYG US EQUITY @ 6M forward return. Pure level
    of corporate spreads captures sustained credit-cycle regimes — when
    spreads are structurally rich vs their 8y history, default risk premia
    are embedded and forward returns mean-revert downward.
    """

    name = "CreditLevel"
    dimensions = ["Level"]
    states = ["Wide", "Tight"]

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
        """Map Level probability to 2 credit level states.

        Level_P high → spreads WIDE (above rolling history)
        Level_P low  → spreads TIGHT
        """
        lv = dim_probs["Level"]
        return {
            "P_Wide":  lv,
            "P_Tight": 1.0 - lv,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CreditTrendRegime — 2-state Widening/Tightening from 3M momentum
# ─────────────────────────────────────────────────────────────────────────────


class CreditTrendRegime(Regime):
    """2-state credit trend regime (spreads Widening vs Tightening).

    Target & justification: HYG US EQUITY @ 6M forward return. The 3M ROC
    of spreads captures the turning-point signal — Verdad's research
    framework showed that spread direction drives forward-return
    separation. Intended use: **composed with** :class:`CreditLevelRegime`
    via the phase_pair mechanism to reproduce the 4-state Verdad cycle.
    Standalone signal is below the T1.4 vol-normalized spread bar; the
    joint composition is where the edge lives.
    """

    name = "CreditTrend"
    dimensions = ["Trend"]
    states = ["Widening", "Tightening"]

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
        """Map Trend probability to 2 credit trend states.

        Trend_P high → spreads WIDENING (rising)
        Trend_P low  → spreads TIGHTENING (falling)
        """
        tr = dim_probs["Trend"]
        return {
            "P_Widening":   tr,
            "P_Tightening": 1.0 - tr,
        }
