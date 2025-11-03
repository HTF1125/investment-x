import plotly.graph_objects as go
import pandas as pd

from ix.db.query import Series
from ix.core import Cycle
from ix.misc import oneyearlater
from ix.misc import theme

# Dark theme timeseries layout based on p.ipynb styles
# Move legend below the plot to avoid overlap with title
timeseries_layout = dict(
    title=dict(
        y=0.95,
        x=0.5,
        xanchor="center",
        yanchor="top",
        font=dict(size=14, family="Arial Black", color="#FFFFFF"),
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
        title=dict(
            font=dict(
                color="#FFFFFF",
                size=10,
                family="Arial Black",
            )
        ),
        gridcolor="rgba(255,255,255,0.2)",
        zeroline=False,
        showline=True,
        linecolor="rgba(255,255,255,0.4)",
        mirror=True,
        showgrid=False,
        tickfont=dict(color="#FFFFFF"),
    ),
    yaxis2=dict(
        title=dict(
            font=dict(
                color="#FFFFFF",
                size=10,
                family="Arial Black",
            )
        ),
        overlaying="y",
        side="right",
        tickformat=".0%",
        gridcolor="rgba(255,255,255,0.2)",
        zeroline=False,
        showline=False,
        showgrid=False,
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
    margin=dict(t=60, b=60),
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
                line=dict(width=3, color=theme.colors.blue[400]),
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
                line=dict(width=3, dash="dash", color=theme.colors.red[400]),
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
                line=dict(width=3, color=theme.colors.green[400]),
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
            ),
            yaxis=dict(
                range=[30, 70],
                tickformat=".0f",
            ),
            yaxis2=dict(
                tickformat=".0%",
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

from ix.db.query import Series

# from ix.db.custom import financial_conditions_index_us
import plotly.graph_objects as go
from ix.core import Offset, Cycle
from ix.misc import oneyearlater


def FinancialConditionsUS(start: str = "2015-1-1"):
    # TODO: Implement financial conditions index
    fig = go.Figure()

    # Temporary placeholder - return empty figure
    fig.add_annotation(
        text="Financial Conditions Index not available",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16),
    )

    fig.update_layout(
        title="US Financial Conditions Index",
        xaxis_title="Date",
        yaxis_title="Index Value",
        height=400,
    )

    return fig
