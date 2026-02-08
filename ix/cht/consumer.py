import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries
from .style import apply_academic_style, add_zero_line, get_value_label


def MedianWageByQuartile() -> go.Figure:
    """Median Wage Growth by Quartile 12MMA"""
    try:
        df = MultiSeries(
            **{
                "1st Quartile": Series("USLM7851182:PX_LAST"),
                "2nd Quartile": Series("USLM7851183:PX_LAST"),
                "3rd Quartile": Series("USLM7851184:PX_LAST"),
                "4th Quartile": Series("USLM7851185:PX_LAST"),
            }
        ).iloc[-12 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                mode="lines",
                line=dict(width=2.5),
                hovertemplate=f"<b>{col}</b>: %{{y:.2f}}%<extra></extra>",
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Median Wage Growth by Quartile 12MMA</b>"),
        yaxis_title="Wage Growth (%)",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])

    return fig
