from ix import Series
import plotly.graph_objects as go
from ix.misc.theme import theme
from ix.db.query import Cycle


def IsmCycleSP500() -> go.Figure:

    name = "S&P500"
    px = Series("SPX Index:PX_LAST").resample("W").last().pct_change(52).dropna()

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

    fig.update_layout(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                range=[30, 70],
                title=dict(
                    text="ISM",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="Asset YoY",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat=".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

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

    fig.update_layout(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                range=[30, 70],
                title=dict(
                    text="ISM",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="Asset YoY",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat=".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

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

    fig.update_layout(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                range=[30, 70],
                title=dict(
                    text="ISM",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="Asset YoY",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat=".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

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

    fig.update_layout(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                range=[30, 70],
                title=dict(
                    text="ISM",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="Asset YoY",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat=".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

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

    fig.update_layout(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                range=[30, 70],
                title=dict(
                    text="ISM",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="Asset YoY",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat=".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

    return fig


def IsmCycleGoldtoCopper() -> go.Figure:

    name = "Gold/Copper"
    px = (Series("GC1 Comdty:PX_LAST") / Series("HG1 Comdty:PX_LAST")).resample("W").last().pct_change(52).dropna()

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

    fig.update_layout(
        {
            "title": dict(
                text=f"ISM Cycle vs {name}",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                range=[30, 70],
                title=dict(
                    text="ISM",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="Asset YoY",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat=".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

    return fig
