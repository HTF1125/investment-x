from typing import Union, overload
import pandas as pd
from ix.core import to_pri_return
from ix.db import get_pxs
from ix import db
from ix import misc


logger = misc.get_logger(__name__)


class Signal:
    def __init__(self) -> None:
        self.code = self.__class__.__name__
        self.db = db.Signal.find_one(db.Signal.code == self.code).run() or db.Signal(
            code=self.code
        )

    def fit(self) -> pd.Series:
        """Override this method to define how the signal is calculated."""
        raise NotImplementedError(f"Must implement `{self.fit.__name__}` method.")

    def refresh(self) -> "Signal":
        """Refreshes the signal data by recalculating and saving to the database."""
        try:
            logger.info("Starting data refresh")
            data = self.fit().dropna().round(2)
            self.db.data = data.to_dict()
            db.Signal.save(self.db)
        except TypeError as e:
            logger.error(f"Data validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during refresh: {e}")
            raise
        return self

    @property
    def data(self) -> pd.Series:
        """Fetches the signal from the database, refreshing if not present."""
        if not self.db.data:
            self.refresh()
        states = pd.Series(self.db.data)
        states.index = pd.to_datetime(states.index)
        return states.sort_index().rename(self.code)

    def save(self) -> None:
        db.Signal.save(self.db)

    @overload
    def get_performance(
        self,
        px: pd.Series,
        periods: int,
        start: Union[str, None] = None,
    ) -> pd.Series: ...

    @overload
    def get_performance(
        self,
        px: pd.Series,
        periods: list[int],
        start: Union[str, None] = None,
    ) -> pd.DataFrame: ...

    def get_performance(
        self,
        px: pd.Series,
        periods: Union[int, list[int]] = 1,
        start: Union[str, None] = None,
    ) -> Union[pd.Series, pd.DataFrame]:
        performance = get_signal_performances(self.data, px, periods)
        return performance.loc[start:] if start else performance


class UsOecdLeading(Signal):
    def fit(self) -> pd.Series:
        """Calculates the US OECD Leading indicator signal."""
        TICKERS = {"OEUSKLAC Index": "UsOecdLeading"}
        EWM_SPAN = 3
        data = get_pxs(codes=TICKERS).diff().ewm(span=EWM_SPAN).mean().squeeze()
        adjusted_data = data + data.diff()
        adjusted_data.index += pd.DateOffset(days=20)
        return adjusted_data.clip(-0.25, 0.25) * 4


class UsIsmPmiManu(Signal):
    def fit(self) -> pd.Series:
        """Calculates the US ISM PMI Manufacturing indicator signal."""
        TICKERS = {"NAPMPMI Index": "UsIsmPmiManu"}
        EWM_SPAN = 3
        data = get_pxs(codes=TICKERS).sub(50).ewm(span=EWM_SPAN).mean().squeeze()
        adjusted_data = data + data.diff() * 0.2
        adjusted_data.index += pd.DateOffset(days=5)
        return adjusted_data.clip(-10, 10) / 10


class SpxVix(Signal):

    def fit(self) -> pd.Series:
        vix = db.get_pxs(["VIX Index"]).squeeze()
        signal = vix / vix.ewm(50).mean() - 1
        win = 252 // 4
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * -1


class SpxPutCallRatio(Signal):

    def fit(self) -> pd.Series:
        data = db.get_pxs(codes=["PCRTEQTY Index"]).squeeze()
        signal = data.rolling(20).mean()
        roll = signal.rolling(200)
        z = (signal - roll.mean()) / roll.std()
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * -1


class JunkBondDemand(Signal):

    def fit(self) -> pd.Series:
        st = db.get_pxs("SPY").pct_change(20).squeeze()
        bd = db.get_pxs("AGG").pct_change(20).squeeze()
        safe = st - bd
        signal = safe.rolling(10).mean()
        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * -1


class SpxMomMa125(Signal):
    def fit(self) -> pd.Series:
        data = db.get_pxs("SPY").squeeze()
        signal = data / data.rolling(125).mean() - 1
        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


# class UsLargeSmallRatio(Signal):

#     def fit(self) -> pd.Series:
#         large = db.get_pxs("SPY").squeeze()
#         small = db.get_pxs("RTY").squeeze()
#         return large.div(small).dropna()


# class GoldSilverRatio(Signal):

#     def fit(self) -> pd.Series:

#         gold = db.get_pxs("GC=F Comdty").squeeze()
#         silver = db.get_pxs("SI=F Comdty").squeeze()

#         return (gold / silver).dropna()


class MarketBreadth(Signal):

    def fit(self) -> pd.Series:
        signal = db.get_pxs("SUM INX Index").squeeze()

        roll = signal.rolling(120)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


def get_signal_performances(
    signal: pd.Series,
    px: pd.Series,
    periods: Union[int, list[int]] = 1,
    commission: int = 0,
) -> Union[pd.Series, pd.DataFrame]:
    """
    Calculate the performance of the signal over given periods.

    Args:
        signal (pd.Series): Signal values.
        px (pd.Series): Price data for the assets.
        periods (int | list[int]): Look-back periods for performance calculation.
        commission (int): Commission percentage in basis points.

    Returns:
        pd.Series | pd.DataFrame: Performance for each period.
    """
    if isinstance(periods, list):
        return pd.concat(
            [
                get_signal_performances(signal, px, period, commission)
                for period in periods
            ],
            axis=1,
        )

    pri_return = to_pri_return(px=px, periods=periods, forward=True)
    annualized_return = (1 + pri_return) ** (1 / periods) - 1
    signal_shifted = signal.reindex(pri_return.index).ffill().shift(1)
    returns = annualized_return.mul(signal_shifted)

    if commission:
        returns -= signal_shifted.diff(periods).abs() * commission / 10_000 / periods

    return returns.add(1).cumprod().rename(periods)


def all_signals() -> list[type[Signal]]:
    """
    Returns a list of all document models for easy reference in database initialization.
    """
    return [
        UsIsmPmiManu,
        UsOecdLeading,
        SpxVix,
        SpxPutCallRatio,
        SpxMomMa125,
        MarketBreadth,
    ]
