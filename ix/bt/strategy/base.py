import numpy as np
import pandas as pd
from ix import db
from ix.misc import get_logger, as_date
from ix.core import to_ann_return, to_ann_volatility

logger = get_logger(__name__)


class Strategy:

    principal: int = 10_000
    assets: list[str] = ["SPY", "AGG", "TLT"]
    bm_assets: dict[str, float] = {"SPY": 1.00}
    start: pd.Timestamp = pd.Timestamp("2000-1-1")
    end: pd.Timestamp = pd.Timestamp("2040-1-1")
    frequency: str = "ME"

    def __init__(self) -> None:
        self.d = self.start
        self.v = self.principal
        self.l = self.principal
        self.w = pd.Series(dtype=float)
        self.s = pd.Series(dtype=float)
        self.c = pd.Series(dtype=float)
        self.a = pd.Series(dtype=float)
        self.pxs = db.get_pxs(self.assets)

        self.trade_dates = self.generate_trade_dates()

        code = self.__class__.__name__
        self.db = db.Strategy.find_one({"code": code}).run() or db.Strategy(code=code)
        if self.db.book.d:
            self.d = pd.Timestamp(self.db.book.d[-1]) + pd.DateOffset(days=1)
            self.v = self.db.book.v[-1]
            self.l = self.db.book.l[-1]
            self.w = pd.Series(self.db.book.w[-1])
            self.s = pd.Series(self.db.book.s[-1])
            self.c = pd.Series(self.db.book.c[-1])
            self.a = pd.Series(self.db.book.a[-1])
        self.initialize()

    def save(self):
        self.db.last_updated = as_date(self.d, "%Y-%m-%d")
        if self.db.book.v:
            if len(self.db.book.v) >= 252:
                self.db.ann_return = to_ann_return(self.nav)
                self.db.ann_volatility = to_ann_volatility(self.nav)
            self.db.nav_history = self.nav.iloc[-30:].to_list()
        self.db.save()

    def initialize(self):
        raise NotImplementedError(
            "Must implement `initialize` method to calculate needed signals."
        )

    def allocate(self) -> pd.Series:
        raise NotImplementedError(
            "Must implement `allocate` method to calculate targeted asset weight."
        )

    def mtm(self) -> None:
        self.c = self.s.mul(self.p)
        self.v = self.c.sum() + self.l
        self.w = self.c.div(self.v)

    def sim(self) -> "Strategy":

        # Assuming self.trade_dates is already defined
        for i in range(len(self.trade_dates) - 1):
            start, end = self.trade_dates[i : i + 2]
            if i > 0:
                start = start + pd.DateOffset(days=1)
            self.a = self.allocate()
            if isinstance(self.a, pd.Series):
                print(f"{self.d} : {self.a.to_dict()}")
            pxs = self.pxs.loc[start:end]
            if not pxs.empty:
                for self.d in pxs.index:
                    self.mtm()
                    if not self.a.empty:
                        self.c = self.a.mul(self.v).dropna()
                        self.s = self.c.div(self.p).dropna()
                        self.l = self.v - self.c.sum()
                        self.w = self.c.div(self.v)
                    self.record()

        b = db.get_pxs(codes=list(self.bm_assets)).reindex(self.dates).ffill()
        self.db.book.b = list(
            b.pct_change().sum(axis=1).add(1).cumprod().mul(self.principal).values
        )
        return self

    @property
    def p(self) -> pd.Series:
        result = self.pxs.loc[self.d]
        if isinstance(result, pd.Series):
            return result
        raise ValueError("..")

    def record(self) -> None:
        d = as_date(self.d, "%Y-%m-%d")
        self.db.book.d.append(d)
        self.db.book.v.append(self.v)
        self.db.book.l.append(self.l)
        self.db.book.s.append(self.s.dropna().to_dict())
        self.db.book.w.append(self.w.dropna().to_dict())
        self.db.book.c.append(self.c.dropna().to_dict())
        self.db.book.a.append(self.a.dropna().to_dict())
        self.a = pd.Series(dtype=float)

    @staticmethod
    def clean_weight(
        weight: pd.Series,
        decimals: int = 4,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        sum_weight: float = 1.0,
    ) -> pd.Series:
        """Clean weight based on minimum, maximum and summartion of weight.

        Args:
            weight (pd.Series): weight of assets.
            decimals (int, optional): number of decimals to be rounded for
                weight. Defaults to 4.
            min_weight (float, optional): minimum weight. Defaults to 0..
            max_weight (float, optional): maximum weight. Defaults to 1..
            sum_weight (float, optional): summation weight. Defaults to 1..

        Returns:
            pd.Series: clean weight of assets.
        """
        if weight.empty:
            return weight

        # clip weight values by minimum and maximum.
        weight = weight.clip(lower=min_weight, upper=max_weight)
        weight = weight.round(decimals=decimals)
        # repeat round and weight calculation.
        for _ in range(200):
            weight = weight / sum_weight * sum_weight
            weight = weight.round(decimals=decimals)
            if weight.sum() == sum_weight:
                return weight
        # if residual remains after repeated rounding.
        # allocate the the residual weight on the max weight.
        residual = sum_weight - weight.sum()
        # !!! Error may occur when there are two max weights???
        weight.iloc[int(np.argmax(weight))] += np.round(residual, decimals=decimals)
        return weight

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.db.book.d)

    @property
    def nav(self) -> pd.Series:
        return pd.Series(data=self.db.book.v, index=self.dates, name="Strategy")

    @property
    def bm(self) -> pd.Series:
        return pd.Series(data=self.db.book.b, index=self.dates, name="Benchmark")

    def generate_trade_dates(self):
        # Generate monthly dates
        date_range = pd.date_range(start=self.d, end=self.end, freq=self.frequency)
        # Ensure self.d is included
        trade_dates = pd.DatetimeIndex([self.d]).union(date_range)
        trade_dates = trade_dates.sort_values().drop_duplicates()
        # Filter out dates before self.d
        trade_dates = trade_dates[trade_dates >= self.d]
        return trade_dates
