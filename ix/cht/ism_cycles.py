from ix import Series
import plotly.graph_objects as go
from ix.misc.theme import theme
from ix.db.query import Cycle
from .base import timeseries_layout


def IsmCycleSP500() -> go.Figure:

    name = "S&P500"
    px = Series("SPX Index:PX_LAST").resample("W").last().pct_change(52).dropna()

    fig = go.Figure()

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM {ism.iloc[-1]:.2f}",
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    cycle = Cycle(ism, 60)
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=px.index,
            y=px.values,
            name=f"{name} YoY",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="%{y:.2%}",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
            "yaxis2": dict(
                title=dict(text="Asset YoY", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
        }
    )
    fig.update_layout(layout)

    return fig


def IsmCycleUST10Y() -> go.Figure:

    name = "US Treasury 10Y"
    px = Series("TRYUS10Y:PX_YTM").resample("W").last().pct_change(52).dropna()

    fig = go.Figure()

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="ISM",
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="%{y:.2f}",
            # yaxis="y2",
        )
    )

    cycle = Cycle(ism, 60)
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=px.index,
            y=px.values,
            name=f"{name} YoY",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="%{y:.2%}",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
            "yaxis2": dict(
                title=dict(text="Asset YoY", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
        }
    )
    fig.update_layout(layout)

    return fig


def IsmCycleCrude() -> go.Figure:

    name = "Crudi Oil"
    px = Series("CL1 Comdty:PX_LAST").resample("W").last().pct_change(52).dropna()

    fig = go.Figure()

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="ISM",
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="%{y:.2f}",
            # yaxis="y2",
        )
    )

    cycle = Cycle(ism, 60)
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=px.index,
            y=px.values,
            name=f"{name} YoY",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="%{y:.2%}",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
            "yaxis2": dict(
                title=dict(text="Asset YoY", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
        }
    )
    fig.update_layout(layout)

    return fig


def IsmCycleBitcoin() -> go.Figure:

    name = "Bitcoin"
    px = Series("XBTUSD Curncy:PX_LAST").resample("W").last().pct_change(52).dropna()

    fig = go.Figure()

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="ISM",
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="%{y:.2f}",
            # yaxis="y2",
        )
    )

    cycle = Cycle(ism, 60)
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=px.index,
            y=px.values,
            name=f"{name} YoY",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="%{y:.2%}",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
            "yaxis2": dict(
                title=dict(text="Asset YoY", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
        }
    )
    fig.update_layout(layout)

    return fig


def IsmCycleDollar() -> go.Figure:

    name = "DXY"
    px = Series("DXY Index:PX_LAST").resample("W").last().pct_change(52).dropna()

    fig = go.Figure()

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="ISM",
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="%{y:.2f}",
            # yaxis="y2",
        )
    )

    cycle = Cycle(ism, 60)
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=px.index,
            y=px.values,
            name=f"{name} YoY",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="%{y:.2%}",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
            "yaxis2": dict(
                title=dict(text="Asset YoY", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
        }
    )
    fig.update_layout(layout)

    return fig


def IsmCycleGoldtoCopper() -> go.Figure:

    name = "Gold/Copper"
    px = (
        (Series("GC1 Comdty:PX_LAST") / Series("HG1 Comdty:PX_LAST"))
        .resample("W")
        .last()
        .pct_change(52)
        .dropna()
    )

    fig = go.Figure()

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name="ISM",
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="%{y:.2f}",
            # yaxis="y2",
        )
    )

    cycle = Cycle(ism, 60)
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="%{y:.2f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=px.index,
            y=px.values,
            name=f"{name} YoY",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="%{y:.2%}",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
            "yaxis2": dict(
                title=dict(text="Asset YoY", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
        }
    )
    fig.update_layout(layout)

    return fig
