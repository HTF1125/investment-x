import json
import threading
import dash_bootstrap_components as dbc
import dash
from dash import dcc, html, Input, Output, callback, ALL, no_update
from ix.bt.analysis.performance import Performance
from ix import task

# Supported periods and universes.
periods = ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]
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


@callback(
    Output("performance-graphs-container", "children"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
)
def update_performance_graphs(n_clicks_list):
    ctx = dash.callback_context
    # Default selected period is "1D"
    if not ctx.triggered:
        selected_period = "1D"
    else:
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        selected_period = json.loads(triggered_id)["period"]

    graph_divs = []
    for universe in universes:
        performance_instance = Performance.from_universe(
            universe=universe, period=selected_period
        )
        fig = performance_instance.plot()
        # Update the Plotly figure to use transparent backgrounds.
        fig.update_layout(
            font=dict(family="Arial, sans-serif", size=12, color="#f8f9fa"),
            paper_bgcolor="rgba(0,0,0,0)",  # transparent
            plot_bgcolor="rgba(0,0,0,0)",  # transparent
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
                    "border": "1px solid #f8f9fa",  # light border
                    "padding": "5px",
                    "backgroundColor": "transparent",  # transparent background
                    "boxShadow": "1px 1px 3px rgba(0,0,0,0.5)",
                    "width": "100%",
                },
            )
        )
    return graph_divs


@callback(
    Output({"type": "period-button", "period": ALL}, "style"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
)
def update_button_styles(n_clicks_list):
    ctx = dash.callback_context
    if not ctx.triggered:
        active_period = "1D"
    else:
        active_period = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["period"]

    # Each button is transparent with a thin border.
    # The active button gets a thicker border.
    return [
        {
            "backgroundColor": "transparent",
            "border": (
                "2px solid #f8f9fa" if period == active_period else "1px solid #f8f9fa"
            ),
            "padding": "0.5rem",
            "margin": "0.25rem",
            "color": "#f8f9fa",
            "borderRadius": "4px",
            "cursor": "pointer",
        }
        for period in periods
    ]


@callback(
    Output("dummy-output", "children"),
    Input("refresh-button", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_callback(n_clicks):
    threading.Thread(target=task.run, daemon=True).start()
    return no_update


def get_layout():
    return dbc.Container(
        [
            dbc.Card(
                [
                    dbc.CardHeader(
                        dbc.Row(
                            [
                                dbc.Col(html.H3("Performance", className="mb-0")),
                                dbc.Col(
                                    dbc.Button(
                                        "Refresh",
                                        id="refresh-button",
                                        color="primary",
                                        className="px-4",
                                    ),
                                    width="auto",
                                    className="text-end",
                                ),
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
                                                id={
                                                    "type": "period-button",
                                                    "period": period,
                                                },
                                                n_clicks=0,
                                                # Initial style; will be updated by callback.
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
