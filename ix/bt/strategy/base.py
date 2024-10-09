import numpy as np
import pandas as pd
from ix import db
from ix.db.models.strategy import Book
from ix.misc import get_logger, as_date
from ix.core import to_ann_return, to_ann_volatility

logger = get_logger(__name__)


class Strategy:

    assets: list[str] = ["SPY", "AGG", "TLT"]
    start: str = "2000-1-1"
    frequency: int = 1

    def __init__(self, principal: int = 10_000) -> None:
        self.d = self.start
        self.v = principal
        self.l = principal
        self.p = pd.Series(dtype=float)
        self.w = pd.Series(dtype=float)
        self.s = pd.Series(dtype=float)
        self.c = pd.Series(dtype=float)
        self.a = pd.Series(dtype=float)
        self.pxs = db.get_pxs(self.assets)
        code = self.__class__.__name__
        self.db = (
            db.Strategy.find_one({"code": code}).run()
            or db.Strategy(code=code).create()
        )
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
        for idx, (self.d, self.p) in enumerate(self.pxs.loc[self.d :].iterrows(), 0):
            print(self.d)
            self.mtm()
            if not self.a.empty:
                self.c = self.a.mul(self.v).dropna()
                self.s = self.c.div(self.p).dropna()
                self.l = self.v - self.c.sum()
                self.w = self.c.div(self.v)
            self.record()
            if idx % self.frequency == 0:
                self.a = self.clean_weight(self.allocate())
        return self

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
        return pd.Series(data=self.db.book.v, index=self.dates, name="Net Asset Value")
