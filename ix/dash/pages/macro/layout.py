"""
Dash App: Macro Charts with Period Selection (Dark Theme)
- Uses figures from macro_charts_dark_theme.CHART_FUNCTIONS
- Modern header, sticky period selector, responsive grid, and pattern-matching callbacks

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
    Patch,
    ALL,
    callback_context,
    callback,
    register_page,
)
from ix.cht import CHART_FUNCTIONS

# Import chart builders from your charts module
# Make sure the file name is exactly: macro_charts_dark_theme.py
register_page(__name__, path="/macro", title="Macro", name="Macro")

# =====================================
# Helper: period ranges
# =====================================
from ix.misc.date import today


def get_period_range(period: str = "20Y"):
    p = int(period.replace("Y", ""))
    return today() - relativedelta(years=p)


# =====================================
# UI components (dark)
# =====================================


def create_header():
    return html.Div(
        style={
            "background": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
            "padding": "32px 24px",
            "marginBottom": "24px",
            "borderRadius": "16px",
            "boxShadow": "0 10px 25px rgba(0,0,0,0.3)",
            "position": "relative",
            "overflow": "hidden",
            "border": "1px solid rgba(148, 163, 184, 0.1)",
        },
        children=[
            html.Div(
                style={
                    "position": "absolute",
                    "top": "-50%",
                    "right": "-20%",
                    "width": "300px",
                    "height": "300px",
                    "background": "rgba(59, 130, 246, 0.1)",
                    "borderRadius": "50%",
                    "filter": "blur(80px)",
                }
            ),
            html.Div(
                style={"position": "relative", "zIndex": 2},
                children=[
                    html.H1(
                        "Global Macro Analysis Dashboard",
                        style={
                            "color": "#f1f5f9",
                            "fontSize": "2.0rem",
                            "fontWeight": "700",
                            "margin": "0 0 8px 0",
                            "letterSpacing": "-0.025em",
                        },
                    ),
                    html.P(
                        "Real-time insights into liquidity, financial conditions, and business cycle indicators",
                        style={
                            "color": "rgba(241, 245, 249, 0.8)",
                            "fontSize": "1rem",
                            "margin": "0",
                            "fontWeight": "400",
                            "lineHeight": "1.6",
                        },
                    ),
                ],
            ),
        ],
    )


def _btn_style(active: bool):
    if active:
        return {
            "background": "linear-gradient(145deg, #3b82f6, #2563eb)",
            "color": "white",
            "border": "1px solid #60a5fa",
            "borderRadius": "5px",
            "padding": "10px 10px",
            "fontSize": "0.875rem",
            "fontWeight": "600",
            "cursor": "pointer",
            "transition": "all 0.2s ease",
            "boxShadow": "0 4px 12px rgba(59, 130, 246, 0.4)",
            "transform": "translateY(-1px)",
            "minWidth": "60px",
        }
    else:
        return {
            "background": "linear-gradient(145deg, #374151, #1f2937)",
            "color": "#d1d5db",
            "border": "1px solid #4b5563",
            "borderRadius": "5px",
            "padding": "10px 10px",
            "fontSize": "0.875rem",
            "fontWeight": "600",
            "cursor": "pointer",
            "transition": "all 0.2s ease",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            "minWidth": "60px",
        }


def create_time_period_selector():
    return html.Div(
        style={
            "background": "rgba(30, 41, 59, 0.95)",
            "backdropFilter": "saturate(180%) blur(20px)",
            "border": "1px solid rgba(148, 163, 184, 0.2)",
            "borderRadius": "16px",
            "padding": "5px 5px",
            "marginBottom": "20px",
            "boxShadow": "0 8px 32px rgba(0,0,0,0.2)",
            "position": "sticky",
            "top": "10px",
            "zIndex": 1000,
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "20px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        [
                            html.Span(
                                "📊", style={"fontSize": "1.2rem", "marginRight": "8px"}
                            ),
                            html.Span(
                                "Time Period:",
                                style={
                                    "fontSize": "1rem",
                                    "fontWeight": "600",
                                    "color": "#e2e8f0",
                                },
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                        children=[
                            html.Button(
                                period,
                                id={"type": "period-btn", "period": period},
                                n_clicks=0,
                                style=_btn_style(active=(period == "20Y")),
                            )
                            for period in ["1Y", "3Y", "5Y", "10Y", "20Y", "30Y", "50Y"]
                        ],
                    ),
                ],
            ),
        ],
    )


def Card(children: ...):

    return html.Div(
        style={
            "background": "rgba(30, 41, 59, 0.95)",
            "borderRadius": "16px",
            "padding": "24px",
            "boxShadow": "0 4px 20px rgba(0,0,0,0.2)",
            "border": "1px solid rgba(148, 163, 184, 0.1)",
            "backdropFilter": "saturate(180%) blur(20px)",
            "transition": "all 0.3s ease",
            "height": "100%",
            "display": "flex",
            "flexDirection": "column",
        },
        children=[
            html.Div(
                style={
                    "flex": "1",
                    "background": "rgba(15, 23, 42, 0.6)",
                    "borderRadius": "12px",
                    "padding": "8px",
                },
                children=[children],
            ),
        ],
    )


def Grid(children: ..., gap: str = "24px", marginBottom: str = "32px"):
    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(480px, 1fr))",
            "gap": gap,
            "marginBottom": marginBottom,
        },
        children=children,
    )


def create_footer():
    return html.Div(
        style={
            "marginTop": "48px",
            "padding": "24px",
            "background": "rgba(30, 41, 59, 0.7)",
            "borderRadius": "12px",
            "textAlign": "center",
            "border": "1px solid rgba(148, 163, 184, 0.1)",
        },
        children=[
            html.P(
                f"Data updated as of {pd.Timestamp.now().strftime('%B %d, %Y')} • Built with Dash & Plotly",
                style={
                    "color": "#94a3b8",
                    "fontSize": "0.875rem",
                    "margin": "0",
                    "fontWeight": "500",
                },
            ),
        ],
    )


# =====================================
# App & Layout
# =====================================




# Ensure names exist even if CHART_FUNCTIONS changes
import plotly.graph_objects as go


def Chart(fig: go.Figure, chart_name: str):
    return dcc.Graph(
        id={"type": "chart", "name": chart_name},
        figure=fig,
        style={"height": "400px", "background": "transparent"},
        animate=True,
        config={"displayModeBar": False, "responsive": True},
    )


layout = html.Div(
    style={
        "minHeight": "100vh",
        "background": "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "padding": "16px",
    },
    children=[
        dcc.Store(id="preset-store", data="20Y"),
        html.Div(
            style={
                "maxWidth": "1600px",
                "margin": "0 auto",
                "width": "100%",
                "height": "calc(100vh - 32px)",  # Account for padding
                "overflowY": "auto",
                "overflowX": "hidden",
                "paddingRight": "8px",  # Space for scrollbar
                "scrollbarWidth": "thin",  # For Firefox
                "scrollbarColor": "#4b5563 #1e293b",  # For Firefox
            },
            children=[
                create_time_period_selector(),
                Grid([Card(Chart(cht(), k)) for k, cht in CHART_FUNCTIONS.items()]),
                create_footer(),
            ],
        ),
    ],
)


# =====================================
# Callbacks
# =====================================


@callback(
    Output({"type": "chart", "name": ALL}, "figure"),
    Output("preset-store", "data"),
    Input({"type": "period-btn", "period": ALL}, "n_clicks"),
)
def update_x_range(button_clicks):
    trig = (
        callback_context.triggered[0]["prop_id"] if callback_context.triggered else None
    )

    if trig and "period-btn" in trig:
        button_id = json.loads(trig.split(".")[0])
        period = button_id["period"]
        active_preset = period
        start_dt = get_period_range(period)
    else:
        active_preset = "20Y"
        start_dt = get_period_range("20Y")

    end_dt = today() + relativedelta(years=1)

    xr = [pd.to_datetime(start_dt), pd.to_datetime(end_dt) + pd.DateOffset(months=4)]

    patches = []
    # Create patches for all charts in CHART_FUNCTIONS
    for _ in range(len(CHART_FUNCTIONS)):
        patch = Patch()
        patch["layout"]["xaxis"]["range"] = xr
        patches.append(patch)

    return patches, active_preset


@callback(
    Output({"type": "period-btn", "period": ALL}, "style"),
    Input("preset-store", "data"),
)
def highlight_buttons(active_preset):
    periods = ["1Y", "3Y", "5Y", "10Y", "20Y", "30Y", "50Y"]
    return [{**_btn_style(p == active_preset)} for p in periods]
