import pandas as pd
from ix.db import get_pxs
from ix.bt.strategy import Strategy


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
    start = "2000-1-1"
    frequency = 20

    def initialize(self) -> None:
        self.mom = self.pxs.pct_change(90)

    def allocate(self) -> pd.Series:
        momentum = self.mom.loc[str(self.d)]
        momentum = momentum.sub(min(momentum.loc["SPY"], 0))
        momentum = momentum[momentum > 0]
        # top_momentum = momentum.sort_values().iloc[:3]
        top_momentum = momentum[momentum > 0]
        if len(top_momentum) < 2:
            return pd.Series({"SPY": 1})
        allocation = pd.Series(1 / len(top_momentum), index=top_momentum.index)
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
