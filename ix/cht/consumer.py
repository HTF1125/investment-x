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
        )
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
                hovertemplate=f"{col}: %{{y:.2f}}%<extra></extra>",
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Median Wage Growth by Quartile 12MMA</b>"),
        yaxis_title="Wage Growth (%)",
    )

    if not df.empty:
        from datetime import datetime
        latest_date = df.index.max()
        start_date = datetime(latest_date.year - 10, 1, 1)
        fig.update_xaxes(range=[start_date, latest_date])
    return fig

    return fig
