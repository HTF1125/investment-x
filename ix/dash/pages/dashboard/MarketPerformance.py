import pandas as pd
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import plotly.graph_objects as go
from ix.db import Universe
from ix.core import rebase
from ix.dash.settings import colors
from ix.misc.date import today, oneyearbefore
from ix.dash.components import ChartGrid

def CardwithHeader(title: str, children: ...):
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H4(
                    title,
                    className="mb-0",
                    style={
                        "color": "#f1f5f9",
                        "fontSize": "1.1rem",
                        "fontWeight": "600",
                        "lineHeight": "1.2",
                    },
                ),
                style={
                    "background": "rgba(51, 65, 85, 0.9)",
                    "borderBottom": "1px solid rgba(148, 163, 184, 0.3)",
                    "padding": "0.35rem 0.75rem",
                    "minHeight": "unset",
                    "height": "2.2rem",
                    "display": "flex",
                    "alignItems": "center",
                },
            ),
            dbc.CardBody(
                children=children,
                style={
                    "padding": "0.5rem",
                    "background": "rgba(30, 41, 59, 0.9)",
                },
            ),
        ],
        style={
            "background": "rgba(30, 41, 59, 0.9)",
            "border": "1px solid rgba(148, 163, 184, 0.3)",
            "borderRadius": "12px",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
            "transition": "all 0.3s ease",
            "overflow": "hidden",
            "marginBottom": "1rem",
        },
        className="h-100",
    )


def create_performance_chart(pxs: pd.DataFrame) -> go.Figure:

    fig = go.Figure()
    for i, (name, series) in enumerate(pxs.items()):
        d = rebase(series.dropna()).sub(1)
        latest_value = float(d.iloc[-1])

        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d.values,
                name=f"{name} : ({latest_value:.2%})",
                line=dict(
                    width=2,
                    color=colors[i % len(colors)],
                    shape="spline",
                ),
                hovertemplate=f"<b>{name}</b> : %{{y:.2%}} %<extra></extra>",
            )
        )
    fig.update_layout(
        xaxis=dict(
            title="Date",
            title_font=dict(size=12, color="#94a3b8", family="Inter"),
            tickfont=dict(size=11, color="#64748b"),
            gridcolor="rgba(148, 163, 184, 0.2)",
            gridwidth=1,
        ),
        yaxis=dict(
            title="Performance",
            title_font=dict(size=12, color="#94a3b8", family="Inter"),
            tickfont=dict(size=11, color="#64748b"),
            gridcolor="rgba(148, 163, 184, 0.2)",
            gridwidth=1,
            tickformat=".0%",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30, 41, 59, 0.9)",
            bordercolor="rgba(148, 163, 184, 0.3)",
            font=dict(size=10, color="#f1f5f9", family="Inter"),
            borderwidth=0,
            valign="middle",
            xref="paper",
            yref="paper",
            # itemwidth=100,
            itemsizing="trace",
            title_text='',
            traceorder="normal",
            # Centered and fill horizontally
            # Use full width by setting x=0.5 and anchor to center, and let Plotly auto-wrap
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        font=dict(family="Inter", color="#f1f5f9"),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(30, 41, 59, 0.95)",
            bordercolor="rgba(148, 163, 184, 0.3)",
            font=dict(color="#f1f5f9", family="Inter", size=11),
        ),
    )
    return fig


def Section(
    universes: list[str] = [
        "Major Indices",
        "Global Markets",
        "Sectors",
        "Themes",
        "Commodities",
        "Currencies",
    ],
    periods: list[int] = [1, 5, 21, 63, 126, 252],
):

    # Collect all performance charts second
    chart_cards = []
    for universe in universes:
        universe_db = Universe.from_name(universe)
        pxs = universe_db.get_series(field="PX_LAST")
        pxs = pxs.loc[oneyearbefore() : today()]

        chart_cards.append(
            CardwithHeader(
                title=universe,
                children=dcc.Graph(
                    figure=create_performance_chart(pxs),
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                        "autosizable": True,
                    },
                    style={
                        "width": "100%",
                        "height": "400px",
                        "minHeight": "300px",
                        "maxHeight": "500px",
                        "minWidth": "400px",
                    },
                ),
            )
        )

    return html.Div(
        [
            html.Section(
                [
                    # Heatmaps section
                    html.Div(
                        [
                            html.H3(
                                "Performance Heatmaps",
                                style={
                                    "fontSize": "1.3rem",
                                    "fontWeight": "600",
                                    "color": "#f1f5f9",
                                    "marginTop": "1.5rem",
                                    "marginBottom": "1rem",
                                    "paddingBottom": "0.5rem",
                                    "borderBottom": "2px solid #3b82f6",
                                },
                            ),
                            ChartGrid(chart_cards),
                        ]
                    ),
                ],
                style={"padding": "1rem 0"},
            ),
        ]
    )
