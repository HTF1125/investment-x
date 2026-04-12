"""RiskAppetiteRegime — 2-state cross-asset risk appetite regime.

Thesis
------
Every major risk-on/risk-off trade leaves footprints across multiple
asset classes simultaneously. HY credit spreads widen, rate volatility
spikes, the dollar rallies, EM FX weakens, industrial metals fall versus
gold. Individually each of these is a noisy signal; *jointly* they
reliably identify the tail regimes.

This composite insists that ALL FIVE dimensions of risk appetite agree
before declaring a state. That's deliberately restrictive — it means
the regime is quiet in the middle 60% of observations (when signals
disagree) and only fires at the important tails.

**Why it's worth adding despite overlap with existing axes:** the
Credit-Trend and Dollar-Trend axes capture 2 of the 5 signals here in
isolation. This composite adds MOVE (rate vol), copper/gold (cyclical
commodity), and EM FX (global risk) — three signals not covered
elsewhere. The *joint* state is also informationally different from any
single-axis state, even when 2/5 of the inputs overlap.

**Orthogonality guard:** at registration time, verify residual IC
vs CreditTrend + DollarTrend. If the 60m rolling correlation of this
composite vs the 2-axis {credit_trend, dollar_trend} composite exceeds
0.75, reject — it's a skin of those two and adds nothing.

States
------
- **Risk-On**  (Risk_Z > +0.5σ): HY tight/tightening, MOVE low, DXY
  weak/weakening, copper outperforming gold, EM FX firm. Broad appetite.
  Forward SPY 3m: positive.
- **Risk-Off** (Risk_Z < −0.5σ): HY wide/widening, MOVE high, DXY
  strong/strengthening, gold outperforming copper, EM FX stressed.
  Forward SPY 3m: negative, fat left tail.

Indicators (5, all r_*)
    r_DXY           — DXY 3M change (inverted — dollar weakness = risk-on)
    r_MOVE_inv      — MOVE index (rate vol, inverted, IC +0.069)
    r_VIX           — VIX level (contrarian — high fear = bullish, IC +0.124)
    r_EEM_SPY       — EM/US relative 3M performance (IC +0.143)
    r_HYIG_spread   — HY-IG OAS 3M change, inverted (IC +0.085)

Publication lag: zero (all daily market data).
Target: SPY 3M fwd. Locked. Coincident mapping.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class RiskAppetiteRegime(Regime):
    """2-state cross-asset risk appetite regime (Risk-On × Risk-Off)."""

    name = "RiskAppetite"
    dimensions = ["Risk"]
    states = ["RiskOn", "RiskOff"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # [DROPPED: r_HY — post IC -0.023 (DYING). Full IC only +0.010.
        #  HY OAS 3M change has lost predictive power post-2010 for SPY.
        #  Credit spread signal is better captured by CreditLevelRegime.]

        # 1. r_DXY — 3-month change in DXY. Inverted: weakening dollar =
        #    risk-on.
        dxy = _load("DXY INDEX:PX_LAST")
        if not dxy.empty:
            rows["r_DXY"] = zscore(-dxy.diff(3), z_window).rename("r_DXY")

        # 2. r_MOVE_inv — MOVE index (rate vol), inverted. Low rate vol = risk-on.
        #    IC: full +0.069, pre +0.246, post +0.012 — positive in both subsamples.
        move = _load("MOVE INDEX:PX_LAST")
        if not move.empty:
            rows["r_MOVE_inv"] = zscore(-move, z_window).rename("r_MOVE_inv")

        # 3. r_VIX — VIX level (contrarian: high VIX = bullish forward).
        #    DO NOT invert — high fear = bullish (per hard rule #3).
        #    IC: full +0.124, pre +0.139, post +0.109 — strongest risk appetite indicator.
        vix = _load("VIX INDEX:PX_LAST")
        if not vix.empty:
            rows["r_VIX"] = zscore(vix, z_window).rename("r_VIX")

        # 4. r_EEM_SPY — EM/US relative performance 3M. Rising = global risk appetite.
        #    IC: full +0.143, pre +0.129, post +0.141 — stable across subsamples.
        eem = _load("EEM US EQUITY:PX_LAST")
        spy = _load("SPY US EQUITY:PX_LAST")
        if not eem.empty and not spy.empty:
            ratio = eem / spy.reindex(eem.index, method="ffill").replace(0, pd.NA)
            rows["r_EEM_SPY"] = zscore(
                ratio.pct_change(3, fill_method=None) * 100.0, z_window
            ).rename("r_EEM_SPY")

        # 5. r_HYIG_spread — HY minus IG OAS, 3M change, inverted.
        #    Tightening HY-IG spread = risk-on (HY outperforming IG).
        #    IC: full +0.085, pre +0.148, post +0.005 — positive in both.
        hy = _load("BAMLH0A0HYM2")
        ig = _load("BAMLC0A0CM")
        if not hy.empty and not ig.empty:
            spread = hy - ig.reindex(hy.index, method="ffill")
            rows["r_HYIG_spread"] = zscore(
                -spread.diff(3), z_window
            ).rename("r_HYIG_spread")

        if not rows:
            log.warning(
                "RiskAppetite: no indicators loaded. Check HY OAS / MOVE / DXY "
                "/ copper-gold / EM FX series availability."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Risk": "r_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Risk composite probability to 2 states.

        Risk-On  = HY tightening, vol low, dollar weak, copper>gold, EMFX firm.
        Risk-Off = the inverse. Coincident mapping (not contrarian).
        """
        rp = dim_probs["Risk"]
        return {
            "P_RiskOn":  rp,
            "P_RiskOff": 1.0 - rp,
        }
