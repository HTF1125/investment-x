"""LiquidityRegime — pure central-bank quantity regime.

States
------
- **Easing**:     Central-bank quantities expanding — balance sheets growing,
                  net liquidity rising, TGA drawing down, credit impulse up.
                  Historically bullish for risk assets across all horizons.
- **Tightening**: Central-bank quantities contracting — balance sheets
                  shrinking, net liquidity falling, TGA refilling, credit
                  impulse negative. Historically bearish for risk assets.

Indicators (5, all ``l_*``)
    l_G4_BS_YoY      — G4 (Fed + ECB + BoJ + PBoC) aggregate balance sheet YoY
    l_FedAssets_YoY  — Fed total assets (WALCL) YoY
    l_FedNetLiq_3M   — Fed net liquidity (assets − TGA − RRP) 3-month change
    l_TGA_Drawdown   — Treasury General Account 13-week drawdown (inverted
                       so drawdown = positive liquidity injection)
    l_CreditImpulse  — US bank credit impulse (2nd derivative of credit
                       growth), leads equities 6-9 months

Design principle
----------------
**This regime measures quantity, not price.** The previous version mixed
HY OAS, IG spreads, DXY and the yield curve into the composite, which
double-counted signals already covered by :class:`CreditLevelRegime`,
:class:`DollarLevelRegime`, and :class:`YieldCurveRegime`. A liquidity
regime should measure what those price-based regimes cannot: the actual
flow of central-bank money through the plumbing.

This is the Hedgeye / 42 Macro / Global Macro Investor definition of
"liquidity" — net central-bank balance-sheet expansion, TGA drains, and
credit impulse. It is orthogonal to the credit/dollar/curve regimes by
construction, so composing ``liquidity`` with any of them produces genuinely
new information rather than a redundant correlation.

Target & Justification
----------------------
Target:   SPY US EQUITY (S&P 500)
Horizon:  3 months forward return
Rationale: Central-bank liquidity transmission to equity markets runs
          2-4 months via the portfolio-rebalancing channel (Fed reserves
          → bank deposits → risk asset allocations). 3M is the shortest
          horizon where the signal has time to propagate cleanly. Tested
          against the new vol-normalized T1.4 bar (0.25 Sharpe delta).
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series, zscore

log = logging.getLogger(__name__)


class LiquidityRegime(Regime):
    """Central-bank liquidity → 2-state regime (Easing / Tightening)."""

    name = "Liquidity"
    dimensions = ["Liquidity"]
    states = ["Easing", "Tightening"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. G4 balance sheet YoY (aggregate Fed + ECB + BoJ + PBoC)
        try:
            from ix.core.indicators.central_bank import g4_balance_sheet_yoy

            g4_yoy = g4_balance_sheet_yoy().resample("ME").last()
            if not g4_yoy.empty:
                rows["l_G4_BS_YoY"] = zscore(g4_yoy, z_window).rename(
                    "l_G4_BS_YoY"
                )
        except Exception as exc:
            log.warning("G4 balance sheet load failed: %s", exc)

        # 2. Fed total assets YoY
        try:
            from ix.core.indicators.central_bank import fed_assets_yoy

            fed_yoy = fed_assets_yoy().resample("ME").last()
            if not fed_yoy.empty:
                rows["l_FedAssets_YoY"] = zscore(fed_yoy, z_window).rename(
                    "l_FedAssets_YoY"
                )
        except Exception as exc:
            log.warning("Fed assets YoY load failed: %s", exc)

        # 3. Fed net liquidity (assets − TGA − RRP), 3-month change
        try:
            from ix.core.indicators.liquidity import fed_net_liquidity

            fnl = fed_net_liquidity().resample("ME").last()
            if not fnl.empty:
                fnl_3m = fnl.diff(3)
                rows["l_FedNetLiq_3M"] = zscore(fnl_3m, z_window).rename(
                    "l_FedNetLiq_3M"
                )
        except Exception as exc:
            log.warning("Fed net liquidity load failed: %s", exc)

        # 4. TGA 13-week drawdown (drawdown = liquidity injection, so INVERT
        # the raw series since the indicator returns positive when the TGA
        # is being REFILLED — we want positive = injection)
        try:
            from ix.core.indicators.liquidity import tga_drawdown

            tga = tga_drawdown().resample("ME").last()
            if not tga.empty:
                rows["l_TGA_Drawdown"] = zscore(-tga, z_window).rename(
                    "l_TGA_Drawdown"
                )
        except Exception as exc:
            log.warning("TGA drawdown load failed: %s", exc)

        # 5. Credit impulse — 2nd derivative of US bank credit growth
        try:
            from ix.core.indicators.liquidity import credit_impulse

            ci = credit_impulse(freq="ME")
            if not ci.empty:
                rows["l_CreditImpulse"] = zscore(ci, z_window).rename(
                    "l_CreditImpulse"
                )
        except Exception as exc:
            log.warning("Credit impulse load failed: %s", exc)

        # VIX monitor-only (kept for display, excluded from composite by prefix)
        vix_raw = load_series("VIX INDEX:PX_LAST")
        if vix_raw.empty:
            vix_raw = load_series("VIX:PX_LAST")
        if not vix_raw.empty:
            rows["m_VIX"] = zscore(-vix_raw, z_window).rename("m_VIX")

        return rows

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        lp = dim_probs["Liquidity"]
        return {
            "P_Easing": lp,
            "P_Tightening": 1.0 - lp,
        }
