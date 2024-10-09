import pandas as pd
from ix.db import get_pxs
from ix.bt.strategy import Strategy


import pandas as pd
import numpy as np


class SectorRotationMom90(Strategy):
    assets = [
        "XLY",
        "XLP",
        "XLE",
        "XLF",
        "XLV",
        "XLI",
        "XLB",
        "XLU",
        "XLC",
        "XLK",
        "XLRE",
        "SPY",
    ]
    start = "2000-01-01"
    frequency = 20
    momentum_window = 90
    min_assets = 2

    def initialize(self) -> None:
        self.mom = self.pxs.pct_change(self.momentum_window)

    def allocate(self) -> pd.Series:
        momentum = self.mom.loc[str(self.d)]
        spy_momentum = momentum.get("SPY", 0)

        # Adjust momentum relative to SPY
        adjusted_momentum = momentum.sub(min(spy_momentum, 0))

        # Filter positive momentum
        positive_momentum = adjusted_momentum[adjusted_momentum > 0]

        if len(positive_momentum) < self.min_assets:
            return pd.Series({"SPY": 1.0})

        # Normalize allocations
        allocation = positive_momentum / positive_momentum.sum()

        return allocation


class SectorRotationCESI(Strategy):
    assets = [
        "XLY",
        "XLP",
        "XLE",
        "XLF",
        "XLV",
        "XLI",
        "XLB",
        "XLU",
        "XLC",
        "XLK",
        "XLRE",
        "SPY",
    ]
    start = "2003-1-1"
    frequency = 20

    def initialize(self) -> None:
        self.cesi = get_pxs(["CESIUSD Index"]).squeeze()

    def allocate(self) -> pd.Series:
        if self.cesi.loc[: self.d].iloc[-1] >= 28:
            s = self.p.filter(items=["XLV", "XLP", "XLK", "XLI", "XLB"]).dropna()
        elif self.cesi.loc[: self.d].iloc[-1] <= -15:
            s = self.p.filter(
                items=["XLY", "XLF", "XLC", "XLE", "XLU", "XLRE"]
            ).dropna()
        else:
            s = self.p.dropna()
        return pd.Series(1 / len(s), index=s.index)
