import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Carlson_DefenseFirst(Strategy):
    """Defense First: defensive assets guide portfolio risk posture.

    Source: Thomas Carlson, "Defense First: A Multi-Asset Tactical Model
            for Adaptive Downside Protection", SSRN #5334772, July 2025.
    Mode: replicate
    Built: 2026-03-28 by ix-strategy-builder
    Data mapping: 6 exact, 0 proxy, 0 excluded

    Rules:
    - 4 defensive assets: TLT (deflation), GLD (monetary), DBC (inflation),
      UUP (liquidity crisis). Cash hurdle: BIL. Fallback: SPY.
    - Monthly: rank defensive assets by average of 1/3/6/12-month returns.
    - Allocate 40/30/20/10 across ranked positions.
    - If a defensive asset's momentum < BIL momentum, replace with SPY.
    """


    label = "Defense First"
    family = "defensive"
    mode = "replicate"
    description = "Ranks defensive assets (TLT, GLD, DBC) by 13612W momentum (12*r1 + 4*r3 + 2*r6 + r12) with BIL cash hurdle. If top defensive assets beat cash, overweight them; otherwise hold SPY. Monthly rebalance with dual momentum filter requiring positive absolute returns."
    author = "Thomas Carlson"

    universe = {
        "TLT": {"code": "TLT US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
        "DBC": {"code": "DBC US EQUITY:PX_LAST", "weight": 0.0},
        "UUP": {"code": "DXY.Z:FG_PRICE_IDX", "weight": 0.0},  # Dollar Index proxy for UUP ETF
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
    }

    bm_assets: dict[str, float] = {"SPY": 0.5}
    start = pd.Timestamp("2007-06-01")
    frequency = "ME"
    commission = 15
    slippage = 5

    DEFENSIVE = ["TLT", "GLD", "DBC", "UUP"]
    RANK_WEIGHTS = [0.40, 0.30, 0.20, 0.10]
    MOM_WINDOWS = [21, 63, 126, 252]  # ~1, 3, 6, 12 months in trading days

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        # BIL for cash hurdle — load separately since it's not in universe
        self._bil = Series("BIL US EQUITY:PX_LAST")

        # Pre-compute multi-period momentum for each asset
        mom_frames = []
        for w in self.MOM_WINDOWS:
            mom_frames.append(prices.pct_change(w))
        # Average across the 4 windows
        self._momentum = sum(mom_frames) / len(mom_frames)

        # BIL momentum (same multi-period average)
        bil_moms = [self._bil.pct_change(w) for w in self.MOM_WINDOWS]
        self._bil_mom = sum(bil_moms) / len(bil_moms)

    def generate_signals(self) -> pd.Series:
        if self.d not in self._momentum.index:
            return pd.Series(0.0, index=self.assets)

        mom_today = self._momentum.loc[self.d]
        bil_mom = float(self._bil_mom.asof(self.d)) if not self._bil_mom.empty else 0.0

        # Get defensive asset momenta
        def_mom = {a: float(mom_today.get(a, 0.0)) for a in self.DEFENSIVE}

        # Rank by momentum (highest first)
        ranked = sorted(def_mom.items(), key=lambda x: x[1], reverse=True)

        weights = {}
        spy_weight = 0.0

        for i, (asset, mom_val) in enumerate(ranked):
            rank_w = self.RANK_WEIGHTS[i]
            if pd.isna(mom_val) or mom_val < bil_mom:
                # Fails cash hurdle — allocate to SPY
                spy_weight += rank_w
                weights[asset] = 0.0
            else:
                weights[asset] = rank_w

        weights["SPY"] = spy_weight

        return pd.Series(weights).reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        # Signals ARE the weights (already sum to 1.0)
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Carlson 2025, SSRN #5334772",
            "mode": "replicate",
            "mom_windows": self.MOM_WINDOWS,
            "rank_weights": self.RANK_WEIGHTS,
        }


# ------------------------------------------------------------------
# SB_Faber_GTAA5 — Research-driven (ix-strategy-builder)
# ------------------------------------------------------------------
