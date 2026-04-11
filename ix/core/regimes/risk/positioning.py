"""PositioningRegime — 3-state contrarian positioning regime.

Thesis
------
When everyone who was going to buy has bought, forward returns are low.
When everyone who was going to sell has sold, forward returns are high.
Positioning is a reliable contrarian indicator at extremes — the trick
is triangulating across independent measures of "the crowd." This regime
blends two direct equity-positioning signals measured on different
venues (survey vs derivatives) into a composite whose tails correspond
to the rarest (and most actionable) crowd configurations.

Indicators (2, all p_*). Both NOT inverted: high composite z = crowd
is long = contrarian bearish for forward returns.

    p_NAAIM       — NAAIM Exposure Index (0-200 bullish). Active-
                    manager average equity exposure. 1027 weekly obs
                    since 2006-07.
    p_CFTC_SP500  — CFTC Commitments of Traders net positioning
                    (long - short) on E-mini S&P 500 futures.
                    1336 weekly obs since 2000-09.

States
------
- **ExtremeLong**  (Pos_Z > +1.0): Crowd is crowded long, contrarian
  bearish. Forward SPY 3m: below average, elevated drawdown risk.
- **Neutral**      (-1.0 ≤ Pos_Z ≤ +1.0): Normal positioning, no signal.
- **Capitulation** (Pos_Z < -1.0): Crowd has capitulated, contrarian
  bullish. Forward SPY 3m: strongly positive, highest-value state.

**Hard rule compliance:** this does not invert any contrarian gauge
forbidden by Hard Rule #3 (VIX / FCI / put-call). Positioning inputs
are used as-is; the contrarian interpretation lives in the state
mapping (high crowd positioning -> contrarian-bearish ExtremeLong
state), not in the sign of the inputs.

Publication lag: NAAIM weekly (same-week), CFTC weekly (3-day reporting
lag). Target: SPY 3M fwd.

History / audit notes
---------------------
- 2026-04-12 rebuilt after the all-regimes triage flagged this as
  DEGENERATE (4 rows built, 100% Neutral):
  * Previous loaders referenced `CFTC_GOLD_NET:PX_LAST` /
    `CFTC_OIL_NET:PX_LAST` which only had 61 obs from 2025-01 -
    insufficient for a z_window=96 rolling baseline.
  * Replaced with `NAAIM_EXPOSURE:PX_LAST` (1027 obs since 2006) and
    the correct FactSet CFTC long/short codes
    (`CFTNCLALLSP500EMINCMEF_US` / `CFTNCSALLSP500EMINCMEF_US`,
    1336 obs since 2000). Net = long - short.
  * Gold / Oil positioning dropped from the composite - those are
    commodity-overlay positioning, a different channel from direct
    equity positioning. They belong in a separate regime, not here.
  * smooth_halflife 3 -> 1 in the registry (same degeneracy fix as
    cb_surprise - hl=3 collapses 3-state regimes to constant-Neutral
    because smoothed tail probabilities never cross argmax threshold).
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class PositioningRegime(Regime):
    """3-state contrarian positioning regime (Extreme Long × Neutral × Capitulation)."""

    name = "Positioning"
    dimensions = ["Positioning"]
    states = ["ExtremeLong", "Neutral", "Capitulation"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # p_NAAIM — NAAIM active-manager equity exposure (0-200 scale).
        # NOT inverted: high NAAIM = crowded long = high composite z
        # maps to the ExtremeLong (contrarian bearish) state via the
        # sigmoid + state projection downstream.
        naaim = _load("NAAIM_EXPOSURE:PX_LAST")
        if not naaim.empty:
            rows["p_NAAIM"] = zscore(naaim, z_window).rename("p_NAAIM")

        # p_CFTC_SP500 — CFTC Commitments of Traders net positioning on
        # E-mini S&P 500 futures. net = long - short across the reporting
        # aggregate. NOT inverted: high net long = crowd is long =
        # contrarian bearish (same sign convention as NAAIM).
        cftc_long = _load("CFTNCLALLSP500EMINCMEF_US")
        cftc_short = _load("CFTNCSALLSP500EMINCMEF_US")
        if not cftc_long.empty and not cftc_short.empty:
            net = (cftc_long - cftc_short).dropna()
            if not net.empty:
                rows["p_CFTC_SP500"] = zscore(net, z_window).rename("p_CFTC_SP500")

        if not rows:
            log.warning(
                "Positioning: no indicators loaded. Expected DB codes: "
                "'NAAIM_EXPOSURE:PX_LAST', "
                "'CFTNCLALLSP500EMINCMEF_US', 'CFTNCSALLSP500EMINCMEF_US'."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Positioning": "p_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Positioning composite z-score to 3 states.

        We use a *tri-modal* mapping because the signal is only useful at
        the tails — the middle 60% of observations carry no information.

        Extreme Long    (P > ~0.84, i.e. z > +1.0)
        Neutral         (0.16 ≤ P ≤ 0.84)
        Capitulation    (P < ~0.16, i.e. z < −1.0)

        The sigmoid has already squashed z → P, so we recover approximate
        thresholds and build triangular state probabilities that sum to 1.
        """
        p = dim_probs["Positioning"]
        # Thresholds on the *probability* (sigmoid output), ~equivalent to
        # z-score ±1.0 at default sensitivity=2.
        lo = 0.30
        hi = 0.70
        p_long = ((p - hi) / (1.0 - hi)).clip(lower=0, upper=1)
        p_cap = ((lo - p) / lo).clip(lower=0, upper=1)
        p_neutral = (1.0 - p_long - p_cap).clip(lower=0)
        # Re-normalize
        total = (p_long + p_neutral + p_cap).clip(lower=1e-9)
        return {
            "P_ExtremeLong":  p_long / total,
            "P_Neutral":      p_neutral / total,
            "P_Capitulation": p_cap / total,
        }
