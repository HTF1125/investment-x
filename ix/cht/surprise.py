import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, Offset, Cycle
from .style import apply_academic_style, add_zero_line, get_value_label


def USSurpriseUST10YCycle() -> go.Figure:
    """US Economic Surprise vs Yield Deviation"""
    try:
        df = MultiSeries(
            **{
                "UST10Y Deviation (10W Lead)": Offset(
                    Series("TRYUS10Y:PX_YTM")
                    - Series("TRYUS10Y:PX_YTM").rolling(60).mean(),
                    days=70,
                ),
                "CESI (US)": Series("USFXCESIUSD:PX_LAST"),
                "Cycle": Cycle(Series("USFXCESIUSD:PX_LAST")),
            }
        ).iloc[-500:]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. UST10Y (Secondary)
    col1 = "UST10Y Deviation (10W Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=f"UST10Y Dev (Lead 10W) ({df[col1].iloc[-1]:.2f}%)",
            mode="lines",
            line=dict(width=3),
            hovertemplate="UST10Y Dev: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    # 2. CESI (Primary)
    col2 = "CESI (US)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "Economic Surprise (CESI)"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="Economic Surprise (CESI): %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 3. Cycle (Primary)
    col3 = "Cycle"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col3],
            name=get_value_label(df[col3], "CESI Cycle"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="CESI Cycle: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Economic Surprise vs Yield Deviation</b>"),
        yaxis=dict(title="CESI / Surprise Cycle"),
        yaxis2=dict(
            title="UST 10Y Deviation (%)", showgrid=False, autorange="reversed"
        ),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def USSurpriseDollarCycle() -> go.Figure:
    """US Economic Surprise vs Dollar Deviation"""
    try:
        df = MultiSeries(
            **{
                "Dollar Deviation (10W Lead)": Offset(
                    Series("DXY INDEX:PX_LAST")
                    - Series("DXY INDEX:PX_LAST").rolling(60).mean(),
                    days=70,
                ),
                "CESI (US)": Series("USFXCESIUSD:PX_LAST"),
                "Cycle": Cycle(Series("USFXCESIUSD:PX_LAST")),
            }
        ).iloc[-500:]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Dollar (Secondary Reversed)
    col1 = "Dollar Deviation (10W Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=f"Dollar Dev (Lead 10W) ({df[col1].iloc[-1]:+.2f}%)",
            mode="lines",
            line=dict(width=3),
            hovertemplate="Dollar Dev: %{y:+.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    # 2. CESI (Primary)
    col2 = "CESI (US)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "Economic Surprise (CESI)"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="Economic Surprise (CESI): %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 3. Cycle (Primary)
    col3 = "Cycle"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col3],
            name=get_value_label(df[col3], "CESI Cycle"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="CESI Cycle: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Economic Surprise vs Dollar Deviation</b>"),
        yaxis=dict(title="CESI / Surprise Cycle"),
        yaxis2=dict(title="Dollar Deviation (%)", showgrid=False, autorange="reversed"),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig
