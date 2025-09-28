import plotly.graph_objects as go
from ix.dash.settings import theme

import pandas as pd


def apply_layout(fig: go.Figure):

    return fig.update_layout(
        title=dict(
            font=dict(size=14, color=theme.text),
            y=0.90,
            x=0.5,
            xanchor="center",
            yanchor="bottom",
            yref="container",
        ),
        paper_bgcolor=theme.bg,
        plot_bgcolor=theme.bg_light,
        font=dict(color=theme.text, family="Roboto, Arial, sans-serif", size=12),
        margin=dict(l=20, r=20, t=30, b=30),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=theme.bg_light,
            bordercolor=theme.border,
            font=dict(color=theme.text, size=11),
        ),
        legend=dict(
            x=0.5,
            y=-0.15,
            xanchor="center",
            yanchor="top",
            orientation="h",
            bgcolor="rgba(0,0,0,0)",
            bordercolor=theme.border,
            borderwidth=1,
            font=dict(
                color=theme.text,
                size=10,
            ),
            itemsizing="trace",
            itemwidth=30,
            yref="paper",
            traceorder="normal",
        ),
        xaxis=dict(
            gridcolor=theme.border,
            gridwidth=0.5,
            zeroline=False,
            showline=True,
            linecolor=theme.border,
            tickformat="%b\n%Y",  # Month-Year
            tickfont=dict(color=theme.text_light, size=10),
            automargin="height",
        ),
        yaxis=dict(
            gridcolor=theme.border,
            gridwidth=0.5,
            zeroline=True,
            zerolinecolor=theme.text_light,
            zerolinewidth=1,
            tickfont=dict(color=theme.text_light, size=10),
            domain=[0, 0.9],
        ),
        yaxis2=dict(
            gridcolor=theme.border,
            gridwidth=0.5,
            zeroline=True,
            zerolinecolor=theme.text_light,
            zerolinewidth=1,
            tickfont=dict(color=theme.text_light, size=10),
            domain=[0, 0.9],
            overlaying="y",
            side="right",
        ),
        uniformtext=dict(minsize=10, mode="show"),
        autosize=True,
    )


def OecdCliRegime() -> go.Figure:
    fig = go.Figure()

    fig.update_layout(
        barmode="stack",
        title=dict(text=f"PMI Manufacturing Regime"),
    )
    from ix.db import oecd_cli_regime

    regimes = oecd_cli_regime()

    # Use theme.chart_colors for bar colors
    colors = theme.chart_colors
    for i, (name, series) in enumerate(regimes.items()):
        color = colors[i % len(colors)]
        fig.add_trace(
            go.Bar(
                x=series.index,
                y=series.values,
                name=name,
                marker_color=color,
                hovertemplate="%{y:.2f}",
            )
        )

    return apply_layout(fig)
