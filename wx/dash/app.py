"""
Global Market Returns Dashboard
A comprehensive dashboard for tracking market performance across different asset classes
"""
import sys
import os
# Add parent directory to path to import ix module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dash import Dash, html, dash_table, dcc, Input, Output, callback
import base64

# Local imports
from components import TechCapexChart, PerformanceChart
from utils import get_data_with_frequency, create_pdf_report
from config import (
    UNIVERSES,
    FREQUENCY_OPTIONS,
    UNIVERSE_ICONS,
    APP_CONFIG,
    COLORS,
    CUSTOM_CSS,
)


def create_universe_section(universe_name, data):
    """Create a section with performance chart and table for each universe"""
    if not data:
        return html.Div()

    # Get column names from the first row
    columns = [{"name": "Asset", "id": "Asset", "type": "text"}]
    if data:
        for col in data[0].keys():
            if col != "Asset":
                column_config = {
                    "name": col,
                    "id": col,
                    "type": "numeric",
                    "format": {"specifier": ".2f"},
                }
                columns.append(column_config)

    icon = UNIVERSE_ICONS.get(universe_name, "📊")

    # Generate performance chart
    try:
        performance_chart = PerformanceChart()
        universe_config = UNIVERSES.get(universe_name, [])
        fig, performance_data = performance_chart.get_chart_data(universe_config, universe_name, icon)

        chart_component = dcc.Graph(
            figure=fig,
            config={'displayModeBar': True, 'displaylogo': False}
        ) if fig else html.Div(
            f"Performance chart not available for {universe_name}",
            style={
                "textAlign": "center",
                "color": COLORS["danger"],
                "fontSize": "1rem",
                "padding": "20px",
            }
        )
    except Exception as e:
        print(f"Error creating performance chart for {universe_name}: {e}")
        chart_component = html.Div(
            f"Error loading performance chart: {str(e)}",
            style={
                "textAlign": "center",
                "color": COLORS["danger"],
                "fontSize": "1rem",
                "padding": "20px",
            }
        )

    return html.Div(
        [
            # Section header
            html.Div(
                [
                    html.H3(
                        [html.Span(icon, style={"marginRight": "10px"}), universe_name],
                        style={
                            "margin": "0",
                            "fontSize": "1.2rem",
                            "fontWeight": "600",
                            "color": "white",
                        },
                    )
                ],
                style={
                    "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%)",
                    "padding": "15px 20px",
                    "borderRadius": "8px 8px 0 0",
                },
            ),
            # Performance Chart
            html.Div(
                [chart_component],
                style={
                    "backgroundColor": "white",
                    "padding": "20px",
                    "borderBottom": "1px solid #e5e7eb",
                    "minHeight": "520px",  # Ensure minimum height for proper legend spacing
                }
            ),
            # Data Table
            html.Div(
                [
                    dash_table.DataTable(
                        data=data,
                        columns=columns,
                        style_table={"overflowX": "auto", "minWidth": "100%"},
                        style_header={
                            "backgroundColor": COLORS["table_bg"],
                            "fontWeight": "600",
                            "textAlign": "center",
                            "padding": "10px",
                            "fontSize": "11px",
                            "color": "#475569",
                            "border": f"1px solid {COLORS['border']}",
                            "whiteSpace": "nowrap",
                        },
                        style_cell={
                            "textAlign": "center",
                            "padding": "8px 12px",
                            "fontFamily": "'Inter', sans-serif",
                            "fontSize": "11px",
                            "border": f"1px solid {COLORS['border']}",
                            "whiteSpace": "nowrap",
                            "minWidth": "60px",
                        },
                        style_data_conditional=[
                            {"if": {"row_index": "odd"}, "backgroundColor": COLORS["table_bg"]}
                        ]
                        + [
                            {
                                "if": {
                                    "filter_query": f"{{{col}}} > 3",
                                    "column_id": col,
                                },
                                "backgroundColor": COLORS["success"],
                                "color": "white",
                                "fontWeight": "600",
                            }
                            for col in data[0].keys()
                            if col != "Asset"
                        ]
                        + [
                            {
                                "if": {
                                    "filter_query": f"{{{col}}} > 0 && {{{col}}} <= 3",
                                    "column_id": col,
                                },
                                "backgroundColor": COLORS["success_light"],
                                "color": COLORS["success_text"],
                            }
                            for col in data[0].keys()
                            if col != "Asset"
                        ]
                        + [
                            {
                                "if": {
                                    "filter_query": f"{{{col}}} < -3",
                                    "column_id": col,
                                },
                                "backgroundColor": COLORS["danger"],
                                "color": "white",
                                "fontWeight": "600",
                            }
                            for col in data[0].keys()
                            if col != "Asset"
                        ]
                        + [
                            {
                                "if": {
                                    "filter_query": f"{{{col}}} < 0 && {{{col}}} >= -3",
                                    "column_id": col,
                                },
                                "backgroundColor": COLORS["danger_light"],
                                "color": COLORS["danger_text"],
                            }
                            for col in data[0].keys()
                            if col != "Asset"
                        ],
                        style_cell_conditional=[
                            {
                                "if": {"column_id": "Asset"},
                                "textAlign": "left",
                                "fontWeight": "600",
                                "backgroundColor": "#f1f5f9",
                                "borderRight": "2px solid #d1d5db",
                            }
                        ],
                        page_action="none",
                        sort_action="native",
                    )
                ],
                style={
                    "backgroundColor": "white",
                    "borderRadius": "0 0 8px 8px",
                    "border": "1px solid #e5e7eb",
                    "overflowX": "auto",
                },
            ),
        ],
        style={
            "marginBottom": "30px",
            "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            "borderRadius": "8px",
            "overflow": "hidden",
            "maxWidth": "1200px",
            "margin": "0 auto 30px auto",
        },
    )


