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
    start = pd.Timestamp("2000-01-03")
    frequency = "ME"
    momentum_window = 90
    min_assets = 2

    def initialize(self) -> None:
        self.mom = self.pxs.pct_change(self.momentum_window)

    def allocate(self) -> pd.Series:
        momentum = self.mom.loc[str(self.d)]

        # Adjust momentum relative to SPY
        adjusted_momentum = momentum.sub(min(float(momentum.loc["SPY"]), 0))

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
        "XLF",
        "XLV",
        "XLI",
        "XLC",
        "XLK",
        "SPY",
    ]
    frequency = "ME"
    start = pd.Timestamp("2007-01-03")

    def initialize(self) -> None:
        self.cesi = (
            get_pxs(["CESIUSD Index"])
            .resample("D")
            .last()
            .ffill()
            .squeeze()
            .rolling(20)
            .mean()
        )

    def allocate(self) -> pd.Series:
        if self.cesi.loc[: self.d].iloc[-1] >= 10:
            s = self.p.filter(items=["XLF", "XLV", "XLC"]).dropna()
        elif self.cesi.loc[: self.d].iloc[-1] <= -10:
            s = self.p.filter(items=["XLK", "XLI", "XLY"]).dropna()
        else:
            s = pd.Series({"SPY": 1.0})
        return pd.Series(1 / len(s), index=s.index)


class UsIsmPmiManuEB(Strategy):
    assets = ["SPY", "AGG"]
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.5, "AGG": 0.5}

    def initialize(self) -> None:
        from ix.bt.signal import UsIsmPmiManu

        self.signal = UsIsmPmiManu().refresh().data
        self.momentum = self.pxs.pct_change(20)

    def allocate(self) -> pd.Series:

        w = 0.5 + 0.5 * self.signal.loc[: self.d].iloc[-1]
        m = self.momentum["AGG"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY": w, "AGG": 1.0 - w})
        return pd.Series({"SPY": w, "AGG": 0.0})


class UsOecdLeiEB(Strategy):
    assets = ["SPY", "AGG"]
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.5, "AGG": 0.5}

    def initialize(self) -> None:
        from ix.bt.signal import UsOecdLeading

        self.signal = UsOecdLeading().data
        self.momentum = self.pxs.pct_change(20)

    def allocate(self) -> pd.Series:

        w = 0.5 + 0.5 * self.signal.loc[: self.d].iloc[-1]
        m = self.momentum["AGG"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY": w, "AGG": 1.0 - w})
        return pd.Series({"SPY": w, "AGG": 0.0})
