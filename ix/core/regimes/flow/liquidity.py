"""LiquidityRegime — US-focused central-bank quantity + private credit regime.

States
------
- **Easing**:     CB quantities expanding, private credit growing, net
                  liquidity rising. Historically bullish for risk assets.
- **Tightening**: CB quantities contracting, private credit slowing, net
                  liquidity falling. Historically bearish for risk assets.

Indicators (5, all ``l_*``)
    l_FedAssets_YoY   — Fed total assets (WALCL) YoY. The single most
                        important US liquidity variable. QE/QT cycle anchor.
    l_TGA_Drawdown    — Treasury General Account 13-week drawdown (inverted
                        so drawdown = positive liquidity injection). Captures
                        fiscal plumbing that bypasses the Fed balance sheet.
    l_CreditImpulse   — US bank credit impulse (2nd derivative of credit
                        growth). Leads equities 6-9 months. The credit
                        *transmission* channel from CB reserves to the real
                        economy.
    l_BankLoans_3M    — C&I bank loans (BUSLOANS) 3-month growth rate. The
                        private credit channel — Howell/Peccatiello argue
                        private credit is 2-3x more important than CB balance
                        sheets. Measures actual bank lending, not just
                        reserve levels.
    l_FedNetLiq_6M    — Fed net liquidity (assets − TGA − RRP) 6-month
                        change. Captures medium-term plumbing dynamics that
                        match the 3-6M target horizon better than 3M diff.

Design principle
----------------
**Three distinct channels with low internal correlation (mean |ρ| = 0.017):**

1. CB Quantity: FedAssets_YoY + FedNetLiq_6M
2. Treasury Plumbing: TGA_Drawdown
3. Credit Channel: CreditImpulse + BankLoans_3M

Previous version (v1) used 5 indicators that were mostly Fed balance sheet
measured different ways (G4 BS YoY, Fed Assets YoY, Fed Net Liq 3M, TGA,
Credit Impulse). G4_BS_YoY was dropped because it overlapped with
FedAssets (Fed is ~60% of G4) and empirically hurt the composite (removing
it improved avg VN by +0.025). FedNetLiq_3M was replaced by the 6M window
which better matches the target horizon.

The global CB cycle (non-US central banks) is now captured by the separate
:class:`GlobalLiquidityRegime`, which this regime can be composed with.

Target & Justification
----------------------
Target:   SPY US EQUITY (S&P 500)
Horizon:  3 months forward return
Rationale: Fed plumbing + private credit transmission to equity markets runs
          2-4 months. Validated at 0.875 vol-normalized Sharpe delta (3M)
          and 0.719 (6M), both well above the 0.25 T1.4 bar.
          Subsample-stable across pre/post-2010 split.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series, zscore

log = logging.getLogger(__name__)


class LiquidityRegime(Regime):
    """US liquidity → 2-state regime (Easing / Tightening)."""

    name = "Liquidity"
    dimensions = ["Liquidity"]
    states = ["Easing", "Tightening"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # [DROPPED: l_FedAssets_YoY — full IC -0.010, pre IC -0.065.
        #  Negative IC in both full sample and pre-2010 subsample.
        #  Fed assets YoY is too slow-moving to predict 3M forward SPY.]

        # 2. TGA 13-week drawdown (inverted: drawdown = liquidity injection)
        try:
            from ix.core.indicators.liquidity import tga_drawdown

            tga = tga_drawdown().resample("ME").last()
            if not tga.empty:
                rows["l_TGA_Drawdown"] = zscore(-tga, z_window).rename(
                    "l_TGA_Drawdown"
                )
        except Exception as exc:
            log.warning("TGA drawdown load failed: %s", exc)

        # 3. Credit impulse — 2nd derivative of US bank credit growth
        try:
            from ix.core.indicators.liquidity import credit_impulse

            ci = credit_impulse(freq="ME")
            if not ci.empty:
                rows["l_CreditImpulse"] = zscore(ci, z_window).rename(
                    "l_CreditImpulse"
                )
        except Exception as exc:
            log.warning("Credit impulse load failed: %s", exc)

        # 4. Bank C&I loans 3M growth — private credit channel
        try:
            from ix.db.query import Series as DbSeries

            bus = DbSeries("BUSLOANS").resample("ME").last()
            if not bus.empty:
                rows["l_BankLoans_3M"] = zscore(
                    bus.pct_change(3), z_window
                ).rename("l_BankLoans_3M")
        except Exception as exc:
            log.warning("Bank loans load failed: %s", exc)

        # [DROPPED: l_FedNetLiq_6M — full IC +0.006 (NOISE), pre IC -0.104.
        #  Barely positive full-sample and strongly negative pre-2010.
        #  Removing improves composite stability across subsamples.]

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
