"""
ISM Cycle Analysis Module

This module contains functions for creating ISM (Institute for Supply Management)
cycle analysis charts and sections for the dashboard.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc


def ism_cycle_chart(px: pd.Series):
    """Create ISM cycle chart with asset performance"""
    from ix import Series, Cycle
    import numpy as np

    # Prepare ISM and Cycle data
    twenty_years_ago = pd.Timestamp.today() - pd.DateOffset(years=20)

    # Get ISM data directly
    ism = Series("ISMPMI_M:PX_LAST").loc[twenty_years_ago:]

    # Create cycle from ISM data
    try:
        cycle = Cycle(ism, 60)
    except Exception:
        # If cycle fails, create a simple moving average as fallback
        cycle = ism.rolling(window=12).mean()

    # Prepare performance YoY (keep as decimal for proper percentage display)
    performance_yoy = px.resample("W-Fri").last().ffill().pct_change(52)

    performance_yoy = performance_yoy[performance_yoy.index >= twenty_years_ago]

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
            line=dict(color="#60a5fa", width=2),
            yaxis="y1",
            hovertemplate="ISM PMI: %{y:.2f}<extra></extra>",
        )
    )

    # ISM Cycle
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name=(
                f"ISM Cycle 48M ({latest_cycle:.2f})"
                if latest_cycle is not None
                else "ISM Cycle 48M"
            ),
            mode="lines",
            line=dict(color="#fbbf24", width=2, dash="dot"),
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
            marker=dict(color="#22c55e"),
            opacity=0.6,
            yaxis="y2",
            hovertemplate=f"{px.name} YoY: %{{y:.1%}}<extra></extra>",
        )
    )

    # Layout with dual y-axis
    fig.update_layout(
        height=500,
        xaxis=dict(
            title="Date",
            title_font=dict(size=12, color="#a0aec0"),
            tickfont=dict(size=10, color="#cbd5e0"),
            gridcolor="rgba(255, 255, 255, 0.1)",
        ),
        yaxis=dict(
            title="ISM / Cycle",
            title_font=dict(size=12, color="#a0aec0"),
            tickfont=dict(size=10, color="#cbd5e0"),
            gridcolor="rgba(255, 255, 255, 0.1)",
        ),
        yaxis2=dict(
            title="YoY Return",
            title_font=dict(size=12, color="#a0aec0"),
            tickfont=dict(size=10, color="#cbd5e0"),
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=".1%",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.05,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.05)",
            font=dict(size=9, color="#cbd5e0"),
        ),
        margin=dict(l=60, r=60, t=80, b=40),
        font=dict(family="Inter"),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(45, 55, 72, 0.95)",
            bordercolor="rgba(255, 255, 255, 0.2)",
            font=dict(color="#ffffff", family="Inter"),
        ),
    )

    return fig


def create_ism_section():
    """Create ISM cycle analysis section with all 6 charts"""
    try:
        from ix import Series

        pxs = pd.DataFrame(
            {
                "S&P500": Series("SPX Index:PX_LAST"),
                "US Treasury 10Y": Series("TRYUS10Y:PX_YTM"),
                "Crude Oil": Series("CL1 Comdty:PX_LAST"),
                "Bitcoin": Series("XBTUSD Curncy:PX_LAST"),
                "Dollar": Series("DXY Index:PX_LAST"),
                "Gold/Copper": Series("HG1 Comdty:PX_LAST")
                / Series("GC1 Comdty:PX_LAST"),
            }
        )

        # Create charts for each asset
        charts = []
        for name in pxs:
            try:
                asset_data = pxs[name]
                chart = ism_cycle_chart(asset_data)
                charts.append(
                    dbc.Col(
                        [
                            html.Div(
                                [dcc.Graph(figure=chart, className="small-chart")],
                                className="chart-container",
                            )
                        ],
                        xs=12,  # Full width on extra small screens
                        sm=12,  # Full width on small screens
                        md=6,  # Half width on medium screens
                        lg=4,  # Third width on large screens
                        xl=4,  # Third width on extra large screens
                        style={"margin-bottom": "20px"},
                    )
                )
            except Exception as e:
                print(f"Error creating chart for {name}: {e}")
                continue

        return html.Div(
            [
                html.H3("📊 ISM Cycle Analysis", className="universe-title"),
                html.P(
                    "ISM Manufacturing PMI vs Asset Performance Analysis",
                    style={
                        "color": "#a0aec0",
                        "text-align": "center",
                        "margin-bottom": "30px",
                    },
                ),
                dbc.Row(charts, className="g-3"),  # Add gap between columns
            ],
            className="universe-section",
            style={"width": "100%"},  # Ensure full width
        )
    except Exception as e:
        return html.Div(
            [
                html.H3("📊 ISM Cycle Analysis", className="universe-title"),
                html.P(
                    f"Error loading ISM data: {str(e)}",
                    style={"color": "#f56565", "text-align": "center"},
                ),
            ],
            className="universe-section",
        )
