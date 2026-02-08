import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries
from .style import apply_academic_style, add_zero_line, get_value_label


def USFederalDebt() -> go.Figure:
    """US Federal Debt"""
    try:
        df = MultiSeries(
            **{
                "Outstanding ($Tn)": Series("US.CGOVD:PX_LAST", scale=1).div(10**12),
                "YoY (%)": Series("US.CGOVD:PX_LAST", scale=1).pct_change(12).mul(100),
            }
        ).iloc[-12 * 5 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Trace 1: Outstanding (Left Axis)
    col1 = "Outstanding ($Tn)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], "Outstanding", ".2f"),
            line=dict(width=2.5),
            hovertemplate="Outstanding: %{y:.2f}T<extra></extra>",
        ),
        secondary_y=False,
    )

    # Trace 2: YoY (Right Axis)
    col2 = "YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "YoY", "+.2f"),
            line=dict(width=2.5),
            hovertemplate="YoY: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Federal Debt</b>"),
        yaxis=dict(title="Outstanding ($Tn)", showgrid=True),
        yaxis2=dict(
            title="YoY (%)",
            showgrid=False,
            zeroline=True,
            zerolinecolor="black",
            zerolinewidth=1,
        ),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])

    return fig
