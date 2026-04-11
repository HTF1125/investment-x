"""LiquidityImpulseRegime — 2-state US liquidity quantity regime.

Thesis
------
The existing `LiquidityRegime` is *price-based* — it reads credit spreads,
the yield curve, the dollar, balance sheet YoY. This regime is
*quantity-based*: it measures the 3-month rate of change in the pool of
cash actually available to chase risk assets in the US financial system.

Since 2022 the dominant liquidity driver has not been Fed asset purchases
(balance sheet has been shrinking) but Treasury cash management: when the
TGA is drawn down, cash floods into the banking system; when RRP is
unwound, the same; when the Fed's balance sheet contracts, the opposite.
Those three moves are the *impulse*, and they are not captured by the
existing LiquidityRegime which uses YoY balance sheet only.

**Hard rule compliance:** this regime is US-specific (Fed BS + TGA + RRP),
not Global M2. It explicitly avoids the banned Global M2 signal. The
3-month rate of change, not the level, is the signal.

**Orthogonality guard:** re-check 60m correlation vs the existing
`LiquidityRegime` after first full backtest. Expected |ρ| < 0.50 because
the existing regime uses level-based price signals and this uses
quantity-based flow signals.

States
------
- **Expanding**  (Impulse_Z > 0): Net liquidity is rising over the last
  3 months. Risk assets have a tailwind.
  Forward SPY 3m: positive.
- **Contracting** (Impulse_Z ≤ 0): Net liquidity is falling over the last
  3 months. Risk assets face a headwind.
  Forward SPY 3m: negative, higher drawdown risk.

Indicators (3, all li_*)
    li_TGA           — US Treasury General Account (WTREGEN), 3M change,
                        INVERTED (TGA drawdown = cash into system).
    li_RRP           — Fed reverse repo facility balance (RRPONTSYD), 3M
                        change, INVERTED (RRP unwind = cash released).
    li_NetLiq        — Net liquidity = WALCL − TGA − RRP, 3M change.
                        The aggregate (IC +0.142 full, +0.142 post).

Publication lag: 1 week (WALCL is weekly). Uses month-end resampling.
Target: SPY 3M fwd. Locked.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class LiquidityImpulseRegime(Regime):
    """2-state US liquidity quantity impulse regime (Expanding × Contracting)."""

    name = "LiquidityImpulse"
    dimensions = ["Impulse"]
    states = ["Expanding", "Contracting"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. li_TGA — Treasury General Account balance. INVERTED because
        #    TGA drawdowns release cash into the banking system → bullish
        #    for risk.
        tga = _load("WTREGEN")
        if not tga.empty:
            rows["li_TGA"] = zscore(-tga.diff(3), z_window).rename("li_TGA")

        # 3. li_RRP — Reverse repo facility balance. INVERTED because
        #    RRP unwinds release cash (money market funds redeploy it into
        #    T-bills and eventually risk assets).
        rrp = _load("RRPONTSYD")
        if not rrp.empty:
            rows["li_RRP"] = zscore(-rrp.diff(3), z_window).rename("li_RRP")

        # 4. li_NetLiq — Net liquidity (WALCL - TGA - RRP), 3M change.
        #    The aggregate plumbing variable. IC: full +0.142, post +0.142
        #    (no pre-2010 data for RRP, which started in 2013).
        walcl = _load("WALCL")
        if not walcl.empty and not tga.empty and not rrp.empty:
            nl = walcl - tga.reindex(walcl.index, method="ffill") - rrp.reindex(
                walcl.index, method="ffill"
            )
            rows["li_NetLiq"] = zscore(nl.diff(3), z_window).rename("li_NetLiq")

        if not rows:
            log.warning(
                "LiquidityImpulse: no indicators loaded. Seed WALCL / WTREGEN / "
                "RRPONTSYD from FRED."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Impulse": "li_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Impulse composite probability to 2 states.

        Expanding  = net liquidity rising. Forward returns positive
                     (coincident).
        Contracting = net liquidity falling. Forward returns negative.
        """
        ip = dim_probs["Impulse"]
        return {
            "P_Expanding":   ip,
            "P_Contracting": 1.0 - ip,
        }
