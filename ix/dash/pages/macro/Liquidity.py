"""
Global Liquidity Analysis Section

This module contains the global liquidity analysis component for the macro dashboard.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, callback, Output, Input
import dash_mantine_components as dmc
from ix import Series, MonthEndOffset, M2, Cycle
from ix.misc.date import twentyyearsbefore, today
from ix.dash.pages.dashboard.MarketPerformance import CardwithHeader


def create_liquidity_cycle_chart(start_date=None, end_date=None):
    """Create global liquidity cycle chart"""
    from ix.dash.settings import Theme

    try:
        # Prepare date range
        if start_date:
            start = pd.Timestamp(f"{start_date}-01-01")
        else:
            start = twentyyearsbefore()

        if end_date:
            end = pd.Timestamp(f"{end_date}-12-31")
        else:
            end = today()

        # Prepare data
        global_liquidity = MonthEndOffset(M2("ME").WorldTotal.pct_change(12), months=6)
        cycle = Cycle(global_liquidity, 60)
        ism = Series("ISMPMI_M:PX_LAST", freq="ME")

        global_liquidity = global_liquidity.loc[start:end]
        cycle = cycle.loc[start:end]
        ism = ism.loc[start:end]

        # Get latest values for legend
        latest_liquidity = (
            global_liquidity.iloc[-1] if not global_liquidity.empty else None
        )
        latest_cycle = cycle.iloc[-1] if not cycle.empty else None
        latest_ism = ism.iloc[-1] if not ism.empty else None

        # Create figure
        fig = go.Figure()

        # Global Liquidity (6M Lead)
        fig.add_trace(
            go.Scatter(
                x=global_liquidity.index,
                y=global_liquidity.values,
                name=f"Global Liquidity YoY (6M Lead){f' ({latest_liquidity:.2%})' if latest_liquidity is not None else ''}",
                mode="lines",
                line=dict(color=Theme["colors"]["blue"][6], width=2),
                yaxis="y1",
                hovertemplate="Liquidity: %{y:.2%}<extra></extra>",
            )
        )

        # Cycle
        fig.add_trace(
            go.Scatter(
                x=cycle.index,
                y=cycle.values,
                name=f"Cycle{f' ({latest_cycle:.2%})' if latest_cycle is not None else ''}",
                mode="lines",
                line=dict(color=Theme["colors"]["yellow"][6], width=2, dash="dot"),
                yaxis="y1",
                hovertemplate="Cycle: %{y:.2%}<extra></extra>",
            )
        )

        # ISM
        fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name=f"ISM ({latest_ism:.2f})" if latest_ism is not None else "ISM",
                mode="lines",
                line=dict(color=Theme["colors"]["green"][6], width=2),
                yaxis="y2",
                hovertemplate="ISM: %{y:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            height=400,
            xaxis=dict(
                title="Date",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                gridcolor="rgba(255, 255, 255, 0.1)",
            ),
            yaxis=dict(
                title="Liquidity / Cycle",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                gridcolor="rgba(255, 255, 255, 0.1)",
                tickformat=".0%",
            ),
            yaxis2=dict(
                title="ISM",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                overlaying="y",
                side="right",
                showgrid=False,
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.02,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255, 255, 255, 0.05)",
                font=dict(
                    size=9, color=Theme["colors"]["gray"][3], family=Theme["fontFamily"]
                ),
            ),
            margin=dict(l=50, r=50, t=60, b=40),
            font=dict(family=Theme["fontFamily"]),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.95)",
                bordercolor="rgba(255, 255, 255, 0.2)",
                font=dict(color="#ffffff", family=Theme["fontFamily"]),
            ),
        )

        return fig

    except Exception as e:
        # Return error figure
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error loading liquidity data<br>Please try refreshing",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(
                size=14, color=Theme["colors"]["red"][6], family=Theme["fontFamily"]
            ),
        )
        error_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        return error_fig


def create_m2_contribution_chart(start_date=None, end_date=None):
    """Create M2 contribution chart"""
    from ix.dash.settings import Theme

    try:
        # Prepare date range
        if start_date:
            start = pd.Timestamp(f"{start_date}-01-01")
        else:
            start = twentyyearsbefore()

        if end_date:
            end = pd.Timestamp(f"{end_date}-12-31")
        else:
            end = today()

        m2 = M2("ME")

        fig = go.Figure()

        # Add total line
        total_data = m2.WorldTotal.pct_change(12).loc[start:end]
        fig.add_trace(
            go.Scatter(
                x=total_data.index,
                y=total_data.values,
                name="Total",
                mode="lines",
                line=dict(color=Theme["colors"]["blue"][6], width=3),
                hovertemplate="<b>%{fullData.name} : %{y:.2%}<extra></extra>",
            )
        )

        # Add contribution bars
        colors = [
            Theme["colors"][color][6]
            for color in ["green", "yellow", "red", "violet", "pink", "cyan", "orange"]
        ]
        for i, (name, series) in enumerate(m2.WorldContribution.items()):
            contribution_data = series.loc[start:end]
            fig.add_trace(
                go.Bar(
                    x=contribution_data.index,
                    y=contribution_data.values,
                    name=name,
                    marker_color=colors[i % len(colors)],
                    hovertemplate="<b>%{fullData.name} : %{y:.2%}<extra></extra>",
                )
            )

        fig.update_layout(
            barmode="relative",  # Stacked bar chart
            height=400,
            xaxis=dict(
                title="Date",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                gridcolor="rgba(255, 255, 255, 0.1)",
            ),
            yaxis=dict(
                title="Contribution (percentage points)",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                tickformat=".0%",
                gridcolor="rgba(255, 255, 255, 0.1)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.02,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255, 255, 255, 0.05)",
                font=dict(
                    size=9, color=Theme["colors"]["gray"][3], family=Theme["fontFamily"]
                ),
            ),
            margin=dict(l=50, r=50, t=60, b=40),
            font=dict(family=Theme["fontFamily"]),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.95)",
                bordercolor="rgba(255, 255, 255, 0.2)",
                font=dict(color="#ffffff", family=Theme["fontFamily"]),
            ),
        )

        return fig

    except Exception as e:
        # Return error figure
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error loading M2 data<br>Please try refreshing",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(
                size=14, color=Theme["colors"]["red"][6], family=Theme["fontFamily"]
            ),
        )
        error_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        return error_fig


def create_m2_country_chart(start_date=None, end_date=None):
    """Create M2 YoY change by country chart"""
    from ix.dash.settings import Theme
    from ix.db.query import M2

    try:
        # Prepare date range
        if start_date:
            start = pd.Timestamp(f"{start_date}-01-01")
        else:
            start = pd.Timestamp.today() - pd.DateOffset(years=20)

        if end_date:
            end = pd.Timestamp(f"{end_date}-12-31")
        else:
            end = today()

        # Get M2 World DataFrame (individual countries)
        m2 = M2()
        world_df = m2.World

        # Calculate YoY % change for each country
        world_yoy = world_df.pct_change(12).loc[start:end]

        fig = go.Figure()

        # Use Mantine theme colors
        colors = [
            Theme["colors"]["blue"][6],
            Theme["colors"]["orange"][6],
            Theme["colors"]["green"][6],
            Theme["colors"]["red"][6],
            Theme["colors"]["violet"][6],
            Theme["colors"]["yellow"][6],
            Theme["colors"]["pink"][6],
            Theme["colors"]["cyan"][6],
            Theme["colors"]["teal"][6],
            Theme["colors"]["lime"][6],
        ]

        # Add a line for each country
        for i, col in enumerate(world_yoy.columns):
            series = world_yoy[col].dropna()
            latest = series.iloc[-1] if not series.empty else None
            fig.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series.values,
                    name=f"{col} ({latest:.2%})" if latest is not None else col,
                    mode="lines",
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f"{col} YoY: " + "%{y:.2%}<extra></extra>",
                )
            )

        fig.update_layout(
            height=400,
            xaxis=dict(
                title="Date",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                gridcolor="rgba(255, 255, 255, 0.1)",
            ),
            yaxis=dict(
                title="YoY Change",
                title_font=dict(
                    size=12,
                    color=Theme["colors"]["gray"][5],
                    family=Theme["fontFamily"],
                ),
                tickfont=dict(size=10, color=Theme["colors"]["gray"][3]),
                tickformat=".1%",
                gridcolor="rgba(255, 255, 255, 0.1)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.02,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255, 255, 255, 0.05)",
                font=dict(
                    size=9, color=Theme["colors"]["gray"][3], family=Theme["fontFamily"]
                ),
            ),
            margin=dict(l=50, r=50, t=60, b=40),
            font=dict(family=Theme["fontFamily"]),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=f"rgba({int(Theme['colors']['dark'][7][1:3], 16)}, {int(Theme['colors']['dark'][7][3:5], 16)}, {int(Theme['colors']['dark'][7][5:7], 16)}, 0.95)",
                bordercolor="rgba(255, 255, 255, 0.2)",
                font=dict(color="#ffffff", family=Theme["fontFamily"]),
            ),
        )

        return fig

    except Exception as e:
        # Return error figure
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error loading M2 country data<br>Please try refreshing",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(
                size=14, color=Theme["colors"]["red"][6], family=Theme["fontFamily"]
            ),
        )
        error_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        return error_fig


def Section():
    """Create liquidity analysis section"""
    try:
        from ix.dash.components import ChartGrid

        # Create container for dynamic charts
        charts_container = html.Div(id="liquidity-charts-container")

        return dmc.Container(
            [
                # Header section with Mantine styling
                dmc.Stack(
                    [
                        dmc.Title(
                            "🌊 Global Liquidity Analysis",
                            order=2,
                            ta="center",
                            c="gray",
                            fw="bold",
                            mb="xs",
                            style={"color": "#ffffff"},
                        ),
                        dmc.Text(
                            "Global M2 Liquidity Cycle & Country Contributions",
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
                    title="Error Loading Liquidity Data",
                    children=[
                        dmc.Text(
                            f"Unable to load liquidity analysis: {str(e)}", size="sm"
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


# Liquidity Charts callback - returns complete chart components
@callback(
    Output("liquidity-charts-container", "children"),
    [Input("macro-start-date", "value"), Input("macro-end-date", "value")],
    prevent_initial_call=False,
)
def update_liquidity_charts(start_year, end_year):
    """Generate and return complete liquidity charts with data"""
    from ix.dash.settings import Theme

    charts = []

    try:
        # Chart 1: Liquidity Cycle
        liquidity_fig = create_liquidity_cycle_chart(start_year, end_year)
        liquidity_chart = CardwithHeader(
            "Global M2 Liquidity Cycle",
            dcc.Graph(
                figure=liquidity_fig,
                config={"displayModeBar": False},
                style={"height": "400px"},
            ),
        )
        charts.append(liquidity_chart)

        # Chart 2: M2 Contributions
        m2_fig = create_m2_contribution_chart(start_year, end_year)
        m2_chart = CardwithHeader(
            "M2 Country Contributions",
            dcc.Graph(
                figure=m2_fig,
                config={"displayModeBar": False},
                style={"height": "400px"},
            ),
        )
        charts.append(m2_chart)

        # Chart 3: M2 by Country
        m2_country_fig = create_m2_country_chart(start_year, end_year)
        m2_country_chart = CardwithHeader(
            "M2 YoY by Country",
            dcc.Graph(
                figure=m2_country_fig,
                config={"displayModeBar": False},
                style={"height": "400px"},
            ),
        )
        charts.append(m2_country_chart)

    except Exception as e:
        print(f"Error creating liquidity charts: {e}")
        # Create error chart
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error loading liquidity data<br>Please try refreshing",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(
                size=14, color=Theme["colors"]["red"][6], family=Theme["fontFamily"]
            ),
        )
        error_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
        )

        error_component = CardwithHeader(
            "Liquidity Analysis",
            dcc.Graph(
                figure=error_fig,
                config={"displayModeBar": False},
                style={"height": "400px"},
            ),
        )
        charts.append(error_component)

    # Return charts wrapped in ChartGrid
    try:
        from ix.dash.components import ChartGrid

        return ChartGrid(charts)
    except ImportError:
        # Fallback to simple div if ChartGrid not available
        return html.Div(charts)
