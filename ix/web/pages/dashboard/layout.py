"""
Simple Dashboard Layout - Rewritten from scratch for reliability.
"""

from dash import html, dcc
import dash
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from ix.web.pages.dashboard.data_manager import DataManager
from ix.web.pages.dashboard.visualizations import HeatmapGenerator
from ix.misc import get_logger
from ix.misc.date import last_business_day

logger = get_logger(__name__)


# Get last business day default
def get_last_business_day():
    """Get the last business day (Monday-Friday)."""
    # For now, default to October 13, 2025
    return datetime(2025, 10, 13)


# Register this page as the home page
dash.register_page(
    __name__,
    path="/",
    title="Dashboard",
    name="Dashboard",
    order=0,
)


def create_performance_chart(universe_name: str, as_of_date: str = None):
    """Create a compact performance table for a universe."""
    try:
        logger.info(f"Creating performance table for {universe_name}")

        # Load data directly
        universe_data = DataManager.load_universe_data_optimized(
            universe_name, as_of_date
        )

        if not universe_data.get("data_available", False):
            return html.Div(
                f"No data available for {universe_name}",
                style={
                    "padding": "1rem",
                    "textAlign": "center",
                    "color": "#ef4444",
                    "backgroundColor": "rgba(30, 41, 59, 0.5)",
                    "borderRadius": "6px",
                    "fontSize": "0.85rem",
                },
            )

        # Get the data
        latest_values = universe_data.get("latest_values", {})
        performance_matrix = universe_data.get("performance_matrix", {})

        if not latest_values or not performance_matrix:
            return html.Div(
                f"Insufficient data for {universe_name}",
                style={
                    "padding": "1rem",
                    "textAlign": "center",
                    "color": "#ef4444",
                    "backgroundColor": "rgba(30, 41, 59, 0.5)",
                    "borderRadius": "6px",
                    "fontSize": "0.85rem",
                },
            )

        # Keep assets in original order
        assets = list(latest_values.keys())
        periods = sorted(
            [k for k in performance_matrix.keys()],
            key=lambda x: int(x.replace("D", "")),
        )

        # Create table header
        header_row = html.Tr(
            [
                html.Th(
                    "Asset",
                    style={
                        "padding": "0.4rem 0.5rem",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "color": "#94a3b8",
                        "textAlign": "left",
                        "borderBottom": "1px solid rgba(148, 163, 184, 0.2)",
                        "position": "sticky",
                        "top": "0",
                        "backgroundColor": "rgba(15, 23, 42, 0.95)",
                        "zIndex": "1",
                    },
                ),
                html.Th(
                    "Latest",
                    style={
                        "padding": "0.4rem 0.5rem",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "color": "#94a3b8",
                        "textAlign": "right",
                        "borderBottom": "1px solid rgba(148, 163, 184, 0.2)",
                        "position": "sticky",
                        "top": "0",
                        "backgroundColor": "rgba(15, 23, 42, 0.95)",
                        "zIndex": "1",
                    },
                ),
            ]
            + [
                html.Th(
                    period,
                    style={
                        "padding": "0.4rem 0.5rem",
                        "fontSize": "0.75rem",
                        "fontWeight": "600",
                        "color": "#94a3b8",
                        "textAlign": "right",
                        "borderBottom": "1px solid rgba(148, 163, 184, 0.2)",
                        "position": "sticky",
                        "top": "0",
                        "backgroundColor": "rgba(15, 23, 42, 0.95)",
                        "zIndex": "1",
                    },
                )
                for period in periods
            ]
        )

        # Create table rows
        table_rows = []
        for asset in assets:
            latest = latest_values.get(asset, 0)

            cells = [
                html.Td(
                    asset,
                    style={
                        "padding": "0.4rem 0.5rem",
                        "fontSize": "0.75rem",
                        "color": "#f1f5f9",
                        "fontWeight": "500",
                        "borderBottom": "1px solid rgba(148, 163, 184, 0.1)",
                    },
                ),
                html.Td(
                    f"{latest:.2f}",
                    style={
                        "padding": "0.4rem 0.5rem",
                        "fontSize": "0.75rem",
                        "color": "#cbd5e1",
                        "textAlign": "right",
                        "fontFamily": "monospace",
                        "borderBottom": "1px solid rgba(148, 163, 184, 0.1)",
                    },
                ),
            ]

            # Add performance cells with color coding
            for period in periods:
                perf = performance_matrix[period].get(asset, 0) * 100

                # Show "-" for zero performance, otherwise show percentage
                if perf == 0:
                    perf_text = "-"
                    color = "#94a3b8"
                else:
                    perf_text = f"{perf:+.2f}%"
                    color = "#10b981" if perf > 0 else "#ef4444"

                cells.append(
                    html.Td(
                        perf_text,
                        style={
                            "padding": "0.4rem 0.5rem",
                            "fontSize": "0.75rem",
                            "color": color,
                            "textAlign": "right",
                            "fontWeight": "600",
                            "fontFamily": "monospace",
                            "borderBottom": "1px solid rgba(148, 163, 184, 0.1)",
                        },
                    )
                )

            table_rows.append(html.Tr(cells))

        # Create the table
        return html.Div(
            [
                html.H3(
                    universe_name,
                    style={
                        "color": "#f1f5f9",
                        "fontSize": "0.9rem",
                        "fontWeight": "600",
                        "margin": "0 0 0.5rem 0",
                        "textAlign": "center",
                    },
                ),
                html.Div(
                    html.Table(
                        [
                            html.Thead(header_row),
                            html.Tbody(table_rows),
                        ],
                        style={
                            "width": "100%",
                            "borderCollapse": "collapse",
                        },
                    ),
                    style={
                        "maxHeight": "400px",
                        "overflowY": "auto",
                        "overflowX": "auto",
                        "borderRadius": "4px",
                        "border": "1px solid rgba(148, 163, 184, 0.2)",
                    },
                ),
            ],
            style={"width": "100%"},
        )

    except Exception as e:
        logger.error(f"Error creating performance table for {universe_name}: {e}")
        return html.Div(
            f"Error loading {universe_name}: {str(e)}",
            style={
                "padding": "1rem",
                "textAlign": "center",
                "color": "#ef4444",
                "backgroundColor": "rgba(30, 41, 59, 0.5)",
                "borderRadius": "6px",
                "fontSize": "0.85rem",
            },
        )


