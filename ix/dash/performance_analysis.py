"""
Performance Analysis Module

This module contains functions for creating performance charts and universe sections
for the dashboard.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc
from ix import MultiSeries, Rebase

def create_performance_chart(
    data: pd.Series, title: str, height: int = 350
) -> go.Figure:
    """Create horizontal bar chart"""
    colors = ["#48bb78" if x > 0 else "#f56565" for x in data.values]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=data.index,
            x=data.values,
            orientation="h",
            text=[f"{v:+.2%}%" for v in data.values],
            textposition="auto",
            textfont=dict(size=10, color="white", family="Inter"),
            marker=dict(color=colors, opacity=0.8),
            hovertemplate="<b>%{y}</b><br>Performance: %{x:.2%}%<extra></extra>",
        )
    )

    fig.update_layout(
        height=height,
        title=dict(
            text=title, x=0.5, font=dict(size=16, color="#ffffff", family="Inter")
        ),
        xaxis=dict(
            title="Return (%)",
            title_font=dict(size=12, color="#a0aec0"),
            tickfont=dict(size=10, color="#cbd5e0"),
            gridcolor="rgba(255, 255, 255, 0.1)",
            zeroline=True,
            zerolinecolor="rgba(255, 255, 255, 0.3)",
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=10, color="#cbd5e0"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=80, r=40, t=50, b=40),
        font=dict(family="Inter"),
        hoverlabel=dict(
            bgcolor="rgba(45, 55, 72, 0.95)",
            bordercolor="rgba(255, 255, 255, 0.2)",
            font=dict(color="#ffffff", family="Inter"),
        ),
        hovermode="y unified",
    )
    return fig

def create_rebased_chart(rebased_data: pd.DataFrame, title: str = "Rebased Performance") -> go.Figure:
    """Create rebased performance chart"""
    # Use consistent color scheme with ISM charts - darker, more saturated colors
    colors = [
        "#3b82f6",  # Blue-500 (darker blue)
        "#eab308",  # Yellow-500 (darker yellow)
        "#22c55e",  # Green-500 (same as YoY bars)
        "#ef4444",  # Red-500
        "#8b5cf6",  # Violet-500
        "#f97316",  # Orange-500
        "#06b6d4",  # Cyan-500
        "#84cc16",  # Lime-500
        "#ec4899",  # Pink-500
        "#6366f1",  # Indigo-500
        "#14b8a6",  # Teal-500
        "#ca8a04",  # Yellow-600 (darker)
        "#dc2626",  # Red-600
        "#7c3aed",  # Violet-600
        "#d97706",  # Orange-600
    ]

    fig = go.Figure()
    for i, column in enumerate(rebased_data.columns):

        d = rebased_data[column].dropna()

        # Get the latest value for the legend - convert to percentage change from base 100
        latest_value = d.iloc[-1] if len(d) > 0 else 100
        legend_name = f"{column} ({latest_value:+.2%}%)"

        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d.values,
                mode="lines",
                name=legend_name,
                line=dict(width=2, color=colors[i % len(colors)]),
                hovertemplate=f"{column}: %{{y:.2%}}<extra></extra>",
            )
        )

    fig.update_layout(
        height=500,
        title=dict(
            text="Performance", x=0.5, font=dict(size=16, color="#ffffff", family="Inter")
        ),
        xaxis=dict(
            title="Date",
            title_font=dict(size=12, color="#a0aec0"),
            tickfont=dict(size=10, color="#cbd5e0"),
            gridcolor="rgba(255, 255, 255, 0.1)",
        ),
        yaxis=dict(
            title="Rebased Value (Base = 100)",
            title_font=dict(size=12, color="#a0aec0"),
            tickfont=dict(size=10, color="#cbd5e0"),
            gridcolor="rgba(255, 255, 255, 0.1)",
            range=[0, None],  # Start y-axis from 0
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",
            y=1.05,  # Position above the chart
            xanchor="center",
            x=0.5,  # Center the legend
            bgcolor="rgba(255, 255, 255, 0.05)",
            font=dict(size=9, color="#cbd5e0"),
        ),
        margin=dict(l=60, r=60, t=80, b=40),  # Increased top margin for legend
        font=dict(family="Inter"),
        hovermode="x unified",  # Unified hover mode
        hoverlabel=dict(
            bgcolor="rgba(45, 55, 72, 0.95)",
            bordercolor="rgba(255, 255, 255, 0.2)",
            font=dict(color="#ffffff", family="Inter"),
        ),
    )
    return fig


def create_universe_section(universe_name: str, icon: str):
    """Create a section for each universe"""
    try:
        from ix.db import Universe

        universe = Universe.from_name(universe_name)

        # Get performance data
        perf_5d = universe.get_pct_change(5).iloc[-1].sort_values(ascending=True)
        perf_21d = universe.get_pct_change(21).iloc[-1].sort_values(ascending=True)

        # Get rebased data (try 2025, fallback to last 252 days)
        try:
            rebased_data = (
                universe.get_series(field="PX_LAST").loc["2025"].ffill().pct_change().add(1).cumprod().sub(1)
            )
        except:
            rebased_data = universe.get_series(field="PX_LAST").tail(252).apply(Rebase)


        # Ensure rebased_data is a DataFrame
        if isinstance(rebased_data, pd.Series):
            rebased_data = rebased_data.to_frame()

        # Create charts
        rebased_chart = create_rebased_chart(rebased_data, f"{universe_name} - YTD Performance")
        chart_5d = create_performance_chart(perf_5d, "5-Day Performance", 350)
        chart_21d = create_performance_chart(perf_21d, "21-Day Performance", 350)

        return html.Div(
            [
                html.H3(f"{icon} {universe_name}", className="universe-title"),
                # Large rebased chart first
                html.Div(
                    [dcc.Graph(figure=rebased_chart, className="large-chart")],
                    className="chart-container",
                ),
                # Smaller performance charts side by side
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        dcc.Graph(
                                            figure=chart_5d, className="small-chart"
                                        )
                                    ],
                                    className="chart-container",
                                )
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        dcc.Graph(
                                            figure=chart_21d, className="small-chart"
                                        )
                                    ],
                                    className="chart-container",
                                )
                            ],
                            width=6,
                        ),
                    ]
                ),
            ],
            className="universe-section",
        )

    except Exception as e:
        return html.Div(
            [
                html.H3(f"{icon} {universe_name}", className="universe-title"),
                html.P(
                    f"Error loading data: {str(e)}",
                    style={"color": "#f56565", "text-align": "center"},
                ),
            ],
            className="universe-section",
        )


# Universe configurations
UNIVERSES = [
    ("Major Indices", "🌍"),
    ("Sectors", "🏢"),
    ("Themes", "🚀"),
    ("Global Markets", "🗺️"),
    ("Commodities", "💰"),
]
