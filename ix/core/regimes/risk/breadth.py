"""BreadthRegime — 2-state equity market breadth regime.

Thesis
------
Price can rise on narrow leadership while the majority of stocks are
rolling over — the classic pre-top breadth divergence. Breadth regimes
capture this by scoring *how many* names are participating in the trend,
not just *whether* the index is up.

This regime measures two orthogonal breadth dimensions:
  1. **Participation** — % of index constituents above their 200-day MA
  2. **Momentum** — McClellan Oscillator (exponential advance-decline)

When both are broad and rising, the trend is healthy. When one or both
are narrow and falling, the trend is distributing. Breadth is a leading
indicator at tops (divergence appears 1–3 months before price rolls)
and a lagging confirmation at bottoms (breadth thrusts mark the low).

Orthogonal to the existing 9 axes: none of them measure equity internals.
Orthogonal specifically to Growth (which uses macro data) and to Liquidity
(which uses credit/FX/CB data) — breadth is a price-based microstructure
signal.

States
------
- **Broad**    (Breadth_Z > 0): Wide participation, positive McClellan.
  Healthy trend. Forward SPY 3m returns: positive, low drawdown risk.
- **Narrow**   (Breadth_Z ≤ 0): Narrow participation, negative/weakening
  McClellan. Distribution or washout. Forward SPY 3m returns: negative
  on average, but contrarian at extreme washouts (<20% above 200DMA).

Indicators (4, all b_*)
    b_Above200DMA       — % of S&P 1500 constituents above their 200DMA
    b_Above50DMA        — % of S&P 1500 constituents above their 50DMA
    b_McClellan         — McClellan Oscillator (EMA19 − EMA39 of A-D line)
    b_NHNL              — New Highs − New Lows / total (10d rolling)

Publication lag: zero (all market data).
Target: SPY 3M fwd. Locked.

Status: DRAFT — depends on breadth feeds that may not yet be in the
timeseries store. The class uses standard Bloomberg / S&P codes; if they
are unavailable `_load_indicators` degrades silently and returns a
reduced composite. Seed data needed: S5TH (% above 200DMA), S5FI (% above
50DMA), NYSE McClellan Oscillator, NHIGH/NLOW NYSE daily.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class BreadthRegime(Regime):
    """2-state equity market breadth regime (Broad × Narrow)."""

    name = "Breadth"
    dimensions = ["Breadth"]
    states = ["Broad", "Narrow"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # b_Above200DMA — % of S&P 500 constituents above their 200-day
        # moving average. Primary long-term participation gauge. Top |IC|
        # post-2010 (-0.129 on SPY 3M — contrarian, high breadth = rally
        # exhaustion).
        p200 = _load("SPX INDEX:PCT_ABOVE_MAVG_200")
        if not p200.empty:
            rows["b_Above200DMA"] = zscore(p200, z_window).rename("b_Above200DMA")

        # [DROPPED 2026-04-12: b_Above50DMA and b_DivergenceSpread — the
        #  all-regimes triage showed r=+0.98 (b_Above200DMA ↔ b_Above50DMA),
        #  r=+0.99 (b_Above50DMA ↔ b_DivergenceSpread), and r=+0.95
        #  (b_Above200DMA ↔ b_DivergenceSpread). All three are derivatives
        #  of the same underlying % above moving average signal — adding
        #  them triple-counts the same information in the composite
        #  without orthogonal content. b_Above200DMA alone carries the
        #  full signal. If McClellan / NHNL / A-D data ever lands in the
        #  DB, add those (genuinely orthogonal dimensions) as the second
        #  and third inputs instead.]

        if not rows:
            log.warning(
                "Breadth: no indicators loaded. Expected DB code: "
                "'SPX INDEX:PCT_ABOVE_MAVG_200'."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Breadth": "b_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Breadth probability to 2 states.

        Broad  = healthy participation, rising McClellan.
        Narrow = thin participation, distribution or washout.
        Forward-return mapping is COINCIDENT at the Broad end
        (healthy breadth → forward returns positive) and CONTRARIAN at
        the deep-Narrow end (washout → mean-reversion rally forward).
        """
        bp = dim_probs["Breadth"]
        return {
            "P_Broad":  bp,
            "P_Narrow": 1.0 - bp,
        }
