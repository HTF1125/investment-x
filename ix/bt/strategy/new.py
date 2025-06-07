import pandas as pd
from .base import Strategy


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
        pct_change = self.pxs.pct_change()
        corr_diff = pct_change.rolling(20).corr() - pct_change.rolling(250).corr()
        corr_difff = corr_diff.unstack()["SPY"].drop(labels="SPY", axis=1).mean(axis=1)
        self.corr_signal = corr_difff

    def allocate(self) -> pd.Series:
        if self.corr_signal.loc[self.d] < 0:
            return pd.Series({"SPY": 1.0})
        momentum = self.mom.loc[str(self.d)]
        # Filter positive momentum
        positive_momentum = momentum.nlargest(3)
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
    start = pd.Timestamp("2007-01-03")

    def initialize(self) -> None:
        self.cesi = (
            get_px_last(["^CESIUSD"])
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
    assets = [
        "SPY US Equity",
        "AGG US Equity",
    ]
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
    assets = [
        "SPY US Equity",
        "AGG US Equity",
    ]
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY US Equity": 0.6, "AGG US Equity": 0.4}

    def initialize(self) -> None:
        self.signal = get_ticker("USA.LOLITOAA.STSA").get_data("PX_DIFF_DIFF")
        self.signal.index += pd.DateOffset(days=10)
        self.momentum = self.pxs.pct_change(20)

    def allocate(self) -> pd.Series:

        signal = self.signal.loc[: self.d].iloc[-1]
        m = self.momentum["AGG US Equity"].loc[self.d]
        if signal > 0:
            return pd.Series(
                {"SPY US Equity": 0.8, "AGG US Equity": 0.2 if m > 0 else 0}
            )

        return pd.Series({"SPY US Equity": 0.3, "AGG US Equity": 0.7})


class UsOecdLeiEB2(Strategy):
    assets = ["SPY US Equity", "AGG US Equity"]
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY US Equity": 0.6, "AGG US Equity": 0.4}

    def initialize(self) -> None:
        from ix.core.tech import WaveTrend

        self.signal = (
            WaveTrend.from_meta("USA.LOLITOAA.STSA")
            .hlc["wt_diff"]
            .clip(-10, 10)
            .div(10)
        )
        self.momentum = self.pxs.pct_change(20)

    def allocate(self) -> pd.Series:

        w = 0.5 + 0.5 * self.signal.loc[: self.d].iloc[-1]
        m = self.momentum["AGG US Equity"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY US Equity": w, "AGG US Equity": 1.0 - w})
        return pd.Series({"SPY US Equity": w, "AGG US Equity": 0.0})


class MAM60CF(Strategy):
    assets = [
        "SPY",
        "IWM",
        "EEM",
        "QQQ",
        "LQD",
        "IEF",
        "TLT",
        "GLD",
    ]

    start = pd.Timestamp("2007-01-03")
    frequency = "ME"
    momentum_window = 60
    min_assets = 2

    def initialize(self) -> None:
        self.mom = self.pxs.pct_change(self.momentum_window)
        pct_change = self.pxs.pct_change()
        corr_diff = pct_change.rolling(20).corr() - pct_change.rolling(90).corr()
        corr_difff = corr_diff.unstack().mean(axis=1)
        self.corr_signal = corr_difff
        # self.corr_signal.loc["2020":].plot()

    def allocate(self) -> pd.Series:
        if self.corr_signal.loc[self.d] < 0:
            return pd.Series({"SPY": 1.0})
        momentum = self.mom.loc[str(self.d)]
        momentum = momentum[momentum > 0]
        # Filter positive momentum
        positive_momentum = momentum.nlargest(4)
        # Normalize allocations
        allocation = positive_momentum / positive_momentum.sum()
        return allocation




class SPX_Earnings(Strategy):

    assets = [
        "SPY US Equity",
    ]

    start = pd.Timestamp("2007-01-03")
    frequency = "ME"
    min_assets = 1

    def initialize(self):
        eps = get_ticker("SPX Index").eps_ntma_yoy
        self.earnings_momentum = eps.diff(50)
        return

    def allocate(self) -> pd.Series:

        if self.earnings_momentum.loc[str(self.d)] > 0:
            return pd.Series({"SPY US Equity": 1.0})
        return pd.Series({"SPY US Equity": 0.0})


def all_strategies() -> list[type[Strategy]]:
    return [
        # UsIsmPmiManuEB,
        UsOecdLeiEB,
        SectorRotationCESI,
        SectorRotationMom90,
    ]
