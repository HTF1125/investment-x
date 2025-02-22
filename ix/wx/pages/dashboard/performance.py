from dash import dcc, html, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
import dash
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from ix.bt.analysis.performance import performance_fig
from ix import db
from ix.misc import periods


def create_chart_layout():
    return {
        "margin": {"l": 25, "r": 25, "t": 25, "b": 25},
        "xaxis": {"rangeslider": {"visible": False}},
        "yaxis": {"fixedrange": False},
        "font": {"family": "Arial, sans-serif", "size": 12, "color": "#ffffff"},
        "paper_bgcolor": "#212529",
        "plot_bgcolor": "#212529",
    }


layout = dbc.Container(
    fluid=True,
    children=[
        dcc.Interval(id="refresh-interval", interval=300000, n_intervals=0),
        dcc.Store(id="performance-store", storage_type="local"),
        dbc.Card(
            style={
                "backgroundColor": "#212529",
                "color": "#ffffff",
                "border": "1px solid #f8f9fa",
            },
            children=[
                dbc.CardHeader(
                    style={
                        "backgroundColor": "#212529",
                        "borderBottom": "2px solid #f8f9fa",
                    },
                    children=dbc.Row(
                        [
                            dbc.Col(html.H3("Performance", style={"color": "#ffffff"})),
                        ]
                    ),
                ),
                dbc.CardBody(
                    style={"backgroundColor": "#212529", "color": "#ffffff"},
                    children=[
                        html.Div(
                            [
                                html.Label(
                                    "Select Period: ",
                                    style={"fontWeight": "bold", "color": "#f8f9fa"},
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
                                            style={
                                                "backgroundColor": "#343a40",
                                                "border": "1px solid #f8f9fa",
                                                "color": "#f8f9fa",
                                            },
                                        )
                                        for period in periods
                                    ]
                                ),
                            ]
                        ),
                        dcc.Loading(
                            id="loading-performance-graphs",
                            type="default",
                            children=html.Div(id="performance-graphs-container"),
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@callback(Output("performance-store", "data"), Input("refresh-interval", "n_intervals"))
def refresh_data(n_intervals):
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


@callback(
    Output("performance-graphs-container", "children"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
    State("performance-store", "data"),
)
def update_graphs(n_clicks_list, data):
    if data is None:
        return []
    ctx = dash.callback_context
    selected_period = "1D"
    for t in ctx.triggered:
        if "period-button" in t["prop_id"]:
            try:
                selected_period = json.loads(t["prop_id"].split(".")[0]).get(
                    "period", "1D"
                )
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
        fig = performance_fig(performance_data[selected_period].copy())
        fig.update_layout(create_chart_layout())
        graph_divs.append(
            dbc.Col(
                html.Div(
                    [
                        html.H4(
                            f"{universe}",
                            style={
                                "textAlign": "center",
                                "color": "#f8f9fa",
                                "marginBottom": "10px",
                            },
                        ),
                        dcc.Graph(
                            figure=fig,
                            config={"displayModeBar": False},
                            style={"height": "300px"},
                        ),
                    ],
                    style={
                        "border": "1px solid #f8f9fa",
                        "padding": "10px",
                        "backgroundColor": "#212529",
                    },
                ),
                width=3,
            )
        )

    return [dbc.Row(graph_divs, className="g-2")]
