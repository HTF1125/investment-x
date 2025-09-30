import plotly.graph_objects as go
import pandas as pd
from ix.db import Series
from ix.core import Cycle
from ix.misc import oneyearlater

# Dark theme timeseries layout based on p.ipynb styles
# Move legend below the plot to avoid overlap with title
timeseries_layout = dict(
    title=dict(
        text="",
        x=0.05,
        font=dict(size=12, family="Arial Black", color="#FFFFFF"),
    ),
    xaxis=dict(
        tickformat="%b<br>%Y",
        gridcolor="rgba(255,255,255,0.2)",
        zeroline=False,
        showline=True,
        linecolor="rgba(255,255,255,0.4)",
        mirror=True,
        tickangle=0,
        tickfont=dict(color="#FFFFFF"),
    ),
    yaxis=dict(
        title=dict(text="", font=dict(color="#FFFFFF")),
        gridcolor="rgba(255,255,255,0.2)",
        zeroline=False,
        showline=True,
        linecolor="rgba(255,255,255,0.4)",
        mirror=True,
        tickfont=dict(color="#FFFFFF"),
    ),
    yaxis2=dict(
        title=dict(text="", font=dict(color="#FFFFFF")),
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
    hovermode="x unified",
    legend=dict(
        x=0.5,
        y=-0.18,  # Move legend below the plot area
        xanchor="center",
        yanchor="top",
        orientation="h",
        bgcolor="rgba(0,0,0,0.6)",
        bordercolor="rgba(255,255,255,0.3)",
        borderwidth=1,
        font=dict(color="#FFFFFF"),
    ),
    paper_bgcolor="#111111",
    plot_bgcolor="#111111",
    hoverlabel=dict(
        bgcolor="rgba(0,0,0,0.9)",
        font=dict(color="#FFFFFF", size=10),
        bordercolor="rgba(255,255,255,0.2)",
    ),
    margin=dict(t=20, b=90),  # Add more top and bottom margin for title and legend
)


def add_ism(fig: go.Figure) -> go.Figure:
    ism_data = Series("ISMPMI_M:PX_LAST").dropna()
    if not ism_data.empty:
        fig.add_trace(
            go.Scatter(
                x=ism_data.index,
                y=ism_data.values,
                name=f"ISM {float(ism_data.iloc[-1]):.2f}",
                line=dict(width=3, color="#1f77b4"),
                marker=dict(size=4),
                hovertemplate="<b>ISM</b>: %{y:.2f}<extra></extra>",
            )
        )
    return fig


def ISM_Cycle(px: pd.Series, start: str = "2015-1-1") -> go.Figure:

    fig = go.Figure()
    # ISM trace
    ism_data = Series("ISMPMI_M:PX_LAST").dropna()
    if not ism_data.empty:
        fig.add_trace(
            go.Scatter(
                x=ism_data.index,
                y=ism_data.values,
                name=f"ISM {float(ism_data.iloc[-1]):.2f}",
                line=dict(width=3, color="#1f77b4"),
                marker=dict(size=4),
                hovertemplate="<b>ISM</b>: %{y:.2f}<extra></extra>",
            )
        )
    # Cycle trace
    cycle_data = Cycle(ism_data, 60)
    if not cycle_data.empty:
        fig.add_trace(
            go.Scatter(
                x=cycle_data.index,
                y=cycle_data.values,
                name=f"Cycle {float(cycle_data.iloc[-1]):.2f}",
                line=dict(width=3, dash="dash", color="#ff7f0e"),
                marker=dict(size=4),
                hovertemplate="<b>Cycle</b>: %{y:.2f}<extra></extra>",
            )
        )

    # S&P 500 or asset trace
    asset_returns = px.resample("W").last().pct_change(52).dropna()
    if not asset_returns.empty:
        # Use asset_returns.name for label, but ensure it's not None
        asset_name = asset_returns.name if asset_returns.name else "Asset"
        # Format the hovertemplate correctly for plotly (not f-string for %{y})
        fig.add_trace(
            go.Scatter(
                x=asset_returns.index,
                y=asset_returns.values,
                name=f"{asset_name} YoY {float(asset_returns.iloc[-1]):.2%}",
                line=dict(width=3, color="#2ca02c"),
                marker=dict(size=4),
                hovertemplate=f"<b>{asset_name} YoY</b>: %{{y:.2%}}<extra></extra>",
                yaxis="y2",
            )
        )

    # Add annotation at y=50 to show expansion and contraction
    if not ism_data.empty:
        x_start = ism_data.index.min()
        x_end = ism_data.index.max()
        fig.add_shape(
            type="line",
            x0=x_start,
            x1=x_end,
            y0=50,
            y1=50,
            line=dict(color="rgba(200,200,200,0.5)", width=2, dash="dot"),
            xref="x",
            yref="y",
            layer="below",
        )

        fig.add_annotation(
            x=1,
            y=65,
            xref="paper",
            yref="y",
            text="Expansion",
            showarrow=False,
            font=dict(color="green", size=12),
            align="right",
            xanchor="right",
        )
        fig.add_annotation(
            x=1,
            y=35,
            xref="paper",
            yref="y",
            text="Contraction",
            showarrow=False,
            font=dict(color="red", size=12),
            align="right",
            xanchor="right",
        )

    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"ISM Business Cycle vs {asset_name}",
                y=0.96,  # Move title slightly down to avoid overlap with top
                x=0.5,
                xanchor="center",
                yanchor="top",
                font=dict(size=18, family="Arial Black", color="#FFFFFF"),
            ),
            yaxis=dict(
                title=dict(text="ISM Cycle"),
                range=[30, 70],
                tickformat=".0f",
                domain=[0, 0.9],
            ),
            yaxis2=dict(
                title=dict(text=f"{asset_name} YoY"),
                tickformat=".0%",
                domain=[0, 0.9],
            ),
        )
    )
    fig.update_xaxes(range=[pd.Timestamp(start), oneyearlater()])
    return fig


