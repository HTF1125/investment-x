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
from ix.dash.settings import Theme


def ism_cycle_chart(px: pd.Series, color_index=0, start_date=None, end_date=None):
    """Create ISM cycle chart with asset performance"""
    from ix import Series, Cycle
    import numpy as np

    # Use theme colors for ISM charts
    theme_colors = [
        Theme["colors"]["blue"][6],  # Blue
        Theme["colors"]["green"][6],  # Green
        Theme["colors"]["red"][6],  # Red
        Theme["colors"]["violet"][6],  # Violet
        Theme["colors"]["orange"][6],  # Orange
        Theme["colors"]["cyan"][6],  # Cyan
        Theme["colors"]["pink"][6],  # Pink
        Theme["colors"]["lime"][6],  # Lime
    ]

    asset_color = theme_colors[color_index % len(theme_colors)]

    # Prepare date range
    if start_date:
        start_date = pd.Timestamp(f"{start_date}-01-01")
    else:
        start_date = pd.Timestamp.today() - pd.DateOffset(years=20)

    if end_date:
        end_date = pd.Timestamp(f"{end_date}-12-31")
    else:
        end_date = pd.Timestamp.today()

    # Get ISM data directly
    ism = Series("ISMPMI_M:PX_LAST")
    cycle = Cycle(ism, 48)
    ism = ism.loc[start_date:end_date]
    cycle = cycle.loc[start_date:end_date]

    # Prepare performance YoY (keep as decimal for proper percentage display)
    performance_yoy = px.resample("W-Fri").last().ffill().pct_change(52)
    performance_yoy = performance_yoy[
        (performance_yoy.index >= start_date) & (performance_yoy.index <= end_date)
    ]

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
            line=dict(color=Theme["colors"]["blue"][6], width=2.5),  # Theme blue
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
            line=dict(
                color=Theme["colors"]["yellow"][6], width=2.5, dash="dot"
            ),  # Theme yellow
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
        height=400,
        xaxis=dict(
            title="Date",
            title_font=dict(
                size=13,
                color=Theme["colors"]["gray"][3],
                family=Theme["fontFamily"],
            ),
            tickfont=dict(size=11, color=Theme["colors"]["gray"][3]),
            gridcolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.3)",
            gridwidth=1,
            showline=True,
            linecolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.3)",
        ),
        yaxis=dict(
            title="ISM / Cycle",
            title_font=dict(
                size=13,
                color=Theme["colors"]["gray"][3],
                family=Theme["fontFamily"],
            ),
            tickfont=dict(size=11, color=Theme["colors"]["gray"][3]),
            gridcolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.3)",
            gridwidth=1,
            showline=True,
            linecolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.3)",
        ),
        yaxis2=dict(
            title="YoY Return",
            title_font=dict(
                size=13,
                color=Theme["colors"]["gray"][3],
                family=Theme["fontFamily"],
            ),
            tickfont=dict(size=11, color=Theme["colors"]["gray"][3]),
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=".1%",
            showline=True,
            linecolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.3)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.4)",  # Theme dark background
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.8)",
            bordercolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.3)",
            borderwidth=1,
            font=dict(
                size=10,
                color=Theme["colors"]["gray"][3],
                family=Theme["fontFamily"],
            ),
        ),
        margin=dict(l=60, r=60, t=70, b=50),
        font=dict(family=Theme["fontFamily"]),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.95)",
            bordercolor=f"rgba({int(Theme['colors']['gray'][5][1:3], 16)}, {int(Theme['colors']['gray'][5][3:5], 16)}, {int(Theme['colors']['gray'][5][5:7], 16)}, 0.8)",
            font=dict(
                color=Theme["colors"]["gray"][2],
                family=Theme["fontFamily"],
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


# ISM Charts callback - returns complete chart components
@callback(
    Output("ism-charts-container", "children"),
    [Input("macro-start-date", "value"), Input("macro-end-date", "value")],
    prevent_initial_call=False,
)
def update_ism_charts(start_year, end_year):
    """Generate and return complete ISM charts with data"""
    from ix import Series

    # Define assets to analyze
    assets = {
        "S&P500": Series("SPX Index:PX_LAST"),
        "US Treasury 10Y": Series("TRYUS10Y:PX_YTM"),
        "Crude Oil": Series("CL1 Comdty:PX_LAST"),
        "Bitcoin": Series("XBTUSD Curncy:PX_LAST"),
        "Dollar": Series("DXY Index:PX_LAST"),
        "Gold/Copper": Series("HG1 Comdty:PX_LAST") / Series("GC1 Comdty:PX_LAST"),
    }

    charts = []
    for i, (name, data) in enumerate(assets.items()):
        try:
            # Generate the figure
            fig = ism_cycle_chart(
                data, color_index=i, start_date=start_year, end_date=end_year
            )

            # Create the complete chart component
            chart_component = CardwithHeader(
                name,
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"height": "400px"},
                ),
            )

            charts.append(chart_component)

        except Exception as e:
            print(f"Error creating chart for {name}: {e}")
            # Create error chart
            error_fig = go.Figure()
            error_fig.add_annotation(
                text=f"Error loading {name} data<br>Please try refreshing",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(
                    size=15,
                    color=Theme["colors"]["red"][6],
                    family=Theme["fontFamily"],
                ),
            )
            error_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.4)",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                margin=dict(l=0, r=0, t=0, b=0),
            )

            error_component = dcc.Graph(
                figure=error_fig,
                config={"displayModeBar": False},
                style={"height": "400px"},
            )
            charts.append(error_component)

    # Return charts wrapped in ChartGrid
    try:
        from ix.dash.components import ChartGrid

        return ChartGrid(charts)
    except ImportError:
        # Fallback to simple div if ChartGrid not available
        return html.Div(charts)
