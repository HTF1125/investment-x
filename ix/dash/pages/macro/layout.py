"""
Dash App: Macro Charts with Period Selection (Dark Theme) - Optimized
- Uses figures from macro_charts_dark_theme.CHART_FUNCTIONS
- Individual chart callbacks for parallel loading
- Enhanced styling with improved spacing and visual hierarchy
- Fixed navbar overlap issue

Usage
-----
1) Ensure `macro_charts_dark_theme.py` (the charts module) is in the same folder.
2) Run:  python macro_dashboard.py
3) Open: http://127.0.0.1:8050
"""

from __future__ import annotations

import json
from dateutil.relativedelta import relativedelta
import pandas as pd

from dash import (
    Dash,
    html,
    dcc,
    Input,
    Output,
    State,
    Patch,
    ALL,
    callback_context,
    callback,
    register_page,
)

# Import chart builders from your charts module
register_page(__name__, path="/macro", title="Macro", name="Macro")

# =====================================
# Helper: period ranges
# =====================================
from ix.misc.date import today


def get_period_range(period: str = "5Y"):
    p = int(period.replace("Y", ""))
    return today() - relativedelta(years=p)


# =====================================
# UI components (dark) - Enhanced
# =====================================


def _btn_style(active: bool):
    if active:
        return {
            "background": "linear-gradient(145deg, #3b82f6, #2563eb)",
            "color": "white",
            "border": "2px solid #60a5fa",
            "borderRadius": "10px",
            "padding": "14px 24px",
            "fontSize": "0.95rem",
            "fontWeight": "700",
            "cursor": "pointer",
            "transition": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            "boxShadow": "0 8px 25px rgba(59, 130, 246, 0.4), 0 2px 10px rgba(59, 130, 246, 0.25)",
            "transform": "translateY(-2px) scale(1.02)",
            "minWidth": "75px",
            "letterSpacing": "0.025em",
            "textAlign": "center",
        }
    else:
        return {
            "background": "linear-gradient(145deg, #475569, #334155)",
            "color": "#e2e8f0",
            "border": "1px solid #64748b",
            "borderRadius": "10px",
            "padding": "14px 24px",
            "fontSize": "0.95rem",
            "fontWeight": "600",
            "cursor": "pointer",
            "transition": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            "boxShadow": "0 4px 12px rgba(0,0,0,0.2), inset 0 1px 2px rgba(255,255,255,0.1)",
            "minWidth": "75px",
            "letterSpacing": "0.025em",
            "textAlign": "center",
        }


def create_time_period_selector():
    return html.Div(
        style={
            "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.95))",
            "backdropFilter": "saturate(180%) blur(20px)",
            "border": "1px solid rgba(148, 163, 184, 0.25)",
            "borderRadius": "16px",
            "padding": "20px 28px",
            "marginBottom": "32px",
            "marginTop": "0px",
            "boxShadow": "0 8px 32px rgba(0,0,0,0.25)",
            "position": "sticky",  # Sticky positioning
            "top": "90px",  # Position below navbar (90px buffer for desktop)
            "zIndex": 100,  # High enough to stay above charts but below navbar
        },
        className="time-period-selector",  # Add class for responsive CSS
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "gap": "24px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        [
                            html.Span(
                                "⏱️",
                                style={
                                    "fontSize": "1.5rem",
                                    "marginRight": "12px",
                                    "filter": "drop-shadow(0 2px 4px rgba(0,0,0,0.3))",
                                },
                            ),
                            html.Span(
                                "Time Period:",
                                style={
                                    "fontSize": "1.1rem",
                                    "fontWeight": "700",
                                    "color": "#f1f5f9",
                                    "letterSpacing": "0.025em",
                                },
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "12px",
                            "flexWrap": "wrap",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                        children=[
                            html.Button(
                                period,
                                id={"type": "period-btn", "period": period},
                                n_clicks=0,
                                style=_btn_style(active=(period == "5Y")),
                                className="period-btn",
                            )
                            for period in ["1Y", "3Y", "5Y", "10Y", "20Y", "30Y", "50Y"]
                        ],
                    ),
                ],
            ),
        ],
    )


from ix.dash.components import Grid, Card


def create_footer():
    return html.Div(
        style={
            "marginTop": "60px",
            "padding": "24px",
            "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8))",
            "borderRadius": "14px",
            "textAlign": "center",
            "border": "1px solid rgba(148, 163, 184, 0.15)",
            "boxShadow": "0 4px 20px rgba(0,0,0,0.1)",
        },
        children=[
            html.P(
                f"Data updated as of {pd.Timestamp.now().strftime('%B %d, %Y')} • Built with Dash & Plotly",
                style={
                    "color": "#94a3b8",
                    "fontSize": "0.9rem",
                    "margin": "0",
                    "fontWeight": "500",
                    "letterSpacing": "0.025em",
                },
            ),
        ],
    )


