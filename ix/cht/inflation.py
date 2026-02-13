"""Inflation-related charts."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ix.db.query import Series, MultiSeries, MonthEndOffset
from .style import apply_academic_style, get_value_label, get_color


def CpiIsmPriceIndicators() -> go.Figure:
    """CPI vs ISM Price Paid Indicators (6M Lead)"""
    try:
        df = MultiSeries(
            **{
                "CPI YoY (%)": Series("BLSCUUR0000SA0:PX_LAST")
                .resample("ME")
                .ffill()
                .pct_change(12)
                .mul(100),
                "ISM Manu-Price Paid (6M Lead)": MonthEndOffset(
                    Series("ISMPRI_M:PX_LAST"), 6
                ),
                "ISM Serv-Price Paid (6M Lead)": MonthEndOffset(
                    Series("ISMPRI_NM:PX_LAST"), 6
                ),
            }
        ).iloc[-12 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # CPI (Primary Y-Axis - Left)
    col1 = "CPI YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".2f"),
            mode="lines",
            line=dict(color=get_color("Primary", 0), width=3),
            hovertemplate=f"{col1}: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # ISM Manufacturing Price Paid (Secondary Y-Axis - Right)
    col2 = "ISM Manu-Price Paid (6M Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "ISM Manu Price", ".1f"),
            mode="lines",
            line=dict(width=2),
            hovertemplate=f"{col2}: %{{y:.2f}}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    # ISM Services Price Paid (Secondary Y-Axis - Right)
    col3 = "ISM Serv-Price Paid (6M Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col3],
            name=get_value_label(df[col3], "ISM Serv Price", ".1f"),
            mode="lines",
            line=dict(width=2),
            hovertemplate=f"{col3}: %{{y:.2f}}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>CPI vs. ISM Price Indicators</b>"),
    )

    fig.update_yaxes(
        title="CPI YoY (%)",
        secondary_y=False,
    )
    fig.update_yaxes(
        title="ISM Diffusion Index",
        secondary_y=True,
        showgrid=False,
    )

    # Add reference line at 50 (neutral ISM level)
    fig.add_hline(
        y=50,
        line_dash="solid",
        line_color="gray",
        line_width=1,
        secondary_y=True,
        opacity=0.5,
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])

    return fig
