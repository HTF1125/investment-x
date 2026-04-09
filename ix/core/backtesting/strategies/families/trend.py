"""Trend-following strategy families — SMA and breadth-based allocation."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, SECTORS, MULTI5, MULTI8, BROAD6


class TrendSMA(FamilyStrategy):
    """Binary trend filter: 100% equity when price > N-month SMA, else 100% bond."""
    family = "Trend"

    def __init__(self, sma_months: int, equity: str = "SPY", bond: str = "IEF", **kw):
        self.sma_months = sma_months
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = f"TrendSMA({sma_months}, {equity}/{bond})"
        self.description = (
            f"SMA trend-following: holds 100% {equity} when current price is above "
            f"its {sma_months}-month simple moving average, otherwise holds 100% "
            f"{bond}. Binary signal — fully in or fully out. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        if self._equity not in hist.columns or len(hist) < self.sma_months + 1:
            return pd.Series({self._equity: 0.5, self._bond: 0.5}).reindex(
                self.asset_names, fill_value=0.0
            )
        price = hist[self._equity].iloc[-1]
        sma_val = hist[self._equity].iloc[-self.sma_months:].mean()
        if price > sma_val:
            w = {self._equity: 1.0, self._bond: 0.0}
        else:
            w = {self._equity: 0.0, self._bond: 1.0}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {"sma_months": self.sma_months, "equity": self._equity, "bond": self._bond}


class DualSMA(FamilyStrategy):
    """Dual SMA crossover: equity when fast-SMA > slow-SMA, else bond."""
    family = "Trend"

    def __init__(self, fast: int, slow: int, equity: str = "SPY", bond: str = "IEF", **kw):
        self.fast = fast
        self.slow = slow
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = f"DualSMA({fast}/{slow}, {equity}/{bond})"
        self.description = (
            f"Dual SMA crossover: holds 100% {equity} when the {fast}-month SMA "
            f"crosses above the {slow}-month SMA, otherwise holds 100% {bond}. "
            f"Crossover signals tend to lag less than single-SMA but generate more "
            f"whipsaws. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        if self._equity not in hist.columns or len(hist) < self.slow + 1:
            return pd.Series({self._equity: 0.5, self._bond: 0.5}).reindex(
                self.asset_names, fill_value=0.0
            )
        fast_sma = hist[self._equity].iloc[-self.fast:].mean()
        slow_sma = hist[self._equity].iloc[-self.slow:].mean()
        if fast_sma > slow_sma:
            w = {self._equity: 1.0, self._bond: 0.0}
        else:
            w = {self._equity: 0.0, self._bond: 1.0}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "equity": self._equity, "bond": self._bond}


class TrendBreadth(FamilyStrategy):
    """Breadth-weighted trend: equity weight = fraction of assets above N-month SMA."""
    family = "Trend"

    def __init__(
        self,
        sma_months: int = 10,
        assets: list[str] | None = None,
        equity: str = "SPY",
        bond: str = "IEF",
        **kw,
    ):
        self.sma_months = sma_months
        self._breadth_assets = assets or MULTI5
        self._equity = equity
        self._bond = bond
        all_assets = list(set([equity, bond] + self._breadth_assets))
        self._build_universe(all_assets)
        n = len(self._breadth_assets)
        asset_list = ", ".join(self._breadth_assets)
        self.label = f"TrendBreadth({sma_months}, {n} assets)"
        self.description = (
            f"Multi-asset trend breadth: computes the fraction of {n} monitored "
            f"assets ({asset_list}) trading above their {sma_months}-month SMA. "
            f"This fraction becomes the equity weight — higher breadth = more "
            f"risk-on. Remainder allocated to {bond}. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        assets = self._avail(self._breadth_assets)
        if len(hist) < self.sma_months + 1 or not assets:
            return pd.Series({self._equity: 0.5, self._bond: 0.5}).reindex(
                self.asset_names, fill_value=0.0
            )
        above = sum(
            1 for a in assets
            if hist[a].iloc[-1] > hist[a].iloc[-self.sma_months:].mean()
        )
        breadth = above / len(assets)
        w = {self._equity: breadth, self._bond: 1 - breadth}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "sma_months": self.sma_months,
            "breadth_assets": self._breadth_assets,
            "equity": self._equity,
            "bond": self._bond,
        }