from ix.cht import __chts__

# =====================================
# Optimized Chart Component
# =====================================

import plotly.graph_objects as go


def Chart(chart_name: str):
    return dcc.Loading(
        id={"type": "chart-loading", "name": chart_name},
        children=dcc.Graph(
            id={"type": "chart", "name": chart_name},
            figure=go.Figure(),  # Empty figure initially
            style={
                "height": "520px",
                "background": "transparent",
                "borderRadius": "12px",
            },
            animate=False,  # Disable animation for faster loading
            config={
                "displayModeBar": False,
                "responsive": True,
                "doubleClick": "reset",
                "scrollZoom": True,
            },
        ),
        type="dot",
        color="#3b82f6",
        style={"height": "520px"},
        loading_state={"is_loading": True},  # Start with loading enabled
    )


# =====================================
# Main Layout - Fixed to work with navbar and responsive sticky selector
# =====================================

layout = html.Div(
    style={
        # Remove conflicting full-height styling that overrides app layout
        "background": "transparent",  # Let app background show through
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "padding": "0px",  # No padding - let app handle spacing
        "margin": "0px",  # No margin
    },
    children=[
        dcc.Store(id="preset-store", data="5Y"),
        html.Div(
            style={
                "maxWidth": "1600px",
                "margin": "0 auto",
                "width": "100%",
                "padding": "20px",  # Consistent padding all around
                "boxSizing": "border-box",
            },
            children=[
                create_time_period_selector(),
                Grid([Card(Chart(k.__name__)) for k in __chts__]),
                create_footer(),
            ],
        ),
    ],
)


# =====================================
# Optimized Callbacks - Individual Chart Loading
# =====================================
# Create individual callbacks for each chart for parallel loading
def create_chart_callback(chart_func):
    """Create a callback for a specific chart function to avoid closure issues"""

    @callback(
        Output({"type": "chart", "name": chart_func.__name__}, "figure"),
        Output({"type": "chart-loading", "name": chart_func.__name__}, "loading_state"),
        Input("preset-store", "data"),
        prevent_initial_call=False,
    )
    def update_individual_chart(period):
        """Load individual chart with period filtering"""
        try:
            # Create the chart using the captured chart function
            fig = chart_func()

            # Apply period range for ALL periods including 20Y
            if period:
                start_dt = get_period_range(period)
                end_dt = today() + relativedelta(months=6)  # Add 6 months buffer
                xr = [
                    pd.to_datetime(start_dt),
                    pd.to_datetime(end_dt),
                ]

                fig.update_layout(
                    xaxis=dict(
                        range=xr,
                        showgrid=True,
                        gridcolor="rgba(148, 163, 184, 0.1)",
                        zeroline=False,
                    )
                )

            # Ensure proper dark theme styling with legend
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                # Increase bottom margin to accommodate legend and x-axis
                margin=dict(l=60, r=40, t=40, b=100),
                # Ensure legend is visible and properly styled
                legend=dict(
                    visible=True,
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,  # Move legend further down
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(0,0,0,0)",
                    bordercolor="rgba(148, 163, 184, 0.3)",
                    borderwidth=1,
                    font=dict(color="#e2e8f0", size=11),
                    itemsizing="trace",
                    itemwidth=30,
                    yref="paper",
                ),
            )

            return fig, {"is_loading": False}

        except Exception as e:
            # Create error figure
            error_fig = go.Figure()
            error_fig.add_annotation(
                text=f"Error loading {chart_func.__name__}: {str(e)[:60]}...",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="#ef4444"),
            )
            error_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                margin=dict(l=0, r=0, t=0, b=0),
                height=520,
            )
            return error_fig, {"is_loading": False}

    return update_individual_chart


# Create callbacks for each chart
for chart_func in __chts__:
    create_chart_callback(chart_func)


# Period button callback
@callback(
    Output("preset-store", "data"),
    Input({"type": "period-btn", "period": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def update_period_store(button_clicks):
    """Update the period store when a button is clicked"""
    ctx = callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"]
        if "period-btn" in trigger_id and ctx.triggered[0]["value"]:
            button_id = json.loads(trigger_id.split(".")[0])
            return button_id["period"]
    return "5Y"


# Button styling callback
@callback(
    Output({"type": "period-btn", "period": ALL}, "style"),
    Input("preset-store", "data"),
)
def highlight_buttons(active_preset):
    """Update button styles based on active period"""
    periods = ["1Y", "3Y", "5Y", "10Y", "20Y", "30Y", "50Y"]
    return [_btn_style(p == active_preset) for p in periods]
