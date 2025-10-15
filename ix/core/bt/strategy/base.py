import pandas as pd
from ix import db
from ix.misc import get_logger, as_date
from ix.core.perf import to_ann_return, to_ann_volatility

logger = get_logger(__name__)


class Strategy:
    principal: int = 10_000
    assets: list[str] = ["SPY US Equity", "AGG US Equity", "TLT US Equity",]
    bm_assets: dict[str, float] = {"SPY US Equity": 1.00}
    start: pd.Timestamp = pd.Timestamp("2020-1-3")
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
        self.db = (
            db.Strategy.find_one({"code": self.__class__.__name__}).run()
            or db.Strategy(code=self.__class__.__name__)
        )
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
        self.pxs = db.get_px_last(self.assets)
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
            db.get_px_last(codes=list(self.bm_assets))
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

    def plot(self):
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=1,
            vertical_spacing=0.1,
        )

        # Strategy NAV and benchmark trace
        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=self.nav.round(2),
                mode="lines",
                name="Strategy",
                line=dict(color="#1f77b4"),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=self.bm.round(2),
                mode="lines",
                name="Benchmark",
                line=dict(color="#ff7f0e"),
            ),
            row=1,
            col=1,
        )

        # Title for the plot
        title = f"{self.__class__.__name__} Performance"
        # latest_date = self.dates[-1].strftime("%Y-%m-%d")
        # fig.update_layout(title_text=f"{title}<br>As of {latest_date}")

        # Allocation data
        allocations = self.allocations.round(4)

        if not allocations.empty and not allocations.isna().all().all():
            # Stacked area chart for allocations
            colors = [
                "#1f77b4",
                "#ff7f0e",
                "#2ca02c",
                "#d62728",
                "#9467bd",
                "#8c564b",
                "#e377c2",
                "#7f7f7f",
                "#bcbd22",
                "#17becf",
            ]  # example colors

            # Prepare data for stacked area plot
            allocations_filled = allocations.fillna(0).values
            labels = allocations.columns
            for i in range(allocations_filled.shape[1]):
                fig.add_trace(
                    go.Scatter(
                        x=allocations.index,
                        y=allocations_filled[:, i],
                        name=labels[i],
                        stackgroup="allocations",
                        line=dict(width=0.5, color=colors[i % len(colors)]),
                        fillcolor=colors[i % len(colors)],
                    ),
                    row=2,
                    col=1,
                )

        else:
            # No allocation data
            fig.add_annotation(
                text="No allocation data",
                xref="x domain",
                yref="y domain",
                x=0.5,
                y=0.5,
                showarrow=False,
                row=2,
                col=1,
            )

        # Update layout
        fig.update_layout(
            showlegend=True,
            hovermode="x unified",
        )

        fig.update_yaxes(title_text="Value", row=1, col=1)
        fig.update_yaxes(title_text="Allocation", row=2, col=1)

        return fig

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