# Create the Dash app
app = Dash(__name__)

# Enhanced CSS
app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            {CUSTOM_CSS}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
"""

app.layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.H1(
                    f"📊 {APP_CONFIG['title']}",
                    style={
                        "textAlign": "center",
                        "color": "white",
                        "fontSize": "2.5rem",
                        "fontWeight": "700",
                        "margin": "0 0 10px 0",
                    },
                ),
                html.P(
                    APP_CONFIG["description"],
                    style={
                        "textAlign": "center",
                        "color": "rgba(255,255,255,0.9)",
                        "fontSize": "1.1rem",
                        "margin": "0 0 30px 0",
                    },
                ),
                # Frequency selector
                html.Div(
                    [
                        html.Label(
                            "📈 Time Period:",
                            style={
                                "color": "white",
                                "fontSize": "14px",
                                "fontWeight": "600",
                                "marginRight": "15px",
                            },
                        ),
                        dcc.Dropdown(
                            id="frequency-dropdown",
                            options=FREQUENCY_OPTIONS,
                            value=APP_CONFIG["default_frequency"],
                            style={"width": "150px", "fontSize": "14px"},
                        ),
                        html.Button(
                            [
                                html.Div(
                                    id="btn-loading",
                                    style={
                                        "display": "none",
                                        "width": "16px",
                                        "height": "16px",
                                        "border": f"2px solid {COLORS['primary']}",
                                        "borderTop": "2px solid transparent",
                                        "borderRadius": "50%",
                                        "animation": "spin 1s linear infinite",
                                    }
                                ),
                                html.Span("📄 Download PDF", id="btn-text"),
                            ],
                            id="download-pdf-btn",
                            style={
                                "marginLeft": "20px",
                                "padding": "10px 20px",
                                "backgroundColor": "white",
                                "color": COLORS["primary"],
                                "border": "none",
                                "borderRadius": "6px",
                                "fontWeight": "600",
                                "cursor": "pointer",
                                "fontSize": "14px",
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "8px",
                            },
                        ),
                        dcc.Download(id="download-pdf"),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "backgroundColor": "rgba(255,255,255,0.1)",
                        "padding": "15px",
                        "borderRadius": "10px",
                        "backdropFilter": "blur(10px)",
                        "maxWidth": "500px",
                        "margin": "0 auto",
                        "gap": "15px",
                    },
                ),
            ],
            style={
                "padding": "40px 20px",
                "background": COLORS["background"],
            },
        ),
        # Main content
        html.Div(
            [
                # Universe sections with charts and tables
                dcc.Loading(
                    id="loading-tables",
                    type="dot",
                    color=COLORS["primary"],
                    style={"minHeight": "200px"},
                    children=html.Div(id="tables-container"),
                ),
                # CAPEX Chart Section (moved to bottom)
                html.Div(
                    [
                        # Section header (matching universe sections)
                        html.Div(
                            [
                                html.H3(
                                    [html.Span("📊", style={"marginRight": "10px"}), "Tech Companies CAPEX Analysis"],
                                    style={
                                        "margin": "0",
                                        "fontSize": "1.2rem",
                                        "fontWeight": "600",
                                        "color": "white",
                                    },
                                )
                            ],
                            style={
                                "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%)",
                                "padding": "15px 20px",
                                "borderRadius": "8px 8px 0 0",
                            },
                        ),
                        # Chart container
                        html.Div(
                            [
                                dcc.Loading(
                                    id="loading-capex-chart",
                                    type="dot",
                                    color=COLORS["primary"],
                                    children=html.Div(id="capex-chart-container"),
                                ),
                            ],
                            style={
                                "backgroundColor": "white",
                                "borderRadius": "0 0 8px 8px",
                                "padding": "20px",
                                "minHeight": "600px",  # Ensure minimum height for proper legend spacing
                            }
                        ),
                    ],
                    style={
                        "marginBottom": "30px",
                        "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                        "borderRadius": "8px",
                        "overflow": "hidden",
                        "maxWidth": "1200px",
                        "margin": "0 auto 30px auto",
                    },
                )
            ],
            style={
                "padding": "30px 20px",
                "background": "linear-gradient(to bottom, rgba(102,126,234,0.1), #f9fafb)",
                "minHeight": "100vh",
            },
        ),
    ]
)


@callback(
    Output("capex-chart-container", "children"),
    Input("frequency-dropdown", "value")
)
def update_capex_chart(selected_frequency):
    """Update CAPEX chart"""
    try:
        chart_component = TechCapexChart()
        fig, weekly_pct_change, individual_weekly_changes = chart_component.get_chart_data()

        if fig is None:
            return html.Div(
                "CAPEX data not available",
                style={
                    "textAlign": "center",
                    "color": COLORS["danger"],
                    "fontSize": "1.1rem",
                    "padding": "20px",
                },
            )

        return dcc.Graph(
            figure=fig,
            style={"height": f"{APP_CONFIG['capex_chart_height']}px"},
            config={'displayModeBar': True, 'displaylogo': False}
        )

    except Exception as e:
        print(f"Error loading CAPEX chart: {e}")
        return html.Div(
            f"Error loading CAPEX chart: {str(e)}",
            style={
                "textAlign": "center",
                "color": COLORS["danger"],
                "fontSize": "1.1rem",
                "padding": "20px",
            },
        )


@callback(
    [Output("btn-text", "style"), Output("btn-loading", "style")],
    [Input("download-pdf-btn", "n_clicks")],
    prevent_initial_call=True
)
def update_button_loading(n_clicks):
    """Show loading state when button is clicked"""
    if n_clicks and n_clicks > 0:
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


@callback(
    Output("download-pdf", "data"),
    [Input("download-pdf-btn", "n_clicks")],
    [Input("frequency-dropdown", "value")],
    prevent_initial_call=True
)
def download_pdf(n_clicks, selected_frequency):
    """Handle PDF download"""
    if n_clicks and n_clicks > 0:
        universe_data = get_data_with_frequency(UNIVERSES, selected_frequency)
        pdf_buffer = create_pdf_report(universe_data, selected_frequency)

        return dcc.send_bytes(
            pdf_buffer.getvalue(),
            filename=f"market_returns_{selected_frequency}.pdf"
        )
    return None


@callback(Output("tables-container", "children"), Input("frequency-dropdown", "value"))
def update_tables(selected_frequency):
    """Update tables based on selected frequency"""
    try:
        universe_data = get_data_with_frequency(UNIVERSES, selected_frequency)
        if not universe_data:
            return html.Div(
                "No data available",
                style={
                    "textAlign": "center",
                    "color": COLORS["danger"],
                    "fontSize": "1.2rem",
                    "padding": "50px",
                },
            )

        return [create_universe_section(name, data) for name, data in universe_data.items()]

    except Exception as e:
        print(f"Error in callback: {e}")
        return html.Div(
            f"Error loading data: {str(e)}",
            style={
                "textAlign": "center",
                "color": COLORS["danger"],
                "padding": "50px"
            },
        )


if __name__ == "__main__":
    app.run_server()
