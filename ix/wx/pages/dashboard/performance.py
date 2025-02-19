from dash import dcc, html, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
import dash
import json
import pandas as pd

# Import your specific modules
from ix.bt.analysis.performance import Performance
from ix import db

# Global list of periods
periods = ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]

# Define the layout
layout = dbc.Container(
    [
        # Interval component to trigger refresh every 5 minutes (300,000 ms)
        dcc.Interval(
            id="refresh-interval",
            interval=300000,
            n_intervals=0,
        ),
        dcc.Store(id="performance-store", storage_type="local"),
        dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Row(
                        [
                            dbc.Col(html.H3("Performance", className="mb-0")),
                        ],
                        align="center",
                    ),
                    style={
                        "backgroundColor": "transparent",
                        "color": "#f8f9fa",
                        "borderBottom": "2px solid #f8f9fa",
                        "padding": "1rem",
                    },
                ),
                dbc.CardBody(
                    [
                        # Period selector using a button group.
                        html.Div(
                            [
                                html.Label(
                                    "Select Period: ",
                                    style={
                                        "marginRight": "20px",
                                        "fontWeight": "bold",
                                        "color": "#f8f9fa",
                                    },
                                ),
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            period,
                                            id={"type": "period-button", "period": period},
                                            n_clicks=0,
                                            style={
                                                "backgroundColor": "transparent",
                                                "border": "1px solid #f8f9fa",
                                                "padding": "0.5rem",
                                                "margin": "0.25rem",
                                                "color": "#f8f9fa",
                                                "borderRadius": "4px",
                                                "cursor": "pointer",
                                            },
                                        )
                                        for period in periods
                                    ]
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "marginBottom": "1rem",
                            },
                        ),
                        dcc.Loading(
                            id="loading-performance-graphs",
                            children=html.Div(
                                id="performance-graphs-container",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(4, 1fr)",
                                    "gridGap": "10px",
                                    "justifyItems": "center",
                                },
                            ),
                            type="default",
                        ),
                        html.Div(id="dummy-output", style={"display": "none"}),
                    ],
                    style={
                        "backgroundColor": "transparent",
                        "color": "#f8f9fa",
                        "padding": "1.5rem",
                    },
                ),
            ],
            style={
                "backgroundColor": "transparent",
                "border": "1px solid #f8f9fa",
                "borderRadius": "8px",
                "boxShadow": "2px 2px 5px rgba(0,0,0,0.5)",
                "margin": "1rem 0",
            },
            className="rounded-3 w-100",
        ),
    ],
    fluid=True,
    className="py-1",
    style={"backgroundColor": "transparent"},
)

# --- Callback 1: Refresh Performance Data ---
@callback(
    Output("performance-store", "data"),
    Input("refresh-interval", "n_intervals")
)
def refresh_data(n_intervals):
    """
    This callback refreshes performance data every 5 minutes.
    """
    universes = [
        "LocalIndices",
        "GicsUS",
        "GlobalMarkets",
        "Styles",
        "GlobalBonds",
        "Commodities",
        "Themes",
        "Currencies",
    ]
    data = {}
    for universe in universes:
        universe_obj = db.Universe.find_one({"code": universe}).run()
        if not universe_obj:
            continue
        data[universe] = []
        for asset in universe_obj.assets:
            metadata = db.Metadata.find_one({"code": asset.code}).run()
            if metadata is None:
                continue
            perf = asset.model_dump()
            for period in periods:
                perf[period] = metadata.tp(field=f"PCT_CHG_{period}").data
            data[universe].append(perf)
    return data

# --- Callback 2: Update Graphs Based on Selected Period ---
@callback(
    Output("performance-graphs-container", "children"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
    State("performance-store", "data"),
)
def update_graphs(n_clicks_list, data):
    """
    This callback updates the performance graphs based on the selected period.
    It uses the data stored in 'performance-store'.
    """
    if data is None:
        return []  # No data yet; dcc.Loading will show a spinner

    ctx = dash.callback_context
    selected_period = "1D"  # default period
    for t in ctx.triggered:
        if "period-button" in t["prop_id"]:
            try:
                selected_period = json.loads(t["prop_id"].split(".")[0]).get("period", "1D")
                break
            except (json.JSONDecodeError, KeyError):
                selected_period = "1D"

    graph_divs = []
    for universe, performances in data.items():
        performance_data = pd.DataFrame(performances)
        if "name" not in performance_data.columns:
            continue
        performance_data = performance_data.set_index("name")
        if selected_period not in performance_data.columns:
            continue

        performance_instance = Performance(performance_data[selected_period])
        fig = performance_instance.plot()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#555"),
            yaxis=dict(gridcolor="#555"),
        )
        graph_divs.append(
            html.Div(
                [
                    html.H3(
                        f"{universe}",
                        style={
                            "textAlign": "center",
                            "fontSize": "12px",
                            "color": "#f8f9fa",
                            "marginBottom": "0.5rem",
                        },
                    ),
                    dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": False, "responsive": True},
                        style={"height": "250px"},
                    ),
                ],
                style={
                    "border": "1px solid #f8f9fa",
                    "padding": "5px",
                    "backgroundColor": "transparent",
                    "boxShadow": "1px 1px 3px rgba(0,0,0,0.5)",
                    "width": "100%",
                },
            )
        )
    return graph_divs

# --- Callback 3: Update Period Button Styles ---
@callback(
    Output({"type": "period-button", "period": ALL}, "style"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
)
def update_button_styles(n_clicks_list):
    ctx = dash.callback_context
    if not ctx.triggered:
        active_period = "1D"
    else:
        try:
            active_period = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["period"]
        except Exception:
            active_period = "1D"
    return [
        {
            "backgroundColor": "transparent",
            "border": "2px solid #f8f9fa" if period == active_period else "1px solid #f8f9fa",
            "padding": "0.5rem",
            "margin": "0.25rem",
            "color": "#f8f9fa",
            "borderRadius": "4px",
            "cursor": "pointer",
        }
        for period in periods
    ]