def create_summary_cards():
    """Create summary statistics cards."""
    try:
        # Load all data
        dashboard_data = DataManager.refresh_global_dashboard_data()

        total_markets = 0
        gainers = 0
        losers = 0
        changes = []

        for universe_name, universe_data in dashboard_data.items():
            if universe_data.get("data_available", False):
                perf_matrix = universe_data.get("performance_matrix", {})
                if "1D" in perf_matrix:
                    day_changes = perf_matrix["1D"]
                    total_markets += len(day_changes)
                    for change in day_changes.values():
                        if change > 0:
                            gainers += 1
                        elif change < 0:
                            losers += 1
                        changes.append(change)

        avg_change = sum(changes) / len(changes) if changes else 0

        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            "Total Markets",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "0.65rem",
                                "margin": "0 0 0.2rem 0",
                                "textTransform": "uppercase",
                                "letterSpacing": "0.05em",
                            },
                        ),
                        html.Div(
                            str(total_markets),
                            style={
                                "color": "#f1f5f9",
                                "fontSize": "1.25rem",
                                "margin": "0",
                                "fontWeight": "700",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.6)",
                        "padding": "0.5rem 0.75rem",
                        "borderRadius": "4px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                        "textAlign": "center",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            "Gainers",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "0.65rem",
                                "margin": "0 0 0.2rem 0",
                                "textTransform": "uppercase",
                                "letterSpacing": "0.05em",
                            },
                        ),
                        html.Div(
                            [
                                html.Span(
                                    str(gainers),
                                    style={
                                        "color": "#10b981",
                                        "fontSize": "1.25rem",
                                        "fontWeight": "700",
                                        "marginRight": "0.35rem",
                                    },
                                ),
                                html.Span(
                                    (
                                        f"({(gainers/total_markets*100):.0f}%)"
                                        if total_markets > 0
                                        else "(0%)"
                                    ),
                                    style={
                                        "color": "#10b981",
                                        "fontSize": "0.65rem",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "baseline",
                                "justifyContent": "center",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.6)",
                        "padding": "0.5rem 0.75rem",
                        "borderRadius": "4px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                        "textAlign": "center",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            "Losers",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "0.65rem",
                                "margin": "0 0 0.2rem 0",
                                "textTransform": "uppercase",
                                "letterSpacing": "0.05em",
                            },
                        ),
                        html.Div(
                            [
                                html.Span(
                                    str(losers),
                                    style={
                                        "color": "#ef4444",
                                        "fontSize": "1.25rem",
                                        "fontWeight": "700",
                                        "marginRight": "0.35rem",
                                    },
                                ),
                                html.Span(
                                    (
                                        f"({(losers/total_markets*100):.0f}%)"
                                        if total_markets > 0
                                        else "(0%)"
                                    ),
                                    style={
                                        "color": "#ef4444",
                                        "fontSize": "0.65rem",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "baseline",
                                "justifyContent": "center",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.6)",
                        "padding": "0.5rem 0.75rem",
                        "borderRadius": "4px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                        "textAlign": "center",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            "Avg Change (1D)",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "0.65rem",
                                "margin": "0 0 0.2rem 0",
                                "textTransform": "uppercase",
                                "letterSpacing": "0.05em",
                            },
                        ),
                        html.Div(
                            f"{avg_change*100:+.2f}%",
                            style={
                                "color": "#10b981" if avg_change > 0 else "#ef4444",
                                "fontSize": "1.25rem",
                                "margin": "0",
                                "fontWeight": "700",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.6)",
                        "padding": "0.5rem 0.75rem",
                        "borderRadius": "4px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                        "textAlign": "center",
                    },
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(130px, 1fr))",
                "gap": "0.5rem",
                "marginBottom": "0.75rem",
            },
        )

    except Exception as e:
        logger.error(f"Error creating summary cards: {e}")
        return html.Div(
            "Error loading summary data",
            style={"color": "#ef4444", "textAlign": "center"},
        )


