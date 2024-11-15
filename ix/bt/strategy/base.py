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
    start: pd.Timestamp = pd.Timestamp("2000-1-3")
    frequency: str = "ME"

    def __init__(self) -> None:
        self.d = self.start
        self.v = self.principal
        self.l = self.principal
        self.w = pd.Series(dtype=float)
        self.s = pd.Series(dtype=float)
        self.c = pd.Series(dtype=float)
        self.a = pd.Series(dtype=float)
        self.pxs = pd.DataFrame(dtype=float)
        self.db = db.Strategy.find_one(
            {"code": self.__class__.__name__}
        ).run() or db.Strategy(code=self.__class__.__name__)
        if self.db.book.d:
            self.d = pd.Timestamp(self.db.book.d[-1])
            self.v = self.db.book.v[-1]
            self.l = self.db.book.l[-1]
            self.w = pd.Series(self.db.book.w[-1])
            self.s = pd.Series(self.db.book.s[-1])
            self.c = pd.Series(self.db.book.c[-1])
            self.a = pd.Series(self.db.book.a[-1])

        self.pxs = pd.DataFrame()
        self.trade_dates = []

    def save(self):
        self.db.last_updated = as_date(self.d, "%Y-%m-%d")
        if self.db.book.v:
            self.db.ann_return = to_ann_return(self.nav)
            self.db.ann_volatility = to_ann_volatility(self.nav)
            self.db.nav_history = self.nav.iloc[-30:].to_list()
        db.Strategy.save(self.db)

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
        if not self.a.empty:
            self.c = self.a.mul(self.v).dropna()
            self.s = self.c.div(self.p).dropna()
            self.l = self.v - self.c.sum()
            self.w = self.c.div(self.v)
            self.a = pd.Series(dtype=float)

    @property
    def p(self) -> pd.Series:
        p = {asset: self.pxs[asset].loc[self.d] for asset in self.assets}
        return pd.Series(p).dropna()

    def sim(self) -> "Strategy":
        self.pxs = db.get_pxs(self.assets)
        self.trade_dates = self.generate_trade_dates()
        self.initialize()
        if self.d == self.start:
            self.a = self.allocate()
        for i, self.d in enumerate(pd.to_datetime(self.pxs.loc[self.d :].index)):

            if i == 0 and self.d != self.start:
                continue

            self.mtm()
            if self.d in self.trade_dates:
                self.a = self.allocate().dropna()
            self.record()

        b = (
            db.get_pxs(codes=list(self.bm_assets))
            .resample("D")
            .last()
            .reindex(self.dates)
            .ffill()
        )

        bm_weight = pd.Series(self.bm_assets)

        self.db.book.b = list(
            b.pct_change()
            .mul(bm_weight)
            .sum(axis=1)
            .add(1)
            .cumprod()
            .mul(self.principal)
            .values
        )

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
        dates = pd.date_range(
            start=self.start, end=self.pxs.index[-1], freq=self.frequency
        )
        reb_dates = []
        for date in dates:
            last_date = self.pxs.loc[:date].index[-1]
            reb_dates.append(last_date)
        return reb_dates

    def refresh(self) -> "Strategy":
        self.d = self.start
        self.v = self.principal
        self.l = self.principal
        self.w = pd.Series(dtype=float)
        self.s = pd.Series(dtype=float)
        self.c = pd.Series(dtype=float)
        self.a = pd.Series(dtype=float)
        self.db = db.Strategy(code=self.__class__.__name__)
        self.sim()
        return self
