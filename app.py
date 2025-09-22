import pandas as pd
from ix import MultiSeries, Rebase
import plotly.graph_objects as go
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Global Markets Dashboard"

# Import Universe class
from ix.db import Universe
# Simple CSS styling


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
            text=[f"{v:+.2f}%" for v in data.values],
            textposition="auto",
            textfont=dict(size=10, color="white", family="Inter"),
            marker=dict(color=colors, opacity=0.8),
            hovertemplate="<b>%{y}</b><br>Performance: %{x:.2f}%<extra></extra>",
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
    )
    return fig


def create_rebased_chart(rebased_data: pd.DataFrame, title: str) -> go.Figure:
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

        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d.values,
                mode="lines",
                name=column,
                line=dict(width=2, color=colors[i % len(colors)]),
                hovertemplate=f"{column}: %{{y:.2f}}<extra></extra>",
            )
        )

    fig.update_layout(
        height=500,
        title=dict(
            text=title, x=0.5, font=dict(size=18, color="#ffffff", family="Inter")
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
    )
    return fig


def create_universe_section(universe_name: str, icon: str):
    """Create a section for each universe"""
    try:
        universe = Universe.from_name(universe_name)

        # Get performance data
        perf_5d = universe.get_pct_change(5).iloc[-1].sort_values(ascending=True)
        perf_21d = universe.get_pct_change(21).iloc[-1].sort_values(ascending=True)

        # Get rebased data (try 2025, fallback to last 252 days)
        try:
            rebased_data = (
                universe.get_series(field="PX_LAST").loc["2025"].apply(Rebase)
            )
            rebased_title = f"{icon} {universe_name} - 2025 Rebased Performance"
        except:
            rebased_data = universe.get_series(field="PX_LAST").tail(252).apply(Rebase)
            rebased_title = (
                f"{icon} {universe_name} - Last 252 Days Rebased Performance"
            )

        # Create charts
        rebased_chart = create_rebased_chart(rebased_data, rebased_title)
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
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        yaxis=dict(title="ISM / Cycle", color="white", gridcolor="#334155"),
        yaxis2=dict(
            title="YoY Return",
            color="white",
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=".1%",
        ),
        legend=dict(
            orientation="h",
            y=1.05,
            x=0.5,
            xanchor="center",
            yanchor="top",
            font=dict(color="white", size=10),
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        margin=dict(l=40, r=40, t=60, b=60),
        height=500,
        hovermode="x unified",
    )

    return fig


def create_ism_section():
    """Create ISM cycle analysis section with all 6 charts"""
    try:
        from ix import Series, Cycle

        # Define all the assets to analyze
        assets = [
            ("SPX Index:PX_LAST", "S&P 500"),
            ("TRYUS10Y:PX_YTM", "US Treasury 10Y"),
            ("CL1 Comdty:PX_LAST", "Crude Oil"),
            ("XBTUSD Curncy:PX_LAST", "Bitcoin"),
            ("DXY Index:PX_LAST", "Dollar"),
        ]

        # Create charts for each asset
        charts = []
        for code, name in assets:
            try:
                asset_data = Series(code, name=name)
                chart = ism_cycle_chart(asset_data)
                charts.append(
                    dbc.Col(
                        [
                            html.Div(
                                [dcc.Graph(figure=chart, className="small-chart")],
                                className="chart-container",
                            )
                        ],
                        width=6,
                        style={"margin-bottom": "20px"},
                    )
                )
            except Exception as e:
                print(f"Error creating chart for {name}: {e}")
                continue

        # Add Gold/Copper ratio chart
        try:
            GoldCopperRatio = Series("HG1 Comdty:PX_LAST") / Series(
                "GC1 Comdty:PX_LAST"
            )
            GoldCopperRatio.name = "Gold/Copper"
            chart = ism_cycle_chart(GoldCopperRatio)
            charts.append(
                dbc.Col(
                    [
                        html.Div(
                            [dcc.Graph(figure=chart, className="small-chart")],
                            className="chart-container",
                        )
                    ],
                    width=6,
                    style={"margin-bottom": "20px"},
                )
            )
        except Exception as e:
            print(f"Error creating Gold/Copper chart: {e}")

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
                dbc.Row(charts),
            ],
            className="universe-section",
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


# App layout
app.layout = dbc.Container(
    [
        # Header
        html.H1("📈 Global Markets Dashboard", className="main-title"),
        html.P(
            "Real-time performance analysis across all asset universes",
            className="subtitle",
        ),
        # ISM Cycle Analysis section
        create_ism_section(),
        # Universe sections
        html.Div(
            [
                create_universe_section(universe_name, icon)
                for universe_name, icon in UNIVERSES
            ]
        ),
        # Footer
        html.Div(
            [
                html.Hr(
                    style={
                        "border-color": "rgba(255, 255, 255, 0.2)",
                        "margin": "40px 0",
                    }
                ),
                html.P(
                    "📈 Global Markets Dashboard | Powered by Dash & Plotly",
                    style={
                        "text-align": "center",
                        "color": "#718096",
                        "margin": "20px 0",
                    },
                ),
            ]
        ),
    ],
    fluid=True,
)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
