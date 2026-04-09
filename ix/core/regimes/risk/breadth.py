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

        # 1. b_Above200DMA — % of S&P 500 constituents above their 200-day
        #    moving average. Primary long-term participation gauge.
        p200 = _load("SPX INDEX:PCT_ABOVE_MAVG_200")
        if not p200.empty:
            rows["b_Above200DMA"] = zscore(p200, z_window).rename("b_Above200DMA")

        # 2. b_Above50DMA — % of S&P 500 above 50-day MA. Faster-reacting
        #    near-term participation gauge.
        p50 = _load("SP50:FMA_PCT_ABOVE_50")
        if not p50.empty:
            rows["b_Above50DMA"] = zscore(p50, z_window).rename("b_Above50DMA")

        # 3. b_DivergenceSpread — synthetic breadth divergence signal.
        #    (% above 50DMA) − (% above 200DMA). When positive the near-term
        #    trend is healthier than the long-term trend (early-cycle
        #    recovery) or when extreme the long-term trend is weakening
        #    (late-cycle rally masking deterioration). When negative the
        #    long-term trend is intact but near-term has rolled over
        #    (intermediate correction). Captures the divergence between
        #    the two participation windows without needing McClellan data.
        if not p200.empty and not p50.empty:
            p200_m = p200.reindex(p50.index, method="ffill")
            spread = p50 - p200_m
            rows["b_DivergenceSpread"] = zscore(spread, z_window).rename(
                "b_DivergenceSpread"
            )

        if not rows:
            log.warning(
                "Breadth: no indicators loaded. Expected DB codes: "
                "'SPX INDEX:PCT_ABOVE_MAVG_200' and 'SP50:FMA_PCT_ABOVE_50'."
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
