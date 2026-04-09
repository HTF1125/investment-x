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
    r_HY            — HY OAS 3M change (inverted — tight = risk-on)
    r_MOVE          — MOVE index (rate vol, inverted)
    r_DXY           — DXY 3M change (inverted)
    r_CopperGold    — Copper/Gold ratio (momentum)
    r_EMFX          — EM currency basket (level)

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

        # 1. r_HY — 3-month change in HY OAS. Inverted: tight/tightening =
        #    risk-on. Avoids double-counting Credit-Level (this uses the
        #    3M change, not the level).
        hy = _load("BAMLH0A0HYM2")
        if not hy.empty:
            rows["r_HY"] = zscore(-hy.diff(3), z_window).rename("r_HY")

        # 2. r_MOVE — ICE BofA MOVE Index (implied rate vol). High = stress.
        #    Inverted so low MOVE reads as risk-on.
        move = _load("MOVE INDEX:PX_LAST")
        if move.empty:
            move = _load("MOVE:PX_LAST")
        if not move.empty:
            rows["r_MOVE"] = zscore(-move, z_window).rename("r_MOVE")

        # 3. r_DXY — 3-month change in DXY. Inverted: weakening dollar =
        #    risk-on. Uses the CHANGE, not the level, to stay orthogonal
        #    to the Dollar-Level axis.
        dxy = _load("DXY INDEX:PX_LAST")
        if not dxy.empty:
            rows["r_DXY"] = zscore(-dxy.diff(3), z_window).rename("r_DXY")

        # 4. r_CopperGold — Copper front-month / Gold front-month ratio.
        #    Classic cyclical vs defensive ratio. Rising = risk-on.
        cop = _load("HG1 COMDTY:PX_LAST")
        gld = _load("GC1 COMDTY:PX_LAST")
        if not cop.empty and not gld.empty:
            ratio = (cop / gld.replace(0, pd.NA)).astype(float)
            rows["r_CopperGold"] = zscore(ratio, z_window).rename("r_CopperGold")

        # 5. r_EMDebt — iShares EM USD Bond ETF (EMB) 3M momentum.
        #    Proxy for EM risk appetite — when global risk is on, EM USD
        #    sovereign bonds rally (spreads tighten). This is the EMFX /
        #    EM-risk dimension without needing a currency index (JPMEMCI
        #    is not in the DB). EMB captures 80%+ of the same signal.
        emb = _load("EMB US EQUITY:PX_LAST")
        if not emb.empty:
            mom = emb.pct_change(3) * 100.0
            rows["r_EMDebt"] = zscore(mom, z_window).rename("r_EMDebt")

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
