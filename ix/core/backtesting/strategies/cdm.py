import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Antonacci_CDM(Strategy):
    """Composite Dual Momentum: 4-module relative+absolute momentum.

    Source: Gary Antonacci, "Risk Premia Harvesting Through Dual Momentum",
            SSRN #2042750. Also: "Dual Momentum Investing" (book, 2014).
    Mode: replicate
    Built: 2026-03-28 by ix-strategy-builder
    Data mapping: 9 exact, 0 proxy, 0 excluded

    Rules:
    - 4 modules, 25% each: Equities (SPY/EFA), Credit (LQD/HYG),
      Real Estate (VNQ/REM), Economic Stress (GLD/TLT).
    - Within each module: pick the asset with higher 12-month return
      (relative momentum).
    - If winner's 12-month return > BIL's 12-month return, hold it.
      Otherwise hold BIL (absolute momentum filter).
    - Monthly rebalance.
    """


    label = "Composite Dual Momentum"
    family = "momentum"
    mode = "replicate"
    description = "Antonacci CDM: four independent modules — US/Intl equities (SPY vs EFA), credit (HYG vs LQD), real estate (REM vs IEF), stress hedge (GLD vs TLT). Each picks the better asset by 12-month return, then checks absolute momentum vs BIL. If negative, goes to cash. Equal-weight across modules."
    author = "Gary Antonacci"

    MODULES = [
        ("Equities", "SPY", "EFA"),
        ("Credit", "LQD", "HYG"),
        ("RealEstate", "VNQ", "REM"),
        ("Stress", "GLD", "TLT"),
    ]

    _ALL_ASSETS = ["SPY", "EFA", "LQD", "HYG", "VNQ", "REM", "GLD", "TLT", "BIL"]

    universe = {t: {"code": f"{t} US EQUITY:PX_LAST", "weight": 0.0}
                for t in _ALL_ASSETS}
    universe["SPY"]["weight"] = 1.0

    bm_assets: dict[str, float] = {"SPY": 0.5}
    start = pd.Timestamp("2008-01-01")
    frequency = "ME"
    commission = 15
    slippage = 5

    MOM_WINDOW = 252  # 12 months in trading days

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self._mom12 = prices.pct_change(self.MOM_WINDOW)

    def generate_signals(self) -> pd.Series:
        if self.d not in self._mom12.index:
            return pd.Series(0.0, index=self.assets)

        mom = self._mom12.loc[self.d]
        bil_mom = float(mom.get("BIL", 0.0)) if pd.notna(mom.get("BIL", float("nan"))) else 0.0

        weights = {a: 0.0 for a in self.assets}
        module_weight = 0.25

        for _, asset_a, asset_b in self.MODULES:
            mom_a = float(mom.get(asset_a, float("nan")))
            mom_b = float(mom.get(asset_b, float("nan")))

            if pd.isna(mom_a) and pd.isna(mom_b):
                weights["BIL"] += module_weight
                continue

            # Relative momentum: pick the winner
            if pd.isna(mom_b) or (pd.notna(mom_a) and mom_a >= mom_b):
                winner, winner_mom = asset_a, mom_a
            else:
                winner, winner_mom = asset_b, mom_b

            # Absolute momentum: winner must beat T-bills
            if pd.notna(winner_mom) and winner_mom > bil_mom:
                weights[winner] += module_weight
            else:
                weights["BIL"] += module_weight

        return pd.Series(weights).reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Antonacci, SSRN #2042750",
            "mode": "replicate",
            "mom_window": self.MOM_WINDOW,
            "modules": [m[0] for m in self.MODULES],
        }


# ------------------------------------------------------------------
# SB_Consensus_MacroTrend — Research-driven (ix-strategy-builder)
# ------------------------------------------------------------------