# Create the layout - Finviz-inspired ultra-compact design with date selector
last_business_day = last_business_day()

layout = html.Div(
    [
        # Header - Ultra Compact with Date Selector
        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            "Investment Dashboard",
                            style={
                                "color": "#f1f5f9",
                                "fontSize": "1.25rem",
                                "fontWeight": "600",
                                "margin": "0",
                            },
                        ),
                        html.Span(
                            f"Last updated: {datetime.now().strftime('%H:%M:%S')}",
                            style={
                                "color": "#64748b",
                                "fontSize": "0.7rem",
                                "marginLeft": "1rem",
                            },
                        ),
                    ],
                    style={"flex": "1", "display": "flex", "alignItems": "center"},
                ),
                html.Div(
                    [
                        html.Label(
                            "As of Date:",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "0.75rem",
                                "marginRight": "0.5rem",
                                "fontWeight": "500",
                            },
                        ),
                        dcc.DatePickerSingle(
                            id="dashboard-date-picker",
                            date=last_business_day.date(),
                            display_format="YYYY-MM-DD",
                            style={
                                "backgroundColor": "rgba(15, 23, 42, 0.8)",
                                "border": "1px solid rgba(148, 163, 184, 0.3)",
                                "borderRadius": "4px",
                                "color": "#f1f5f9",
                                "fontSize": "0.75rem",
                                "padding": "0.25rem 0.5rem",
                                "minWidth": "120px",
                            },
                            className="compact-date-picker",
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "padding": "0.25rem 0.75rem",
                        "background": "rgba(15, 23, 42, 0.6)",
                        "borderRadius": "4px",
                        "border": "1px solid rgba(148, 163, 184, 0.2)",
                    },
                ),
            ],
            style={
                "marginBottom": "0.5rem",
                "padding": "0.5rem 0.75rem",
                "background": "rgba(30, 41, 59, 0.3)",
                "borderRadius": "6px",
                "border": "1px solid rgba(148, 163, 184, 0.15)",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
            },
        ),
        # Summary Statistics
        html.Div(
            id="summary-stats-container",
            children=html.Div(
                "Click the date picker or refresh button to load data",
                style={
                    "textAlign": "center",
                    "color": "#94a3b8",
                    "padding": "2rem",
                    "fontSize": "0.9rem",
                },
            ),
        ),
        # Performance Charts Grid - 2 columns for better readability
        html.Div(
            id="charts-container",
            children=[
                # Major Indices
                html.Div(
                    children=html.Div(
                        id="chart-major-indices",
                        children=html.Div(
                            "Select a date to load data",
                            style={
                                "textAlign": "center",
                                "color": "#94a3b8",
                                "padding": "2rem",
                                "fontSize": "0.85rem",
                            },
                        ),
                    ),
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.2)",
                        "padding": "0.5rem",
                        "borderRadius": "6px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                    },
                ),
                # Global Markets
                html.Div(
                    children=html.Div(
                        id="chart-global-markets",
                        children=html.Div(
                            "Select a date to load data",
                            style={
                                "textAlign": "center",
                                "color": "#94a3b8",
                                "padding": "2rem",
                                "fontSize": "0.85rem",
                            },
                        ),
                    ),
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.2)",
                        "padding": "0.5rem",
                        "borderRadius": "6px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                    },
                ),
                # Sectors
                html.Div(
                    children=html.Div(
                        id="chart-sectors",
                        children=html.Div(
                            "Select a date to load data",
                            style={
                                "textAlign": "center",
                                "color": "#94a3b8",
                                "padding": "2rem",
                                "fontSize": "0.85rem",
                            },
                        ),
                    ),
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.2)",
                        "padding": "0.5rem",
                        "borderRadius": "6px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                    },
                ),
                # Themes
                html.Div(
                    children=html.Div(
                        id="chart-themes",
                        children=html.Div(
                            "Select a date to load data",
                            style={
                                "textAlign": "center",
                                "color": "#94a3b8",
                                "padding": "2rem",
                                "fontSize": "0.85rem",
                            },
                        ),
                    ),
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.2)",
                        "padding": "0.5rem",
                        "borderRadius": "6px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                    },
                ),
                # Commodities
                html.Div(
                    children=html.Div(
                        id="chart-commodities",
                        children=html.Div(
                            "Select a date to load data",
                            style={
                                "textAlign": "center",
                                "color": "#94a3b8",
                                "padding": "2rem",
                                "fontSize": "0.85rem",
                            },
                        ),
                    ),
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.2)",
                        "padding": "0.5rem",
                        "borderRadius": "6px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                    },
                ),
                # Currencies
                html.Div(
                    children=html.Div(
                        id="chart-currencies",
                        children=html.Div(
                            "Select a date to load data",
                            style={
                                "textAlign": "center",
                                "color": "#94a3b8",
                                "padding": "2rem",
                                "fontSize": "0.85rem",
                            },
                        ),
                    ),
                    style={
                        "backgroundColor": "rgba(30, 41, 59, 0.2)",
                        "padding": "0.5rem",
                        "borderRadius": "6px",
                        "border": "1px solid rgba(148, 163, 184, 0.15)",
                    },
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(450px, 1fr))",
                "gap": "0.75rem",
            },
        ),
    ],
    style={
        "maxWidth": "1800px",
        "margin": "0 auto",
        "padding": "0.5rem",
        "backgroundColor": "transparent",
        "color": "#ffffff",
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
)


# Register callback for date changes
from dash import callback, Output, Input


@callback(
    [
        Output("chart-major-indices", "children"),
        Output("chart-global-markets", "children"),
        Output("chart-sectors", "children"),
        Output("chart-themes", "children"),
        Output("chart-commodities", "children"),
        Output("chart-currencies", "children"),
        Output("summary-stats-container", "children"),
    ],
    Input("dashboard-date-picker", "date"),
    prevent_initial_call=True,
)
def update_charts_by_date(selected_date):
    """Update all charts when date changes."""
    if selected_date is None:
        selected_date = get_last_business_day().date()

    # Convert to string format for data loading
    date_str = pd.to_datetime(selected_date).strftime("%Y-%m-%d")

    return (
        create_performance_chart("Major Indices", date_str),
        create_performance_chart("Global Markets", date_str),
        create_performance_chart("Sectors", date_str),
        create_performance_chart("Themes", date_str),
        create_performance_chart("Commodities", date_str),
        create_performance_chart("Currencies", date_str),
        create_summary_cards(),
    )
