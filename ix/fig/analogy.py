import plotly.graph_objects as go

from ix.db.query import Offset, Series
from ix.misc import theme
from .base import timeseries_layout


def sp500_7year_cycle() -> go.Figure:

    # =GetSeries({"S&P500 YoY=Series('SPX Index:PX_LAST', 'ME').pct_change(12).mul(100).dropna()","S&P500 YoY (7Y Lead)=MonthEndOffset(Series('SPX Index:PX_LAST', 'ME').pct_change(12).mul(100).dropna(),7*12)"}, EOMONTH(AsOfDate,-240))
    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    sp500_yo_y = Series("SPX Index:PX_LAST", "W").pct_change(52).dropna()
    if not sp500_yo_y.empty:
        fig.add_trace(
            go.Scatter(
                x=sp500_yo_y.index,
                y=sp500_yo_y.values,
                name=f"S&P500 YoY",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>S&P500 YoY</b>: %{y:.2%}<extra></extra>",
                yaxis="y1",
            )
        )

    sp500_yo_y_7y_lead = Offset(sp500_yo_y, days=7 * 52 * 7)

    if not sp500_yo_y_7y_lead.empty:
        fig.add_trace(
            go.Scatter(
                x=sp500_yo_y_7y_lead.index,
                y=sp500_yo_y_7y_lead.values,
                name=f"S&P500 YoY (7Y Lead)",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>S&P500 YoY (7Y Lead)</b>: %{y:.2%}<extra></extra>",
                yaxis="y1",
            )
        )
        fig.update_layout(
            {
                "title": dict(
                    text=f"S&P500 YoY & S&P500 YoY (7Y Lead)",
                ),
                "yaxis": dict(
                    tickformat=".0%",
                    range=[-0.2, 0.4],
                ),
            }
        )
    return fig
