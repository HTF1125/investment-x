import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager

class UsIsmPmiManuEB(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.5},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.5},
    }
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.5, "AGG": 0.5}

    def initialize(self) -> None:
        from ix.core.backtesting.signals import UsIsmPmiManu

        self.signal = UsIsmPmiManu().data
        self.signal = self.signal.reindex(self.pxs.index, method="ffill").fillna(0.0)
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.momentum = prices.pct_change(20)

    def generate_signals(self) -> pd.Series:
        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        sig = float(self.signal.asof(self.d))
        return pd.Series({"SPY": sig, "AGG": -sig})

    def allocate(self) -> pd.Series:

        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        w = 0.5 + 0.5 * float(self.signal.asof(self.d))
        m = self.momentum["AGG"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY": w, "AGG": 1.0 - w})
        return pd.Series({"SPY": w, "AGG": 0.0})


class UsOecdLeiEB(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.6},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.4},
    }
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.6, "AGG": 0.4}

    def initialize(self) -> None:
        signal = Series("USA.LOLITOAA.STSA:PX_DIFF_DIFF")
        if signal.empty:
            base = Series("USA.LOLITOAA.STSA")
            signal = base.diff().diff()
        signal.index = signal.index + pd.DateOffset(days=10)
        self.signal = signal.reindex(self.pxs.index, method="ffill").fillna(0.0)
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.momentum = prices.pct_change(20)

    def generate_signals(self) -> pd.Series:
        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        sig = float(self.signal.asof(self.d))
        return pd.Series({"SPY": sig, "AGG": -sig})

    def allocate(self) -> pd.Series:

        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        signal = float(self.signal.asof(self.d))
        m = self.momentum["AGG"].loc[self.d]
        if signal > 0:
            return pd.Series({"SPY": 0.8, "AGG": 0.2 if m > 0 else 0})

        return pd.Series({"SPY": 0.3, "AGG": 0.7})


class UsOecdLeiEB2(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.6},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.4},
    }
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.6, "AGG": 0.4}

    def initialize(self) -> None:
        from ix.core.technical import WaveTrend

        self.signal = (
            WaveTrend.from_meta("USA.LOLITOAA.STSA")
            .hlc["wt_diff"]
            .clip(-10, 10)
            .div(10)
        )
        self.signal = self.signal.reindex(self.pxs.index, method="ffill").fillna(0.0)
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.momentum = prices.pct_change(20)

    def generate_signals(self) -> pd.Series:
        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        sig = float(self.signal.asof(self.d))
        return pd.Series({"SPY": sig, "AGG": -sig})

    def allocate(self) -> pd.Series:

        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        w = 0.5 + 0.5 * float(self.signal.asof(self.d))
        m = self.momentum["AGG"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY": w, "AGG": 1.0 - w})
        return pd.Series({"SPY": w, "AGG": 0.0})


class MAM60CF(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IWM": {"code": "IWM US EQUITY:PX_LAST", "weight": 0.0},
        "EEM": {"code": "EEM US EQUITY:PX_LAST", "weight": 0.0},
        "QQQ": {"code": "QQQ US EQUITY:PX_LAST", "weight": 0.0},
        "LQD": {"code": "LQD US EQUITY:PX_LAST", "weight": 0.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
        "TLT": {"code": "TLT US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
    }

    start = pd.Timestamp("2007-01-03")
    frequency = "ME"
    momentum_window = 60
    top_n = 4

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.mom = prices.pct_change(self.momentum_window)
        pct_change = prices.pct_change()
        corr_diff = pct_change.rolling(20).corr() - pct_change.rolling(90).corr()
        corr_difff = corr_diff.unstack().mean(axis=1)
        self.corr_signal = (
            corr_difff.reindex(prices.index, method="ffill").fillna(0.0)
        )
        # self.corr_signal.loc["2020":].plot()

    def generate_signals(self) -> pd.Series:
        if self.d not in self.mom.index:
            return pd.Series(0.0, index=self.assets)
        return self.mom.loc[self.d].reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        corr_val = float(self.corr_signal.asof(self.d)) if not self.corr_signal.empty else 0.0
        if corr_val < 0:
            return pd.Series({"SPY": 1.0})
        momentum = self.generate_signals()
        momentum = momentum[momentum > 0]
        positive_momentum = momentum.nlargest(self.top_n)
        if positive_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        return positive_momentum / positive_momentum.sum()


class SPX_Earnings(Strategy):

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
    }

    start = pd.Timestamp("2007-01-03")
    frequency = "ME"
    min_assets = 1

    def initialize(self):
        eps_ntma = Series("SPX Index:EPS_NTMA", freq="W-Fri").ffill()
        eps_ltma = Series("SPX Index:EPS_LTMA", freq="W-Fri").ffill()
        growth = eps_ntma.div(eps_ltma).sub(1).mul(100)
        self.earnings_momentum = growth.diff(52)
        self.earnings_momentum = self.earnings_momentum.reindex(
            self.pxs.index, method="ffill"
        ).fillna(0.0)
        return

    def generate_signals(self) -> pd.Series:
        if self.earnings_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        return pd.Series(
            {"SPY": float(self.earnings_momentum.asof(self.d))},
            index=self.assets,
        )

    def allocate(self) -> pd.Series:

        if self.earnings_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        if float(self.earnings_momentum.asof(self.d)) > 0:
            return pd.Series({"SPY": 1.0})
        return pd.Series({"SPY": 0.0})


# ------------------------------------------------------------------
# Static allocation strategies (buy-and-hold benchmarks)
# ------------------------------------------------------------------

