import numpy as np
import pandas as pd
from ix import db
from ix.misc import get_logger, as_date


logger = get_logger(__name__)


class Book:

    def __init__(self) -> None:

        self.data = {
            "d": [],
            "v": [],
            "s": [],
            "c": [],
            "w": [],
            "a": [],
            "l": [],
        }

    @property
    def d(self) -> pd.DatetimeIndex:
        d = pd.to_datetime(self.data["d"])
        return d

    @property
    def v(self) -> pd.Series:
        v = pd.Series(data=self.data["v"], index=self.d)
        return v

    @property
    def l(self) -> pd.Series:
        l = pd.Series(data=self.data["l"], index=self.d)
        return l

    @property
    def w(self) -> pd.DataFrame:
        w = pd.DataFrame(data=self.data["w"], index=self.d)
        return w

    @property
    def a(self) -> pd.DataFrame:
        a = pd.DataFrame(data=self.data["a"], index=self.d)
        a = a.sort_index().dropna(how="all")
        return a


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
        self.book = Book()
        try:
            strategy = db.Strategy.find_one({"code": self.__class__.__name__}).run()
            if strategy is not None:
                data = strategy.data
                self.book.data = data
                d = self.book.data["d"][-1]
                d = pd.Timestamp(d) + pd.DateOffset(days=1)
                self.d = d
                self.v = self.book.data["v"][-1]
                self.l = self.book.data["l"][-1]
                self.p = self.book.data["p"][-1]
                self.w = self.book.data["w"][-1]
                self.s = self.book.data["s"][-1]
                self.c = self.book.data["c"][-1]
                self.a = self.book.data["a"][-1]
            self.initialize()
        except Exception as e:
            print(e)

    def dump(self):
        try:
            strategy = db.Strategy.find_one({"code": self.__class__.__name__}).run()
            if strategy is None:
                db.Strategy.insert_one(
                    db.Strategy(code=self.__class__.__name__, data=self.book.data)
                )
            else:
                strategy.update({"data": self.book.data}).run()
        except Exception as e:
            print(e)

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
        self.book.data["d"].append(d)
        self.book.data["v"].append(self.v)
        self.book.data["l"].append(self.l)
        self.book.data["s"].append(self.s.dropna().to_dict())
        self.book.data["w"].append(self.w.dropna().to_dict())
        self.book.data["c"].append(self.c.dropna().to_dict())
        self.book.data["a"].append(self.a.dropna().to_dict())
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
