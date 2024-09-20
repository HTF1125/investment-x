# This class represents a signal related to the OECD US Composite Leading Indicators.


import pandas as pd
from .base import Signal
from ix import db


class ISC(Signal):

    corr_win: int = 500

    def compute(self) -> pd.Series:

        data = db.get_px("T10YIE.Index, DGS10.Index, THREEFFTP10.Index").dropna()
        data["ShortTerm.Index"] = (
            data["DGS10.Index"] - data["THREEFFTP10.Index"] - data["T10YIE.Index"]
        )
        data = (
            data.rolling(self.corr_win)
            .corr()
            .unstack()["ShortTerm.Index"]["T10YIE.Index"]
        )
        data = data.multiply(-1)
        return data


class MarketVolatility(Signal):

    def compute(self) -> pd.Series:

        vix = db.get_vix()
        signal = vix / vix.rolling(50).mean() - 1
        win = 252 // 4
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z


class PutCallRatio(Signal):

    normalize_window: int = 120

    def compute(self) -> pd.Series:
        data = db.get_pxs(codes=["PCRTEQTY Index"], field="PxLast")
        signal = data.rolling(20).mean()
        roll = signal.rolling(self.normalize_window)
        z = (signal - roll.mean()) / roll.std()
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z


class JunkBondDemand(Signal):

    def compute(self) -> pd.Series:
        st = db.get_px(tickers="SPY").pct_change(20)
        bd = db.get_px(tickers="AGG").pct_change(20)
        safe = st - bd
        signal = safe.rolling(10).mean()
        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


class MarketMomentum(Signal):

    def compute(self) -> pd.Series:
        data = db.get_spx()
        signal = data / data.rolling(125).mean() - 1

        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


class MarketBreadth(Signal):
    def compute(self) -> pd.Series:
        signal = db.get_px("SUM INX Index")

        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


class MarketStregnth(Signal):
    def compute(self) -> pd.Series:
        signal = db.get_stock_strength()
        signal = signal.rolling(5).mean()

        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


class SafeHavenDemand(Signal):
    def compute(self) -> pd.Series:

        st = db.get_px(tickers="SPY").pct_change(20)
        bd = db.get_px(tickers="AGG").pct_change(20)
        signal = st - bd
        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


class OecdLeadingNorm(Signal):
    NORMAILIZE_WINDOW: int = 12
    DIFF_CLIP_LIMIT: float = 0.2
    STD_CLIP_LOWER: float = -2.0
    STD_CLIP_UPPER: float = 2.0
    ROLLING_WINDOW: int = 12 * 5

    def compute(self) -> pd.Series:
        data = db.get_px("OEUSKLAC Index").diff().dropna()
        data.index = data.index + pd.DateOffset(days=12)
        rolling_mean = data.rolling(3).mean()
        rolling_std = data.rolling(3).std()
        z_scores = ((data -rolling_mean) / rolling_std).clip(lower=-2, upper=2) / 2.0
        return z_scores


class OecdCliRoCC(Signal):

    def compute(self) -> pd.Series:
        data = db.get_px("OEUSKLAC Index")
        data = data - data.shift(1)
        data = data - data.shift(1)
        data = data.dropna()
        data.index = data.index + pd.DateOffset(days=12)
        rolling_mean = data.rolling(3).mean()
        rolling_std = data.rolling(3).std()
        z_scores = (data - rolling_mean / rolling_std).clip(lower=-2, upper=2) / 2.0
        return z_scores * (-1)


class EconSurpriseDMEM(Signal):

    def compute(self) -> pd.Series:

        dm = db.get_px("CESIUSD Index")
        em = db.get_px("CESIEM Index")
        ratio = dm - em
        return ratio.dropna()


class UsEuRatio(Signal):

    def compute(self) -> pd.Series:

        us = db.get_px("SPX Index")
        eu = db.get_px("SXXP Index")

        return (us / eu).dropna()


class GoldSilverRatio(Signal):

    def compute(self) -> pd.Series:

        gold = db.get_px("GC=F Comdty")
        silver = db.get_px("SI=F Comdty")

        return (gold / silver).dropna()


class UsLargeSmallRatio(Signal):

    def compute(self) -> pd.Series:

        large = db.get_px("SPX Index")
        small = db.get_px("RTY Index")

        return (large / small).dropna()


class AverageHourlyEarningYoY(Signal):

    def compute(self) -> pd.Series:

        ahe = db.get_px("CES0500000003 Index")
        ahe.index += pd.DateOffset(months=1)
        return ahe.pct_change(12).dropna()


class FearGreedIndex(Signal):

    def compute(self) -> pd.Series:

        signals = [
            MarketBreadth,
            MarketMomentum,
            # MarketStregnth,
            JunkBondDemand,
            PutCallRatio,
            SafeHavenDemand,
        ]

        fgi = pd.DataFrame()

        for signal in signals:

            try:
                vv = signal().signal.dropna().to_frame()
                fgi = pd.concat([fgi, vv], axis=1)
            except:
                continue

        return fgi.dropna(axis=0, thresh=3).mean(axis=1).rolling(5).mean().dropna()


class SP50021DFwd(Signal):
    def compute(self) -> pd.Series:

        from src.ix import core

        return core.to_log_return(db.get_px("SPY"), periods=21, forward=True)


class SP50060DFwd(Signal):
    def compute(self) -> pd.Series:
        from src.ix import core

        return core.to_log_return(db.get_px("SPY"), periods=63, forward=True)


class SpyMoM252D(Signal):
    def compute(self) -> pd.Series:
        from src.ix import core

        return core.to_log_return(db.get_px("SPY"), periods=252, forward=False)


class UsEquityCitiSurpriseCorr(Signal):

    def compute(self) -> pd.Series:
        returns = db.get_px(["CESIUSD Index", "SPY"])
        returns["SPY"] = returns["SPY"].pct_change(5)
        return returns.dropna().rolling(252).corr().unstack().iloc[:, 1]


class UsTreasuryCitiSurpriseCorr(Signal):

    def compute(self) -> pd.Series:

        returns = db.get_px(["CESIUSD Index", "IEF"])
        returns["IEF"] = returns["IEF"].pct_change(5)
        return returns.dropna().rolling(252).corr().unstack()["IEF"]["CESIUSD Index"]


class UsEquityTrend1(Signal):

    def compute(self) -> pd.Series:

        px = db.get_px("SPY")
        ma1 = px.rolling(10 * 21).mean()
        ma2 = px.rolling(3 * 21).mean()
        return (ma2 / ma1 - 1).dropna()


class UsTreasuryTrend1(Signal):

    def compute(self) -> pd.Series:

        px = db.get_px("IEF")
        ma1 = px.rolling(10 * 21).mean()
        ma2 = px.rolling(3 * 21).mean()
        return (ma2 / ma1 - 1).dropna()


class GoldTrend1(Signal):

    def compute(self) -> pd.Series:

        px = db.get_px("GLD")
        ma1 = px.rolling(10 * 21).mean()
        ma2 = px.rolling(3 * 21).mean()
        return (ma2 / ma1 - 1).dropna()