def ism_cycle_sp500(start: str = "2015-1-1") -> go.Figure:

    px = Series("SPX Index:PX_LAST", freq="W")
    px.name = "S&P500"
    return ISM_Cycle(px, start)


def ism_cycle_ust10y(start: str = "2015-1-1") -> go.Figure:

    px = Series("TRYUS10Y:PX_YTM", freq="W")
    px.name = "US Treasury 10Y"
    return ISM_Cycle(px, start)


def ism_cycle_crude(start: str = "2015-1-1") -> go.Figure:

    px = Series("CL1 Comdty:PX_LAST", freq="W")
    px.name = "Crude Oil"
    return ISM_Cycle(px, start)


def ism_cycle_bitcoin(start: str = "2015-1-1") -> go.Figure:

    px = Series("XBTUSD Curncy:PX_LAST", freq="W")
    px.name = "Bitcoin"
    return ISM_Cycle(px, start)


def ism_cycle_dollar(start: str = "2015-1-1") -> go.Figure:

    px = Series("DXY Index:PX_LAST", freq="W")
    px.name = "Dollar"
    return ISM_Cycle(px, start)


def ism_cycle_copper_to_gold_ratio(start: str = "2015-1-1") -> go.Figure:

    px = Series("HG1 Comdty:PX_LAST", freq="W") / Series("GC1 Comdty:PX_LAST", freq="W")
    px.name = "Copper/Gold"
    return ISM_Cycle(px, start)


import pandas as pd
from ix.db import Series
from ix.db.custom import financial_conditions_index_us
import plotly.graph_objects as go
from ix.core import Offset, Cycle
from ix.misc import oneyearlater


def financial_conditions_us(start: str = "2015-1-1"):

    fig = go.Figure()
    fci = Offset(financial_conditions_index_us(), months=6).clip(-1, 1)
    if not fci.empty:
        fig.add_trace(
            go.Scatter(
                x=fci.index,
                y=fci.values,
                name=f"FCI Lead 6M {float(fci.iloc[-1]):.2%}",
                line=dict(width=3, color="#1f77b4"),
                marker=dict(size=4),
                hovertemplate="<b>FCI</b>: %{y:.2f}<extra></extra>",
            )
        )

    cycle_data = Cycle(fci, 52 * 6)
    if not cycle_data.empty:
        fig.add_trace(
            go.Scatter(
                x=cycle_data.index,
                y=cycle_data.values,
                name=f"Cycle {float(cycle_data.iloc[-1]):.2%}",
                line=dict(width=3, dash="dash", color="#ff7f0e"),
                marker=dict(size=4),
                hovertemplate="<b>Cycle</b>: %{y:.2f}<extra></extra>",
            )
        )

    ism_data = Series("ISMPMI_M:PX_LAST").dropna()
    if not ism_data.empty:
        fig.add_trace(
            go.Scatter(
                x=ism_data.index,
                y=ism_data.values,
                name=f"ISM {float(ism_data.iloc[-1]):.2f}",
                line=dict(width=3, color="#2ca02c"),
                marker=dict(size=4),
                hovertemplate="<b>ISM</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )

    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"Financial Conditions Index (US)",
                y=0.96,  # Move title slightly down to avoid overlap with top
                x=0.5,
                xanchor="center",
                yanchor="top",
                font=dict(size=18, family="Arial Black", color="#FFFFFF"),
            ),
            yaxis=dict(
                title=dict(text="FCI Cycle"),
                range=[-1, 1],
                tickformat=".0%",
                domain=[0, 0.9],
            ),
            yaxis2=dict(
                title=dict(text=f"ISM"),
                range=[30, 70],
                tickformat=".0f",
                domain=[0, 0.9],
            ),
        )
    )
    fig.update_xaxes(range=[pd.Timestamp(start), oneyearlater()])
    return fig
