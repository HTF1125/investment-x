"""
ISM Business Cycle Analysis Section

This module contains the ISM (Institute for Supply Management) business cycle
analysis component for the dashboard.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, callback, Output, Input
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from ix.misc.date import today
from ix.dash.settings import theme


def ism_cycle_chart(px: pd.Series, color_index=0):
    """Create ISM cycle chart with asset performance"""
    from ix import Series, Cycle
    import numpy as np

    # Use theme colors for ISM charts
    theme_colors = [
        theme["colors"]["blue"][6],  # Blue
        theme["colors"]["green"][6],  # Green
        theme["colors"]["red"][6],  # Red
        theme["colors"]["violet"][6],  # Violet
        theme["colors"]["orange"][6],  # Orange
        theme["colors"]["cyan"][6],  # Cyan
        theme["colors"]["pink"][6],  # Pink
        theme["colors"]["lime"][6],  # Lime
    ]

    asset_color = theme_colors[color_index % len(theme_colors)]


    # Get ISM data directly
    ism = Series("ISMPMI_M:PX_LAST")
    cycle = Cycle(ism, 48)


    # Prepare performance YoY (keep as decimal for proper percentage display)
    performance_yoy = px.resample("W-Fri").last().ffill().pct_change(52).dropna()

    # Get latest values for legend
    latest_ism = ism.iloc[-1] if not ism.empty else None
    latest_cycle = cycle.iloc[-1] if not cycle.empty else None
    latest_performance = performance_yoy.iloc[-1] if not performance_yoy.empty else None

    # Create figure
    fig = go.Figure()

    # ISM PMI
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM PMI ({latest_ism:.2f})" if latest_ism is not None else "ISM PMI",
            mode="lines",
            line=dict(color=theme["colors"]["blue"][6], width=2.5),  # theme blue
            yaxis="y1",
            hovertemplate="ISM PMI: %{y:.2f}<extra></extra>",
        )
    )

    # ISM Cycle
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name="Cycle",
            mode="lines",
            line=dict(
                color=theme["colors"]["yellow"][6], width=2.5, dash="dot"
            ),  # theme yellow
            yaxis="y1",
            hovertemplate="ISM Cycle 48M: %{y:.2f}<extra></extra>",
        )
    )

    # Asset YoY %
    performance_name = f"{px.name} YoY"
    if latest_performance is not None:
        performance_name += f" ({latest_performance:.1%})"

    fig.add_trace(
        go.Bar(
            x=performance_yoy.index,
            y=performance_yoy,
            name=performance_name,
            marker=dict(color=asset_color),
            opacity=0.6,
            yaxis="y2",
            hovertemplate=f"{px.name} YoY: %{{y:.1%}}<extra></extra>",
        )
    )

    # Modern chart layout with custom styling
    fig.update_layout(
        xaxis=dict(
            title="Date",
            title_font=dict(
                size=13,
                color=theme["colors"]["gray"][3],
                family=theme["fontFamily"],
            ),
            tickfont=dict(size=11, color=theme["colors"]["gray"][3]),
            gridcolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.3)",
            gridwidth=1,
            showline=True,
            linecolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.3)",
        ),
        yaxis=dict(
            title="ISM / Cycle",
            title_font=dict(
                size=13,
                color=theme["colors"]["gray"][3],
                family=theme["fontFamily"],
            ),
            tickfont=dict(size=11, color=theme["colors"]["gray"][3]),
            gridcolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.3)",
            gridwidth=1,
            showline=True,
            linecolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.3)",
        ),
        yaxis2=dict(
            title="YoY Return",
            title_font=dict(
                size=13,
                color=theme["colors"]["gray"][3],
                family=theme["fontFamily"],
            ),
            tickfont=dict(size=11, color=theme["colors"]["gray"][3]),
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=".1%",
            showline=True,
            linecolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.3)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=f"rgba({int(theme['colors']['dark'][7][1:3], 16)}, {int(theme['colors']['dark'][7][3:5], 16)}, {int(theme['colors']['dark'][7][5:7], 16)}, 0.4)",  # theme dark background
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor=f"rgba({int(theme['colors']['dark'][7][1:3], 16)}, {int(theme['colors']['dark'][7][3:5], 16)}, {int(theme['colors']['dark'][7][5:7], 16)}, 0.8)",
            bordercolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.3)",
            borderwidth=1,
            font=dict(
                size=10,
                color=theme["colors"]["gray"][3],
                family=theme["fontFamily"],
            ),
        ),
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family=theme["fontFamily"]),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=f"rgba({int(theme['colors']['dark'][7][1:3], 16)}, {int(theme['colors']['dark'][7][3:5], 16)}, {int(theme['colors']['dark'][7][5:7], 16)}, 0.95)",
            bordercolor=f"rgba({int(theme['colors']['gray'][5][1:3], 16)}, {int(theme['colors']['gray'][5][3:5], 16)}, {int(theme['colors']['gray'][5][5:7], 16)}, 0.8)",
            font=dict(
                color=theme["colors"]["gray"][2],
                family=theme["fontFamily"],
                size=12,
            ),
        ),
    )

    return fig


from ix.dash.pages.dashboard.MarketPerformance import CardwithHeader


def Section():
    """Create ISM cycle analysis section using ChartGrid"""
    try:
        from ix.dash.components import ChartGrid

        # Create container for dynamic charts
        charts_container = html.Div(id="ism-charts-container")

        return dmc.Container(
            [
                # Header section with Mantine styling
                dmc.Stack(
                    [
                        dmc.Title(
                            "📊 ISM Cycle Analysis",
                            order=2,
                            ta="center",
                            c="gray",
                            fw="bold",
                            mb="xs",
                            style={"color": "#ffffff"},
                        ),
                        dmc.Text(
                            "ISM Manufacturing PMI vs Asset Performance Analysis",
                            c="gray",
                            ta="center",
                            size="sm",
                            mb="lg",
                            style={"color": "#a0aec0"},
                        ),
                    ],
                    gap="xs",
                ),
                # Dynamic charts container
                charts_container,
            ],
            fluid=True,
            p="lg",
            style={
                "background": "rgba(26, 32, 44, 0.8)",
                "border-radius": "16px",
                "border": "1px solid rgba(255, 255, 255, 0.1)",
                "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
            },
        )
    except Exception as e:
        return dmc.Container(
            [
                dmc.Alert(
                    title="Error Loading ISM Data",
                    children=[
                        dmc.Text(
                            f"Unable to load ISM cycle analysis: {str(e)}", size="sm"
                        ),
                        dmc.Text(
                            "Please try refreshing the page or contact support if the issue persists.",
                            size="xs",
                            c="gray",
                            mt="xs",
                            style={"color": "#a0aec0"},
                        ),
                    ],
                    color="red",
                    variant="filled",
                    radius="md",
                    icon=True,
                ),
            ],
            p="lg",
        )
