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
    commission: int = 15

    def __init__(self, verbose: bool = False) -> None:

        self.verbose = verbose
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

    def delete(self):
        return (
            db.Strategy.find_one(db.Strategy.code == self.__class__.__name__)
            .delete()
            .run()
        )

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
            t = self.w.sub(self.a, fill_value=0).abs().sum()
            cost = self.v * t * self.commission / 10_000
            self.v = self.v - cost
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
        for i, self.d in enumerate(pd.to_datetime(self.pxs.loc[self.d :].index)):
            if i == 0 and self.d != self.start:
                continue
            self.mtm()
            if self.d in self.trade_dates or i == 1:
                self.a = self.allocate().dropna()
                if self.verbose:
                    logger.info(f"{self.d} : allocation : {self.a.to_dict()}")
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
        self.delete()
        self.d = self.start
        self.v = self.principal
        self.l = self.principal
        self.w = pd.Series(dtype=float)
        self.s = pd.Series(dtype=float)
        self.c = pd.Series(dtype=float)
        self.a = pd.Series(dtype=float)
        self.db = db.Strategy(code=self.__class__.__name__)
        self.sim()
        self.save()
        return self

    def plot(self, figsize=(12, 8), title=None):
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import numpy as np

        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 1, height_ratios=[3, 2])
        ax1 = fig.add_subplot(gs[0, :])
        ax2 = fig.add_subplot(gs[1, :], sharex=ax1)

        # Plot strategy NAV and benchmark
        ax1.plot(
            self.dates,
            self.nav.round(2),
            label="Strategy",
            linewidth=2,
            color="#1f77b4",
        )
        ax1.plot(
            self.dates,
            self.bm.round(2),
            label="Benchmark",
            linewidth=2,
            color="#ff7f0e",
        )

        # Set title
        if title is None:
            title = f"{self.__class__.__name__} Performance"
        latest_date = self.dates[-1].strftime("%Y-%m-%d")
        fig.suptitle(
            f"{title}\nAs of {latest_date}",
            fontsize=16,
            fontweight="bold",
            color="#333333",
        )

        # Set labels for NAV plot
        ax1.set_ylabel("Value", fontsize=12, fontweight="bold", color="#333333")
        ax1.legend(fontsize=10, loc="upper left")
        ax1.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))

        # Plot allocations as stacked area chart
        allocations = self.allocations.round(4)

        if not allocations.empty and not allocations.isna().all().all():
            # Create a color map
            colors = plt.cm.get_cmap("tab20")(
                np.linspace(0, 1, len(allocations.columns))
            )

            # Prepare data for stacked area plot
            allocations_filled = allocations.fillna(0).values
            ax2.stackplot(
                allocations.index,
                allocations_filled.T,
                labels=allocations.columns,
                colors=colors,
                alpha=0.8,
            )

            # Set labels for allocations plot
            ax2.set_xlabel("Date", fontsize=12, fontweight="bold", color="#333333")
            ax2.set_ylabel(
                "Allocation", fontsize=12, fontweight="bold", color="#333333"
            )
            ax2.legend(fontsize=10, loc="center left", bbox_to_anchor=(1, 0.5))
            ax2.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_visible(False)
            ax2.set_ylim(0, 1)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.0%}"))

        else:
            ax2.text(
                0.5,
                0.5,
                "No allocation data",
                ha="center",
                va="center",
                fontsize=14,
                color="#333333",
            )
            ax2.axis("off")

        # Format x-axis for both subplots
        ax1.xaxis.set_major_locator(mdates.YearLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax1.xaxis.set_minor_locator(mdates.MonthLocator())
        ax2.xaxis.set_major_locator(mdates.YearLocator())
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax2.xaxis.set_minor_locator(mdates.MonthLocator())

        fig.autofmt_xdate()

        # Add a subtle background color
        fig.patch.set_facecolor("#f9f9f9")
        ax1.set_facecolor("#ffffff")
        ax2.set_facecolor("#ffffff")

        # Adjust layout and display the plot
        plt.tight_layout(rect=[0, 0, 1, 0.95])  # Add space for title
        plt.show()

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.db.book.d)

    @property
    def nav(self) -> pd.Series:
        return pd.Series(data=self.db.book.v, index=self.dates, name="Strategy")

    @property
    def bm(self) -> pd.Series:
        return pd.Series(data=self.db.book.b, index=self.dates, name="Benchmark")

    @property
    def alpha(self) -> pd.Series:

        return (
            self.nav.pct_change().sub(self.bm.pct_change()).fillna(0).add(1).cumprod()
        )

    @property
    def allocations(self) -> pd.DataFrame:
        return pd.DataFrame(
            data=self.db.book.a,
            index=self.dates,
        ).dropna(how="all")

    @property
    def weights(self) -> pd.DataFrame:
        return pd.DataFrame(
            data=self.db.book.w,
            index=self.dates,
        ).dropna(how="all")
