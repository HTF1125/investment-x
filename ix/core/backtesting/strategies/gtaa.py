import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Faber_GTAA5(Strategy):
    """Faber GTAA-5: trend-following across 5 asset classes via 10-month SMA.

    Source: Meb Faber, "A Quantitative Approach to Tactical Asset Allocation",
            SSRN #962461, 2006 (updated 2013). Journal of Wealth Management.
    Mode: replicate
    Built: 2026-03-28 by ix-strategy-builder
    Data mapping: 6 exact, 0 proxy, 0 excluded

    Rules:
    - 5 asset classes: US Stocks (SPY), Foreign Stocks (EFA), US Bonds (IEF),
      REITs (VNQ), Commodities (DBC). Equal weight 20% each.
    - Monthly: if price > 10-month SMA, hold asset. Otherwise hold cash (BIL).
    - Rebalance on last trading day of month.
    """


    label = "GTAA-5"
    family = "trend"
    mode = "replicate"
    description = "Faber GTAA: holds each of 5 assets (SPY, EFA, IEF, VNQ, DBC) only when price is above its 10-month SMA. Below SMA → replace with BIL cash. Equal-weight across assets that pass the trend filter. Monthly rebalance."
    author = "Meb Faber"

    RISK_ASSETS = ["SPY", "EFA", "IEF", "VNQ", "DBC"]

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.20},
        "EFA": {"code": "EFA US EQUITY:PX_LAST", "weight": 0.20},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.20},
        "VNQ": {"code": "VNQ US EQUITY:PX_LAST", "weight": 0.20},
        "DBC": {"code": "DBC US EQUITY:PX_LAST", "weight": 0.20},
        "BIL": {"code": "BIL US EQUITY:PX_LAST", "weight": 0.00},  # Cash proxy
    }

    bm_assets: dict[str, float] = {"SPY": 0.5}
    start = pd.Timestamp("2007-06-01")
    frequency = "ME"
    commission = 15
    slippage = 5

    SMA_MONTHS = 10  # 10-month SMA (~210 trading days)

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        # 10-month SMA: ~210 trading days (21 days/month * 10)
        self._sma = prices.rolling(window=210, min_periods=180).mean()
        self._prices = prices

    def generate_signals(self) -> pd.Series:
        if self.d not in self._prices.index:
            return pd.Series(0.0, index=self.assets)

        px = self._prices.loc[self.d]
        sma = self._sma.loc[self.d]

        signals = {}
        cash_weight = 0.0
        for asset in self.RISK_ASSETS:
            price_val = px.get(asset, float("nan"))
            sma_val = sma.get(asset, float("nan"))
            if pd.notna(price_val) and pd.notna(sma_val) and price_val > sma_val:
                signals[asset] = 0.20  # Above SMA — hold 20%
            else:
                signals[asset] = 0.0   # Below SMA — goes to cash
                cash_weight += 0.20
        signals["BIL"] = cash_weight

        return pd.Series(signals).reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        # Signals ARE the weights (always sum to 1.0)
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Faber 2006, SSRN #962461",
            "mode": "replicate",
            "sma_months": self.SMA_MONTHS,
        }


# ------------------------------------------------------------------
# SB_Keller_BAABalanced — Research-driven (ix-strategy-builder)
# ------------------------------------------------------------------
