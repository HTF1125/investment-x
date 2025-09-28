from ix.fig.base import TimeseriesChart
from ix.db.query import Series, Cycle
import plotly.graph_objects as go
from ix.dash.settings import theme


class IsmCycle(TimeseriesChart):
    def add_ism(self):
        ism = Series("ISMPMI_M:PX_LAST").dropna()
        cycle = Cycle(ism, 60)
        self.fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name="ISM",
                line=dict(color=theme.chart_colors[0], width=2),
                hovertemplate="%{y:.2f}",
            )
        )
        self.fig.add_trace(
            go.Scatter(
                x=cycle.index,
                y=cycle.values,
                name="Cycle",
                line=dict(color=theme.chart_colors[1], width=2),
                hovertemplate="%{y:.2f}",
            )
        )

    def add_asset(self) -> None:
        sp = (
            Series("SPX Index:PX_LAST").resample("W-Fri").last().pct_change(52).dropna()
        )
        self.fig.add_trace(
            go.Scatter(
                x=sp.index,
                y=sp.values,
                name="SP500 YoY",
                line=dict(color=theme.chart_colors[2], width=3),
                hovertemplate="%{y:.2f}",
                yaxis="y2",
            )
        )

    def plot(self):
        self.add_ism()
        self.add_asset()
        return self.layout()
